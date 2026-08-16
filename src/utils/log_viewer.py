"""Log dosyası okuma yardımcıları."""
from pathlib import Path


def read_log_tail(
    path: Path,
    max_lines: int = 400,
    max_bytes: int = 256 * 1024,
) -> str:
    """Log dosyasının son satırlarını güvenli şekilde okur."""
    path = Path(path)
    if not path.is_file():
        return ""

    try:
        size = path.stat().st_size
        read_size = min(size, max_bytes)
        with open(path, "rb") as f:
            if read_size < size:
                f.seek(-read_size)
            data = f.read(read_size)
    except OSError:
        return ""

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")

    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
        return "… (eski satırlar kısaltıldı)\n" + "\n".join(lines)
    return "\n".join(lines)
