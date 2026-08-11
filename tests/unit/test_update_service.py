"""update_service modülü unit testleri."""
import pytest

from src.services import update_service


@pytest.mark.unit
class TestParseTag:
    @pytest.mark.parametrize("tag,expected", [
        ("v0.0.6", "0.0.6"),
        ("0.0.6", "0.0.6"),
        ("v1.2.3-beta", "1.2.3-beta"),
    ])
    def test_valid_tags(self, tag, expected):
        assert update_service._parse_tag(tag) == expected

    @pytest.mark.parametrize("tag", ["", "release", "v"])
    def test_invalid_tags(self, tag):
        assert update_service._parse_tag(tag) is None


@pytest.mark.unit
class TestIsNewerVersion:
    def test_newer(self):
        assert update_service.is_newer_version("0.0.7", "0.0.6") is True

    def test_same(self):
        assert update_service.is_newer_version("0.0.6", "0.0.6") is False

    def test_older(self):
        assert update_service.is_newer_version("0.0.5", "0.0.6") is False

    def test_invalid_version_fallback(self):
        assert update_service.is_newer_version("not-a-version", "0.0.6") is True
