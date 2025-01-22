"""Lock mechanism for multi-user synchronization using S3"""

import os
import socket
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class S3SyncLock:
    """S3-based locking mechanism for multi-user synchronization"""
    
    def __init__(self, s3_client, bucket: str, remote_lock_key: str = '.sync_lock', remote_ttl_seconds: int = 60 * 15):
        """Initialize the S3SyncLock"""
        """
        s3_client: boto3.client (S3 client)
        bucket: str (S3 bucket name)
        remote_lock_key: str (default: '.sync_lock')
        remote_ttl_seconds: int (default: 15 minutes)
        """

        # Remote lock configuration
        self.s3_client = s3_client
        self.bucket = bucket
        self.remote_lock_key = remote_lock_key
        self.remote_ttl_seconds = remote_ttl_seconds
        
        # User identification
        self.user_id = f"{os.getenv('USER', 'unknown')}@{socket.gethostname()}"

    def _get_remote_lock_info(self) -> Optional[dict]:
        """Get current remote lock information from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=self.remote_lock_key
            )
            return json.loads(response['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise

    def _is_remote_lock_expired(self, lock_info: dict) -> bool:
        """Check if the existing remote lock has expired"""
        lock_time = datetime.fromisoformat(lock_info['timestamp'])
        current_time = datetime.now(timezone.utc)
        return (current_time - lock_time).total_seconds() > self.remote_ttl_seconds

    def acquire(self) -> bool:
        """Acquire remote lock for synchronization"""
        current_lock = self._get_remote_lock_info()
        
        if current_lock:
            if not self._is_remote_lock_expired(current_lock):
                raise Exception(
                    f"Remote sync is in progress by {current_lock['user_id']} "
                    f"(started at {current_lock['timestamp']})"
                )
            
        lock_data = {
            'user_id': self.user_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=self.remote_lock_key,
                Body=json.dumps(lock_data),
                ContentType='application/json'
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to acquire remote lock: {e}")
            return False

    def release(self):
        """Release remote lock"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=self.remote_lock_key
            )
        except ClientError as e:
            logger.error(f"Failed to release remote lock: {e}")
            raise

    def __enter__(self):
        """Context manager support"""
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.release() 