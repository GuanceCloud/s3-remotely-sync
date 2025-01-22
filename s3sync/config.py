"""Configuration handler for S3 Sync Tool"""

import os
import yaml
from typing import Optional, Dict, List

class Config:
    """Configuration handler"""
    
    DEFAULT_CONFIG_FILE = '.s3-remotely-sync.yml'
    
    @staticmethod
    def load_config(local_path: str) -> Dict:
        """Load configuration from YAML file"""
        config_path = os.path.join(local_path, Config.DEFAULT_CONFIG_FILE)
        if not os.path.exists(config_path):
            return {}
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}")
            return {}
    
    @staticmethod
    def merge_config(file_config: Dict, cli_args: Dict) -> Dict:
        """Merge file config with CLI arguments, CLI args take precedence"""
        config = {
            'bucket': cli_args.get('bucket') or file_config.get('bucket'),
            'prefix': cli_args.get('prefix') or file_config.get('prefix'),
            'endpoint_url': cli_args.get('endpoint_url') or file_config.get('endpoint-url'),
            'region': cli_args.get('region') or file_config.get('region'),
            'extensions': cli_args.get('extensions') or file_config.get('extensions'),
            'blacklist': cli_args.get('blacklist') or file_config.get('blacklist', False)
        }
        
        # Remove None values
        return {k: v for k, v in config.items() if v is not None} 
