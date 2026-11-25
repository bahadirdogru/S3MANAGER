//! Tauri command surface used by the Svelte frontend (`src/lib/api.ts`).

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;

use base64::Engine;
use futures::StreamExt;
use serde::Serialize;
use tauri::{AppHandle, State};
use tokio::sync::RwLock;

use crate::config::{default_endpoint as endpoint_for, Credentials, Settings};
use crate::error::{AppError, AppResult};
use crate::metadata::{guess_content_type, is_text_mime, UploadMetadataSettings};
use crate::s3::{Acl, Item, ListPage, MetadataUpdate, MultipartInfo, ObjectInfo, Spaces};
use crate::transfers::{app_sink, expand_local, TransferEvent, TransferManager, UploadRequest};

const GITHUB_REPO: &str = "bahadirdogru/S3MANAGER";
const PREVIEW_TEXT_MAX: u64 = 256 * 1024;
const PREVIEW_IMAGE_MAX: u64 = 5 * 1024 * 1024;

pub struct AppState {
    pub settings: Settings,
    pub spaces: RwLock<Option<Arc<Spaces>>>,
    pub transfers: Arc<TransferManager>,
}

impl AppState {
    pub fn new() -> Self {
        Self { settings: Settings::new(), spaces: RwLock::new(None), transfers: Arc::default() }
    }

    async fn spaces(&self) -> AppResult<Arc<Spaces>> {
        self.spaces.read().await.clone().ok_or(AppError::NotConnected)
    }
}

type S<'a> = State<'a, AppState>;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Startup {
    credentials: Option<Credentials>,
    theme: String,
    version: String,
    config_dir: String,
}

#[tauri::command]
pub fn get_startup(state: S<'_>) -> Startup {
    Startup {
        credentials: state.settings.load_credentials(),
        theme: state.settings.load_theme(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        config_dir: state.settings.dir.to_string_lossy().into_owned(),
    }
}

#[tauri::command]
pub fn default_endpoint(region: String) -> String {
    endpoint_for(&region)
}

#[tauri::command]
pub async fn connect(state: S<'_>, credentials: Credentials, remember: bool) -> AppResult<()> {
    let spaces = Spaces::new(credentials.clone());
    spaces.test_connection().await?;
    if remember {
        state.settings.save_credentials(&credentials)?;
    }
    log::info!("Bağlandı: {} @ {}", credentials.bucket, credentials.endpoint);
    *state.spaces.write().await = Some(Arc::new(spaces));
    Ok(())
}

#[tauri::command]
pub async fn disconnect(state: S<'_>) -> AppResult<()> {
    state.transfers.cancel_all();
    *state.spaces.write().await = None;
    Ok(())
}

#[tauri::command]
pub async fn ping(state: S<'_>) -> AppResult<()> {
    state.spaces().await?.test_connection().await
}

#[tauri::command]
pub async fn list_page(
    state: S<'_>,
    prefix: String,
    search: Option<String>,
    token: Option<String>,
    max_keys: Option<i32>,
) -> AppResult<ListPage> {
    let search = search.unwrap_or_default();
    state.spaces().await?.list_page(&prefix, search.trim_start_matches('/'), token, max_keys.unwrap_or(200)).await
}

#[tauri::command]
pub async fn get_acls(state: S<'_>, keys: Vec<String>) -> AppResult<HashMap<String, Acl>> {
    let spaces = state.spaces().await?;
    let results = futures::stream::iter(keys)
        .map(|k| {
            let spaces = spaces.clone();
            async move {
                let acl = spaces.get_acl(&k).await;
                (k, acl)
            }
        })
        .buffer_unordered(8)
        .collect::<Vec<_>>()
        .await;
    Ok(results.into_iter().collect())
}

#[tauri::command]
pub async fn set_acl(state: S<'_>, keys: Vec<String>, acl: Acl) -> AppResult<()> {
    let spaces = state.spaces().await?;
    for k in keys {
        spaces.put_acl(&k, acl).await?;
    }
    Ok(())
}

#[tauri::command]
pub async fn object_info(state: S<'_>, key: String) -> AppResult<ObjectInfo> {
    state.spaces().await?.head(&key).await
}

#[tauri::command]
pub async fn update_metadata(state: S<'_>, key: String, update: MetadataUpdate) -> AppResult<()> {
    state.spaces().await?.update_metadata(&key, update).await
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase", tag = "kind")]
pub enum Preview {
    Image { mime: String, data_url: String, size: u64 },
    Text { mime: String, text: String, truncated: bool, size: u64 },
    Unsupported { mime: String, size: u64 },
}

#[tauri::command]
pub async fn preview(state: S<'_>, key: String, size: u64) -> AppResult<Preview> {
    let guessed = guess_content_type(&key, "");
    let base = guessed.split(';').next().unwrap_or("").to_string();
    let is_image = base.starts_with("image/");
    if !(is_image || is_text_mime(&base)) {
        return Ok(Preview::Unsupported { mime: base, size });
    }
    if is_image && size > PREVIEW_IMAGE_MAX {
        return Ok(Preview::Unsupported { mime: base, size });
    }
    let spaces = state.spaces().await?;
    let limit = if is_image { PREVIEW_IMAGE_MAX } else { PREVIEW_TEXT_MAX };
    let (bytes, ct, total) = spaces.read_head_bytes(&key, limit.max(1)).await?;
    let mime = ct.map(|c| c.split(';').next().unwrap_or("").trim().to_string()).filter(|c| !c.is_empty()).unwrap_or(base);
    if is_image {
        let data = base64::engine::general_purpose::STANDARD.encode(&bytes);
        Ok(Preview::Image { data_url: format!("data:{mime};base64,{data}"), mime, size: total })
    } else {
        Ok(Preview::Text {
            truncated: total > bytes.len() as u64,
            text: String::from_utf8_lossy(&bytes).into_owned(),
            mime,
            size: total,
        })
    }
}

#[tauri::command]
pub async fn create_folder(state: S<'_>, path: String) -> AppResult<()> {
    state.spaces().await?.create_folder(&path).await
}

#[tauri::command]
pub async fn delete_items(state: S<'_>, items: Vec<Item>) -> AppResult<usize> {
    state.spaces().await?.delete_items(&items).await
}

/// `dest` is the full destination key (file) or prefix (folder).
#[tauri::command]
pub async fn copy_item(state: S<'_>, item: Item, dest: String) -> AppResult<()> {
    let spaces = state.spaces().await?;
    match item.kind {
        crate::s3::ItemKind::File => spaces.copy_object(&item.path, &dest).await,
        crate::s3::ItemKind::Folder => spaces.copy_folder(&item.path, &dest).await,
    }
}

#[tauri::command]
pub async fn move_item(state: S<'_>, item: Item, dest: String) -> AppResult<()> {
    let spaces = state.spaces().await?;
    match item.kind {
        crate::s3::ItemKind::File => spaces.move_object(&item.path, &dest).await,
        crate::s3::ItemKind::Folder => spaces.move_folder(&item.path, &dest).await,
    }
}

#[tauri::command]
pub async fn rename_item(state: S<'_>, item: Item, new_name: String) -> AppResult<String> {
    let name = new_name.trim();
    if name.is_empty() || name.contains('/') || name.contains('\\') {
        return Err(AppError::msg("Ad boş olamaz ve / veya \\ içeremez"));
    }
    state.spaces().await?.rename(&item, name).await
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ShareLink {
    url: String,
    expires_at: i64,
}

#[tauri::command]
pub async fn share_link(state: S<'_>, key: String, days: u64) -> AppResult<ShareLink> {
    let days = if days == 7 { 7 } else { 3 };
    let seconds = days * 24 * 60 * 60;
    let url = state.spaces().await?.presign(&key, seconds).await?;
    Ok(ShareLink { url, expires_at: chrono::Utc::now().timestamp() + seconds as i64 })
}

#[tauri::command]
pub fn expand_upload(paths: Vec<String>, prefix: String) -> AppResult<Vec<UploadRequest>> {
    expand_local(&paths, &prefix)
}

#[tauri::command]
pub async fn start_upload(app: AppHandle, state: S<'_>, requests: Vec<UploadRequest>, acl: Acl) -> AppResult<Vec<TransferEvent>> {
    let spaces = state.spaces().await?;
    let meta = state.settings.load_upload_metadata();
    Ok(state.transfers.start_uploads(app_sink(app), spaces, requests, acl, meta))
}

#[tauri::command]
pub async fn start_download(app: AppHandle, state: S<'_>, items: Vec<Item>, dest_dir: String) -> AppResult<Vec<TransferEvent>> {
    let spaces = state.spaces().await?;
    state.transfers.start_downloads(app_sink(app), spaces, items, PathBuf::from(dest_dir)).await
}

#[tauri::command]
pub fn cancel_transfer(state: S<'_>, id: String) {
    state.transfers.cancel(&id);
}

#[tauri::command]
pub fn cancel_all_transfers(state: S<'_>) {
    state.transfers.cancel_all();
}

#[tauri::command]
pub fn active_transfers(state: S<'_>) -> usize {
    state.transfers.active_count()
}

#[tauri::command]
pub async fn list_multipart(state: S<'_>, prefix: Option<String>) -> AppResult<Vec<MultipartInfo>> {
    state.spaces().await?.list_multipart(prefix.as_deref().unwrap_or("")).await
}

#[tauri::command]
pub async fn abort_multipart(state: S<'_>, key: String, upload_id: String) -> AppResult<()> {
    state.spaces().await?.abort_multipart(&key, &upload_id).await
}

#[tauri::command]
pub fn get_upload_metadata(state: S<'_>) -> UploadMetadataSettings {
    state.settings.load_upload_metadata()
}

#[tauri::command]
pub fn save_upload_metadata(state: S<'_>, settings: UploadMetadataSettings) -> AppResult<()> {
    state.settings.save_upload_metadata(&settings)
}

#[tauri::command]
pub fn save_theme(state: S<'_>, theme: String) -> AppResult<()> {
    state.settings.save_theme(&theme)
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateInfo {
    current: String,
    latest: String,
    url: String,
    body: String,
    newer: bool,
    dismissed: bool,
}

#[tauri::command]
pub async fn check_update(state: S<'_>) -> AppResult<UpdateInfo> {
    let current = env!("CARGO_PKG_VERSION");
    let resp: serde_json::Value = reqwest::Client::new()
        .get(format!("https://api.github.com/repos/{GITHUB_REPO}/releases/latest"))
        .header("Accept", "application/vnd.github+json")
        .header("User-Agent", format!("S3MANAGER/{current}"))
        .timeout(std::time::Duration::from_secs(15))
        .send()
        .await
        .and_then(|r| r.error_for_status())
        .map_err(|e| AppError::msg(format!("Güncelleme kontrolü başarısız: {e}")))?
        .json()
        .await
        .map_err(|e| AppError::msg(format!("Güncelleme yanıtı okunamadı: {e}")))?;
    let tag = resp["tag_name"].as_str().unwrap_or_default();
    let latest = tag.trim().trim_start_matches('v').to_string();
    let newer = match (semver::Version::parse(&latest), semver::Version::parse(current)) {
        (Ok(l), Ok(c)) => l > c,
        _ => !latest.is_empty() && latest != current,
    };
    Ok(UpdateInfo {
        dismissed: state.settings.dismissed_update().as_deref() == Some(latest.as_str()),
        url: resp["html_url"]
            .as_str()
            .map(String::from)
            .unwrap_or_else(|| format!("https://github.com/{GITHUB_REPO}/releases/latest")),
        body: resp["body"].as_str().unwrap_or_default().trim().to_string(),
        current: current.to_string(),
        latest,
        newer,
    })
}

#[tauri::command]
pub fn dismiss_update(state: S<'_>, version: String) -> AppResult<()> {
    state.settings.set_dismissed_update(&version)
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct LogTail {
    path: String,
    text: String,
}

#[tauri::command]
pub fn read_log(state: S<'_>, lines: Option<usize>) -> LogTail {
    let path = state.settings.log_file();
    let text = std::fs::read_to_string(&path).unwrap_or_default();
    let n = lines.unwrap_or(500);
    let all: Vec<&str> = text.lines().collect();
    let start = all.len().saturating_sub(n);
    LogTail { path: path.to_string_lossy().into_owned(), text: all[start..].join("\n") }
}
