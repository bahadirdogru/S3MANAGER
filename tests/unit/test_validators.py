"""validators modülü unit testleri."""
import pytest

from src.utils.validators import (
    validate_spaces_key,
    validate_spaces_secret,
    validate_bucket_name,
    validate_endpoint,
    validate_region,
)


@pytest.mark.unit
class TestValidateSpacesKey:
    def test_empty_key(self):
        ok, msg = validate_spaces_key("")
        assert ok is False
        assert msg is not None

    def test_short_key(self):
        ok, msg = validate_spaces_key("short")
        assert ok is False

    def test_valid_key(self):
        ok, msg = validate_spaces_key("a" * 20)
        assert ok is True
        assert msg is None


@pytest.mark.unit
class TestValidateSpacesSecret:
    def test_empty_secret(self):
        ok, msg = validate_spaces_secret("")
        assert ok is False

    def test_short_secret(self):
        ok, msg = validate_spaces_secret("x" * 30)
        assert ok is False

    def test_valid_secret(self):
        ok, msg = validate_spaces_secret("x" * 40)
        assert ok is True


@pytest.mark.unit
class TestValidateBucketName:
    @pytest.mark.parametrize("name", ["my-bucket", "abc", "a" * 63])
    def test_valid_names(self, name):
        if len(name) >= 3:
            ok, msg = validate_bucket_name(name)
            assert ok is True, msg

    @pytest.mark.parametrize("name", ["", "ab", "My-Bucket", "bucket_", "-bucket"])
    def test_invalid_names(self, name):
        ok, _ = validate_bucket_name(name)
        assert ok is False


@pytest.mark.unit
class TestValidateEndpoint:
    def test_empty(self):
        ok, _ = validate_endpoint("")
        assert ok is False

    def test_missing_scheme(self):
        ok, _ = validate_endpoint("nyc3.digitaloceanspaces.com")
        assert ok is False

    @pytest.mark.parametrize("url", ["https://nyc3.digitaloceanspaces.com", "http://localhost:9000"])
    def test_valid_urls(self, url):
        ok, msg = validate_endpoint(url)
        assert ok is True, msg


@pytest.mark.unit
class TestValidateRegion:
    def test_valid_region(self):
        ok, msg = validate_region("nyc3")
        assert ok is True
        assert msg is None

    def test_invalid_region(self):
        ok, msg = validate_region("invalid")
        assert ok is False
        assert "nyc3" in msg
