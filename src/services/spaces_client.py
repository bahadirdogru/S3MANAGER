"""DigitalOcean Spaces client wrapper using boto3"""
import os
import time
from typing import Any, Callable, Dict, List, Optional

import boto3
import boto3.s3.transfer
from botocore.config import Config
from botocore.exceptions import ClientError

from ..utils.helpers import MULTIPART_THRESHOLD_MB
from ..utils.logging_config import get_logger

logger = get_logger('spaces_client')


class UploadCancelled(Exception):
    """Yükleme kullanıcı tarafından iptal edildi."""

_TRANSFER_CONFIG = boto3.s3.transfer.TransferConfig(
    multipart_threshold=MULTIPART_THRESHOLD_MB * 1024 * 1024,
    max_concurrency=3,
    multipart_chunksize=5 * 1024 * 1024,
    use_threads=True,
    num_download_attempts=3,
)


class SpacesClient:
    """Wrapper for boto3 S3 client configured for DigitalOcean Spaces"""

    def __init__(self, key: str, secret: str, region: str, endpoint: str, bucket: str):
        self.key = key
        self.secret = secret
        self.region = region
        self.endpoint = endpoint
        self.bucket = bucket
        self._create_client()

    def _create_client(self):
        session = boto3.Session(aws_access_key_id=self.key, aws_secret_access_key=self.secret)
        config = Config(
            connect_timeout=60,
            read_timeout=300,
            retries={'max_attempts': 3, 'mode': 'standard'},
            max_pool_connections=10,
        )
        self.client = session.client(
            's3',
            region_name=self.region,
            endpoint_url=self.endpoint,
            config=config,
        )

    def cancel_active_transfers(self):
        """Devam eden boto3 transferlerini HTTP oturumunu kapatarak kes."""
        try:
            try:
                self.client.close()
            except Exception:
                pass
            endpoint = getattr(self.client, '_endpoint', None)
            if endpoint is not None:
                http_session = getattr(endpoint, 'http_session', None)
                if http_session is not None:
                    http_session.close()
            logger.info("Aktif transferler için HTTP oturumu kapatıldı")
        except Exception as e:
            logger.warning(f"Transfer iptal hatası: {e}")
        finally:
            self._create_client()

    def test_connection(self) -> tuple[bool, Optional[str]]:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True, None
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code', 'Unknown')
            return False, f"Bağlantı hatası: {code}"
        except Exception as e:
            return False, f"Bağlantı hatası: {str(e)}"

    def list_objects(self, prefix: str = '', delimiter: str = '/') -> Dict[str, Any]:
        try:
            files: List[dict] = []
            folders: List[dict] = []
            paginator = self.client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix, Delimiter=delimiter):
                page_folders, page_files = self._parse_list_page(page, prefix)
                folders.extend(page_folders)
                files.extend(page_files)
            return {'files': files, 'folders': folders, 'prefix': prefix}
        except ClientError as e:
            raise Exception(f"Dosyalar listelenirken hata: {str(e)}")

    def list_objects_page(
        self,
        prefix: str = '',
        delimiter: str = '/',
        continuation_token: Optional[str] = None,
        max_keys: int = 200,
    ) -> Dict[str, Any]:
        try:
            kwargs: Dict[str, Any] = {
                'Bucket': self.bucket,
                'Prefix': prefix,
                'Delimiter': delimiter,
                'MaxKeys': max_keys,
            }
            if continuation_token:
                kwargs['ContinuationToken'] = continuation_token
            page = self.client.list_objects_v2(**kwargs)
            folders, files = self._parse_list_page(page, prefix)
            return {
                'folders': folders,
                'files': files,
                'prefix': prefix,
                'next_continuation_token': page.get('NextContinuationToken'),
                'is_truncated': page.get('IsTruncated', False),
            }
        except ClientError as e:
            raise Exception(f"Dosyalar listelenirken hata: {str(e)}")

    def _parse_list_page(self, page: Dict[str, Any], prefix: str) -> tuple[List[dict], List[dict]]:
        folders: List[dict] = []
        files: List[dict] = []

        for prefix_info in page.get('CommonPrefixes', []):
            folder_path = prefix_info['Prefix']
            if folder_path.startswith('/'):
                folder_path = folder_path[1:]
            if folder_path == prefix:
                continue
            parts = folder_path.rstrip('/').split('/')
            folder_name = parts[-1] if parts else ''
            if not folder_name or not folder_name.strip():
                folder_name = folder_path.rstrip('/') or '(isimsiz)'
            folders.append({'name': folder_name, 'path': folder_path, 'type': 'folder'})

        for obj in page.get('Contents', []):
            if obj['Key'].endswith('/'):
                continue
            file_key = obj['Key']
            if file_key.startswith('/'):
                file_key = file_key[1:]
            if not file_key:
                continue
            file_name = os.path.basename(file_key) or file_key or '(isimsiz)'
            files.append({
                'name': file_name,
                'path': file_key,
                'size': obj['Size'],
                'modified': obj['LastModified'],
                'etag': obj['ETag'].strip('"'),
                'acl': 'unknown',
                'type': 'file',
            })

        return folders, files

    def get_object_acl(self, key: str) -> str:
        try:
            if key.startswith('/'):
                key = key[1:]
            response = self.client.get_object_acl(Bucket=self.bucket, Key=key)
            for grant in response.get('Grants', []):
                grantee = grant.get('Grantee', {})
                if (
                    grantee.get('Type') == 'Group'
                    and grantee.get('URI') == 'http://acs.amazonaws.com/groups/global/AllUsers'
                    and grant.get('Permission') == 'READ'
                ):
                    return 'public-read'
            return 'private'
        except Exception:
            return 'private'

    def upload_file(
        self,
        local_path: str,
        remote_key: str,
        acl: str = 'private',
        callback: Optional[Any] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
        extra_args: Optional[Dict[str, str]] = None,
    ) -> bool:
        try:
            if should_cancel and should_cancel():
                return False

            merged_args: Dict[str, str] = dict(extra_args or {})
            if acl == 'public-read':
                merged_args['ACL'] = 'public-read'

            file_size = os.path.getsize(local_path)

            if file_size < 10 * 1024 * 1024 and callback is None:
                if should_cancel and should_cancel():
                    return False
                with open(local_path, 'rb') as f:
                    self.client.put_object(
                        Bucket=self.bucket, Key=remote_key, Body=f, **merged_args
                    )
                return True

            def wrapped_callback(bytes_amount):
                if should_cancel and should_cancel():
                    raise UploadCancelled("İptal edildi")
                if callback:
                    try:
                        callback(bytes_amount)
                    except Exception as e:
                        logger.warning(f"Upload callback hatası: {e}")

            self.client.upload_file(
                local_path,
                self.bucket,
                remote_key,
                ExtraArgs=merged_args or None,
                Callback=wrapped_callback if (callback or should_cancel) else None,
                Config=_TRANSFER_CONFIG,
            )
            if should_cancel and should_cancel():
                return False
            return True
        except UploadCancelled:
            logger.info(f"Yükleme iptal edildi: {remote_key}")
            return False
        except ClientError as e:
            if should_cancel and should_cancel():
                logger.info(f"Yükleme iptal edildi (bağlantı kesildi): {remote_key}")
                return False
            raise Exception(f"Yükleme hatası: {str(e)}")

    def list_all_keys(self, prefix: str) -> List[Dict[str, Any]]:
        try:
            if prefix.startswith('/'):
                prefix = prefix[1:]
            if prefix and not prefix.endswith('/'):
                prefix = prefix + '/'
            keys: List[dict] = []
            paginator = self.client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if key.endswith('/'):
                        continue
                    keys.append({
                        'key': key,
                        'size': obj.get('Size', 0),
                        'name': os.path.basename(key),
                    })
            return keys
        except ClientError as e:
            raise Exception(f"Liste hatası: {str(e)}")

    def download_file(
        self,
        remote_key: str,
        local_path: str,
        callback: Optional[Callable[[int], None]] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> bool:
        try:
            if should_cancel and should_cancel():
                return False
            if remote_key.startswith('/'):
                remote_key = remote_key[1:]

            def wrapped_callback(bytes_amount):
                if should_cancel and should_cancel():
                    raise UploadCancelled("İptal edildi")
                if callback:
                    callback(bytes_amount)

            self.client.download_file(
                self.bucket,
                remote_key,
                local_path,
                Config=_TRANSFER_CONFIG,
                Callback=wrapped_callback if (callback or should_cancel) else None,
            )
            if should_cancel and should_cancel():
                return False
            return True
        except UploadCancelled:
            logger.info(f"İndirme iptal edildi: {remote_key}")
            return False
        except ClientError as e:
            if should_cancel and should_cancel():
                logger.info(f"İndirme iptal edildi (bağlantı kesildi): {remote_key}")
                return False
            raise Exception(f"İndirme hatası: {str(e)}")

    def create_folder(self, folder_path: str) -> bool:
        try:
            if not folder_path.endswith('/'):
                folder_path += '/'
            self.client.put_object(
                Bucket=self.bucket, Key=folder_path, Body=b'', ACL='private'
            )
            return True
        except ClientError as e:
            raise Exception(f"Klasör oluşturulurken hata: {str(e)}")

    def delete_object(self, key: str) -> bool:
        try:
            if key.startswith('/'):
                key = key[1:]
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            raise Exception(f"Silme hatası: {str(e)}")

    def delete_folder_recursive(self, folder_path: str) -> bool:
        try:
            if folder_path.startswith('/'):
                folder_path = folder_path[1:]
            if not folder_path.endswith('/'):
                folder_path += '/'

            objects_to_delete = []
            paginator = self.client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket, Prefix=folder_path):
                for obj in page.get('Contents', []):
                    objects_to_delete.append({'Key': obj['Key']})

            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i:i + 1000]
                if batch:
                    self.client.delete_objects(
                        Bucket=self.bucket, Delete={'Objects': batch}
                    )
            return True
        except ClientError as e:
            raise Exception(f"Klasör silinirken hata: {str(e)}")

    def create_presigned_url(self, key: str, expiration: int = 3600) -> str:
        try:
            if key.startswith('/'):
                key = key[1:]
            return self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expiration,
            )
        except ClientError as e:
            raise Exception(f"Presigned URL oluşturulurken hata: {str(e)}")
