"""Utility functions for S3 sync"""

import os
from typing import Set

def should_sync_file(filename: str, extensions: Set[str], blacklist: bool) -> bool:
    """Check if file should be synced based on extension rules"""
    if not extensions:
        return True
        
    ext = os.path.splitext(filename)[1].lower()
    if blacklist:
        return ext not in extensions
    return ext in extensions

def get_local_files(local_path: str, extensions: Set[str], blacklist: bool) -> dict:
    """Get all local files with their modification times"""
    local_files = {}
    for root, _, files in os.walk(local_path):
        for filename in files:
            if should_sync_file(filename, extensions, blacklist):
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, local_path)
                local_files[rel_path] = os.path.getmtime(full_path)
    return local_files 