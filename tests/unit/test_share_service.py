"""share_service modülü unit testleri."""
import pytest
from unittest.mock import MagicMock, patch

from src.services.share_service import ShareService


@pytest.mark.unit
class TestShareService:
    def test_create_share_link_3_days(self):
        client = MagicMock()
        client.create_presigned_url.return_value = "https://example.com/signed"
        service = ShareService(client)
        url, expiration = service.create_share_link("file.txt", days=3)
        assert url == "https://example.com/signed"
        client.create_presigned_url.assert_called_once()
        call_args = client.create_presigned_url.call_args
        assert call_args[0][0] == "file.txt"
        assert call_args[0][1] == ShareService.EXPIRATION_3_DAYS

    def test_create_share_link_7_days(self):
        client = MagicMock()
        client.create_presigned_url.return_value = "https://example.com/signed"
        service = ShareService(client)
        service.create_share_link("file.txt", days=7)
        assert client.create_presigned_url.call_args[0][1] == ShareService.EXPIRATION_7_DAYS

    def test_invalid_days_defaults_to_3(self):
        client = MagicMock()
        client.create_presigned_url.return_value = "https://example.com/signed"
        service = ShareService(client)
        service.create_share_link("file.txt", days=99)
        assert client.create_presigned_url.call_args[0][1] == ShareService.EXPIRATION_3_DAYS

    @patch("src.services.share_service.pyperclip.copy")
    def test_share_to_clipboard(self, mock_copy):
        client = MagicMock()
        client.create_presigned_url.return_value = "https://example.com/signed"
        service = ShareService(client)
        url, _ = service.share_to_clipboard("file.txt", days=3)
        assert url == "https://example.com/signed"
        mock_copy.assert_called_once_with("https://example.com/signed")
