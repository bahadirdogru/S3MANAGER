"""S3 object metadata detection for uploads."""
from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass, field
from typing import Optional, Set

# Extensions where mimetypes stdlib is unreliable or missing.
_EXTENSION_MIME_MAP = {
    'html': 'text/html',
    'htm': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'mjs': 'application/javascript',
    'json': 'application/json',
    'svg': 'image/svg+xml',
    'wasm': 'application/wasm',
    'xml': 'application/xml',
    'txt': 'text/plain',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'webp': 'image/webp',
    'ico': 'image/x-icon',
    'pdf': 'application/pdf',
    'zip': 'application/zip',
    'gz': 'application/gzip',
    'tar': 'application/x-tar',
    'bz2': 'application/x-bzip2',
    '7z': 'application/x-7z-compressed',
    'rar': 'application/vnd.rar',
    'exe': 'application/vnd.microsoft.portable-executable',
    'msi': 'application/x-msdownload',
    'bin': 'application/octet-stream',
    'iso': 'application/x-iso9660-image',
}

_TEXT_MIME_PREFIXES = ('text/',)
_TEXT_MIME_EXACT = {
    'application/javascript',
    'application/json',
    'application/xml',
    'image/svg+xml',
}

DEFAULT_INLINE_EXTENSIONS = frozenset({
    'html', 'htm', 'css', 'js', 'mjs', 'json', 'svg', 'png', 'jpg', 'jpeg',
    'gif', 'webp', 'ico', 'pdf', 'txt', 'xml',
})

DEFAULT_ATTACHMENT_EXTENSIONS = frozenset({
    'zip', 'gz', 'tar', 'bz2', '7z', 'rar', 'exe', 'msi', 'bin', 'iso',
})


@dataclass
class UploadMetadataSettings:
    """User-configurable upload metadata rules."""

    enabled: bool = True
    cache_control: str = ''
    text_charset: str = 'utf-8'
    inline_extensions: Set[str] = field(default_factory=lambda: set(DEFAULT_INLINE_EXTENSIONS))
    attachment_extensions: Set[str] = field(default_factory=lambda: set(DEFAULT_ATTACHMENT_EXTENSIONS))

    def inline_extensions_csv(self) -> str:
        return ','.join(sorted(self.inline_extensions))

    def attachment_extensions_csv(self) -> str:
        return ','.join(sorted(self.attachment_extensions))


def parse_extension_list(value: str) -> Set[str]:
    """Parse comma-separated extension list (without dots)."""
    result: Set[str] = set()
    for part in value.split(','):
        ext = part.strip().lower().lstrip('.')
        if ext:
            result.add(ext)
    return result


def extension_of(path: str) -> str:
    """Return lowercase extension without dot."""
    _, ext = os.path.splitext(path)
    return ext.lstrip('.').lower()


def guess_content_type(path: str, charset: str = 'utf-8') -> str:
    """Guess Content-Type from file path extension."""
    ext = extension_of(path)
    if ext in _EXTENSION_MIME_MAP:
        mime = _EXTENSION_MIME_MAP[ext]
    else:
        guessed, _ = mimetypes.guess_type(path)
        mime = guessed or 'application/octet-stream'

    if _needs_charset(mime) and charset:
        return f'{mime}; charset={charset}'
    return mime


def _needs_charset(mime: str) -> bool:
    base = mime.split(';', 1)[0].strip().lower()
    if base in _TEXT_MIME_EXACT:
        return True
    return any(base.startswith(prefix) for prefix in _TEXT_MIME_PREFIXES)


def _safe_filename(filename: str) -> Optional[str]:
    """Return ASCII-safe filename for Content-Disposition, or None."""
    try:
        filename.encode('ascii')
        return filename
    except UnicodeEncodeError:
        return None


def guess_content_disposition(
    filename: str,
    content_type: str,
    settings: UploadMetadataSettings,
) -> Optional[str]:
    """Guess Content-Disposition header value."""
    ext = extension_of(filename)
    base_mime = content_type.split(';', 1)[0].strip().lower()

    disposition: Optional[str] = None
    if ext in settings.attachment_extensions:
        disposition = 'attachment'
    elif ext in settings.inline_extensions:
        disposition = 'inline'
    elif base_mime.startswith('text/') or base_mime in _TEXT_MIME_EXACT:
        disposition = 'inline'
    elif base_mime.startswith('image/'):
        disposition = 'inline'
    elif base_mime == 'application/pdf':
        disposition = 'inline'

    if disposition is None:
        return None

    safe_name = _safe_filename(os.path.basename(filename))
    if safe_name:
        return f'{disposition}; filename="{safe_name}"'
    return disposition


def build_upload_extra_args(
    local_path: str,
    remote_key: str,
    acl: str,
    settings: Optional[UploadMetadataSettings] = None,
) -> dict:
    """
    Build boto3 ExtraArgs dict for upload (PascalCase keys).

    Uses remote_key extension first, falls back to local_path.
    """
    extra: dict = {}
    if acl == 'public-read':
        extra['ACL'] = 'public-read'

    if settings is None:
        settings = UploadMetadataSettings()
    if not settings.enabled:
        return extra

    mime_path = remote_key if extension_of(remote_key) else local_path
    content_type = guess_content_type(mime_path, settings.text_charset)
    extra['ContentType'] = content_type

    disposition = guess_content_disposition(
        os.path.basename(remote_key) or os.path.basename(local_path),
        content_type,
        settings,
    )
    if disposition:
        extra['ContentDisposition'] = disposition

    if settings.cache_control.strip():
        extra['CacheControl'] = settings.cache_control.strip()

    return extra


def preview_content_type(
    local_path: str,
    remote_key: str,
    settings: Optional[UploadMetadataSettings] = None,
) -> str:
    """Return Content-Type preview for UI (empty if metadata disabled)."""
    if settings is None:
        settings = UploadMetadataSettings()
    if not settings.enabled:
        return ''
    mime_path = remote_key if extension_of(remote_key) else local_path
    return guess_content_type(mime_path, settings.text_charset)
