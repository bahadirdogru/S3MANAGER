"""Input validation utilities"""
import re
from typing import Optional, Tuple


def validate_spaces_key(key: str) -> Tuple[bool, Optional[str]]:
    """Validate DigitalOcean Spaces key"""
    if not key or len(key.strip()) == 0:
        return False, "Spaces key boş olamaz"
    if len(key) < 20:
        return False, "Spaces key çok kısa görünüyor"
    return True, None


def validate_spaces_secret(secret: str) -> Tuple[bool, Optional[str]]:
    """Validate DigitalOcean Spaces secret"""
    if not secret or len(secret.strip()) == 0:
        return False, "Spaces secret boş olamaz"
    if len(secret) < 40:
        return False, "Spaces secret çok kısa görünüyor"
    return True, None


def validate_bucket_name(bucket: str) -> Tuple[bool, Optional[str]]:
    """Validate bucket name"""
    if not bucket or len(bucket.strip()) == 0:
        return False, "Bucket adı boş olamaz"
    
    # Bucket name rules: 3-63 chars, lowercase, alphanumeric and hyphens
    if len(bucket) < 3 or len(bucket) > 63:
        return False, "Bucket adı 3-63 karakter arasında olmalı"
    
    if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', bucket):
        return False, "Bucket adı sadece küçük harf, rakam ve tire içerebilir"
    
    return True, None


def validate_endpoint(endpoint: str) -> Tuple[bool, Optional[str]]:
    """Validate endpoint URL"""
    if not endpoint or len(endpoint.strip()) == 0:
        return False, "Endpoint boş olamaz"
    
    if not endpoint.startswith('http://') and not endpoint.startswith('https://'):
        return False, "Endpoint geçerli bir URL olmalı (http:// veya https:// ile başlamalı)"
    
    return True, None


def validate_region(region: str) -> Tuple[bool, Optional[str]]:
    """Validate region"""
    valid_regions = ['nyc3', 'sfo3', 'sgp1', 'ams3', 'fra1', 'blr1']
    if region.lower() not in valid_regions:
        return False, f"Geçerli bir bölge seçin: {', '.join(valid_regions)}"
    return True, None
