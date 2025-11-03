#!/usr/bin/env python3
"""
Script to run a program with valgrind using multiple input files.
Stops on the first input that triggers a valgrind error.
"""

import sys
import os
import subprocess
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("Usage: ./run_valgrind.py <input_folder> [start_index] <program> [program_args...]")
        print("  start_index: Optional starting input number (0-based, default: 0)")
        print("Example: ./run_valgrind.py ./input ./httpd -d -f ./httpd.conf")
        print("Example: ./run_valgrind.py ./input 3 ./httpd -d -f ./httpd.conf")
        sys.exit(1)

    input_folder = sys.argv[1]

    # Check if second argument is a number (start_index)
    start_index = 0
    program_args_start = 2

    if len(sys.argv) > 2:
        try:
            start_index = int(sys.argv[2])
            program_args_start = 3
        except ValueError:
            # Not a number, so it's part of the program command
            pass

    program_args = sys.argv[program_args_start:]

    # Validate input folder exists
    if not os.path.isdir(input_folder):
        print(f"Error: Input folder '{input_folder}' does not exist")
        sys.exit(1)

    # Get all files in the input folder
    input_files = sorted(Path(input_folder).glob('*'))
    input_files = [f for f in input_files if f.is_file()]

    if not input_files:
        print(f"Error: No input files found in '{input_folder}'")
        sys.exit(1)

    # Validate start_index
    if start_index < 0:
        print(f"Error: start_index must be >= 0, got {start_index}")
        sys.exit(1)
    if start_index >= len(input_files):
        print(f"Error: start_index {start_index} is >= number of input files ({len(input_files)})")
        sys.exit(1)

    print(f"Found {len(input_files)} input files")
    if start_index > 0:
        print(f"Starting from input {start_index} (skipping first {start_index} inputs)")
    print(f"Program command: {' '.join(program_args)}")
    print("-" * 80)

    # Valgrind command with:
    # - uninitialized memory checking enabled
    # - memory leak checking disabled
    # - error exit code 42
    valgrind_cmd = [
        'valgrind',
        '--error-exitcode=42',
        '--track-origins=yes',
        '--undef-value-errors=yes',
        '--leak-check=no'
        # Removed --quiet to show all valgrind output
    ]

    full_cmd = valgrind_cmd + program_args

    # Run valgrind for each input file, starting from start_index
    for idx in range(start_index, len(input_files)):
        input_file = input_files[idx]
        i = idx + 1  # 1-based display number
        print(f"\n[{i}/{len(input_files)}] Testing with: {input_file.name}")
        print("-" * 80)

        try:
            with open(input_file, 'rb') as f:
                result = subprocess.run(
                    full_cmd,
                    stdin=f,
                    capture_output=True,
                    timeout=60  # 60 second timeout per input
                )

            # Always print stderr (contains valgrind output)
            if result.stderr:
                stderr_text = result.stderr.decode('utf-8', errors='replace')
                print(stderr_text)

            # Check if valgrind detected errors (exit code 42)
            if result.returncode == 42:
                print(f"\n{'='*80}")
                print(f"VALGRIND ERROR DETECTED with input: {input_file}")
                print(f"{'='*80}")
                if result.stdout:
                    print("STDOUT:")
                    print(result.stdout.decode('utf-8', errors='replace'))
                print(f"{'='*80}")
                print(f"Stopped at input {i}/{len(input_files)}: {input_file}")
                sys.exit(1)

            # Show any output for debugging (optional)
            if result.returncode != 0:
                print(f"→ Program exited with code {result.returncode} (not a valgrind error)")
            else:
                print(f"→ ✓ OK")

        except subprocess.TimeoutExpired:
            print(f"\n{'='*80}")
            print(f"TIMEOUT (60s) with input: {input_file}")
            print(f"{'='*80}")
            print(f"→ Skipping and continuing to next input...")
            continue
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"ERROR running valgrind with input: {input_file}")
            print(f"Exception: {e}")
            print(f"{'='*80}")
            sys.exit(1)

    print("-" * 80)
    num_tested = len(input_files) - start_index
    print(f"✓ SUCCESS: All {num_tested} inputs completed without valgrind errors")
    sys.exit(0)


if __name__ == '__main__':
    main()
