"""object_metadata modülü unit testleri."""
import pytest

from src.utils.object_metadata import (
    UploadMetadataSettings,
    parse_extension_list,
    extension_of,
    guess_content_type,
    guess_content_disposition,
    build_upload_extra_args,
    preview_content_type,
)


@pytest.mark.unit
class TestParseExtensionList:
    def test_comma_separated(self):
        assert parse_extension_list("html, css, js") == {"html", "css", "js"}

    def test_strips_dots(self):
        assert parse_extension_list(".png,.jpg") == {"png", "jpg"}

    def test_empty(self):
        assert parse_extension_list("") == set()


@pytest.mark.unit
class TestExtensionOf:
    def test_lowercase(self):
        assert extension_of("/path/File.HTML") == "html"


@pytest.mark.unit
class TestGuessContentType:
    def test_html_with_charset(self):
        assert guess_content_type("index.html") == "text/html; charset=utf-8"

    def test_binary(self):
        assert guess_content_type("file.bin") == "application/octet-stream"

    def test_json(self):
        assert guess_content_type("data.json") == "application/json; charset=utf-8"


@pytest.mark.unit
class TestGuessContentDisposition:
    def test_inline_html(self):
        settings = UploadMetadataSettings()
        disp = guess_content_disposition("page.html", "text/html; charset=utf-8", settings)
        assert disp == 'inline; filename="page.html"'

    def test_attachment_zip(self):
        settings = UploadMetadataSettings()
        disp = guess_content_disposition("archive.zip", "application/zip", settings)
        assert disp == 'attachment; filename="archive.zip"'

    def test_unknown_extension_no_disposition(self):
        settings = UploadMetadataSettings()
        disp = guess_content_disposition("data.unknown", "application/octet-stream", settings)
        assert disp is None


@pytest.mark.unit
class TestBuildUploadExtraArgs:
    def test_public_acl(self):
        args = build_upload_extra_args("/tmp/a.txt", "a.txt", "public-read")
        assert args["ACL"] == "public-read"
        assert "ContentType" in args

    def test_disabled_metadata(self):
        settings = UploadMetadataSettings(enabled=False)
        args = build_upload_extra_args("/tmp/a.txt", "a.txt", "private", settings)
        assert "ContentType" not in args

    def test_cache_control(self):
        settings = UploadMetadataSettings(cache_control="max-age=3600")
        args = build_upload_extra_args("/tmp/a.css", "a.css", "private", settings)
        assert args["CacheControl"] == "max-age=3600"

    def test_remote_key_extension_priority(self):
        settings = UploadMetadataSettings()
        args = build_upload_extra_args("/tmp/noext", "remote/file.js", "private", settings)
        assert args["ContentType"].startswith("application/javascript")


@pytest.mark.unit
class TestPreviewContentType:
    def test_disabled_returns_empty(self):
        settings = UploadMetadataSettings(enabled=False)
        assert preview_content_type("/tmp/a.html", "a.html", settings) == ""

    def test_enabled_returns_type(self):
        settings = UploadMetadataSettings()
        assert "text/html" in preview_content_type("/tmp/a.html", "a.html", settings)
