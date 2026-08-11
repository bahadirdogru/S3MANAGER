"""listing_cache modülü unit testleri."""
import pytest
from freezegun import freeze_time

from src.services.listing_cache import ListingCache


@pytest.mark.unit
class TestListingCache:
    def test_put_and_get(self):
        cache = ListingCache(ttl_seconds=60)
        folders = [{"name": "docs", "path": "docs/", "type": "folder"}]
        files = [{"name": "a.txt", "path": "a.txt", "type": "file"}]
        cache.put("docs/", folders, files)
        result = cache.get("docs/")
        assert result is not None
        got_folders, got_files = result
        assert got_folders == folders
        assert got_files == files

    def test_miss_returns_none(self):
        cache = ListingCache()
        assert cache.get("missing/") is None

    @freeze_time("2026-08-11 12:00:00")
    def test_ttl_expiry(self):
        cache = ListingCache(ttl_seconds=60)
        cache.put("p/", [], [])
        with freeze_time("2026-08-11 12:01:01"):
            assert cache.get("p/") is None

    def test_invalidate_single_prefix(self):
        cache = ListingCache()
        cache.put("a/", [], [])
        cache.put("a/b/", [], [])
        cache.put("c/", [], [])
        cache.invalidate("a/")
        assert cache.get("a/") is None
        assert cache.get("a/b/") is None
        assert cache.get("c/") is not None

    def test_invalidate_all(self):
        cache = ListingCache()
        cache.put("a/", [], [])
        cache.put("b/", [], [])
        cache.invalidate()
        assert cache.get("a/") is None
        assert cache.get("b/") is None
