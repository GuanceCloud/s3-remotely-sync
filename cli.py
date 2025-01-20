#!/usr/bin/env python3

"""
Command-line interface for S3 Sync Tool
"""

import sys
import logging
import argparse
import os
from s3sync import S3Sync
from tqdm import tqdm
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

class SyncStats:
    def __init__(self):
        self.uploaded = 0
        self.downloaded = 0
        self.skipped = 0
        self.failed = 0
        self.start_time = time.time()
        # create progress bar
        self.pbar = tqdm(
            total=None,  # total unknown
            desc="sync progress",
            unit="files",
            bar_format="{desc}: {n_fmt} files |{bar}| {percentage:3.0f}% [{elapsed}<{remaining}]",
            colour="green"
        )

    def print_summary(self):
        self.pbar.close()
        elapsed_time = time.time() - self.start_time
        total_files = self.uploaded + self.downloaded + self.skipped + self.failed

        # create statistics table
        table = Table(box=box.ROUNDED, show_header=False, border_style="bright_blue")
        table.add_column("Item", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("file count", f"{total_files:,} files")
        table.add_row("upload file", f"[green]✓ {self.uploaded:,} 个[/green]")
        table.add_row("download file", f"[green]✓ {self.downloaded:,} 个[/green]")
        table.add_row("skip file", f"[yellow]- {self.skipped:,} 个[/yellow]")
        table.add_row("failed file", f"[red]× {self.failed:,} 个[/red]")
        table.add_row("total time", f"{elapsed_time:.1f} seconds")
        
        # use panel to wrap statistics
        panel = Panel(
            table,
            title="[bold cyan]sync complete statistics[/bold cyan]",
            border_style="bright_blue",
            padding=(1, 2)
        )
        
        console.print("\n")  # add empty line
        console.print(panel)

    def update_progress(self, operation, filepath):
        """update progress bar and statistics"""
        if operation == 'upload':
            self.uploaded += 1
            self.pbar.set_description(f"uploading: {os.path.basename(filepath)}")
        elif operation == 'download':
            self.downloaded += 1
            self.pbar.set_description(f"downloading: {os.path.basename(filepath)}")
        elif operation == 'skip':
            self.skipped += 1
            self.pbar.set_description(f"skip: {os.path.basename(filepath)}")
        elif operation == 'fail':
            self.failed += 1
            self.pbar.set_description(f"failed: {os.path.basename(filepath)}")
        
        self.pbar.update(1)

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

    stats = SyncStats()
    
    def progress_callback(operation, filepath):
        """progress callback function"""
        stats.update_progress(operation, filepath)
        
    syncer = S3Sync(
        local_path=args.local_path,
        bucket=args.bucket,
        prefix=args.prefix,
        endpoint_url=args.endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        extensions=args.extensions,
        blacklist=args.blacklist,
        progress_callback=progress_callback
    )

    try:
        console.print("[bold cyan]start sync...[/bold cyan]")
        syncer.sync()
        stats.print_summary()
    except Exception as e:
        stats.pbar.close()
        console.print(f"[bold red]sync failed: {str(e)}[/bold red]")
        sys.exit(1)

if __name__ == '__main__':
    main() 