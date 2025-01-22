# S3 Sync Tool

A Python-based synchronization tool for S3-compatible storage services that supports concurrent multi-user operations.

## Features

- Multi-user concurrent synchronization support
- File extension filtering (whitelist/blacklist)
- Recursive directory synchronization
- Timestamp-based sync decisions
- Support for S3-compatible services (AWS S3, Aliyun OSS, Tencent COS, etc.)
- Metadata-based optimization for large-scale synchronization
- Command-line interface

## Installation

1. Install Python 3.11 or later

2. Install pip (if not installed)

3. Install s3-remotely-sync

```bash
pip install s3-remotely-sync
```

## Usage

### Configure Credentials

```bash
s3rs configure --profile your_profile_name
```

or use default profile name:

```bash
s3rs configure
```

### Basic Synchronization

Sync with custom endpoint (e.g., Aliyun OSS):

```bash
s3rs sync /local/path --bucket bucket-name --prefix prefix --endpoint-url https://oss-cn-beijing.aliyuncs.com
```

Exclude specific file types:

```bash
s3rs sync /local/path --bucket bucket-name --prefix prefix --extensions .tmp .log --blacklist
```

#### Arguments

- `local_path`: Local directory path to sync
- `--bucket`: S3 bucket name
- `--prefix`: S3 prefix (directory path in bucket)
- `--endpoint-url`: S3-compatible service endpoint URL
- `--extensions`: File extensions to include/exclude
- `--blacklist`: Treat extensions as blacklist instead of whitelist

#### Configuration

You can also use a configuration file `.s3-remotely-sync.yml` to store in your local path root directory that you want to sync.

```yaml
# S3/OSS configuration
bucket: s3-remotely-sync
prefix: test
endpoint-url: https://oss-cn-shanghai.aliyuncs.com
region: oss-cn-shanghai

# Sync options
extensions:
  - .md
  - .pages
blacklist: true
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
