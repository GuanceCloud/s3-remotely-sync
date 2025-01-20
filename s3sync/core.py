import os
import time
import logging
from typing import List, Optional
import boto3
from botocore.config import Config
from s3transfer import TransferConfig, S3Transfer
from .lock import S3SyncLock
from .metadata import S3SyncMetadata
from .utils import get_local_files

logging.basicConfig(level=logging.INFO)
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
                 blacklist: bool = False):
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
        
        lock_dir = os.path.expanduser('~/.s3sync')
        os.makedirs(lock_dir, exist_ok=True)
        self.lock = S3SyncLock(f"{lock_dir}/{bucket}_{prefix.replace('/', '_')}.lock")

        transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,
            max_concurrency=10
        )

        self.transfer = S3Transfer(self.s3_client, transfer_config)

    def sync(self):
        """Perform synchronization between local and S3"""
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
                        metadata[rel_path] = {
                            'mtime': local_mtime,
                            'synced_at': time.time()
                        }
                    elif local_mtime < s3_mtime:
                        self._download_file(rel_path, s3_key)
                else:
                    self._upload_file(rel_path, s3_key)
                    metadata[rel_path] = {
                        'mtime': local_mtime,
                        'synced_at': time.time()
                    }

            for rel_path in metadata:
                if rel_path not in local_files:
                    s3_key = f"{self.prefix}/{rel_path}"
                    self._download_file(rel_path, s3_key)

            self.metadata.save(metadata)

        finally:
            self.lock.release()

    def _upload_file(self, rel_path: str, s3_key: str):
        """Upload a file to S3"""
        local_path = os.path.join(self.local_path, rel_path)
        logger.info(f"Uploading: {rel_path}")
        self.transfer.upload_file(local_path, self.bucket, s3_key)

    def _download_file(self, rel_path: str, s3_key: str):
        """Download a file from S3"""
        local_path = os.path.join(self.local_path, rel_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        logger.info(f"Downloading: {rel_path}")
        self.transfer.download_file(self.bucket, s3_key, local_path)
