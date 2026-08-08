"""Upload service with multipart and parallel upload support"""
import os
import threading
from typing import List, Dict, Callable, Optional, Any
from .spaces_client import SpacesClient, UploadCancelled
from ..utils.helpers import should_use_multipart, calculate_multipart_chunk_size
from ..utils.object_metadata import UploadMetadataSettings, build_upload_extra_args
from ..utils.logging_config import get_logger

logger = get_logger('upload_service')


class UploadProgress:
    """Tracks upload progress for a file"""
    
    def __init__(self, filename: str, total_size: int):
        self.filename = filename
        self.total_size = total_size
        self.uploaded = 0
        self.status = 'pending'  # pending, uploading, completed, error
        self.error_message: Optional[str] = None
        self.lock = threading.Lock()
    
    def update(self, bytes_uploaded: int):
        """Update uploaded bytes"""
        with self.lock:
            self.uploaded += bytes_uploaded
    
    def set_status(self, status: str, error_message: Optional[str] = None):
        """Set upload status"""
        with self.lock:
            self.status = status
            if error_message:
                self.error_message = error_message
    
    def get_progress(self) -> float:
        """Get progress percentage"""
        with self.lock:
            if self.total_size == 0:
                return 0.0
            return min(100.0, (self.uploaded / self.total_size) * 100.0)


class UploadService:
    """Service for uploading files to DigitalOcean Spaces with optimizations"""
    
    def __init__(self, spaces_client: SpacesClient):
        self.client = spaces_client
        self.active_uploads: Dict[str, UploadProgress] = {}
        self.upload_lock = threading.Lock()
        self._shutdown = threading.Event()

    def _is_cancelled(self) -> bool:
        return self._shutdown.is_set()
    
    def upload_file(self, local_path: str, remote_key: str, acl: str = 'private',
                   progress_callback: Optional[Callable[[str, float, int, float, bool, int, int], None]] = None,
                   metadata_settings: Optional[UploadMetadataSettings] = None) -> bool:
        """
        Upload a single file
        
        Args:
            local_path: Local file path
            remote_key: Remote object key
            acl: 'private' or 'public-read'
            progress_callback: Callback function(filename, progress_percent, uploaded_bytes, speed_mbps, is_multipart, multipart_parts, multipart_completed)
        """
        logger.info(f"upload_file() çağrıldı: {local_path} -> {remote_key}")
        if self._shutdown.is_set():
            logger.warning("Shutdown is set, upload iptal edildi")
            return False
            
        if not os.path.exists(local_path):
            logger.error(f"Dosya bulunamadı: {local_path}")
            raise Exception(f"Dosya bulunamadı: {local_path}")
        
        file_size = os.path.getsize(local_path)
        filename = os.path.basename(local_path)
        logger.debug(f"Dosya boyutu: {file_size} bytes ({file_size/1024:.2f} KB)")
        
        # Create progress tracker
        progress = UploadProgress(filename, file_size)
        with self.upload_lock:
            self.active_uploads[remote_key] = progress

        extra_args = build_upload_extra_args(local_path, remote_key, acl, metadata_settings)
        
        # Track if any callback was called
        callback_was_called = False
        
        try:
            if self._shutdown.is_set():
                return False
                
            progress.set_status('uploading')
            
            # Send initial progress (0%)
            if progress_callback:
                try:
                    logger.debug("İlk progress callback gönderiliyor (0%)")
                    progress_callback(
                        progress.filename,
                        0.0,  # 0%
                        0,    # 0 bytes
                        0.0,  # 0 MB/s
                        False, # not multipart yet
                        0,    # no parts
                        0     # no completed parts
                    )
                    callback_was_called = True
                    logger.debug("İlk progress callback başarılı")
                except Exception as e:
                    # Don't fail upload if callback fails
                    logger.warning(f"İlk progress callback hatası: {str(e)}", exc_info=True)
            
            # Use multipart for large files
            is_multipart = should_use_multipart(file_size)
            logger.info(f"Multipart kullanılacak mı: {is_multipart} (dosya boyutu: {file_size/1024/1024:.2f} MB, eşik: 100 MB)")
            if is_multipart:
                logger.info("_upload_multipart() çağrılıyor")
                success = self._upload_multipart(
                    local_path, remote_key, acl, progress, progress_callback, extra_args
                )
            else:
                logger.info("_upload_simple() çağrılıyor")
                success = self._upload_simple(
                    local_path, remote_key, acl, progress, progress_callback, extra_args
                )
            logger.info(f"Upload tamamlandı, success={success}: {remote_key}")
            if self._shutdown.is_set():
                if success:
                    logger.warning(f"İptal sonrası arka plan transferi tamamlandı: {remote_key}")
                progress.set_status('error', 'İptal edildi')
                return False
            
            # If upload succeeded but no callbacks were called, send final update
            if success and not callback_was_called and progress_callback:
                try:
                    progress_callback(
                        progress.filename,
                        100.0,  # 100%
                        progress.total_size,
                        0.0,
                        is_multipart,
                        0,
                        0
                    )
                except:
                    pass
                
            if success:
                progress.set_status('completed')
            else:
                progress.set_status('error', 'Yükleme başarısız')
            
            return success
        except UploadCancelled:
            progress.set_status('error', 'İptal edildi')
            return False
        except Exception as e:
            logger.error(f"upload_file() içinde hata: {str(e)}", exc_info=True)
            if not self._shutdown.is_set():
                progress.set_status('error', str(e))
                raise
            return False
        finally:
            # Clean up after a delay (only if not shutting down)
            if not self._shutdown.is_set():
                threading.Timer(5.0, lambda: self._remove_progress(remote_key)).start()
            else:
                self._remove_progress(remote_key)
    
    def _upload_simple(self, local_path: str, remote_key: str, acl: str,
                      progress: UploadProgress,
                      callback: Optional[Callable[[str, float, int, float, bool, int, int], None]],
                      extra_args: Optional[dict] = None) -> bool:
        """Simple upload for smaller files"""
        logger.debug("_upload_simple() başladı")
        import time
        start_time = time.time()
        last_update = start_time
        last_bytes = 0
        callback_count = 0
        
        upload_completed_in_callback = [False]  # Use list to allow modification
        
        def progress_callback(bytes_amount):
            try:
                if self._shutdown.is_set():
                    raise UploadCancelled("İptal edildi")
                nonlocal last_update, last_bytes, callback_count
                callback_count += 1
                if callback_count == 1:
                    logger.info(f">>> _upload_simple: İlk boto3 callback çağrıldı: {bytes_amount} bytes")
                elif callback_count % 50 == 0:  # Log every 50th to reduce spam
                    logger.debug(f"Callback #{callback_count}: {bytes_amount} bytes, total: {progress.uploaded}")
                
                current_time = time.time()
                progress.update(bytes_amount)
                
                # Check if upload is complete (all bytes uploaded)
                is_complete = progress.uploaded >= progress.total_size
                if is_complete and not upload_completed_in_callback[0]:
                    logger.info(f"Upload tamamlandı (callback'te tespit edildi): {progress.uploaded}/{progress.total_size} bytes")
                    upload_completed_in_callback[0] = True
                
                if callback and not self._shutdown.is_set():
                    try:
                        # Calculate speed (outside lock for better performance)
                        time_diff = current_time - last_update
                        speed_mbps = 0.0
                        if time_diff > 0.1:  # Update every 100ms
                            with progress.lock:
                                bytes_diff = progress.uploaded - last_bytes
                            if bytes_diff > 0:
                                speed_bps = bytes_diff / time_diff
                                speed_mbps = speed_bps / (1024 * 1024)
                            last_update = current_time
                            last_bytes = progress.uploaded
                        
                        # Get progress values (minimize lock time)
                        # NOTE: Do NOT call progress.get_progress() inside "with progress.lock" -> deadlock (get_progress acquires lock)
                        with progress.lock:
                            current_uploaded = progress.uploaded
                            filename = progress.filename
                            current_progress = min(100.0, (current_uploaded / progress.total_size) * 100.0) if progress.total_size else 0.0
                        
                        # Log before callback to see if we reach here
                        if callback_count == 1:
                            logger.info(f">>> CALLBACK ÇAĞRILIYOR: filename={filename}, progress={current_progress:.1f}%, uploaded={current_uploaded}")
                            logger.info(f">>> callback fonksiyonu: {callback}, type: {type(callback)}")
                        
                        # If complete, send 100% progress
                        if is_complete:
                            logger.info(f"Callback: Tamamlandı, 100% gönderiliyor")
                            try:
                                callback(
                                    filename, 
                                    100.0,  # 100%
                                    progress.total_size, 
                                    speed_mbps,
                                    False,  # is_multipart
                                    0,      # multipart_parts
                                    0       # multipart_completed
                                )
                                if callback_count == 1:
                                    logger.info(">>> CALLBACK ÇAĞRISI TAMAMLANDI (100%)")
                            except Exception as cb_exc:
                                logger.error(f">>> CALLBACK ÇAĞRISI HATASI (100%): {str(cb_exc)}", exc_info=True)
                                raise
                        else:
                            # Only log every 10th callback to reduce spam
                            if callback_count % 10 == 0:
                                logger.debug(f"Callback: Progress={current_progress:.1f}%, uploaded={current_uploaded}, speed={speed_mbps:.2f} MB/s")
                            
                            try:
                                callback(
                                    filename, 
                                    current_progress, 
                                    current_uploaded, 
                                    speed_mbps,
                                    False,  # is_multipart
                                    0,      # multipart_parts
                                    0       # multipart_completed
                                )
                                if callback_count == 1:
                                    logger.info(">>> CALLBACK ÇAĞRISI TAMAMLANDI (progress)")
                            except Exception as cb_exc:
                                logger.error(f">>> CALLBACK ÇAĞRISI HATASI (progress): {str(cb_exc)}", exc_info=True)
                                # Don't re-raise - let upload continue
                    except Exception as e:
                        # Don't fail upload if callback fails, but log it
                        logger.error(f"Callback içinde hata (upload devam ediyor): {str(e)}", exc_info=True)
            except Exception as e:
                logger.error(f"progress_callback içinde kritik hata: {str(e)}", exc_info=True)
        
        try:
            logger.debug("client.upload_file() çağrılıyor (boto3)")
            
            # Call upload_file - this may hang after callback, but we'll handle it
            try:
                result = self.client.upload_file(
                    local_path, remote_key, acl, callback=progress_callback,
                    should_cancel=self._is_cancelled,
                    extra_args=extra_args,
                )
                logger.debug(f"client.upload_file() tamamlandı, result={result}, callback_count={callback_count}")
            except Exception as upload_err:
                # If upload failed but callback detected completion, assume success
                if upload_completed_in_callback[0]:
                    logger.warning(f"Upload exception ama callback'te tamamlandı: {str(upload_err)}")
                    logger.info("Başarılı kabul ediliyor")
                    result = True
                else:
                    raise
            
            # Ensure final progress is sent if upload completed in callback
            if upload_completed_in_callback[0] and callback and not self._shutdown.is_set():
                logger.debug("Final progress update gönderiliyor (callback'te tamamlandı)")
                try:
                    with progress.lock:
                        progress.uploaded = progress.total_size
                        callback(
                            progress.filename,
                            100.0,
                            progress.total_size,
                            0.0,
                            False,
                            0,
                            0
                        )
                except Exception as e:
                    logger.warning(f"Final callback hatası: {str(e)}")
            
            # If no callbacks were called (very small/fast file), send final update
            if callback_count == 0 and callback and not self._shutdown.is_set():
                logger.debug("Hiç callback çağrılmadı, final update gönderiliyor")
                try:
                    with progress.lock:
                        progress.uploaded = progress.total_size
                        callback(
                            progress.filename,
                            100.0,
                            progress.total_size,
                            0.0,
                            False,
                            0,
                            0
                        )
                except:
                    pass
            
            return result
        except Exception as e:
            logger.error(f"_upload_simple() içinde hata: {str(e)}", exc_info=True)
            # Send error callback if available
            if callback and not self._shutdown.is_set():
                try:
                    callback(
                        progress.filename,
                        progress.get_progress(),
                        progress.uploaded,
                        0.0,
                        False,
                        0,
                        0
                    )
                except:
                    pass
            raise
    
    def _upload_multipart(self, local_path: str, remote_key: str, acl: str,
                         progress: UploadProgress,
                         callback: Optional[Callable[[str, float, int, float, bool, int, int], None]],
                         extra_args: Optional[dict] = None) -> bool:
        """
        Multipart upload for large files
        Note: boto3 handles multipart automatically, but we can optimize chunk size
        """
        import time
        from ..utils.helpers import calculate_multipart_chunk_size
        
        # Calculate multipart info
        chunk_size = calculate_multipart_chunk_size(progress.total_size)
        total_parts = (progress.total_size + chunk_size - 1) // chunk_size
        completed_parts = 0
        last_part_bytes = 0
        
        start_time = time.time()
        last_update = start_time
        last_bytes = 0
        
        callback_count = 0
        
        def progress_callback(bytes_amount):
            if self._shutdown.is_set():
                raise UploadCancelled("İptal edildi")
            nonlocal completed_parts, last_part_bytes, last_update, last_bytes, callback_count
            callback_count += 1
            if callback_count == 1:
                logger.info(f">>> _upload_multipart: İlk boto3 callback çağrıldı: {bytes_amount} bytes")
            elif callback_count % 50 == 0:
                logger.debug(f"_upload_multipart Callback #{callback_count}: {bytes_amount} bytes, total: {progress.uploaded}")
            current_time = time.time()
            progress.update(bytes_amount)
            
            # Estimate completed parts based on uploaded bytes
            estimated_parts = int(progress.uploaded / chunk_size) if chunk_size > 0 else 0
            completed_parts = min(estimated_parts, total_parts)
            
            if callback and not self._shutdown.is_set():
                try:
                    # Get values from progress (minimize lock time)
                    # NOTE: Do NOT call progress.get_progress() inside "with progress.lock" - get_progress() also acquires the lock -> deadlock!
                    with progress.lock:
                        current_uploaded = progress.uploaded
                        filename = progress.filename
                        current_progress = min(100.0, (current_uploaded / progress.total_size) * 100.0) if progress.total_size else 0.0
                    
                    # Calculate speed (outside lock for better performance)
                    time_diff = current_time - last_update
                    speed_mbps = 0.0
                    if time_diff > 0.1:  # Update every 100ms
                        bytes_diff = current_uploaded - last_bytes
                        if bytes_diff > 0:
                            speed_bps = bytes_diff / time_diff
                            speed_mbps = speed_bps / (1024 * 1024)
                        last_update = current_time
                        last_bytes = current_uploaded
                    
                    if callback_count == 1:
                        logger.info(f">>> _upload_multipart: callback() çağrılıyor: filename={filename}, progress={current_progress:.1f}%, uploaded={current_uploaded}, speed={speed_mbps:.2f} MB/s, parts={completed_parts}/{total_parts}")
                        logger.info(f">>> _upload_multipart: callback fonksiyonu: {callback}, type: {type(callback)}")
                    
                    # Call callback OUTSIDE lock to prevent blocking
                    try:
                        callback(
                            filename, 
                            current_progress, 
                            current_uploaded, 
                            speed_mbps,
                            True,           # is_multipart
                            total_parts,    # multipart_parts
                            completed_parts  # multipart_completed
                        )
                        if callback_count == 1:
                            logger.info(f">>> _upload_multipart: callback() çağrısı TAMAMLANDI")
                    except Exception as cb_exc:
                        logger.error(f">>> _upload_multipart: callback() HATASI: {str(cb_exc)}", exc_info=True)
                        # Don't re-raise - let upload continue
                except Exception as e:
                    # Don't fail upload if callback fails
                    logger.error(f">>> _upload_multipart: progress_callback içinde kritik hata: {str(e)}", exc_info=True)
        
        try:
            result = self.client.upload_file(
                local_path, remote_key, acl, callback=progress_callback,
                should_cancel=self._is_cancelled,
                extra_args=extra_args,
            )
            
            # If no callbacks were called, send final update
            if callback_count == 0 and callback and not self._shutdown.is_set():
                try:
                    with progress.lock:
                        progress.uploaded = progress.total_size
                        callback(
                            progress.filename,
                            100.0,
                            progress.total_size,
                            0.0,
                            True,
                            total_parts,
                            total_parts
                        )
                except:
                    pass
            
            return result
        except Exception as e:
            # Send error callback if available
            if callback and not self._shutdown.is_set():
                try:
                    callback(
                        progress.filename,
                        progress.get_progress(),
                        progress.uploaded,
                        0.0,
                        True,
                        total_parts,
                        completed_parts
                    )
                except:
                    pass
            raise
    
    def shutdown(self):
        """Shutdown service and stop all uploads"""
        self._shutdown.set()
        with self.upload_lock:
            for progress in self.active_uploads.values():
                progress.set_status('error', 'İptal edildi')
            self.active_uploads.clear()
        try:
            self.client.cancel_active_transfers()
        except Exception as e:
            logger.warning(f"Upload iptal bağlantı kesme hatası: {e}")
    
    def _remove_progress(self, remote_key: str):
        """Remove progress tracker after delay"""
        with self.upload_lock:
            self.active_uploads.pop(remote_key, None)
