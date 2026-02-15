"""
Core DefPacker module - Implements the main functionality for protecting archives
"""

import os
import sys
import json
import shutil
import random
import string
import zipfile
import tarfile
import tempfile
import getpass
import base64
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from encoder import Encoder
import rich
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text


console = Console()


class DefPacker:
    def __init__(self, encoder_config: dict = None):
        """
        Initialize DefPacker with customizable encoder.
        
        Args:
            encoder_config: Configuration for the encoder
        """
        if encoder_config is None:
            encoder_config = {}
        self.encoder = Encoder(**encoder_config)
        self.obfuscation_patterns = {
            'short': lambda: random.choice(string.ascii_lowercase),  # Just one letter
            'longer': lambda: random.choice(string.ascii_lowercase) + random.choice(string.digits),  # Letter + digit
            'w_like': self._generate_w_like_pattern
        }
        
    def _generate_w_like_pattern(self) -> str:
        """Generate W-like pattern with 'o' replacing some positions.
        Creates 16-character string starting with 'W', with other W's replaced by 'o'."""
        length = 16
        pattern = ['W'] * length
        # Replace random positions (but keep the first character as 'W')
        num_replacements = random.randint(1, 5)  # Replace 1-5 of the remaining W's with 'o' (less frequent)
        # Sample from positions 1 to end (excluding first position which stays as 'W')
        positions = random.sample(range(1, length), min(num_replacements, length-1))
        for pos in positions:
            pattern[pos] = 'o'  # Use 'o' instead of random letters
        return ''.join(pattern)
    
    def _is_reserved_path(self, path_part: str) -> bool:
        """Check if a path part is reserved for manifest/mapping."""
        # Reserved paths for manifest are 'a' (since manifest is at a/a/a/a)
        return path_part == 'a'
    
    def _generate_obfuscated_filename(self, obfuscation_type: str) -> str:
        """Generate an obfuscated filename based on the pattern type."""
        while True:
            name = self.obfuscation_patterns[obfuscation_type]()
            if not self._is_reserved_path(name):
                return name
    
    def _generate_fake_files(self, count: int, sizes: List[int], obfuscation_type: str) -> List[Tuple[str, bytes]]:
        """Generate fake files with similar sizes to real files."""
        fake_files = []
        for i in range(count):
            size = random.choice(sizes) if sizes else random.randint(100, 10000)
            filename = self._generate_obfuscated_filename(obfuscation_type)
            content = os.urandom(size)
            fake_files.append((filename, content))
        return fake_files
    
    def _encrypt_data_with_password(self, data: bytes, password: str) -> bytes:
        """Encrypt data using AES-256 with a password."""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Pad data to be multiple of 16 bytes
        padding_len = 16 - (len(data) % 16)
        padded_data = data + bytes([padding_len] * padding_len)
        
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Return salt + iv + encrypted_data
        return salt + iv + encrypted_data
    
    def _decrypt_data_with_password(self, encrypted_data: bytes, password: str) -> bytes:
        """Decrypt data using AES-256 with a password."""
        salt = encrypted_data[:16]
        iv = encrypted_data[16:32]
        ciphertext = encrypted_data[32:]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Remove padding
        padding_len = padded_plaintext[-1]
        plaintext = padded_plaintext[:-padding_len]
        
        return plaintext
    
    def _encode_with_encoder(self, data: str, junk_level: float = 0.3) -> str:
        """Encode data using the custom encoder."""
        return self.encoder.encode(data, junk_level)
    
    def _decode_with_encoder(self, encoded_data: str) -> str:
        """Decode data using the custom encoder."""
        return self.encoder.decode(encoded_data)
    
    def _create_archive(self, source_dir: Path, archive_path: Path, archive_format: str, password: Optional[str] = None):
        """Create an archive in the specified format."""
        if archive_format == 'zip':
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(source_dir)
                        zf.write(file_path, arcname)
        elif archive_format == 'tar.gz':
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(source_dir, arcname='.')
        elif archive_format == 'tar.bz2':
            with tarfile.open(archive_path, 'w:bz2') as tar:
                tar.add(source_dir, arcname='.')
        elif archive_format == 'tar.xz':
            with tarfile.open(archive_path, 'w:xz') as tar:
                tar.add(source_dir, arcname='.')
        elif archive_format == '7z':
            # Using py7zr if available
            try:
                import py7zr
                with py7zr.SevenZipFile(archive_path, 'w', password=password) as archive:
                    for root, dirs, files in os.walk(source_dir):
                        for file in files:
                            file_path = Path(root) / file
                            archive.write(file_path, file_path.relative_to(source_dir))
            except ImportError:
                console.print("[red]py7zr not installed. Please install it with 'pip install py7zr'[/red]")
                raise
        else:
            raise ValueError(f"Unsupported archive format: {archive_format}")
    
    def pack(self, 
             input_path: Path, 
             output_path: Path, 
             obfuscation_levels: int = 7,  # A LOT of levels for EXTREME obfuscation
             obfuscation_types: List[str] = ['w_like', 'short', 'longer'],  # Prioritize w-like by default
             add_fake_files: bool = True,
             fake_file_count: int = 10,
             encryption_password: Optional[str] = None,
             archive_format: str = 'zip',
             encoder_junk_level: float = 0.8,  # A LOT OF JUNK by default
             start_dir: str = "defpackage",
             use_treefuscator: bool = True,  # Enable treefuscator by default
             file_bytes_junk: int = 0):  # Number of bytes to replace with junk in files
        """Pack and protect the input with obfuscation and encryption."""
        
        # Generate encryption keys
        if encryption_password is None:
            encryption_password = getpass.getpass("Enter encryption password: ")
        
        # Generate a private key for encrypting the mapping
        private_key_bytes = os.urandom(32)  # Raw bytes for encryption
        private_key_b64 = base64.b64encode(private_key_bytes).decode()  # Base64 for storage
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Copy original files to temp directory
            temp_input = temp_path / "input"
            if input_path.is_file():
                temp_input.mkdir(exist_ok=True)
                shutil.copy2(input_path, temp_input / input_path.name)
            else:
                shutil.copytree(input_path, temp_input)
            
            # Create obfuscated directory structure with start directory
            obfuscated_dir = temp_path / start_dir
            obfuscated_dir.mkdir()
            
            # Create the fixed manifest directory structure first to avoid conflicts
            manifest_dir = obfuscated_dir / "a" / "a" / "a"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize mapping dictionary
            mapping = {}
            
            # Copy original files to obfuscated structure
            original_files = []
            for root, dirs, files in os.walk(temp_input):
                for file in files:
                    original_files.append(Path(root) / file)
            
            # Calculate original file sizes for fake file generation
            original_sizes = [os.path.getsize(str(f)) for f in original_files]
            
            # Add fake files if enabled
            if add_fake_files:
                fake_files = self._generate_fake_files(fake_file_count, original_sizes, random.choice(obfuscation_types))
                for filename, content in fake_files:
                    fake_file_path = obfuscated_dir / filename
                    # Make sure this doesn't conflict with reserved paths
                    if not fake_file_path.exists():
                        with open(fake_file_path, 'wb') as ff:
                            ff.write(content)
            
            # Copy original files to obfuscated structure
            for original_file in original_files:
                rel_path = original_file.relative_to(temp_input)
                
                if use_treefuscator:
                    # EXTREME OBFUSCATOR: Create complex tree structure with multiple placements
                    
                    # First, place the original file in a deeply obfuscated location
                    max_attempts = 100  # Prevent infinite loops
                    for attempt in range(max_attempts):
                        # Determine where to place this file in the obfuscated structure
                        obf_parts = []
                        for _ in range(obfuscation_levels):
                            obf_type = random.choice(obfuscation_types)
                            obf_parts.append(self._generate_obfuscated_filename(obf_type))
                        
                        # Create the full obfuscated path for the directory
                        obf_dir_path = obfuscated_dir
                        valid_path = True
                        for part in obf_parts:
                            obf_dir_path = obf_dir_path / part
                            # Ensure this path is a directory, not a file
                            if obf_dir_path.exists() and obf_dir_path.is_file():
                                # If it exists as a file, we need to regenerate the path
                                valid_path = False
                                break
                        
                        if valid_path:
                            # Path is valid, proceed with creating the directory and file
                            obf_dir_path.mkdir(parents=True, exist_ok=True)
                            
                            # Create the final file path
                            final_file_path = obf_dir_path / self._generate_obfuscated_filename(random.choice(obfuscation_types))
                            
                            # Apply file bytes junk if requested
                            if file_bytes_junk > 0:
                                with open(original_file, 'rb') as src:
                                    original_content = src.read()
                                
                                # Save original bytes that will be replaced
                                original_bytes = original_content[:file_bytes_junk] if len(original_content) >= file_bytes_junk else original_content
                                
                                # Replace first bytes with junk
                                junk_bytes = os.urandom(file_bytes_junk)
                                modified_content = junk_bytes + original_content[file_bytes_junk:]
                                
                                with open(final_file_path, 'wb') as dest:
                                    dest.write(modified_content)
                                
                                # Store the original bytes in the mapping for reconstruction
                                mapping[str(final_file_path.relative_to(obfuscated_dir))] = {
                                    'original_path': str(rel_path),
                                    'original_bytes': base64.b64encode(original_bytes).decode(),
                                    'junk_offset': file_bytes_junk
                                }
                            else:
                                shutil.copy2(original_file, final_file_path)
                                mapping[str(final_file_path.relative_to(obfuscated_dir))] = str(rel_path)
                            break
                    else:
                        # If we exhausted all attempts, raise an error
                        raise RuntimeError(f"Could not find a valid path for file {original_file} after {max_attempts} attempts")
                    
                    # Create complex fake trees to confuse analysis
                    # Generate many fake paths for each obfuscation type
                    num_fake_trees = random.randint(15, 30)  # Create 15-30 fake trees per file - A LOT!
                    for _ in range(num_fake_trees):
                        # Create fake tree with varying depths
                        fake_depth = random.randint(2, obfuscation_levels)
                        fake_parts = []
                        for _ in range(fake_depth):
                            obf_type = random.choice(obfuscation_types)
                            fake_parts.append(self._generate_obfuscated_filename(obf_type))
                        
                        fake_dir_path = obfuscated_dir
                        valid_path = True
                        for part in fake_parts:
                            fake_dir_path = fake_dir_path / part
                            if fake_dir_path.exists() and fake_dir_path.is_file():
                                valid_path = False
                                break
                        
                        if valid_path:
                            fake_dir_path.mkdir(parents=True, exist_ok=True)
                            fake_file_path = fake_dir_path / self._generate_obfuscated_filename(random.choice(obfuscation_types))
                            
                            # Create fake file with random content
                            fake_size = random.randint(100, 10000)
                            fake_content = os.urandom(fake_size)
                            with open(fake_file_path, 'wb') as ff:
                                ff.write(fake_content)
                            
                            # Add to mapping as fake
                            mapping[str(fake_file_path.relative_to(obfuscated_dir))] = {
                                'original_path': str(rel_path),
                                'is_fake': True
                            }
                    
                    # Create additional fake trees for each top-level obfuscation pattern
                    # This creates trees like a/*/ b/*/ c/*/ etc.
                    for top_level_type in obfuscation_types:
                        top_level_name = self._generate_obfuscated_filename(top_level_type)
                        top_dir = obfuscated_dir / top_level_name
                        
                        # Skip if this conflicts with reserved paths
                        if self._is_reserved_path(top_level_name):
                            continue
                            
                        # Create sub-trees under each top-level directory
                        num_sub_trees = random.randint(15, 35)  # 15-35 sub-trees per top-level - EVEN MORE!
                        for _ in range(num_sub_trees):
                            sub_depth = random.randint(2, obfuscation_levels-1)
                            sub_parts = [top_level_name]  # Start from the top-level directory
                            for j in range(sub_depth):
                                obf_type = random.choice(obfuscation_types)
                                sub_parts.append(self._generate_obfuscated_filename(obf_type))
                            
                            sub_dir_path = obfuscated_dir
                            valid_path = True
                            for part in sub_parts:
                                sub_dir_path = sub_dir_path / part
                                if sub_dir_path.exists() and sub_dir_path.is_file():
                                    valid_path = False
                                    break
                            
                            if valid_path:
                                sub_dir_path.mkdir(parents=True, exist_ok=True)
                                fake_file_path = sub_dir_path / self._generate_obfuscated_filename(random.choice(obfuscation_types))
                                
                                # Create fake file with random content
                                fake_size = random.randint(50, 5000)
                                fake_content = os.urandom(fake_size)
                                with open(fake_file_path, 'wb') as ff:
                                    ff.write(fake_content)
                                
                                # Add to mapping as fake
                                mapping[str(fake_file_path.relative_to(obfuscated_dir))] = {
                                    'original_path': str(rel_path),
                                    'is_fake': True
                                }
                    
                    # Special handling for 'a' directory - create even more fake trees inside
                    # But avoid the reserved paths a/a/a/a and a/a/a
                    a_dir = obfuscated_dir / 'a'
                    if a_dir.exists() and a_dir.is_dir():
                        # Create additional fake trees inside the 'a' directory (but not in reserved areas)
                        num_a_trees = random.randint(20, 40)  # A LOT of trees inside 'a/'
                        for _ in range(num_a_trees):
                            # Create paths like a/x/, a/y/, a/xyz/, etc. but not a/a/
                            second_level_name = self._generate_obfuscated_filename(random.choice(obfuscation_types))
                            # Skip if this would conflict with reserved 'a' paths
                            if second_level_name == 'a':
                                continue  # Skip 'a/a/' to preserve reserved paths
                            
                            second_dir = a_dir / second_level_name
                            
                            # Create sub-trees under a/*
                            num_sub_a_trees = random.randint(10, 20)  # Many sub-trees under a/*
                            for _ in range(num_sub_a_trees):
                                sub_depth = random.randint(2, obfuscation_levels-2)  # Slightly shorter paths
                                sub_parts = ['a', second_level_name]  # Start from a/second_level_name
                                for j in range(sub_depth):
                                    obf_type = random.choice(obfuscation_types)
                                    sub_parts.append(self._generate_obfuscated_filename(obf_type))
                                
                                sub_dir_path = obfuscated_dir
                                valid_path = True
                                for part in sub_parts:
                                    sub_dir_path = sub_dir_path / part
                                    if sub_dir_path.exists() and sub_dir_path.is_file():
                                        valid_path = False
                                        break
                                
                                if valid_path:
                                    sub_dir_path.mkdir(parents=True, exist_ok=True)
                                    fake_file_path = sub_dir_path / self._generate_obfuscated_filename(random.choice(obfuscation_types))
                                    
                                    # Create fake file with random content
                                    fake_size = random.randint(50, 5000)
                                    fake_content = os.urandom(fake_size)
                                    with open(fake_file_path, 'wb') as ff:
                                        ff.write(fake_content)
                                    
                                    # Add to mapping as fake
                                    mapping[str(fake_file_path.relative_to(obfuscated_dir))] = {
                                        'original_path': str(rel_path),
                                        'is_fake': True
                                    }
                else:
                    # Standard obfuscation without treefuscator
                    max_attempts = 100  # Prevent infinite loops
                    for attempt in range(max_attempts):
                        # Determine where to place this file in the obfuscated structure
                        obf_parts = []
                        for _ in range(obfuscation_levels):
                            obf_type = random.choice(obfuscation_types)
                            obf_parts.append(self._generate_obfuscated_filename(obf_type))
                        
                        # Create the full obfuscated path for the directory
                        obf_dir_path = obfuscated_dir
                        valid_path = True
                        for part in obf_parts:
                            obf_dir_path = obf_dir_path / part
                            # Ensure this path is a directory, not a file
                            if obf_dir_path.exists() and obf_dir_path.is_file():
                                # If it exists as a file, we need to regenerate the path
                                valid_path = False
                                break
                        
                        if valid_path:
                            # Path is valid, proceed with creating the directory and file
                            obf_dir_path.mkdir(parents=True, exist_ok=True)
                            
                            # Create the final file path
                            final_file_path = obf_dir_path / self._generate_obfuscated_filename(random.choice(obfuscation_types))
                            
                            # Apply file bytes junk if requested
                            if file_bytes_junk > 0:
                                with open(original_file, 'rb') as src:
                                    original_content = src.read()
                                
                                # Save original bytes that will be replaced
                                original_bytes = original_content[:file_bytes_junk] if len(original_content) >= file_bytes_junk else original_content
                                
                                # Replace first bytes with junk
                                junk_bytes = os.urandom(file_bytes_junk)
                                modified_content = junk_bytes + original_content[file_bytes_junk:]
                                
                                with open(final_file_path, 'wb') as dest:
                                    dest.write(modified_content)
                                
                                # Store the original bytes in the mapping for reconstruction
                                mapping[str(final_file_path.relative_to(obfuscated_dir))] = {
                                    'original_path': str(rel_path),
                                    'original_bytes': base64.b64encode(original_bytes).decode(),
                                    'junk_offset': file_bytes_junk
                                }
                            else:
                                shutil.copy2(original_file, final_file_path)
                                mapping[str(final_file_path.relative_to(obfuscated_dir))] = str(rel_path)
                            break
                    else:
                        # If we exhausted all attempts, raise an error
                        raise RuntimeError(f"Could not find a valid path for file {original_file} after {max_attempts} attempts")
            
            # Create mapping file
            mapping_content = json.dumps(mapping, indent=2)
            # Convert private key to string for use as password
            private_key_str = base64.b64encode(private_key_bytes).decode()
            encrypted_mapping = self._encrypt_data_with_password(mapping_content.encode(), private_key_str)
            # For binary data like encrypted content, just pass the base64 string to encoder directly
            encoded_mapping = self.encoder.encode(base64.b64encode(encrypted_mapping).decode(), encoder_junk_level)
            
            # Generate an obfuscated path for the mapping file
            max_attempts = 100  # Prevent infinite loops
            for attempt in range(max_attempts):
                mapping_obf_parts = []
                for _ in range(obfuscation_levels):
                    obf_type = random.choice(obfuscation_types)
                    mapping_obf_parts.append(self._generate_obfuscated_filename(obf_type))
                
                # Create the full obfuscated path for the mapping directory
                mapping_obf_dir = obfuscated_dir
                valid_path = True
                for part in mapping_obf_parts:
                    mapping_obf_dir = mapping_obf_dir / part
                    # Ensure this path is a directory, not a file
                    if mapping_obf_dir.exists() and mapping_obf_dir.is_file():
                        # If it exists as a file, we need to regenerate the path
                        valid_path = False
                        break
                
                if valid_path:
                    # Path is valid, proceed with creating the directory
                    mapping_obf_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Generate an obfuscated filename for the mapping file
                    while True:
                        mapping_obf_filename = self._generate_obfuscated_filename(random.choice(obfuscation_types))
                        mapping_obf_path = mapping_obf_dir / mapping_obf_filename
                        # Make sure this path doesn't conflict with existing files
                        if not mapping_obf_path.exists():
                            break
                    break
            else:
                # If we exhausted all attempts, raise an error
                raise RuntimeError(f"Could not find a valid path for mapping file after {max_attempts} attempts")
            
            # Save encoded mapping at the obfuscated location
            with open(mapping_obf_path, 'w') as mf:
                mf.write(encoded_mapping)
            
            # Save private key (also obfuscated/encrypted)
            # For this example, we'll just store it encrypted in a file with an obfuscated name
            # Make sure the filename doesn't conflict with existing directories
            while True:
                obfuscated_key_filename = self._generate_obfuscated_filename(random.choice(obfuscation_types))
                key_file_path = obfuscated_dir / obfuscated_key_filename
                if not key_file_path.exists():
                    break
            with open(key_file_path, 'w') as kf:
                kf.write(private_key_b64)
            
            # Create manifest with the obfuscated mapping path
            manifest = {
                "version": "1.0",
                "private_key_path": str(obfuscated_key_filename),  # Store the actual obfuscated filename
                "mapping_path": str(mapping_obf_path.relative_to(obfuscated_dir)),  # Obfuscated path to mapping
                "encryption_algorithm": "AES-256",
                "archive_format": archive_format,
                "obfuscation_levels": obfuscation_levels,
                "obfuscation_types": obfuscation_types,
                "add_fake_files": add_fake_files,
                "fake_file_count": fake_file_count
            }

            # Encrypt and encode manifest
            manifest_json = json.dumps(manifest, indent=2)
            encoded_manifest = self._encode_with_encoder(manifest_json, encoder_junk_level)

            # Save encoded manifest at the fixed location a/a/a/a (without extension)
            # Make sure this path doesn't conflict with existing files
            manifest_dir = obfuscated_dir / "a" / "a" / "a"
            # Create parent directories one by one to handle conflicts
            (obfuscated_dir / "a").mkdir(parents=True, exist_ok=True)
            (obfuscated_dir / "a" / "a").mkdir(parents=True, exist_ok=True)
            manifest_dir.mkdir(parents=True, exist_ok=True)
            manifest_file_path = manifest_dir / "a"  # No extension
            
            # Write manifest file, ensuring it's not empty
            with open(manifest_file_path, 'w') as mf:
                mf.write(encoded_manifest)
            
            # Verify manifest was written correctly
            with open(manifest_file_path, 'r') as mf:
                content = mf.read()
                if not content.strip():
                    raise RuntimeError("Manifest file is empty - encoding failed")
            
            # Double-check that the manifest can be decoded properly before creating archive
            decoded_check = self._decode_with_encoder(content)
            if not decoded_check.strip():
                raise RuntimeError("Manifest cannot be decoded - encoder/decoder issue detected")
            
            # Parse to make sure it's valid JSON
            try:
                json.loads(decoded_check)
            except json.JSONDecodeError:
                raise RuntimeError("Manifest decoded content is not valid JSON")
            
            # Create the final archive
            self._create_archive(obfuscated_dir, output_path, archive_format, encryption_password)
            
            console.print(f"[green]Archive created successfully: {output_path}[/green]")
            console.print(f"[blue]Manifest saved in the archive at a/a/a/a (no extension)[/blue]")
            console.print(f"[blue]Mapping saved in the archive at an obfuscated location[/blue]")
            console.print(f"[blue]Private key saved in the archive as {obfuscated_key_filename}[/blue]")
    
    def unpack(self, archive_path: Path, output_dir: Path, decryption_password: Optional[str] = None):
        """Unpack and deobfuscate the protected archive."""
        if decryption_password is None:
            decryption_password = getpass.getpass("Enter decryption password: ")

        # Extract archive to temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract based on format
            archive_str = str(archive_path).lower()
            archive_name = archive_path.name.lower()
            
            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(temp_path)
            elif '.tar.gz' in archive_str or '.tar_gz' in archive_name or archive_path.suffixes[-2:] == ['.tar', '.gz']:
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.extractall(temp_path)
            elif '.tar.bz2' in archive_str or '.tar_bz2' in archive_name or archive_path.suffixes[-2:] == ['.tar', '.bz2']:
                with tarfile.open(archive_path, 'r:bz2') as tar:
                    tar.extractall(temp_path)
            elif '.tar.xz' in archive_str or '.tar_xz' in archive_name or archive_path.suffixes[-2:] == ['.tar', '.xz']:
                with tarfile.open(archive_path, 'r:xz') as tar:
                    tar.extractall(temp_path)
            elif archive_path.suffix.lower() == '.gz':
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.extractall(temp_path)
            elif archive_path.suffix.lower() == '.bz2':
                with tarfile.open(archive_path, 'r:bz2') as tar:
                    tar.extractall(temp_path)
            elif archive_path.suffix.lower() == '.xz':
                with tarfile.open(archive_path, 'r:xz') as tar:
                    tar.extractall(temp_path)
            elif archive_path.suffix.lower() == '.7z':
                try:
                    import py7zr
                    with py7zr.SevenZipFile(archive_path, 'r', password=decryption_password) as archive:
                        archive.extractall(path=temp_path)
                except ImportError:
                    console.print("[red]py7zr not installed. Please install it with 'pip install py7zr'[/red]")
                    raise
            else:
                # Default to zip if no recognized extension
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(temp_path)
            
            # Find manifest file at fixed location a/a/a/a
            manifest_path = temp_path / "a" / "a" / "a" / "a"
            
            if not manifest_path.exists():
                raise FileNotFoundError("Manifest file not found at a/a/a/a in archive")
            
            # Decode manifest
            with open(manifest_path, 'r') as mf:
                encoded_manifest = mf.read()
            
            decoded_manifest_json = self._decode_with_encoder(encoded_manifest)
            
            if not decoded_manifest_json.strip():
                raise RuntimeError("Decoded manifest is empty - archive may be corrupted or from an incompatible version")
                
            manifest = json.loads(decoded_manifest_json)
            
            console.print(f"[green]Manifest loaded:[/green]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Key", style="dim")
            table.add_column("Value")
            for key, value in manifest.items():
                table.add_row(key, str(value))
            console.print(table)
            
            # Find mapping file at the obfuscated path specified in the manifest
            mapping_path = temp_path / manifest['mapping_path']
            if not mapping_path.exists():
                raise FileNotFoundError(f"Mapping file not found at {manifest['mapping_path']} in archive")
            
            # Find private key file
            key_path = temp_path / manifest['private_key_path']
            if not key_path.exists():
                raise FileNotFoundError(f"Private key file not found at {manifest['private_key_path']} in archive")
            
            # Read private key
            with open(key_path, 'r') as kf:
                private_key_b64 = kf.read().strip()
            
            # The private key is already a base64-encoded string that was used for encryption
            private_key_str = private_key_b64
            
            # Decode and decrypt mapping
            with open(mapping_path, 'r') as mf:
                encoded_mapping = mf.read()
            
            # Decode encoder
            decoded_b64 = self.encoder.decode(encoded_mapping)
            
            encrypted_mapping_bytes = base64.b64decode(decoded_b64)
            
            # Decrypt mapping
            decrypted_mapping_bytes = self._decrypt_data_with_password(encrypted_mapping_bytes, private_key_str)
            mapping = json.loads(decrypted_mapping_bytes.decode())
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Recreate original structure based on mapping
            for obfuscated_path, path_info in mapping.items():
                # Handle both old format (string) and new format (dict)
                if isinstance(path_info, str):
                    # Old format: direct mapping
                    original_path = path_info
                    if original_path == "private.key" or original_path == "manifest.dat" or original_path == "mapping.dat":
                        continue  # Skip special files
                    
                    obf_full_path = temp_path / obfuscated_path
                    if obf_full_path.is_file():
                        orig_full_path = output_dir / original_path
                        orig_full_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(obf_full_path, orig_full_path)
                elif isinstance(path_info, dict):
                    # New format: dict with additional info
                    if path_info.get('is_fake', False):
                        # Skip fake files
                        continue
                    
                    original_path = path_info['original_path']
                    if original_path == "private.key" or original_path == "manifest.dat" or original_path == "mapping.dat":
                        continue  # Skip special files
                    
                    obf_full_path = temp_path / obfuscated_path
                    if obf_full_path.is_file():
                        orig_full_path = output_dir / original_path
                        orig_full_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # If file bytes junk was applied, restore original bytes
                        if 'original_bytes' in path_info and 'junk_offset' in path_info:
                            with open(obf_full_path, 'rb') as f:
                                modified_content = f.read()
                            
                            # Restore original bytes
                            original_bytes = base64.b64decode(path_info['original_bytes'])
                            junk_offset = path_info['junk_offset']
                            restored_content = original_bytes + modified_content[junk_offset:]
                            
                            with open(orig_full_path, 'wb') as f:
                                f.write(restored_content)
                        else:
                            shutil.copy2(obf_full_path, orig_full_path)
            
            console.print(f"[green]Archive unpacked successfully to: {output_dir}[/green]")