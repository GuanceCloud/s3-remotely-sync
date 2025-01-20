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

1. Clone the repository: 

```bash
git clone https://github.com/guancecloud/s3-remotely-sync.git
cd s3-remotely-sync
```

2. Install the dependencies:

```bash
pip install -r requirements.txt
```

3. Configure your S3 credentials:

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=your_region
```

For other S3-compatible services, use the `--endpoint-url` parameter.

## Usage

Basic synchronization:

```bash
python cli.py /local/path bucket-name prefix
```

Sync with custom endpoint (e.g., Aliyun OSS):

```bash
python cli.py /local/path bucket-name prefix --endpoint-url https://oss-cn-beijing.aliyuncs.com
```

Exclude specific file types:

```bash
python cli.py /local/path bucket-name prefix --extensions .tmp .log --blacklist
```

## Arguments

- `local_path`: Local directory path to sync
- `bucket`: S3 bucket name
- `prefix`: S3 prefix (directory path in bucket)
- `--endpoint-url`: S3-compatible service endpoint URL
- `--extensions`: File extensions to include/exclude
- `--blacklist`: Treat extensions as blacklist instead of whitelist

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
