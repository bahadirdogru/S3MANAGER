use aws_sdk_s3::error::{DisplayErrorContext, ProvideErrorMetadata, SdkError};
use serde::{Serialize, Serializer};

#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("{0}")]
    Msg(String),
    #[error("Depoya bağlı değil")]
    NotConnected,
    #[error("İptal edildi")]
    Cancelled,
    #[error("Dosya hatası: {0}")]
    Io(#[from] std::io::Error),
}

impl AppError {
    pub fn msg(s: impl Into<String>) -> Self {
        AppError::Msg(s.into())
    }
}

// Tauri commands send errors to the frontend as plain strings.
impl Serialize for AppError {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(&self.to_string())
    }
}

pub type AppResult<T> = Result<T, AppError>;

/// Wraps an S3 SDK error with a Turkish context prefix, preferring the
/// service error code (e.g. `NoSuchKey`, `AccessDenied`) over the debug chain.
pub fn s3<E, R>(prefix: &'static str) -> impl FnOnce(SdkError<E, R>) -> AppError
where
    E: ProvideErrorMetadata + std::error::Error + 'static,
    R: std::fmt::Debug,
{
    move |e| {
        let detail = e
            .as_service_error()
            .and_then(|s| {
                s.code().map(|c| match s.message() {
                    Some(m) if !m.is_empty() => format!("{c}: {m}"),
                    _ => c.to_string(),
                })
            })
            .unwrap_or_else(|| DisplayErrorContext(&e).to_string());
        log::warn!("{prefix}: {detail}");
        AppError::Msg(format!("{prefix}: {detail}"))
    }
}

pub fn build_err(e: aws_sdk_s3::error::BuildError) -> AppError {
    AppError::Msg(format!("İstek oluşturulamadı: {e}"))
}
