from setuptools import setup, find_packages
import sys

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

install_requires = [
    "boto3>=1.26.0",
    "botocore>=1.29.0",
    "tqdm>=4.65.0",
    "rich>=13.0.0",
    "pyyaml>=6.0.0"
]

# Windows 特定依赖
if sys.platform == 'win32':
    install_requires.append("pywin32>=228")

setup(
    name="s3-remotely-sync",
    version="0.1.0",
    author="Guance",
    author_email="hmlu06@gmail.com",
    description="A tool for synchronizing files with S3-compatible storage",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GuanceCloud/s3-remotely-sync",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "s3rs=s3sync.cli:main",
        ],
    },
) 