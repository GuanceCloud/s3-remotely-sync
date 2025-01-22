"""Configuration handler for S3 Sync Tool"""

import os
import sys
import stat
import yaml
import configparser
from typing import Optional, Dict, List, Tuple

class Config:
    """Configuration handler"""
    
    DEFAULT_CONFIG_FILE = '.s3-remotely-sync.yml'
    
    def __init__(self):
        # Windows use %USERPROFILE%, Unix use $HOME
        if sys.platform == 'win32':
            self.config_dir = os.path.join(os.environ.get('USERPROFILE', ''), '.s3-remotely-sync')
        else:
            self.config_dir = os.path.expanduser("~/.s3-remotely-sync")
            
        self.config_file = os.path.join(self.config_dir, "config")
        self.credentials_file = os.path.join(self.config_dir, "credentials")
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """ensure config directory exists and set appropriate permissions"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            self._set_secure_permissions(self.config_dir)

    def _set_secure_permissions(self, path: str):
        """set secure file permissions according to operating system"""
        if sys.platform == 'win32':
            import win32security
            import ntsecuritycon as con
            
            # get current user sid
            username = win32security.GetUserNameEx(win32security.NameSamCompatible)
            sid = win32security.LookupAccountName(None, username)[0]
            
            # create new security descriptor
            sd = win32security.SECURITY_DESCRIPTOR()
            
            # set file owner
            sd.SetSecurityDescriptorOwner(sid, False)
            
            # create dacl allow all owner access
            dacl = win32security.ACL()
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                con.FILE_ALL_ACCESS,
                sid
            )
            
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            
            # apply security settings
            win32security.SetFileSecurity(
                path,
                win32security.DACL_SECURITY_INFORMATION | win32security.OWNER_SECURITY_INFORMATION,
                sd
            )
        else:
            # Unix set permission to 700 (only owner can read, write, execute)
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

    def get_credentials(self, profile: str = "default") -> Tuple[Optional[str], Optional[str]]:
        """get credentials from specified profile"""
        config = configparser.ConfigParser()
        if os.path.exists(self.credentials_file):
            config.read(self.credentials_file)
            if profile in config:
                return (
                    config[profile].get("access_key"),
                    config[profile].get("secret_key")
                )
        return None, None

    def set_credentials(self, access_key: str, secret_key: str, profile: str = "default"):
        """set credentials"""
        config = configparser.ConfigParser()
        if os.path.exists(self.credentials_file):
            config.read(self.credentials_file)

        if profile not in config:
            config[profile] = {}

        config[profile]["access_key"] = access_key
        config[profile]["secret_key"] = secret_key

        # ensure directory exists
        os.makedirs(os.path.dirname(self.credentials_file), exist_ok=True)
        
        # write config file
        with open(self.credentials_file, "w") as f:
            config.write(f)
        
        # set file security permissions
        self._set_secure_permissions(self.credentials_file)

    def remove_profile(self, profile: str):
        """remove specified profile"""
        if profile == "default":
            raise ValueError("Cannot remove default profile")
            
        config = configparser.ConfigParser()
        if os.path.exists(self.credentials_file):
            config.read(self.credentials_file)
            if profile in config:
                config.remove_section(profile)
                with open(self.credentials_file, "w") as f:
                    config.write(f)

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
