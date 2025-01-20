"""Metadata handling for S3 sync"""

import json
from typing import Dict
from botocore.exceptions import ClientError

class S3SyncMetadata:
    """Handles metadata operations for S3 sync"""

    def __init__(self, s3_client, bucket: str, prefix: str):
        self.s3_client = s3_client
        self.bucket = bucket
        self.prefix = prefix
        self.metadata_key = f"{prefix.rstrip('/')}/.sync_metadata.json"

    def load(self) -> Dict:
        """Load metadata from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=self.metadata_key
            )
            return json.loads(response['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return {}
            raise

    def save(self, metadata: Dict):
        """Save metadata to S3"""
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=self.metadata_key,
            Body=json.dumps(metadata, indent=2).encode('utf-8')
        ) 