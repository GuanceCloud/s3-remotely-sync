#!/usr/bin/env python3

"""
Command-line interface for S3 Sync Tool
"""

import sys
import logging
import argparse
import os
from s3sync import S3Sync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='S3 Sync Tool')
    parser.add_argument('local_path', help='Local directory path')
    parser.add_argument('bucket', help='S3 bucket name')
    parser.add_argument('prefix', help='S3 prefix (directory)')
    parser.add_argument('--endpoint-url', help='S3-compatible service endpoint URL')
    parser.add_argument('--access-key', help='Access key ID')
    parser.add_argument('--secret-key', help='Secret access key')
    parser.add_argument('--region', help='Region name (e.g., oss-cn-beijing)')
    parser.add_argument('--extensions', nargs='+', help='File extensions to include/exclude')
    parser.add_argument('--blacklist', action='store_true', 
                       help='Treat extensions as blacklist instead of whitelist')

    args = parser.parse_args()

    # Get credentials from environment variables if not provided in arguments
    access_key = args.access_key or os.environ.get('OSS_ACCESS_KEY_ID') or os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = args.secret_key or os.environ.get('OSS_SECRET_ACCESS_KEY') or os.environ.get('AWS_SECRET_ACCESS_KEY')
    region = args.region or os.environ.get('OSS_REGION') or os.environ.get('AWS_DEFAULT_REGION')

    if not access_key or not secret_key:
        logger.error("Access key and secret key must be provided either through arguments or environment variables")
        sys.exit(1)

    syncer = S3Sync(
        local_path=args.local_path,
        bucket=args.bucket,
        prefix=args.prefix,
        endpoint_url=args.endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        extensions=args.extensions,
        blacklist=args.blacklist
    )

    try:
        syncer.sync()
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 