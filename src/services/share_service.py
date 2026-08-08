"""Share service for creating presigned URLs"""
import pyperclip
from datetime import datetime, timedelta
from .spaces_client import SpacesClient


class ShareService:
    """Service for creating and managing presigned URLs"""
    
    # Expiration times in seconds
    EXPIRATION_3_DAYS = 3 * 24 * 60 * 60  # 259200 seconds
    EXPIRATION_7_DAYS = 7 * 24 * 60 * 60  # 604800 seconds
    
    def __init__(self, spaces_client: SpacesClient):
        self.client = spaces_client
    
    def create_share_link(self, key: str, days: int = 3) -> tuple[str, datetime]:
        """
        Create a presigned URL for sharing
        
        Args:
            key: Object key to share
            days: Number of days until expiration (3 or 7)
        
        Returns:
            Tuple of (presigned_url, expiration_datetime)
        """
        if days not in [3, 7]:
            days = 3  # Default to 3 days
        
        expiration_seconds = self.EXPIRATION_3_DAYS if days == 3 else self.EXPIRATION_7_DAYS
        
        try:
            url = self.client.create_presigned_url(key, expiration_seconds)
            expiration = datetime.now() + timedelta(seconds=expiration_seconds)
            return url, expiration
        except Exception as e:
            raise Exception(f"Paylaşım linki oluşturulurken hata: {str(e)}")
    
    def share_to_clipboard(self, key: str, days: int = 3) -> tuple[str, datetime]:
        """
        Create share link and copy to clipboard
        
        Args:
            key: Object key to share
            days: Number of days until expiration (3 or 7)
        
        Returns:
            Tuple of (presigned_url, expiration_datetime)
        """
        url, expiration = self.create_share_link(key, days)
        
        try:
            pyperclip.copy(url)
            return url, expiration
        except Exception as e:
            # If clipboard fails, still return the URL
            raise Exception(f"Panoya kopyalanırken hata: {str(e)}")
