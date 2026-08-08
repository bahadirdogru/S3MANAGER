"""Helper utility functions"""
from datetime import datetime

MULTIPART_THRESHOLD_MB = 100


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.2f} {size_names[i]}"


def format_date(date: datetime) -> str:
    """Format datetime to readable string"""
    return date.strftime("%Y-%m-%d %H:%M:%S")


def join_path(*parts: str) -> str:
    """Join path parts"""
    parts = [p.strip('/') for p in parts if p and p != '/']
    return '/' + '/'.join(parts) if parts else '/'


def should_use_multipart(size_bytes: int, threshold_mb: int = MULTIPART_THRESHOLD_MB) -> bool:
    """Determine if multipart upload should be used"""
    return size_bytes > (threshold_mb * 1024 * 1024)


def calculate_multipart_chunk_size(file_size: int, max_parts: int = 10000) -> int:
    """Calculate optimal chunk size for multipart upload"""
    min_chunk_size = 5 * 1024 * 1024
    max_chunk_size = 5 * 1024 * 1024 * 1024

    chunk_size = file_size // max_parts
    chunk_size = max(chunk_size, min_chunk_size)
    chunk_size = min(chunk_size, max_chunk_size)
    chunk_size = (chunk_size // (1024 * 1024)) * (1024 * 1024)

    return chunk_size
