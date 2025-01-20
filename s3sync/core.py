"""Core S3 sync functionality"""

import os
import time
import logging
from typing import List, Set, Optional
import boto3
from botocore.config import Config
from .lock import S3SyncLock
from .metadata import S3SyncMetadata
from .utils import get_local_files

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
        
        # Initialize S3 client with virtual hosted style configuration
        config = Config(
            s3={'addressing_style': 'virtual'},
            region_name=region or 'us-east-1'
        )
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=config
        )
        
        # Initialize metadata handler
        self.metadata = S3SyncMetadata(self.s3_client, bucket, prefix)
        
        # Initialize lock
        lock_dir = os.path.expanduser('~/.s3sync')
        os.makedirs(lock_dir, exist_ok=True)
        self.lock = S3SyncLock(f"{lock_dir}/{bucket}_{prefix.replace('/', '_')}.lock")

    def sync(self):
        """Perform synchronization between local and S3"""
        if not self.lock.acquire():
            logger.error("Another sync process is running")
            return

        try:
            # Load metadata
            metadata = self.metadata.load()
            local_files = get_local_files(self.local_path, self.extensions, self.blacklist)

            # Compare and sync files
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

            # Check for files to download
            for rel_path in metadata:
                if rel_path not in local_files:
                    s3_key = f"{self.prefix}/{rel_path}"
                    self._download_file(rel_path, s3_key)

            # Save updated metadata
            self.metadata.save(metadata)

        finally:
            self.lock.release()

    def _upload_file(self, rel_path: str, s3_key: str):
        """Upload a file to S3"""
        local_path = os.path.join(self.local_path, rel_path)
        logger.info(f"Uploading: {rel_path}")
        self.s3_client.upload_file(local_path, self.bucket, s3_key)

    def _download_file(self, rel_path: str, s3_key: str):
        """Download a file from S3"""
        local_path = os.path.join(self.local_path, rel_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        logger.info(f"Downloading: {rel_path}")
        self.s3_client.download_file(self.bucket, s3_key, local_path) 