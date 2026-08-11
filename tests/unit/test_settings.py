"""settings modülü unit testleri."""
import pytest
import configparser

from src.config.settings import Settings


@pytest.mark.unit
class TestSettings:
    def test_save_and_load_credentials(self, mock_config_dir):
        settings = Settings()
        assert settings.save_credentials(
            "a" * 20, "b" * 40, "nyc3",
            "https://nyc3.digitaloceanspaces.com", "my-bucket",
        )
        creds = settings.load_credentials()
        assert creds is not None
        assert creds["key"] == "a" * 20
        assert creds["bucket"] == "my-bucket"

    def test_load_credentials_missing(self, mock_config_dir):
        settings = Settings()
        assert settings.load_credentials() is None

    def test_theme_mode_roundtrip(self, mock_config_dir):
        settings = Settings()
        assert settings.save_theme_mode("light")
        assert settings.load_theme_mode() == "light"
        assert settings.save_theme_mode("dark")
        assert settings.load_theme_mode() == "dark"

    def test_get_default_region_endpoint(self, mock_config_dir):
        settings = Settings()
        assert "nyc3" in settings.get_default_region_endpoint("nyc3")

    def test_upload_metadata_settings_roundtrip(self, mock_config_dir):
        settings = Settings()
        original = settings.load_upload_metadata_settings()
        original.cache_control = "max-age=60"
        assert settings.save_upload_metadata_settings(original)
        loaded = settings.load_upload_metadata_settings()
        assert loaded.cache_control == "max-age=60"

    def test_partial_credentials_not_loaded(self, mock_config_dir):
        config_file = mock_config_dir / "config.ini"
        config = configparser.ConfigParser()
        config["digitalocean"] = {"spaces_key": "only-key"}
        with open(config_file, "w", encoding="utf-8") as f:
            config.write(f)
        settings = Settings()
        assert settings.load_credentials() is None
