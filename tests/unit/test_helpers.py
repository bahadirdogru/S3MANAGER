"""helpers modülü unit testleri."""
import pytest
from datetime import datetime

from src.utils.helpers import (
    format_file_size,
    format_date,
    join_path,
    should_use_multipart,
    calculate_multipart_chunk_size,
    MULTIPART_THRESHOLD_MB,
)


@pytest.mark.unit
class TestFormatFileSize:
    def test_zero_bytes(self):
        assert format_file_size(0) == "0 B"

    def test_bytes(self):
        assert format_file_size(512) == "512.00 B"

    def test_kilobytes(self):
        assert format_file_size(1024) == "1.00 KB"

    def test_megabytes(self):
        assert format_file_size(1024 * 1024) == "1.00 MB"


@pytest.mark.unit
class TestFormatDate:
    def test_formats_datetime(self):
        dt = datetime(2026, 8, 11, 14, 30, 0)
        assert format_date(dt) == "2026-08-11 14:30:00"


@pytest.mark.unit
class TestJoinPath:
    def test_empty_parts(self):
        assert join_path() == "/"

    def test_single_part(self):
        assert join_path("folder") == "/folder"

    def test_strips_slashes(self):
        assert join_path("/a/", "/b/", "c") == "/a/b/c"

    def test_skips_empty_strings(self):
        assert join_path("", "a", "") == "/a"


@pytest.mark.unit
class TestMultipartHelpers:
    def test_should_use_multipart_below_threshold(self):
        size = MULTIPART_THRESHOLD_MB * 1024 * 1024
        assert should_use_multipart(size) is False

    def test_should_use_multipart_above_threshold(self):
        size = MULTIPART_THRESHOLD_MB * 1024 * 1024 + 1
        assert should_use_multipart(size) is True

    def test_chunk_size_minimum(self):
        chunk = calculate_multipart_chunk_size(10 * 1024 * 1024)
        assert chunk >= 5 * 1024 * 1024

    def test_chunk_size_large_file(self):
        chunk = calculate_multipart_chunk_size(50 * 1024 * 1024 * 1024)
        assert chunk <= 5 * 1024 * 1024 * 1024
