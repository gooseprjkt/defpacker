#!/usr/bin/env python3
"""
CLI module for DefPacker
"""

import argparse
import sys
from pathlib import Path
from core import DefPacker


def main():
    parser = argparse.ArgumentParser(
        prog='DefPacker',
        description='DefPacker - A tool for defending archives using various obfuscation and encryption techniques.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s pack input_dir/ output.zip                    # Basic packing
  %(prog)s pack input_dir/ output.7z --levels 5         # With 5 obfuscation levels
  %(prog)s pack input.zip output.7z --types short longer w_like --encrypt --format 7z
  %(prog)s unpack protected.zip output_dir/             # Unpacking
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Pack command
    pack_parser = subparsers.add_parser('pack', help='Pack and protect an archive')
    pack_parser.add_argument('input', help='Input file or directory to pack')
    pack_parser.add_argument('output', help='Output archive path')
    pack_parser.add_argument('--levels', type=int, default=7, help='Obfuscation levels (default: 7 for EXTREME obfuscation)')
    pack_parser.add_argument('--types', nargs='+', default=['w_like', 'short', 'longer'], 
                             choices=['short', 'longer', 'w_like'], 
                             help='Obfuscation types to use (default: w_like short longer)')
    pack_parser.add_argument('--no-fake', action='store_true', help='Disable fake files')
    pack_parser.add_argument('--fake-count', type=int, default=10, help='Number of fake files to add (default: 10)')
    pack_parser.add_argument('--encrypt', action='store_true', help='Enable encryption')
    pack_parser.add_argument('--password', help='Encryption password (will prompt if not provided and --encrypt is used)')
    pack_parser.add_argument('--format', choices=['zip', 'tar.gz', 'tar.bz2', 'tar.xz', '7z'], 
                             default='zip', help='Archive format (default: zip)')
    pack_parser.add_argument('--junk-level', type=float, default=0.8, 
                             help='Encoder junk level (0.0-1.0, default: 0.8 for A LOT OF JUNK)')
    pack_parser.add_argument('--start-dir', type=str, default='defpackage',
                             help='Start directory name in the archive (default: defpackage)')
    pack_parser.add_argument('--no-treefuscator', action='store_false', dest='use_treefuscator',
                             help='Disable treefuscator (complex tree structure obfuscation)')
    pack_parser.add_argument('--file-bytes-junk', type=int, default=0,
                             help='Number of bytes to replace with junk at the beginning of each file (default: 0)')
    pack_parser.add_argument('--interactive', '-i', action='store_true', 
                             help='Run in interactive mode')
    
    # Unpack command
    unpack_parser = subparsers.add_parser('unpack', help='Unpack and deobfuscate an archive')
    unpack_parser.add_argument('archive', help='Protected archive to unpack')
    unpack_parser.add_argument('output', help='Output directory')
    unpack_parser.add_argument('--password', help='Decryption password (will prompt if not provided)')
    unpack_parser.add_argument('--interactive', '-i', action='store_true', 
                             help='Run in interactive mode')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize DefPacker with default encoder config
    packer = DefPacker()
    
    if args.command == 'pack' and hasattr(args, 'interactive') and args.interactive:
        # For now, just use command line args in interactive mode
        # Could be extended with rich prompts
        print("Interactive mode not fully implemented yet.")
        return
    elif args.command == 'pack':
        encryption_password = args.password
        if args.encrypt and not encryption_password:
            import getpass
            encryption_password = getpass.getpass("Enter encryption password: ")
        
        packer.pack(
            input_path=Path(args.input),
            output_path=Path(args.output),
            obfuscation_levels=args.levels,
            obfuscation_types=args.types,
            add_fake_files=not args.no_fake,
            fake_file_count=args.fake_count,
            encryption_password=encryption_password,
            archive_format=args.format,
            encoder_junk_level=args.junk_level,
            start_dir=args.start_dir,
            use_treefuscator=args.use_treefuscator,
            file_bytes_junk=args.file_bytes_junk
        )
    elif args.command == 'unpack':
        if hasattr(args, 'interactive') and args.interactive:
            import getpass
            decryption_password = getpass.getpass("Enter decryption password: ")
        else:
            decryption_password = args.password
            if not decryption_password:
                import getpass
                decryption_password = getpass.getpass("Enter decryption password: ")
        
        packer.unpack(
            archive_path=Path(args.archive),
            output_dir=Path(args.output),
            decryption_password=decryption_password
        )


if __name__ == "__main__":
    main()