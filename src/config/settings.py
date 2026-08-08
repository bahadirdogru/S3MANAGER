"""Configuration settings management"""
import configparser
from pathlib import Path
from typing import Optional, Dict

from ..utils.logging_config import get_logger
from ..utils.paths import get_config_dir

logger = get_logger('settings')


class Settings:
    """Manages application settings from config.ini file"""
    
    def __init__(self):
        self.config_dir = get_config_dir()
        self.config_file = self.config_dir / "config.ini"
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)
    
    def load_credentials(self) -> Optional[Dict[str, str]]:
        """
        Load credentials from config.ini
        Returns dict with credentials or None if not found
        """
        # Try config.ini
        if self.config_file.exists():
            config = configparser.ConfigParser()
            config.read(self.config_file)
            if 'digitalocean' in config:
                do_config = config['digitalocean']
                credentials = {
                    'key': do_config.get('spaces_key'),
                    'secret': do_config.get('spaces_secret'),
                    'region': do_config.get('region', 'nyc3'),
                    'endpoint': do_config.get('endpoint'),
                    'bucket': do_config.get('bucket')
                }
                if all(credentials.values()):
                    return credentials
        
        return None
    
    def save_credentials(self, key: str, secret: str, region: str, endpoint: str, bucket: str) -> bool:
        """Save credentials to config.ini file"""
        try:
            config = configparser.ConfigParser()
            if self.config_file.exists():
                config.read(self.config_file)
            
            if 'digitalocean' not in config:
                config.add_section('digitalocean')
            
            config['digitalocean']['spaces_key'] = key
            config['digitalocean']['spaces_secret'] = secret
            config['digitalocean']['region'] = region
            config['digitalocean']['endpoint'] = endpoint
            config['digitalocean']['bucket'] = bucket
            
            with open(self.config_file, 'w') as f:
                config.write(f)
            
            return True
        except Exception as e:
            logger.error(f"Credential kaydetme hatası: {e}")
            return False
    
    def get_default_region_endpoint(self, region: str) -> str:
        """Get default endpoint URL for a region"""
        endpoints = {
            'nyc3': 'https://nyc3.digitaloceanspaces.com',
            'sfo3': 'https://sfo3.digitaloceanspaces.com',
            'sgp1': 'https://sgp1.digitaloceanspaces.com',
            'ams3': 'https://ams3.digitaloceanspaces.com',
            'fra1': 'https://fra1.digitaloceanspaces.com',
            'blr1': 'https://blr1.digitaloceanspaces.com'
        }
        return endpoints.get(region, f'https://{region}.digitaloceanspaces.com')

    def get_dismissed_update_version(self) -> Optional[str]:
        if not self.config_file.exists():
            return None
        config = configparser.ConfigParser()
        config.read(self.config_file)
        if 'updates' in config:
            return config['updates'].get('dismissed_version') or None
        return None

    def set_dismissed_update_version(self, version: str) -> bool:
        try:
            config = configparser.ConfigParser()
            if self.config_file.exists():
                config.read(self.config_file)
            if 'updates' not in config:
                config.add_section('updates')
            config['updates']['dismissed_version'] = version
            with open(self.config_file, 'w') as f:
                config.write(f)
            return True
        except Exception as e:
            logger.error(f"Guncelleme tercihi kaydetme hatasi: {e}")
            return False
