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
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

console = Console()

class SyncStats:
    def __init__(self, local_path, extensions=None, blacklist=False):
        self.uploaded = 0
        self.downloaded = 0
        self.skipped = 0
        self.failed = 0
        self.start_time = time.time()
        self.total_scanned = 0
        self.to_upload = 0
        self.to_download = 0
        
    def update_scan_stats(self, total_files, to_upload, to_download):
        """update scan stats"""
        self.total_scanned = total_files
        self.to_upload = to_upload
        self.to_download = to_download
        
        table = Table(box=box.ROUNDED, show_header=False, border_style="bright_blue")
        table.add_column("Item", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("scan file count", f"{self.total_scanned:,} files")
        table.add_row("to upload", f"[yellow]↑ {self.to_upload:,} files[/yellow]")
        table.add_row("to download", f"[yellow]↓ {self.to_download:,} files[/yellow]")
        table.add_row("sync file count", f"[cyan]{self.to_upload + self.to_download:,} files[/cyan]")
        
        panel = Panel(
            table,
            title="[bold cyan]scan result[/bold cyan]",
            border_style="bright_blue",
            padding=(1, 2)
        )
        
        console.print(panel)

    
    def start_sync_progress(self):
        """start sync"""
        # 创建同步进度条
        self.pbar = tqdm(
            total=self.to_upload + self.to_download,
            desc="syncing...",
            unit="files",
            bar_format="{desc:<30} |{bar:50}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {percentage:3.0f}%",
            colour="green",
            ncols=120,
            position=0,
            leave=True
        )

    def update_progress(self, operation, filepath):
        """update progress bar and stats"""
        filename = os.path.basename(filepath)
        if operation == 'upload':
            self.uploaded += 1
            self.pbar.set_description(f"↑ uploading: {filename[:30]:<30}")
        elif operation == 'download':
            self.downloaded += 1
            self.pbar.set_description(f"↓ downloading: {filename[:30]:<30}")
        elif operation == 'skip':
            self.skipped += 1
            self.pbar.set_description(f"○ skipped: {filename[:30]:<30}")
        elif operation == 'fail':
            self.failed += 1
            self.pbar.set_description(f"× failed: {filename[:30]:<30}")
        
        self.pbar.update(1)

    def print_summary(self):
        """print summary"""
        self.pbar.close()
        elapsed_time = time.time() - self.start_time

        table = Table(box=box.ROUNDED, show_header=False, border_style="bright_blue")
        table.add_column("Item", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("file count", f"{self.uploaded + self.downloaded:,} files")
        table.add_row("upload file", f"[green]✓ {self.uploaded:,} files[/green]")
        table.add_row("download file", f"[green]✓ {self.downloaded:,} files[/green]")
        table.add_row("skip file", f"[yellow]- {self.skipped:,} files[/yellow]")
        table.add_row("failed file", f"[red]× {self.failed:,} files[/red]")
        table.add_row("total time", f"{elapsed_time:.1f} seconds")
        
        panel = Panel(
            table,
            title="[bold cyan]sync complete statistics[/bold cyan]",
            border_style="bright_blue",
            padding=(1, 2)
        )
        
        console.print("\n")
        console.print(panel)

def configure(args):
    """configure credentials"""
    config = Config()
    access_key = input("Access Key ID: ").strip()
    secret_key = input("Secret Access Key: ").strip()
    profile = args.profile or "default"
    
    config.set_credentials(access_key, secret_key, profile)
    console.print(f"[green]Credentials saved to profile '{profile}'[/green]")

def main():
    parser = argparse.ArgumentParser(description='S3 Sync Tool')
    subparsers = parser.add_subparsers(dest='command')

    # configure command
    configure_parser = subparsers.add_parser('configure', help='Configure credentials')
    configure_parser.add_argument('--profile', help='Configuration profile name')

    # sync command
    sync_parser = subparsers.add_parser('sync', help='Sync files with S3')
    sync_parser.add_argument('local_path', help='Local directory path')
    sync_parser.add_argument('--bucket', help='S3 bucket name')
    sync_parser.add_argument('--prefix', help='S3 key prefix')
    sync_parser.add_argument('--endpoint-url', help='S3-compatible service endpoint URL')
    sync_parser.add_argument('--access-key', help='Access key ID')
    sync_parser.add_argument('--secret-key', help='Secret access key')
    sync_parser.add_argument('--profile', default='default', help='Configuration profile name')
    sync_parser.add_argument('--region', help='Region name')
    sync_parser.add_argument('--extensions', nargs='+', help='File extensions to process')
    sync_parser.add_argument('--blacklist', action='store_true', help='Treat extensions as blacklist')

    args = parser.parse_args()

    if args.command == 'configure':
        configure(args)
        return

    if args.command == 'sync':
        # get credentials
        config = Config()
        access_key = args.access_key
        secret_key = args.secret_key

        # if command line not provide credentials, get from config file
        if not (access_key and secret_key):
            access_key, secret_key = config.get_credentials(args.profile)
            if not (access_key and secret_key):
                console.print("[red]Error: No credentials provided. Please run 's3rs configure' first or provide credentials via command line.[/red]")
                sys.exit(1)

        # Load config from file
        file_config = Config.load_config(args.local_path)
        
        # Convert args to dict and merge with file config
        cli_config = vars(args)
        config = Config.merge_config(file_config, cli_config)
        
        # Validate required parameters
        if not config.get('bucket'):
            console.print("[red]Bucket must be specified either in config file or command line[/red]")
            sys.exit(1)
        
        if not config.get('prefix'):
            # Set default prefix to empty string if not specified
            config['prefix'] = ''
            console.print("[yellow]No prefix specified, using root of bucket[/yellow]")

        try:
            stats = SyncStats(
                local_path=args.local_path,
                extensions=args.extensions,
                blacklist=args.blacklist
            )
            
            syncer = S3Sync(
                local_path=args.local_path,
                bucket=config['bucket'],
                prefix=config['prefix'],
                endpoint_url=config['endpoint_url'],
                access_key=access_key,
                secret_key=secret_key,
                region=config['region'],
                extensions=config['extensions'],
                blacklist=config['blacklist'],
                progress_callback=lambda op, fp: stats.update_progress(op, fp)
            )

            # get sync file stats
            total_files, to_upload, to_download = syncer.get_sync_stats()
            stats.update_scan_stats(total_files, to_upload, to_download)
            
            if to_upload + to_download > 0:
                stats.start_sync_progress()
                syncer.sync()
                stats.print_summary()
            else:
                console.print("[bold red]no files to sync[/bold red]")
        except Exception as e:
            if hasattr(stats, 'pbar'):
                stats.pbar.close()
            console.print(f"[bold red]sync failed: {str(e)}[/bold red]")
            sys.exit(1)

if __name__ == '__main__':
    main() 