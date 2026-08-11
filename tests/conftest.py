"""Ortak pytest fixture'ları."""
import pytest
import boto3
from moto import mock_aws

from src.services.spaces_client import SpacesClient
from src.utils import paths as paths_module


@pytest.fixture
def mock_config_dir(tmp_path, monkeypatch):
    """Settings testleri için izole config dizini."""
    config_dir = tmp_path / ".s3manager"
    config_dir.mkdir()
    monkeypatch.setattr(paths_module, "get_config_dir", lambda: config_dir)
    monkeypatch.setattr("src.config.settings.get_config_dir", lambda: config_dir)
    return config_dir


@pytest.fixture
def aws_credentials():
    return {
        "key": "testing",
        "secret": "testing",
        "region": "us-east-1",
        "endpoint": "https://s3.amazonaws.com",
        "bucket": "test-bucket",
    }


@pytest.fixture
def spaces_client(aws_credentials):
    """moto mock S3 ile SpacesClient örneği."""
    with mock_aws():
        s3 = boto3.client("s3", region_name=aws_credentials["region"])
        s3.create_bucket(Bucket=aws_credentials["bucket"])
        client = SpacesClient(**aws_credentials)
        yield client


@pytest.fixture
def sample_s3_objects(spaces_client):
    """Listeleme ve kopyalama testleri için örnek nesneler."""
    s3 = spaces_client.client
    bucket = spaces_client.bucket
    s3.put_object(Bucket=bucket, Key="root.txt", Body=b"root")
    s3.put_object(Bucket=bucket, Key="docs/readme.txt", Body=b"hello")
    s3.put_object(Bucket=bucket, Key="docs/guide.pdf", Body=b"%PDF-1.4")
    s3.put_object(Bucket=bucket, Key="images/photo.png", Body=b"\x89PNG")
    s3.put_object(Bucket=bucket, Key="archive/", Body=b"")
    return spaces_client
