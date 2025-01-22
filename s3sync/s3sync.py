import os
import time
import logging
from typing import List, Optional, Dict
import boto3
from botocore.config import Config
from s3transfer import TransferConfig, S3Transfer
from lock import S3SyncLock
from metadata import S3SyncMetadata
from utils import get_local_files

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class S3Sync:
    """Main S3 synchronization class"""

    def __init__(self, 
                 local_path: str,
                 bucket: str,
                 prefix: str,
                 endpoint_url: Optional[str] = None,
                 access_key: Optional[str] = None,
                 secret_key: Optional[str] = None,
                 region: Optional[str] = None,
                 extensions: Optional[List[str]] = None,
                 blacklist: bool = False,
                 progress_callback: Optional[callable] = None,
                 scan_callback: Optional[callable] = None):
        self.local_path = os.path.abspath(local_path)
        self.bucket = bucket
        self.prefix = prefix.rstrip('/')
        self.extensions = set(ext.lower() for ext in (extensions or []))
        self.blacklist = blacklist
        
        config = Config(
            s3={
                'use_accelerate_endpoint': False,
                'addressing_style': 'virtual',
                'payload_signing_enabled': False,
            }
        )
        
        self.s3_client = boto3.client(
            's3',
            config=config,
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        self.metadata = S3SyncMetadata(self.s3_client, bucket, prefix) 

        transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,
            max_concurrency=10
        )

        self.transfer = S3Transfer(self.s3_client, transfer_config)
 
        self.lock = S3SyncLock(
            s3_client=self.s3_client,
            bucket=bucket,
            remote_lock_key=f"{prefix}/.sync_lock"
        )

        self.progress_callback = progress_callback or (lambda op, fp: None)
        self.scan_callback = scan_callback or (lambda: None)

    def _get_file_times(self, filepath: str) -> Dict[str, float]:
        """get file creation and modification time"""
        stat = os.stat(filepath)
        try:
            ctime = stat.st_birthtime  # macOS
        except AttributeError:
            ctime = stat.st_ctime  # other system use ctime
        
        return {
            'ctime': ctime,
            'mtime': stat.st_mtime
        }

    def _set_file_times(self, filepath: str, times: Dict[str, float]):
        """set file access and modification time"""
        os.utime(filepath, (times['mtime'], times['mtime']))

    def _upload_file(self, rel_path: str, s3_key: str):
        """Upload a file to S3"""
        try:
            local_path = os.path.join(self.local_path, rel_path)
            logger.info(f"上传: {rel_path}")
            
            self.s3_client.upload_file(local_path, self.bucket, s3_key)
            
            self.progress_callback('upload', rel_path)
        except Exception as e:
            logger.error(f"upload {rel_path} failed: {str(e)}")
            self.progress_callback('fail', rel_path)
            raise

    def _download_file(self, rel_path: str, s3_key: str, file_times: Dict[str, float]):
        """Download a file from S3"""
        try:
            local_path = os.path.join(self.local_path, rel_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            logger.info(f"下载: {rel_path}")
            
            self.s3_client.download_file(self.bucket, s3_key, local_path)
            
            if file_times:
                self._set_file_times(local_path, file_times)
            
            self.progress_callback('download', rel_path)
        except Exception as e:
            logger.error(f"download {rel_path} failed: {str(e)}")
            self.progress_callback('fail', rel_path)
            raise

    def sync(self):
        """perform sync between local and S3"""
        if not self.lock.acquire():
            logger.error("Another sync process is running")
            return

        try:
            metadata = self.metadata.load()
            local_files = get_local_files(self.local_path, self.extensions, self.blacklist)

            for rel_path, local_mtime in local_files.items():
                s3_key = f"{self.prefix}/{rel_path}"
                
                if rel_path in metadata:
                    s3_mtime = metadata[rel_path]['mtime']
                    
                    if local_mtime > s3_mtime:
                        self._upload_file(rel_path, s3_key)
                        file_times = self._get_file_times(os.path.join(self.local_path, rel_path))
                        metadata[rel_path] = {
                            'ctime': file_times['ctime'],
                            'mtime': file_times['mtime'],
                            'synced_at': time.time()
                        }
                    elif local_mtime < s3_mtime:
                        self._download_file(rel_path, s3_key, metadata.get(rel_path))
                else:
                    self._upload_file(rel_path, s3_key)
                    file_times = self._get_file_times(os.path.join(self.local_path, rel_path))
                    metadata[rel_path] = {
                        'ctime': file_times['ctime'],
                        'mtime': file_times['mtime'],
                        'synced_at': time.time()
                    }

            for rel_path in metadata:
                if rel_path not in local_files:
                    s3_key = f"{self.prefix}/{rel_path}"
                    self._download_file(rel_path, s3_key, metadata.get(rel_path))

            self.metadata.save(metadata)

        finally:
            self.lock.release()

    def get_sync_stats(self) -> tuple[int, int, int]:
        """get sync stats
        Returns:
            tuple: (total_files, to_upload, to_download)
        """
        to_upload = 0
        to_download = 0
        total_files = 0
        
        metadata = self.metadata.load()
        local_files = get_local_files(self.local_path, self.extensions, self.blacklist)
        total_files = len(local_files)

        for rel_path, local_mtime in local_files.items():
            if rel_path in metadata:
                s3_mtime = metadata[rel_path]['mtime']
                if local_mtime != s3_mtime:
                    to_upload += 1
            else:
                to_upload += 1

        for rel_path in metadata:
            if rel_path not in local_files:
                to_download += 1
                total_files += 1

        return total_files, to_upload, to_download