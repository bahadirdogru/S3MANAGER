//! Content-Type / Content-Disposition / Cache-Control rules for uploads.


use std::collections::BTreeSet;
use std::path::Path;

use serde::{Deserialize, Serialize};

pub const DEFAULT_INLINE_EXTENSIONS: &[&str] = &[
    "html", "htm", "css", "js", "mjs", "json", "svg", "png", "jpg", "jpeg", "gif", "webp", "ico",
    "pdf", "txt", "xml",
];

pub const DEFAULT_ATTACHMENT_EXTENSIONS: &[&str] =
    &["zip", "gz", "tar", "bz2", "7z", "rar", "exe", "msi", "bin", "iso"];

const TEXT_MIME_EXACT: &[&str] =
    &["application/javascript", "application/json", "application/xml", "image/svg+xml"];

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UploadMetadataSettings {
    pub enabled: bool,
    pub cache_control: String,
    pub text_charset: String,
    pub inline_extensions: BTreeSet<String>,
    pub attachment_extensions: BTreeSet<String>,
}

impl Default for UploadMetadataSettings {
    fn default() -> Self {
        Self {
            enabled: true,
            cache_control: String::new(),
            text_charset: "utf-8".into(),
            inline_extensions: DEFAULT_INLINE_EXTENSIONS.iter().map(|s| s.to_string()).collect(),
            attachment_extensions: DEFAULT_ATTACHMENT_EXTENSIONS.iter().map(|s| s.to_string()).collect(),
        }
    }
}

#[derive(Debug, Default, Clone)]
pub struct UploadHeaders {
    pub content_type: Option<String>,
    pub content_disposition: Option<String>,
    pub cache_control: Option<String>,
}

pub fn extension_of(path: &str) -> String {
    Path::new(path)
        .extension()
        .map(|e| e.to_string_lossy().to_lowercase())
        .unwrap_or_default()
}

fn mime_for_extension(ext: &str) -> Option<&'static str> {
    Some(match ext {
        "html" | "htm" => "text/html",
        "css" => "text/css",
        "js" | "mjs" => "application/javascript",
        "json" => "application/json",
        "svg" => "image/svg+xml",
        "wasm" => "application/wasm",
        "xml" => "application/xml",
        "txt" => "text/plain",
        "png" => "image/png",
        "jpg" | "jpeg" => "image/jpeg",
        "gif" => "image/gif",
        "webp" => "image/webp",
        "ico" => "image/x-icon",
        "pdf" => "application/pdf",
        "zip" => "application/zip",
        "gz" => "application/gzip",
        "tar" => "application/x-tar",
        "bz2" => "application/x-bzip2",
        "7z" => "application/x-7z-compressed",
        "rar" => "application/vnd.rar",
        "exe" => "application/vnd.microsoft.portable-executable",
        "msi" => "application/x-msdownload",
        "bin" => "application/octet-stream",
        "iso" => "application/x-iso9660-image",
        _ => return None,
    })
}

pub fn is_text_mime(mime: &str) -> bool {
    let base = mime.split(';').next().unwrap_or("").trim().to_lowercase();
    base.starts_with("text/") || TEXT_MIME_EXACT.contains(&base.as_str())
}

pub fn guess_content_type(path: &str, charset: &str) -> String {
    let ext = extension_of(path);
    let mime = mime_for_extension(&ext)
        .map(String::from)
        .unwrap_or_else(|| mime_guess::from_path(path).first_or_octet_stream().essence_str().to_string());
    if is_text_mime(&mime) && !charset.is_empty() {
        format!("{mime}; charset={charset}")
    } else {
        mime
    }
}

fn guess_content_disposition(filename: &str, content_type: &str, s: &UploadMetadataSettings) -> Option<String> {
    let ext = extension_of(filename);
    let base = content_type.split(';').next().unwrap_or("").trim().to_lowercase();
    let disposition = if s.attachment_extensions.contains(&ext) {
        "attachment"
    } else if s.inline_extensions.contains(&ext)
        || is_text_mime(&base)
        || base.starts_with("image/")
        || base == "application/pdf"
    {
        "inline"
    } else {
        return None;
    };
    // Only ASCII names go into the header; anything else would need RFC 5987.
    if filename.is_ascii() && !filename.contains('"') {
        Some(format!("{disposition}; filename=\"{filename}\""))
    } else {
        Some(disposition.to_string())
    }
}

fn basename(p: &str) -> &str {
    p.rsplit(['/', '\\']).next().unwrap_or(p)
}

/// Uses the remote key's extension first, falling back to the local path.
pub fn build_upload_headers(local_path: &str, remote_key: &str, s: &UploadMetadataSettings) -> UploadHeaders {
    if !s.enabled {
        return UploadHeaders::default();
    }
    let mime_path = if extension_of(remote_key).is_empty() { local_path } else { remote_key };
    let content_type = guess_content_type(mime_path, &s.text_charset);
    let name = Some(basename(remote_key)).filter(|n| !n.is_empty()).unwrap_or_else(|| basename(local_path));
    UploadHeaders {
        content_disposition: guess_content_disposition(name, &content_type, s),
        cache_control: Some(s.cache_control.trim().to_string()).filter(|c| !c.is_empty()),
        content_type: Some(content_type),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn html_gets_charset_and_inline() {
        let h = build_upload_headers("/tmp/a.html", "site/index.html", &UploadMetadataSettings::default());
        assert_eq!(h.content_type.as_deref(), Some("text/html; charset=utf-8"));
        assert_eq!(h.content_disposition.as_deref(), Some("inline; filename=\"index.html\""));
    }

    #[test]
    fn zip_is_attachment() {
        let h = build_upload_headers("/tmp/x.zip", "x.zip", &UploadMetadataSettings::default());
        assert_eq!(h.content_type.as_deref(), Some("application/zip"));
        assert_eq!(h.content_disposition.as_deref(), Some("attachment; filename=\"x.zip\""));
    }

    #[test]
    fn non_ascii_name_drops_filename() {
        let h = build_upload_headers("/tmp/ş.pdf", "ş.pdf", &UploadMetadataSettings::default());
        assert_eq!(h.content_disposition.as_deref(), Some("inline"));
    }

    #[test]
    fn disabled_sends_nothing() {
        let s = UploadMetadataSettings { enabled: false, ..Default::default() };
        assert!(build_upload_headers("a.css", "a.css", &s).content_type.is_none());
    }

    #[test]
    fn cache_control_passthrough() {
        let s = UploadMetadataSettings { cache_control: " max-age=60 ".into(), ..Default::default() };
        assert_eq!(build_upload_headers("a.css", "a.css", &s).cache_control.as_deref(), Some("max-age=60"));
    }
}
