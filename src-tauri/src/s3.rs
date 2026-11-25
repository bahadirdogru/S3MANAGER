//! S3-compatible storage client.

use std::collections::HashMap;
use std::time::Duration;

use aws_sdk_s3::config::retry::RetryConfig;
use aws_sdk_s3::config::timeout::TimeoutConfig;
use aws_sdk_s3::config::{
    BehaviorVersion, Credentials as AwsCredentials, Region, RequestChecksumCalculation,
    ResponseChecksumValidation,
};
use aws_sdk_s3::presigning::PresigningConfig;
use aws_sdk_s3::primitives::{ByteStream, DateTime};
use aws_sdk_s3::types::{Delete, MetadataDirective, ObjectCannedAcl, ObjectIdentifier, Permission, Type};
use aws_sdk_s3::Client;
use serde::{Deserialize, Serialize};

use crate::config::Credentials;
use crate::error::{build_err, s3, AppError, AppResult};

const ALL_USERS_URI: &str = "http://acs.amazonaws.com/groups/global/AllUsers";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ItemKind {
    Folder,
    File,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Item {
    pub name: String,
    pub path: String,
    pub kind: ItemKind,
    #[serde(default)]
    pub size: u64,
    /// Unix seconds
    #[serde(default)]
    pub modified: Option<i64>,
    #[serde(default)]
    pub etag: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ListPage {
    pub prefix: String,
    pub items: Vec<Item>,
    pub next_token: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteObject {
    pub key: String,
    pub size: u64,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ObjectInfo {
    pub key: String,
    pub content_type: String,
    pub cache_control: String,
    pub content_disposition: String,
    pub content_length: u64,
    pub last_modified: Option<i64>,
    pub etag: String,
    pub metadata: HashMap<String, String>,
    pub acl: Acl,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MetadataUpdate {
    pub content_type: String,
    pub cache_control: String,
    pub content_disposition: String,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Acl {
    Private,
    PublicRead,
}

impl Acl {
    pub fn canned(self) -> ObjectCannedAcl {
        match self {
            Acl::Private => ObjectCannedAcl::Private,
            Acl::PublicRead => ObjectCannedAcl::PublicRead,
        }
    }
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct MultipartInfo {
    pub key: String,
    pub upload_id: String,
    pub initiated: Option<i64>,
}

pub struct Spaces {
    pub client: Client,
    pub bucket: String,
}

pub fn norm(key: &str) -> &str {
    key.trim_start_matches('/')
}

pub fn as_prefix(p: &str) -> String {
    let p = norm(p);
    if p.is_empty() || p.ends_with('/') { p.to_string() } else { format!("{p}/") }
}

fn secs(dt: Option<&DateTime>) -> Option<i64> {
    dt.map(|d| d.secs())
}

fn base_name(path: &str) -> String {
    path.trim_end_matches('/').rsplit('/').next().unwrap_or(path).to_string()
}

/// Percent-encodes a key for the `x-amz-copy-source` header (keeps `/`).
fn encode_key(key: &str) -> String {
    let mut out = String::with_capacity(key.len());
    for b in key.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' | b'/' => out.push(b as char),
            _ => out.push_str(&format!("%{b:02X}")),
        }
    }
    out
}

impl Spaces {
    pub fn new(creds: Credentials) -> Self {
        let conf = aws_sdk_s3::config::Builder::new()
            .behavior_version(BehaviorVersion::latest())
            .region(Region::new(creds.region.clone()))
            .endpoint_url(creds.endpoint.trim_end_matches('/'))
            .credentials_provider(AwsCredentials::new(&creds.key, &creds.secret, None, None, "s3manager"))
            .force_path_style(creds.path_style)
            // Many S3-compatible services (Spaces, MinIO, R2…) reject the newer default
            // CRC checksums; only send them when an operation requires it.
            .request_checksum_calculation(RequestChecksumCalculation::WhenRequired)
            .response_checksum_validation(ResponseChecksumValidation::WhenRequired)
            .retry_config(RetryConfig::standard().with_max_attempts(3))
            .timeout_config(
                TimeoutConfig::builder()
                    .connect_timeout(Duration::from_secs(60))
                    .read_timeout(Duration::from_secs(300))
                    .build(),
            )
            .build();
        Spaces { client: Client::from_conf(conf), bucket: creds.bucket }
    }

    fn copy_source(&self, key: &str) -> String {
        format!("{}/{}", self.bucket, encode_key(norm(key)))
    }

    pub async fn test_connection(&self) -> AppResult<()> {
        self.client
            .head_bucket()
            .bucket(&self.bucket)
            .send()
            .await
            .map_err(s3("Bağlantı hatası"))?;
        Ok(())
    }

    /// One page of a folder. `search` narrows the listing server-side to names
    /// starting with it (S3 prefix semantics).
    pub async fn list_page(&self, prefix: &str, search: &str, token: Option<String>, max_keys: i32) -> AppResult<ListPage> {
        let prefix = as_prefix(prefix);
        let out = self
            .client
            .list_objects_v2()
            .bucket(&self.bucket)
            .prefix(format!("{prefix}{search}"))
            .delimiter("/")
            .max_keys(max_keys)
            .set_continuation_token(token)
            .send()
            .await
            .map_err(s3("Dosyalar listelenirken hata"))?;

        let mut items = Vec::new();
        for cp in out.common_prefixes() {
            let Some(p) = cp.prefix() else { continue };
            let p = norm(p);
            if p == prefix || p.is_empty() {
                continue;
            }
            let name = base_name(p);
            items.push(Item {
                name: if name.trim().is_empty() { p.trim_end_matches('/').to_string() } else { name },
                path: p.to_string(),
                kind: ItemKind::Folder,
                size: 0,
                modified: None,
                etag: None,
            });
        }
        for o in out.contents() {
            let Some(key) = o.key().map(norm) else { continue };
            if key.is_empty() || key.ends_with('/') {
                continue;
            }
            items.push(Item {
                name: base_name(key),
                path: key.to_string(),
                kind: ItemKind::File,
                size: o.size().unwrap_or(0).max(0) as u64,
                modified: secs(o.last_modified()),
                etag: o.e_tag().map(|e| e.trim_matches('"').to_string()),
            });
        }
        let next_token = if out.is_truncated().unwrap_or(false) {
            out.next_continuation_token().map(String::from)
        } else {
            None
        };
        Ok(ListPage { prefix, items, next_token })
    }

    /// Every object under `prefix` (recursive). Includes folder markers when `markers`.
    pub async fn list_all(&self, prefix: &str, markers: bool) -> AppResult<Vec<RemoteObject>> {
        let prefix = as_prefix(prefix);
        let mut pages = self
            .client
            .list_objects_v2()
            .bucket(&self.bucket)
            .prefix(&prefix)
            .into_paginator()
            .send();
        let mut out = Vec::new();
        while let Some(page) = pages.next().await {
            let page = page.map_err(s3("Liste hatası"))?;
            for o in page.contents() {
                let Some(key) = o.key() else { continue };
                if !markers && key.ends_with('/') {
                    continue;
                }
                out.push(RemoteObject { key: key.to_string(), size: o.size().unwrap_or(0).max(0) as u64 });
            }
        }
        Ok(out)
    }

    pub async fn get_acl(&self, key: &str) -> Acl {
        let Ok(resp) = self.client.get_object_acl().bucket(&self.bucket).key(norm(key)).send().await else {
            return Acl::Private;
        };
        let public = resp.grants().iter().any(|g| {
            g.permission() == Some(&Permission::Read)
                && g.grantee().is_some_and(|ge| ge.r#type() == &Type::Group && ge.uri() == Some(ALL_USERS_URI))
        });
        if public { Acl::PublicRead } else { Acl::Private }
    }

    pub async fn put_acl(&self, key: &str, acl: Acl) -> AppResult<()> {
        self.client
            .put_object_acl()
            .bucket(&self.bucket)
            .key(norm(key))
            .acl(acl.canned())
            .send()
            .await
            .map_err(s3("ACL güncelleme hatası"))?;
        Ok(())
    }

    pub async fn head(&self, key: &str) -> AppResult<ObjectInfo> {
        let key = norm(key);
        let r = self
            .client
            .head_object()
            .bucket(&self.bucket)
            .key(key)
            .send()
            .await
            .map_err(s3("Metadata okuma hatası"))?;
        Ok(ObjectInfo {
            key: key.to_string(),
            content_type: r.content_type().unwrap_or_default().to_string(),
            cache_control: r.cache_control().unwrap_or_default().to_string(),
            content_disposition: r.content_disposition().unwrap_or_default().to_string(),
            content_length: r.content_length().unwrap_or(0).max(0) as u64,
            last_modified: secs(r.last_modified()),
            etag: r.e_tag().unwrap_or_default().trim_matches('"').to_string(),
            metadata: r.metadata().cloned().unwrap_or_default(),
            acl: self.get_acl(key).await,
        })
    }

    /// Replaces metadata via copy-in-place. Keeps the object's current ACL,
    /// which a plain REPLACE copy would otherwise reset to private.
    pub async fn update_metadata(&self, key: &str, m: MetadataUpdate) -> AppResult<()> {
        let key = norm(key);
        let acl = self.get_acl(key).await;
        let opt = |s: String| Some(s.trim().to_string()).filter(|v| !v.is_empty());
        self.client
            .copy_object()
            .bucket(&self.bucket)
            .key(key)
            .copy_source(self.copy_source(key))
            .metadata_directive(MetadataDirective::Replace)
            .set_content_type(opt(m.content_type))
            .set_cache_control(opt(m.cache_control))
            .set_content_disposition(opt(m.content_disposition))
            .set_metadata(Some(m.metadata))
            .acl(acl.canned())
            .send()
            .await
            .map_err(s3("Metadata güncelleme hatası"))?;
        Ok(())
    }

    /// First `max_bytes` of an object plus its Content-Type.
    pub async fn read_head_bytes(&self, key: &str, max_bytes: u64) -> AppResult<(Vec<u8>, Option<String>, u64)> {
        let r = self
            .client
            .get_object()
            .bucket(&self.bucket)
            .key(norm(key))
            .range(format!("bytes=0-{}", max_bytes.saturating_sub(1)))
            .send()
            .await
            .map_err(s3("Dosya okuma hatası"))?;
        let ct = r.content_type().map(String::from);
        let total = r
            .content_range()
            .and_then(|cr| cr.rsplit('/').next())
            .and_then(|n| n.parse().ok())
            .unwrap_or_else(|| r.content_length().unwrap_or(0).max(0) as u64);
        let bytes = r
            .body
            .collect()
            .await
            .map_err(|e| AppError::msg(format!("Dosya okuma hatası: {e}")))?
            .into_bytes()
            .to_vec();
        Ok((bytes, ct, total))
    }

    pub async fn create_folder(&self, path: &str) -> AppResult<()> {
        self.client
            .put_object()
            .bucket(&self.bucket)
            .key(as_prefix(path))
            .body(ByteStream::from_static(b""))
            .acl(ObjectCannedAcl::Private)
            .send()
            .await
            .map_err(s3("Klasör oluşturulurken hata"))?;
        Ok(())
    }

    /// Deletes keys in chunks of 1000. Falls back to one-by-one deletes when the
    /// service rejects the batch call (some S3-compatibles lack DeleteObjects).
    pub async fn delete_keys(&self, keys: Vec<String>) -> AppResult<usize> {
        let mut deleted = 0;
        for chunk in keys.chunks(1000) {
            let ids = chunk
                .iter()
                .map(|k| ObjectIdentifier::builder().key(norm(k)).build().map_err(build_err))
                .collect::<AppResult<Vec<_>>>()?;
            let delete = Delete::builder().set_objects(Some(ids)).quiet(true).build().map_err(build_err)?;
            let batch = self.client.delete_objects().bucket(&self.bucket).delete(delete).send().await;
            match batch {
                Ok(out) => {
                    if let Some(e) = out.errors().first() {
                        return Err(AppError::msg(format!(
                            "Silme hatası: {} ({})",
                            e.key().unwrap_or_default(),
                            e.code().unwrap_or_default()
                        )));
                    }
                }
                Err(e) => {
                    log::warn!("delete_objects başarısız, tek tek siliniyor: {e}");
                    for k in chunk {
                        self.client
                            .delete_object()
                            .bucket(&self.bucket)
                            .key(norm(k))
                            .send()
                            .await
                            .map_err(s3("Silme hatası"))?;
                    }
                }
            }
            deleted += chunk.len();
        }
        Ok(deleted)
    }

    pub async fn delete_items(&self, items: &[Item]) -> AppResult<usize> {
        let mut keys = Vec::new();
        for it in items {
            match it.kind {
                ItemKind::File => keys.push(norm(&it.path).to_string()),
                ItemKind::Folder => {
                    let prefix = as_prefix(&it.path);
                    keys.extend(self.list_all(&prefix, true).await?.into_iter().map(|o| o.key));
                    // The marker may not show up in listings on every service.
                    if !keys.contains(&prefix) {
                        keys.push(prefix);
                    }
                }
            }
        }
        self.delete_keys(keys).await
    }

    pub async fn copy_object(&self, src: &str, dest: &str) -> AppResult<()> {
        let acl = self.get_acl(src).await;
        self.client
            .copy_object()
            .bucket(&self.bucket)
            .key(norm(dest))
            .copy_source(self.copy_source(src))
            .acl(acl.canned())
            .send()
            .await
            .map_err(s3("Kopyalama hatası"))?;
        Ok(())
    }

    pub async fn copy_folder(&self, src: &str, dest: &str) -> AppResult<()> {
        let (src, dest) = (as_prefix(src), as_prefix(dest));
        if src == dest {
            return Err(AppError::msg("Kaynak ve hedef aynı olamaz"));
        }
        if dest.starts_with(&src) {
            return Err(AppError::msg("Klasör kendi alt klasörüne kopyalanamaz"));
        }
        let objects = self.list_all(&src, true).await?;
        let has_marker = objects.iter().any(|o| o.key == src);
        for o in objects {
            let rel = &o.key[src.len()..];
            self.copy_object(&o.key, &format!("{dest}{rel}")).await?;
        }
        if !has_marker {
            self.create_folder(&dest).await?;
        }
        Ok(())
    }

    pub async fn move_object(&self, src: &str, dest: &str) -> AppResult<()> {
        if norm(src) == norm(dest) {
            return Ok(());
        }
        self.copy_object(src, dest).await?;
        self.delete_keys(vec![src.to_string()]).await?;
        Ok(())
    }

    pub async fn move_folder(&self, src: &str, dest: &str) -> AppResult<()> {
        if as_prefix(src) == as_prefix(dest) {
            return Ok(());
        }
        self.copy_folder(src, dest).await?;
        self.delete_items(&[Item {
            name: String::new(),
            path: src.to_string(),
            kind: ItemKind::Folder,
            size: 0,
            modified: None,
            etag: None,
        }])
        .await?;
        Ok(())
    }

    pub async fn rename(&self, item: &Item, new_name: &str) -> AppResult<String> {
        let path = norm(&item.path).trim_end_matches('/');
        let parent = path.rsplit_once('/').map(|(p, _)| format!("{p}/")).unwrap_or_default();
        match item.kind {
            ItemKind::File => {
                let dest = format!("{parent}{new_name}");
                self.move_object(path, &dest).await?;
                Ok(dest)
            }
            ItemKind::Folder => {
                let dest = format!("{parent}{new_name}/");
                self.move_folder(path, &dest).await?;
                Ok(dest)
            }
        }
    }

    pub async fn presign(&self, key: &str, seconds: u64) -> AppResult<String> {
        let cfg = PresigningConfig::expires_in(Duration::from_secs(seconds))
            .map_err(|e| AppError::msg(format!("Presigned URL hatası: {e}")))?;
        let req = self
            .client
            .get_object()
            .bucket(&self.bucket)
            .key(norm(key))
            .presigned(cfg)
            .await
            .map_err(s3("Presigned URL oluşturulurken hata"))?;
        Ok(req.uri().to_string())
    }

    pub async fn list_multipart(&self, prefix: &str) -> AppResult<Vec<MultipartInfo>> {
        let mut out = Vec::new();
        let (mut key_marker, mut id_marker) = (None, None);
        loop {
            let r = self
                .client
                .list_multipart_uploads()
                .bucket(&self.bucket)
                .prefix(norm(prefix))
                .set_key_marker(key_marker.take())
                .set_upload_id_marker(id_marker.take())
                .send()
                .await
                .map_err(s3("Multipart listeleme hatası"))?;
            for u in r.uploads() {
                out.push(MultipartInfo {
                    key: u.key().unwrap_or_default().to_string(),
                    upload_id: u.upload_id().unwrap_or_default().to_string(),
                    initiated: secs(u.initiated()),
                });
            }
            if !r.is_truncated().unwrap_or(false) {
                break;
            }
            key_marker = r.next_key_marker().map(String::from);
            id_marker = r.next_upload_id_marker().map(String::from);
            if key_marker.is_none() && id_marker.is_none() {
                break;
            }
        }
        Ok(out)
    }

    pub async fn abort_multipart(&self, key: &str, upload_id: &str) -> AppResult<()> {
        self.client
            .abort_multipart_upload()
            .bucket(&self.bucket)
            .key(norm(key))
            .upload_id(upload_id)
            .send()
            .await
            .map_err(s3("Multipart iptal hatası"))?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn prefix_normalization() {
        assert_eq!(as_prefix(""), "");
        assert_eq!(as_prefix("/a/b"), "a/b/");
        assert_eq!(as_prefix("a/"), "a/");
    }

    #[test]
    fn copy_source_encoding() {
        assert_eq!(encode_key("a b/ş+1.txt"), "a%20b/%C5%9F%2B1.txt");
    }

    #[test]
    fn names() {
        assert_eq!(base_name("a/b/"), "b");
        assert_eq!(base_name("a/b/c.txt"), "c.txt");
    }
}

/// Live round-trip against a real S3-compatible endpoint. Run with e.g. MinIO:
/// `S3M_IT_ENDPOINT=http://localhost:9000 S3M_IT_KEY=minioadmin S3M_IT_SECRET=minioadmin \
///  S3M_IT_BUCKET=s3m-test S3M_IT_PATH_STYLE=1 cargo test -- --ignored live_round_trip`
#[cfg(test)]
pub(crate) mod live {
    use super::*;

    pub(crate) fn spaces() -> Option<Spaces> {
        let env = |k: &str| std::env::var(k).ok();
        Some(Spaces::new(Credentials {
            endpoint: env("S3M_IT_ENDPOINT")?,
            key: env("S3M_IT_KEY")?,
            secret: env("S3M_IT_SECRET")?,
            bucket: env("S3M_IT_BUCKET")?,
            region: env("S3M_IT_REGION").unwrap_or_else(|| "us-east-1".into()),
            path_style: env("S3M_IT_PATH_STYLE").is_some(),
        }))
    }

    async fn put(s: &Spaces, key: &str, body: &'static [u8]) {
        s.client.put_object().bucket(&s.bucket).key(key).body(ByteStream::from_static(body)).send().await.unwrap();
    }

    fn names(page: &ListPage) -> Vec<String> {
        let mut v: Vec<_> = page.items.iter().map(|i| i.name.clone()).collect();
        v.sort();
        v
    }

    #[tokio::test]
    #[ignore = "needs S3M_IT_* env vars and a live endpoint"]
    async fn live_round_trip() {
        let Some(s) = spaces() else { panic!("S3M_IT_* not set") };
        let root = format!("it-{}/", uuid::Uuid::new_v4());
        s.test_connection().await.unwrap();

        s.create_folder(&format!("{root}docs")).await.unwrap();
        put(&s, &format!("{root}docs/a b.txt"), b"hello").await;
        put(&s, &format!("{root}docs/sub/ş.txt"), b"world").await;
        put(&s, &format!("{root}top.txt"), b"top").await;

        let page = s.list_page(&root, "", None, 100).await.unwrap();
        assert_eq!(names(&page), vec!["docs", "top.txt"]);
        let filtered = s.list_page(&root, "to", None, 100).await.unwrap();
        assert_eq!(names(&filtered), vec!["top.txt"]);

        // Paging with a tiny page size must still reach every entry. (MinIO wrongly
        // reports IsTruncated=false for max-keys=1 when a folder marker exists, so use 2.)
        put(&s, &format!("{root}docs/c.txt"), b"c").await;
        let (mut seen, mut pages, mut token) = (0, 0, None);
        loop {
            let p = s.list_page(&format!("{root}docs/"), "", token, 2).await.unwrap();
            seen += p.items.len();
            pages += 1;
            token = p.next_token;
            if token.is_none() {
                break;
            }
        }
        assert!(pages > 1, "expected several pages");
        assert_eq!(seen, 3); // "a b.txt", "c.txt", "sub/"

        s.copy_folder(&format!("{root}docs/"), &format!("{root}copy/")).await.unwrap();
        let all = s.list_all(&format!("{root}copy/"), false).await.unwrap();
        assert_eq!(all.len(), 3);

        let folder = Item {
            name: "copy".into(),
            path: format!("{root}copy/"),
            kind: ItemKind::Folder,
            size: 0,
            modified: None,
            etag: None,
        };
        let renamed = s.rename(&folder, "moved").await.unwrap();
        assert_eq!(renamed, format!("{root}moved/"));
        assert!(s.list_all(&format!("{root}copy/"), true).await.unwrap().is_empty());

        let (bytes, _, total) = s.read_head_bytes(&format!("{root}moved/a b.txt"), 3).await.unwrap();
        assert_eq!((bytes.as_slice(), total), (&b"hel"[..], 5));

        s.update_metadata(
            &format!("{root}top.txt"),
            MetadataUpdate {
                content_type: "text/plain; charset=utf-8".into(),
                cache_control: "max-age=60".into(),
                content_disposition: String::new(),
                metadata: HashMap::from([("owner".into(), "it".into())]),
            },
        )
        .await
        .unwrap();
        let info = s.head(&format!("{root}top.txt")).await.unwrap();
        assert_eq!(info.cache_control, "max-age=60");
        assert_eq!(info.metadata.get("owner").map(String::as_str), Some("it"));

        let url = s.presign(&format!("{root}top.txt"), 3600).await.unwrap();
        assert!(url.contains("X-Amz-Signature"));

        let n = s
            .delete_items(&[Item { name: String::new(), path: root.clone(), kind: ItemKind::Folder, size: 0, modified: None, etag: None }])
            .await
            .unwrap();
        assert!(n >= 7);
        assert!(s.list_all(&root, true).await.unwrap().is_empty());
    }
}
