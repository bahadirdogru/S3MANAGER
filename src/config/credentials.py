"""Credentials management"""
from typing import Optional, Dict
from .settings import Settings


class CredentialsManager:
    """Manages DigitalOcean Spaces credentials"""

    def __init__(self):
        self.settings = Settings()
        self._cached_credentials: Optional[Dict[str, str]] = None

    def get_credentials(self) -> Optional[Dict[str, str]]:
        """Get cached or load credentials"""
        if self._cached_credentials is None:
            self._cached_credentials = self.settings.load_credentials()
        return self._cached_credentials

    def update_credentials(self, creds: Dict[str, str]) -> None:
        """Update in-memory cache after login"""
        self._cached_credentials = dict(creds)
