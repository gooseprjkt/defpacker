# DefPacker

DefPacker is a powerful tool for protecting archives using advanced obfuscation and encryption techniques. It makes analysis harder by using multiple layers of protection.

## Features

- **Multi-layer Obfuscation**: Creates deep directory trees with obfuscated names
- **Multiple Obfuscation Patterns**:
  - Short names (a, b, c, d)
  - Longer names (a3, x0, y0, po)
  - W-like patterns (16-char strings with 'W's and 'o's)
- **Fake Files**: Generates files with similar sizes to real files
- **Advanced Encryption**: AES-256 encryption with strong key derivation
- **Secure Manifest**: Encoded manifest with obfuscated paths
- **Flexible Archive Formats**: Support for ZIP, TAR.GZ, TAR.BZ2, TAR.XZ, 7Z
- **Customizable Encoding**: Built-in encoder with configurable junk insertion

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

```bash
# Pack files with default settings
python -m defpacker pack input_dir/ output.zip

# Pack with custom settings
python -m defpacker pack input_dir/ output.7z --levels 5 --types short longer w_like --encrypt --format 7z

# Unpack protected archive
python -m defpacker unpack protected.zip output_dir/
```

### Programmatic Usage

```python
from defpacker.core import DefPacker

packer = DefPacker()
packer.pack(
    input_path="input_dir/",
    output_path="output.zip",
    obfuscation_levels=3,
    obfuscation_types=['short', 'longer', 'w_like'],
    encryption_password="secure_password"
)

packer.unpack(
    archive_path="output.zip",
    output_dir="restored/",
    decryption_password="secure_password"
)
```

## Architecture

- `core/`: Main DefPacker logic
- `encoder/`: Built-in encoding/obfuscation engine
- `cli/`: Command-line interface
- `utils/`: Helper utilities
- `tests/`: Unit and integration tests