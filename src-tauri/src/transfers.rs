//! Upload/download queue with progress events and cancellation.


use std::collections::HashMap;
use std::path::{Component, Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::Instant;

use aws_sdk_s3::primitives::ByteStream;
use aws_sdk_s3::types::{CompletedMultipartUpload, CompletedPart};
use futures::{StreamExt, TryStreamExt};
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter};

/// Where progress events go: the Tauri window in the app, a collector in tests.
pub type Sink = Arc<dyn Fn(&TransferEvent) + Send + Sync>;

pub fn app_sink(app: AppHandle) -> Sink {
    Arc::new(move |ev| {
        let _ = app.emit(TRANSFER_EVENT, ev);
    })
}
use tokio::io::{AsyncReadExt, AsyncSeekExt, AsyncWriteExt};
use tokio::sync::Semaphore;
use tokio_util::sync::CancellationToken;

use crate::error::{s3, AppError, AppResult};
use crate::metadata::{build_upload_headers, UploadMetadataSettings};
use crate::s3::{as_prefix, norm, Acl, Item, ItemKind, Spaces};

pub const TRANSFER_EVENT: &str = "transfer";
/// Files above this size go through multipart upload (per-part progress, resumable abort).
pub const MULTIPART_THRESHOLD: u64 = 16 * 1024 * 1024;
const MIN_PART: u64 = 8 * 1024 * 1024;
const MAX_PARTS: u64 = 10_000;
const PART_CONCURRENCY: usize = 4;
const PARALLEL_FILES: usize = 3;
const EMIT_INTERVAL_MS: u128 = 150;

#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Direction {
    Upload,
    Download,
}

#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum Status {
    Queued,
    Running,
    Done,
    Error,
    Cancelled,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TransferEvent {
    pub id: String,
    pub direction: Direction,
    pub name: String,
    pub remote_key: String,
    pub local_path: String,
    pub total: u64,
    pub transferred: u64,
    pub status: Status,
    pub error: Option<String>,
    /// bytes per second
    pub speed: f64,
    pub multipart: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UploadRequest {
    pub local_path: String,
    pub remote_key: String,
    pub size: u64,
}

struct Reporter {
    sink: Sink,
    ev: TransferEvent,
    started: Instant,
    last_emit: Option<Instant>,
}

impl Reporter {
    fn emit(&mut self) {
        let elapsed = self.started.elapsed().as_secs_f64();
        if elapsed > 0.0 {
            self.ev.speed = self.ev.transferred as f64 / elapsed;
        }
        self.last_emit = Some(Instant::now());
        (self.sink)(&self.ev);
    }

    fn add(&mut self, n: u64) {
        self.ev.transferred += n;
        if self.last_emit.is_none_or(|t| t.elapsed().as_millis() >= EMIT_INTERVAL_MS) {
            self.emit();
        }
    }

    fn set(&mut self, status: Status, error: Option<String>) {
        if status == Status::Running {
            self.started = Instant::now();
        }
        self.ev.status = status;
        self.ev.error = error;
        self.emit();
    }

    fn finish(&mut self, r: AppResult<()>) {
        match r {
            Ok(()) => {
                self.ev.transferred = self.ev.total;
                self.set(Status::Done, None);
            }
            Err(AppError::Cancelled) => self.set(Status::Cancelled, None),
            Err(e) => {
                log::error!("{:?} {} başarısız: {e}", self.ev.direction, self.ev.remote_key);
                self.set(Status::Error, Some(e.to_string()));
            }
        }
    }
}

type Shared = Arc<Mutex<Reporter>>;

fn report(r: &Shared, f: impl FnOnce(&mut Reporter)) {
    if let Ok(mut g) = r.lock() {
        f(&mut g);
    }
}

pub struct TransferManager {
    tokens: Mutex<HashMap<String, CancellationToken>>,
    uploads: Arc<Semaphore>,
    downloads: Arc<Semaphore>,
}

impl Default for TransferManager {
    fn default() -> Self {
        Self {
            tokens: Mutex::default(),
            uploads: Arc::new(Semaphore::new(PARALLEL_FILES)),
            downloads: Arc::new(Semaphore::new(PARALLEL_FILES)),
        }
    }
}

impl TransferManager {
    fn register(&self) -> (String, CancellationToken) {
        let id = uuid::Uuid::new_v4().to_string();
        let token = CancellationToken::new();
        self.tokens.lock().unwrap().insert(id.clone(), token.clone());
        (id, token)
    }

    fn unregister(&self, id: &str) {
        self.tokens.lock().unwrap().remove(id);
    }

    pub fn cancel(&self, id: &str) {
        if let Some(t) = self.tokens.lock().unwrap().get(id) {
            t.cancel();
        }
    }

    pub fn cancel_all(&self) {
        for t in self.tokens.lock().unwrap().values() {
            t.cancel();
        }
    }

    pub fn active_count(&self) -> usize {
        self.tokens.lock().unwrap().len()
    }

    pub fn start_uploads(
        self: &Arc<Self>,
        sink: Sink,
        spaces: Arc<Spaces>,
        reqs: Vec<UploadRequest>,
        acl: Acl,
        meta: UploadMetadataSettings,
    ) -> Vec<TransferEvent> {
        let meta = Arc::new(meta);
        reqs.into_iter()
            .map(|req| {
                let (id, token) = self.register();
                let ev = TransferEvent {
                    id: id.clone(),
                    direction: Direction::Upload,
                    name: req.remote_key.rsplit('/').next().unwrap_or(&req.remote_key).to_string(),
                    remote_key: norm(&req.remote_key).to_string(),
                    local_path: req.local_path.clone(),
                    total: req.size,
                    transferred: 0,
                    status: Status::Queued,
                    error: None,
                    speed: 0.0,
                    multipart: req.size > MULTIPART_THRESHOLD,
                };
                let rep = Arc::new(Mutex::new(Reporter {
                    sink: sink.clone(),
                    ev: ev.clone(),
                    started: Instant::now(),
                    last_emit: None,
                }));
                let (mgr, spaces, meta, sem) = (self.clone(), spaces.clone(), meta.clone(), self.uploads.clone());
                tauri::async_runtime::spawn(async move {
                    let result = async {
                        let _permit = tokio::select! {
                            p = sem.acquire_owned() => p.map_err(|_| AppError::Cancelled)?,
                            _ = token.cancelled() => return Err(AppError::Cancelled),
                        };
                        report(&rep, |r| r.set(Status::Running, None));
                        upload_one(&spaces, &req, acl, &meta, &rep, &token).await
                    }
                    .await;
                    report(&rep, |r| r.finish(result));
                    mgr.unregister(&id);
                });
                ev
            })
            .collect()
    }

    pub async fn start_downloads(
        self: &Arc<Self>,
        sink: Sink,
        spaces: Arc<Spaces>,
        items: Vec<Item>,
        dest_dir: PathBuf,
    ) -> AppResult<Vec<TransferEvent>> {
        let mut jobs: Vec<(String, u64, PathBuf)> = Vec::new();
        for it in &items {
            match it.kind {
                ItemKind::File => jobs.push((norm(&it.path).to_string(), it.size, dest_dir.join(safe_name(&it.name)))),
                ItemKind::Folder => {
                    let prefix = as_prefix(&it.path);
                    let root = dest_dir.join(safe_name(it.name.trim_end_matches('/')));
                    for o in spaces.list_all(&prefix, false).await? {
                        let rel = safe_relative(&o.key[prefix.len()..]);
                        if rel.as_os_str().is_empty() {
                            continue;
                        }
                        jobs.push((o.key, o.size, root.join(rel)));
                    }
                }
            }
        }

        Ok(jobs
            .into_iter()
            .map(|(key, size, local)| {
                let (id, token) = self.register();
                let ev = TransferEvent {
                    id: id.clone(),
                    direction: Direction::Download,
                    name: key.rsplit('/').next().unwrap_or(&key).to_string(),
                    remote_key: key.clone(),
                    local_path: local.to_string_lossy().into_owned(),
                    total: size,
                    transferred: 0,
                    status: Status::Queued,
                    error: None,
                    speed: 0.0,
                    multipart: false,
                };
                let rep = Arc::new(Mutex::new(Reporter {
                    sink: sink.clone(),
                    ev: ev.clone(),
                    started: Instant::now(),
                    last_emit: None,
                }));
                let (mgr, spaces, sem) = (self.clone(), spaces.clone(), self.downloads.clone());
                tauri::async_runtime::spawn(async move {
                    let result = async {
                        let _permit = tokio::select! {
                            p = sem.acquire_owned() => p.map_err(|_| AppError::Cancelled)?,
                            _ = token.cancelled() => return Err(AppError::Cancelled),
                        };
                        report(&rep, |r| r.set(Status::Running, None));
                        download_one(&spaces, &key, &local, &rep, &token).await
                    }
                    .await;
                    report(&rep, |r| r.finish(result));
                    mgr.unregister(&id);
                });
                ev
            })
            .collect())
    }
}

/// Keeps a single path component free of separators and traversal.
fn safe_name(name: &str) -> String {
    let n: String = name.chars().map(|c| if matches!(c, '/' | '\\') { '_' } else { c }).collect();
    if n.is_empty() || n == "." || n == ".." { "_".into() } else { n }
}

/// Turns an object-key suffix into a relative path, dropping `..`, `.` and roots
/// so a hostile key can never write outside the chosen folder.
fn safe_relative(rel: &str) -> PathBuf {
    rel.split('/')
        .filter(|p| !p.is_empty() && *p != "." && *p != "..")
        .map(|p| safe_name(p.trim_end_matches(':')))
        .filter(|p| Path::new(p).components().all(|c| matches!(c, Component::Normal(_))))
        .collect()
}

/// Expands selected local files/folders into upload requests under `prefix`.
/// A folder `photos` becomes `prefix/photos/<relative path>`.
pub fn expand_local(paths: &[String], prefix: &str) -> AppResult<Vec<UploadRequest>> {
    let prefix = as_prefix(prefix);
    let mut out = Vec::new();
    for p in paths {
        let path = PathBuf::from(p);
        let meta = std::fs::metadata(&path)?;
        let name = path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
        if meta.is_dir() {
            walk(&path, &format!("{prefix}{name}/"), &mut out)?;
        } else {
            out.push(UploadRequest { local_path: p.clone(), remote_key: format!("{prefix}{name}"), size: meta.len() });
        }
    }
    Ok(out)
}

fn walk(dir: &Path, key_prefix: &str, out: &mut Vec<UploadRequest>) -> AppResult<()> {
    let mut entries: Vec<_> = std::fs::read_dir(dir)?.filter_map(Result::ok).collect();
    entries.sort_by_key(|e| e.file_name());
    for e in entries {
        let ft = e.file_type()?;
        let name = e.file_name().to_string_lossy().into_owned();
        if ft.is_symlink() {
            continue; // avoid loops and surprises
        }
        if ft.is_dir() {
            walk(&e.path(), &format!("{key_prefix}{name}/"), out)?;
        } else if ft.is_file() {
            out.push(UploadRequest {
                local_path: e.path().to_string_lossy().into_owned(),
                remote_key: format!("{key_prefix}{name}"),
                size: e.metadata()?.len(),
            });
        }
    }
    Ok(())
}

fn part_size(total: u64) -> u64 {
    const MIB: u64 = 1024 * 1024;
    let needed = total.div_ceil(MAX_PARTS);
    needed.max(MIN_PART).div_ceil(MIB) * MIB
}

async fn upload_one(
    spaces: &Spaces,
    req: &UploadRequest,
    acl: Acl,
    meta: &UploadMetadataSettings,
    rep: &Shared,
    token: &CancellationToken,
) -> AppResult<()> {
    let key = norm(&req.remote_key).to_string();
    let size = tokio::fs::metadata(&req.local_path).await?.len();
    report(rep, |r| r.ev.total = size);
    let h = build_upload_headers(&req.local_path, &key, meta);

    if size <= MULTIPART_THRESHOLD {
        let body = ByteStream::from_path(&req.local_path)
            .await
            .map_err(|e| AppError::msg(format!("Dosya okunamadı: {e}")))?;
        let send = spaces
            .client
            .put_object()
            .bucket(&spaces.bucket)
            .key(&key)
            .body(body)
            .acl(acl.canned())
            .set_content_type(h.content_type)
            .set_content_disposition(h.content_disposition)
            .set_cache_control(h.cache_control)
            .send();
        tokio::select! {
            r = send => { r.map_err(s3("Yükleme hatası"))?; }
            _ = token.cancelled() => return Err(AppError::Cancelled),
        }
        return Ok(());
    }

    let created = spaces
        .client
        .create_multipart_upload()
        .bucket(&spaces.bucket)
        .key(&key)
        .acl(acl.canned())
        .set_content_type(h.content_type)
        .set_content_disposition(h.content_disposition)
        .set_cache_control(h.cache_control)
        .send()
        .await
        .map_err(s3("Multipart başlatılamadı"))?;
    let upload_id = created.upload_id().ok_or_else(|| AppError::msg("UploadId alınamadı"))?.to_string();

    let result = tokio::select! {
        r = upload_parts(spaces, &key, &upload_id, &req.local_path, size, rep) => r,
        _ = token.cancelled() => Err(AppError::Cancelled),
    };

    match result {
        Ok(mut parts) => {
            parts.sort_by_key(|p| p.part_number());
            spaces
                .client
                .complete_multipart_upload()
                .bucket(&spaces.bucket)
                .key(&key)
                .upload_id(&upload_id)
                .multipart_upload(CompletedMultipartUpload::builder().set_parts(Some(parts)).build())
                .send()
                .await
                .map_err(s3("Multipart tamamlanamadı"))?;
            Ok(())
        }
        Err(e) => {
            // Don't leave orphaned parts that keep costing storage.
            if let Err(abort) = spaces.abort_multipart(&key, &upload_id).await {
                log::warn!("Multipart abort başarısız ({key}): {abort}");
            }
            Err(e)
        }
    }
}

async fn upload_parts(
    spaces: &Spaces,
    key: &str,
    upload_id: &str,
    local: &str,
    size: u64,
    rep: &Shared,
) -> AppResult<Vec<CompletedPart>> {
    let chunk = part_size(size);
    let count = size.div_ceil(chunk);
    futures::stream::iter(0..count)
        .map(|i| async move {
            let offset = i * chunk;
            let len = chunk.min(size - offset) as usize;
            let mut buf = vec![0u8; len];
            let mut f = tokio::fs::File::open(local).await?;
            f.seek(std::io::SeekFrom::Start(offset)).await?;
            f.read_exact(&mut buf).await?;
            let part_number = (i + 1) as i32;
            let out = spaces
                .client
                .upload_part()
                .bucket(&spaces.bucket)
                .key(key)
                .upload_id(upload_id)
                .part_number(part_number)
                .body(ByteStream::from(buf))
                .send()
                .await
                .map_err(s3("Parça yükleme hatası"))?;
            report(rep, |r| r.add(len as u64));
            Ok::<_, AppError>(
                CompletedPart::builder().set_e_tag(out.e_tag().map(String::from)).part_number(part_number).build(),
            )
        })
        .buffer_unordered(PART_CONCURRENCY)
        .try_collect()
        .await
}

async fn download_one(
    spaces: &Spaces,
    key: &str,
    local: &Path,
    rep: &Shared,
    token: &CancellationToken,
) -> AppResult<()> {
    if let Some(parent) = local.parent() {
        tokio::fs::create_dir_all(parent).await?;
    }
    let tmp = local.with_file_name(format!(
        "{}.part",
        local.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default()
    ));

    let result = async {
        let out = tokio::select! {
            r = spaces.client.get_object().bucket(&spaces.bucket).key(key).send() => r.map_err(s3("İndirme hatası"))?,
            _ = token.cancelled() => return Err(AppError::Cancelled),
        };
        if let Some(len) = out.content_length() {
            report(rep, |r| r.ev.total = len.max(0) as u64);
        }
        let mut body = out.body;
        let mut file = tokio::fs::File::create(&tmp).await?;
        loop {
            let next = tokio::select! {
                n = body.try_next() => n.map_err(|e| AppError::msg(format!("İndirme hatası: {e}")))?,
                _ = token.cancelled() => return Err(AppError::Cancelled),
            };
            let Some(bytes) = next else { break };
            file.write_all(&bytes).await?;
            report(rep, |r| r.add(bytes.len() as u64));
        }
        file.flush().await?;
        drop(file);
        tokio::fs::rename(&tmp, local).await?;
        Ok(())
    }
    .await;

    if result.is_err() {
        let _ = tokio::fs::remove_file(&tmp).await;
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn part_sizes() {
        assert_eq!(part_size(100 * 1024 * 1024), MIN_PART);
        // 200 GiB needs bigger parts to stay under 10k parts.
        let big = 200 * 1024 * 1024 * 1024u64;
        assert!(big.div_ceil(part_size(big)) <= MAX_PARTS);
    }

    #[test]
    fn traversal_is_stripped() {
        assert_eq!(safe_relative("../../etc/passwd"), PathBuf::from("etc/passwd"));
        assert_eq!(safe_relative("a//./b/c.txt"), PathBuf::from("a/b/c.txt"));
    }

    #[test]
    fn expands_folders() {
        let dir = std::env::temp_dir().join(format!("s3m-test-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(dir.join("sub")).unwrap();
        std::fs::write(dir.join("a.txt"), b"hi").unwrap();
        std::fs::write(dir.join("sub/b.txt"), b"hey").unwrap();
        let name = dir.file_name().unwrap().to_string_lossy().into_owned();
        let out = expand_local(&[dir.to_string_lossy().into_owned()], "up").unwrap();
        let keys: Vec<_> = out.iter().map(|r| r.remote_key.clone()).collect();
        assert_eq!(keys, vec![format!("up/{name}/a.txt"), format!("up/{name}/sub/b.txt")]);
        std::fs::remove_dir_all(dir).unwrap();
    }
}

/// Live upload/download/cancel against a real endpoint; same env vars as `s3::live`.
#[cfg(test)]
mod live {
    use super::*;
    use std::time::Duration;

    type Seen = Arc<Mutex<HashMap<String, TransferEvent>>>;

    fn collector() -> (Sink, Seen) {
        let seen: Seen = Arc::default();
        let s = seen.clone();
        (Arc::new(move |e| { s.lock().unwrap().insert(e.id.clone(), e.clone()); }), seen)
    }

    async fn wait_all(seen: &Seen, ids: &[String]) -> Vec<TransferEvent> {
        for _ in 0..600 {
            {
                let m = seen.lock().unwrap();
                let fin: Vec<_> = ids
                    .iter()
                    .filter_map(|id| m.get(id))
                    .filter(|e| matches!(e.status, Status::Done | Status::Error | Status::Cancelled))
                    .cloned()
                    .collect();
                if fin.len() == ids.len() {
                    return fin;
                }
            }
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
        panic!("transfers did not finish");
    }

    fn pattern(len: usize) -> Vec<u8> {
        (0..len).map(|i| (i * 31 % 251) as u8).collect()
    }

    #[tokio::test(flavor = "multi_thread")]
    #[ignore = "needs S3M_IT_* env vars and a live endpoint"]
    async fn live_transfers() {
        let spaces = Arc::new(crate::s3::live::spaces().expect("S3M_IT_* not set"));
        let mgr = Arc::new(TransferManager::default());
        let root = format!("it-tx-{}/", uuid::Uuid::new_v4());
        let local = std::env::temp_dir().join(format!("s3m-tx-{}", uuid::Uuid::new_v4()));
        let src = local.join("site");
        std::fs::create_dir_all(src.join("img")).unwrap();
        std::fs::write(src.join("index.html"), b"<h1>hi</h1>").unwrap();
        let big = pattern(40 * 1024 * 1024 + 123); // > threshold, 6 parts
        std::fs::write(src.join("img/big.bin"), &big).unwrap();

        // Upload a folder: small single PUT + multipart, public-read.
        let reqs = expand_local(&[src.to_string_lossy().into_owned()], &root).unwrap();
        assert_eq!(reqs.len(), 2);
        let (sink, seen) = collector();
        let evs = mgr.start_uploads(sink, spaces.clone(), reqs, Acl::PublicRead, UploadMetadataSettings::default());
        let ids: Vec<_> = evs.iter().map(|e| e.id.clone()).collect();
        for e in wait_all(&seen, &ids).await {
            assert_eq!(e.status, Status::Done, "{:?}", e.error);
            assert_eq!(e.transferred, e.total);
        }
        let html = spaces.head(&format!("{root}site/index.html")).await.unwrap();
        assert_eq!(html.content_type, "text/html; charset=utf-8");
        // MinIO accepts but ignores canned ACLs; set S3M_IT_ACL=1 on Spaces/AWS.
        let acl_supported = std::env::var("S3M_IT_ACL").is_ok();
        if acl_supported {
            assert_eq!(html.acl, Acl::PublicRead);
        }
        let bin = spaces.head(&format!("{root}site/img/big.bin")).await.unwrap();
        assert_eq!(bin.content_length, big.len() as u64);
        if acl_supported {
            assert_eq!(bin.acl, Acl::PublicRead);
        }
        assert!(bin.etag.ends_with("-6"), "multipart etag, got {}", bin.etag);
        assert!(spaces.list_multipart(&root).await.unwrap().is_empty());

        // Download the folder back and compare bytes.
        let dl = local.join("dl");
        let folder = Item { name: "site".into(), path: format!("{root}site/"), kind: ItemKind::Folder, size: 0, modified: None, etag: None };
        let (sink, seen) = collector();
        let evs = mgr.start_downloads(sink, spaces.clone(), vec![folder], dl.clone()).await.unwrap();
        let ids: Vec<_> = evs.iter().map(|e| e.id.clone()).collect();
        for e in wait_all(&seen, &ids).await {
            assert_eq!(e.status, Status::Done, "{:?}", e.error);
        }
        assert_eq!(std::fs::read(dl.join("site/img/big.bin")).unwrap(), big);
        assert_eq!(std::fs::read(dl.join("site/index.html")).unwrap(), b"<h1>hi</h1>");
        assert!(!dl.join("site/img/big.bin.part").exists());

        // Cancel a multipart upload mid-flight: no object, no orphaned parts.
        let huge = local.join("huge.bin");
        std::fs::write(&huge, pattern(200 * 1024 * 1024)).unwrap();
        let reqs = expand_local(&[huge.to_string_lossy().into_owned()], &root).unwrap();
        let (sink, seen) = collector();
        let id = mgr.start_uploads(sink, spaces.clone(), reqs, Acl::Private, UploadMetadataSettings::default())[0].id.clone();
        for _ in 0..200 {
            if seen.lock().unwrap().get(&id).is_some_and(|e| e.status == Status::Running) {
                break;
            }
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
        mgr.cancel(&id);
        let e = wait_all(&seen, std::slice::from_ref(&id)).await.remove(0);
        assert_eq!(e.status, Status::Cancelled);
        assert!(e.transferred < e.total);
        assert!(spaces.head(&format!("{root}huge.bin")).await.is_err());
        assert!(spaces.list_multipart(&root).await.unwrap().is_empty(), "multipart left behind");
        assert_eq!(mgr.active_count(), 0);

        let all = Item { name: String::new(), path: root.clone(), kind: ItemKind::Folder, size: 0, modified: None, etag: None };
        spaces.delete_items(&[all]).await.unwrap();
        std::fs::remove_dir_all(local).unwrap();
    }
}
