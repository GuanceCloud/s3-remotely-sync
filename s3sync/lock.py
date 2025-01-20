"""Lock mechanism for multi-user synchronization"""

import os
import fcntl

class S3SyncLock:
    """File-based locking mechanism for multi-user synchronization"""
    
    def __init__(self, lock_file: str):
        self.lock_file = lock_file
        self.lock_handle = None

    def acquire(self):
        """Acquire a lock for synchronization"""
        self.lock_handle = open(self.lock_file, 'w')
        try:
            fcntl.flock(self.lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except IOError:
            return False

    def release(self):
        """Release the acquired lock"""
        if self.lock_handle:
            fcntl.flock(self.lock_handle, fcntl.LOCK_UN)
            self.lock_handle.close()
            self.lock_handle = None 