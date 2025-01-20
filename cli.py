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
    def __init__(self, local_path, extensions=None, blacklist=False):
        self.uploaded = 0
        self.downloaded = 0
        self.skipped = 0
        self.failed = 0
        self.start_time = time.time()
        
        # 创建扫描进度条
        self.scan_pbar = tqdm(
            desc="扫描文件中",
            unit="files",
            bar_format="{desc:<30} |{bar:50}| {n_fmt} files scanned",
            colour="cyan",
            ncols=120,
            position=0,
            leave=True
        )
        
        # 先扫描获取文件总数
        self.total_files = self._count_files(local_path, extensions, blacklist)
        self.scan_pbar.close()
        
        # 创建同步进度条
        self.pbar = tqdm(
            total=self.total_files,
            desc="准备同步",
            unit="files",
            bar_format="{desc:<30} |{bar:50}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}] {percentage:3.0f}%",
            colour="green",
            ncols=120,
            position=0,
            leave=True
        )

    def _count_files(self, local_path, extensions, blacklist):
        """计算需要同步的文件总数"""
        total = 0
        for root, _, files in os.walk(local_path):
            for file in files:
                if extensions:
                    ext = os.path.splitext(file)[1].lower()
                    if blacklist == (ext in extensions):
                        continue
                total += 1
                self.scan_pbar.update(1)
        return total

    def update_progress(self, operation, filepath):
        """更新进度条和统计信息"""
        filename = os.path.basename(filepath)
        if operation == 'upload':
            self.uploaded += 1
            self.pbar.set_description(f"↑ 上传: {filename[:30]:<30}")
        elif operation == 'download':
            self.downloaded += 1
            self.pbar.set_description(f"↓ 下载: {filename[:30]:<30}")
        elif operation == 'skip':
            self.skipped += 1
            self.pbar.set_description(f"○ 跳过: {filename[:30]:<30}")
        elif operation == 'fail':
            self.failed += 1
            self.pbar.set_description(f"× 失败: {filename[:30]:<30}")
        
        self.pbar.update(1)

    def print_summary(self):
        self.pbar.close()
        elapsed_time = time.time() - self.start_time
        total_files = self.uploaded + self.downloaded + self.skipped + self.failed

        # 创建统计表格
        table = Table(box=box.ROUNDED, show_header=False, border_style="bright_blue")
        table.add_column("Item", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("file count", f"{total_files:,} files")
        table.add_row("upload file", f"[green]✓ {self.uploaded:,} 个[/green]")
        table.add_row("download file", f"[green]✓ {self.downloaded:,} 个[/green]")
        table.add_row("skip file", f"[yellow]- {self.skipped:,} 个[/yellow]")
        table.add_row("failed file", f"[red]× {self.failed:,} 个[/red]")
        table.add_row("total time", f"{elapsed_time:.1f} seconds")
        
        panel = Panel(
            table,
            title="[bold cyan]sync complete statistics[/bold cyan]",
            border_style="bright_blue",
            padding=(1, 2)
        )
        
        console.print("\n")
        console.print(panel)

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

    try:
        stats = SyncStats(
            local_path=args.local_path,
            extensions=args.extensions,
            blacklist=args.blacklist
        )
        
        console.print("\n[bold cyan]开始同步...[/bold cyan]\n")
        
        def progress_callback(operation, filepath):
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

        syncer.sync()
        stats.print_summary()
    except Exception as e:
        if hasattr(stats, 'pbar'):
            stats.pbar.close()
        console.print(f"[bold red]同步失败: {str(e)}[/bold red]")
        sys.exit(1)

if __name__ == '__main__':
    main() 