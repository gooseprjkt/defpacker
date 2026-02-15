# DefPacker Technical Documentation

## Overview

DefPacker is a sophisticated tool for protecting archives through multiple layers of obfuscation and encryption. It makes analysis significantly harder by using various techniques to hide the true structure and content of protected archives.

## Architecture

### Core Components

1. **Encoder Module**: Customizable encoding engine with configurable junk insertion
2. **Core Module**: Main DefPacker logic for packing and unpacking
3. **CLI Module**: Command-line interface
4. **Utils Module**: Helper utilities

### Encoder

The encoder module provides customizable text encoding with junk insertion:

- Configurable character sets for encoding
- Customizable junk symbol pools
- Adjustable junk insertion levels (0.0 to 1.0)
- Token-based encoding with collision detection

### Obfuscation Techniques

#### Directory Structure Obfuscation
- Multiple levels of nested directories
- Various naming patterns:
  - Short names (a, b, c, d)
  - Longer names (a3, x0, y0, po)  
  - W-like patterns (16-character strings with 'W's and 'o's)

#### File Obfuscation
- Fake files with similar sizes to real files
- Random content in fake files
- Obfuscated filenames matching directory patterns

#### Content Protection
- AES-256 encryption for sensitive data
- Secure key derivation with PBKDF2
- Encoded manifests and mappings

### Archive Protection Process

1. **Input Processing**: Copy original files to temporary directory
2. **Structure Creation**: Build obfuscated directory tree with reserved paths
3. **File Placement**: Place original and fake files in obfuscated locations
4. **Mapping Generation**: Create mapping of obfuscated to original paths
5. **Encryption**: Encrypt mapping with private key
6. **Encoding**: Encode encrypted data with junk insertion
7. **Manifest Creation**: Create and encode manifest with obfuscated paths
8. **Archive Creation**: Package everything in selected format

### Security Features

- **Strong Encryption**: AES-256 with PBKDF2 key derivation
- **Path Obfuscation**: Deep directory trees with meaningless names
- **Fake Data**: Plausible-looking fake files to confuse analysis
- **Encoded Metadata**: Manifest and mapping files encoded with junk
- **Reserved Locations**: Fixed paths for critical metadata to avoid conflicts

## Usage Examples

### Basic Usage
```bash
# Pack files with default settings
defpacker pack input_dir/ output.zip

# Pack with custom settings
defpacker pack input_dir/ output.7z --levels 5 --types short longer w_like --encrypt --format 7z

# Unpack protected archive
defpacker unpack protected.zip output_dir/
```

### Advanced Usage
```bash
# High obfuscation with maximum junk
defpacker pack input/ output.zip --levels 10 --junk-level 0.8 --fake-count 50

# Specific obfuscation patterns
defpacker pack input/ output.tar.gz --types w_like w_like w_like --levels 7
```

## Configuration Options

### Obfuscation Levels
- Controls depth of directory nesting
- Higher values create deeper trees
- Default: 3 levels

### Obfuscation Types
- `short`: Single character names (a, b, c)
- `longer`: 2-4 character names (a3, x0, po)
- `w_like`: 16-character W-like patterns (WWoWWoWW...)

### Junk Level
- Controls amount of junk inserted during encoding
- Range: 0.0 (no junk) to 1.0 (maximum junk)
- Default: 0.3

### Fake Files
- Number of fake files to generate
- Size-matched to real files
- Random content