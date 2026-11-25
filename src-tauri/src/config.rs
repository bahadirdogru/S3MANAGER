//! `~/.s3manager/config.ini` — file and section names are kept stable
//! so installs from earlier releases keep their settings.

use std::path::PathBuf;

use ini::Ini;
use serde::{Deserialize, Serialize};

use crate::error::{AppError, AppResult};
use crate::metadata::{UploadMetadataSettings, DEFAULT_ATTACHMENT_EXTENSIONS, DEFAULT_INLINE_EXTENSIONS};

const SEC_CREDS: &str = "digitalocean";
const SEC_META: &str = "upload_metadata";
const SEC_APPEARANCE: &str = "appearance";
const SEC_UPDATES: &str = "updates";

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Credentials {
    pub key: String,
    pub secret: String,
    pub region: String,
    pub endpoint: String,
    pub bucket: String,
    #[serde(default)]
    pub path_style: bool,
}

pub struct Settings {
    pub dir: PathBuf,
    pub file: PathBuf,
}

impl Settings {
    pub fn new() -> Self {
        let dir = dirs::home_dir().unwrap_or_else(|| PathBuf::from(".")).join(".s3manager");
        let _ = std::fs::create_dir_all(&dir);
        let file = dir.join("config.ini");
        Settings { dir, file }
    }

    pub fn log_file(&self) -> PathBuf {
        self.dir.join("app.log")
    }

    fn read(&self) -> Ini {
        Ini::load_from_file(&self.file).unwrap_or_default()
    }

    fn write(&self, ini: &Ini) -> AppResult<()> {
        ini.write_to_file(&self.file)
            .map_err(|e| AppError::msg(format!("Ayarlar kaydedilemedi: {e}")))
    }

    pub fn load_credentials(&self) -> Option<Credentials> {
        let ini = self.read();
        let s = ini.section(Some(SEC_CREDS))?;
        let get = |k: &str| s.get(k).map(str::trim).filter(|v| !v.is_empty()).map(String::from);
        Some(Credentials {
            key: get("spaces_key")?,
            secret: get("spaces_secret")?,
            region: get("region").unwrap_or_else(|| "nyc3".into()),
            endpoint: get("endpoint")?,
            bucket: get("bucket")?,
            path_style: get("path_style").is_some_and(|v| parse_bool(&v)),
        })
    }

    pub fn save_credentials(&self, c: &Credentials) -> AppResult<()> {
        let mut ini = self.read();
        ini.with_section(Some(SEC_CREDS))
            .set("spaces_key", &c.key)
            .set("spaces_secret", &c.secret)
            .set("region", &c.region)
            .set("endpoint", &c.endpoint)
            .set("bucket", &c.bucket)
            .set("path_style", if c.path_style { "true" } else { "false" });
        self.write(&ini)
    }

    pub fn load_upload_metadata(&self) -> UploadMetadataSettings {
        let mut out = UploadMetadataSettings::default();
        let ini = self.read();
        let Some(s) = ini.section(Some(SEC_META)) else {
            return out;
        };
        if let Some(v) = s.get("enabled") {
            out.enabled = parse_bool(v);
        }
        if let Some(v) = s.get("cache_control") {
            out.cache_control = v.trim().to_string();
        }
        if let Some(v) = s.get("text_charset").map(str::trim).filter(|v| !v.is_empty()) {
            out.text_charset = v.to_string();
        }
        out.inline_extensions = match s.get("inline_extensions").map(str::trim) {
            Some(v) if !v.is_empty() => parse_extension_list(v),
            _ => DEFAULT_INLINE_EXTENSIONS.iter().map(|s| s.to_string()).collect(),
        };
        out.attachment_extensions = match s.get("attachment_extensions").map(str::trim) {
            Some(v) if !v.is_empty() => parse_extension_list(v),
            _ => DEFAULT_ATTACHMENT_EXTENSIONS.iter().map(|s| s.to_string()).collect(),
        };
        out
    }

    pub fn save_upload_metadata(&self, m: &UploadMetadataSettings) -> AppResult<()> {
        let mut ini = self.read();
        ini.with_section(Some(SEC_META))
            .set("enabled", if m.enabled { "true" } else { "false" })
            .set("cache_control", m.cache_control.trim())
            .set("text_charset", m.text_charset.trim())
            .set("inline_extensions", m.inline_extensions.iter().cloned().collect::<Vec<_>>().join(","))
            .set(
                "attachment_extensions",
                m.attachment_extensions.iter().cloned().collect::<Vec<_>>().join(","),
            );
        self.write(&ini)
    }

    pub fn load_theme(&self) -> String {
        let ini = self.read();
        match ini.get_from(Some(SEC_APPEARANCE), "theme").map(|v| v.trim().to_lowercase()) {
            Some(v) if v == "light" => "light".into(),
            _ => "dark".into(),
        }
    }

    pub fn save_theme(&self, mode: &str) -> AppResult<()> {
        let mut ini = self.read();
        let mode = if mode.eq_ignore_ascii_case("light") { "light" } else { "dark" };
        ini.with_section(Some(SEC_APPEARANCE)).set("theme", mode);
        self.write(&ini)
    }

    pub fn dismissed_update(&self) -> Option<String> {
        self.read()
            .get_from(Some(SEC_UPDATES), "dismissed_version")
            .map(str::trim)
            .filter(|v| !v.is_empty())
            .map(String::from)
    }

    pub fn set_dismissed_update(&self, version: &str) -> AppResult<()> {
        let mut ini = self.read();
        ini.with_section(Some(SEC_UPDATES)).set("dismissed_version", version);
        self.write(&ini)
    }
}

pub fn default_endpoint(region: &str) -> String {
    format!("https://{}.digitaloceanspaces.com", region.trim())
}

fn parse_bool(v: &str) -> bool {
    matches!(v.trim().to_lowercase().as_str(), "1" | "true" | "yes" | "on")
}

pub fn parse_extension_list(v: &str) -> std::collections::BTreeSet<String> {
    v.split(',')
        .map(|p| p.trim().trim_start_matches('.').to_lowercase())
        .filter(|p| !p.is_empty())
        .collect()
}
