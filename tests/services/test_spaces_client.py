"""SpacesClient servis testleri (moto mock S3)."""
import pytest

@pytest.mark.integration
class TestSpacesClientConnection:
    def test_connection_success(self, spaces_client):
        ok, err = spaces_client.test_connection()
        assert ok is True
        assert err is None


@pytest.mark.integration
class TestSpacesClientListing:
    def test_list_objects_page(self, sample_s3_objects):
        client = sample_s3_objects
        page = client.list_objects_page(prefix="")
        assert len(page["files"]) >= 1
        assert len(page["folders"]) >= 2
        assert page["prefix"] == ""

    def test_list_objects_page_with_prefix(self, sample_s3_objects):
        client = sample_s3_objects
        page = client.list_objects_page(prefix="docs/")
        names = {f["name"] for f in page["files"]}
        assert "readme.txt" in names
        assert "guide.pdf" in names

    def test_parse_list_page_structure(self, sample_s3_objects):
        client = sample_s3_objects
        page = client.list_objects_page(prefix="")
        for f in page["files"]:
            assert f["type"] == "file"
            assert "path" in f
            assert "size" in f


@pytest.mark.integration
class TestSpacesClientCrud:
    def test_create_folder(self, spaces_client):
        spaces_client.create_folder("newfolder/")
        page = spaces_client.list_objects_page(prefix="")
        assert any(f["name"] == "newfolder" for f in page["folders"])

    def test_upload_and_delete(self, spaces_client, tmp_path):
        local = tmp_path / "upload.txt"
        local.write_text("test content", encoding="utf-8")
        spaces_client.upload_file(str(local), "uploads/upload.txt")
        page = spaces_client.list_objects_page(prefix="uploads/")
        assert any(f["name"] == "upload.txt" for f in page["files"])
        spaces_client.delete_object("uploads/upload.txt")
        page = spaces_client.list_objects_page(prefix="uploads/")
        assert not any(f["name"] == "upload.txt" for f in page["files"])

    def test_delete_missing_raises(self, spaces_client):
        spaces_client.delete_object("nonexistent-key.txt")


@pytest.mark.integration
class TestSpacesClientCopyMove:
    def test_copy_object(self, sample_s3_objects):
        client = sample_s3_objects
        client.copy_object("docs/readme.txt", "docs/readme-copy.txt")
        page = client.list_objects_page(prefix="docs/")
        names = {f["name"] for f in page["files"]}
        assert "readme-copy.txt" in names

    def test_move_object(self, sample_s3_objects):
        client = sample_s3_objects
        client.move_object("docs/readme.txt", "docs/moved.txt")
        page = client.list_objects_page(prefix="docs/")
        names = {f["name"] for f in page["files"]}
        assert "moved.txt" in names
        assert "readme.txt" not in names

    def test_rename_object(self, sample_s3_objects):
        client = sample_s3_objects
        client.client.put_object(
            Bucket=client.bucket, Key="rename-me.txt", Body=b"data",
        )
        new_key = client.rename_object("rename-me.txt", "renamed.txt")
        assert new_key == "renamed.txt"
        page = client.list_objects_page(prefix="")
        names = {f["name"] for f in page["files"]}
        assert "renamed.txt" in names
        assert "rename-me.txt" not in names


@pytest.mark.integration
class TestSpacesClientMetadata:
    def test_head_object(self, sample_s3_objects):
        client = sample_s3_objects
        meta = client.head_object("docs/readme.txt")
        assert meta["content_length"] == 5

    def test_get_object_bytes(self, sample_s3_objects):
        client = sample_s3_objects
        data = client.get_object_bytes("docs/readme.txt")
        assert data == b"hello"


@pytest.mark.integration
class TestSpacesClientAcl:
    def test_private_acl_default(self, sample_s3_objects):
        client = sample_s3_objects
        assert client.get_object_acl("docs/readme.txt") == "private"

    def test_public_read_acl(self, spaces_client):
        spaces_client.client.put_object(
            Bucket=spaces_client.bucket,
            Key="public.txt",
            Body=b"public",
            ACL="public-read",
        )
        assert spaces_client.get_object_acl("public.txt") == "public-read"


@pytest.mark.integration
class TestSpacesClientNormalizeKey:
    def test_normalize_strips_leading_slash(self, spaces_client):
        assert spaces_client._normalize_key("/path/file.txt") == "path/file.txt"
