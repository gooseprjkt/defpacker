from setuptools import setup, find_packages

setup(
    name="defpacker",
    version="1.0.0",
    description="DefPacker - A tool for defending archives using various obfuscation and encryption techniques",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "cryptography>=3.4.8",
        "rich>=10.0.0",
        "py7zr>=0.19.0",
    ],
    entry_points={
        'console_scripts': [
            'defpacker=cli:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)