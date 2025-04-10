#!/usr/bin/env python3

import os
import sys
from pathlib import Path

def merge_cli_files():
    """
    Merge all the CLI part files into a single cli.py file.
    This resolves the imports and prevents circular dependencies.
    """
    # Get the directory containing the script
    module_dir = Path(__file__).parent
    
    # Input files in order
    input_files = [
        module_dir / "cli.py",
        module_dir / "cli_part2.py",
        module_dir / "cli_part3.py"
    ]
    
    # Ensure all files exist
    missing_files = [f for f in input_files if not f.exists()]
    if missing_files:
        print(f"Error: Missing files: {', '.join(str(f) for f in missing_files)}")
        return False
    
    # Create a temporary file to store the merged content
    output_file = module_dir / "cli_merged.py"
    
    # Extract the content from each file
    content_parts = []
    
    # Extract from the first file (everything)
    with open(input_files[0], 'r') as f:
        content_parts.append(f.read())
    
    # For subsequent files, extract only the content after imports and CLI function definitions
    for input_file in input_files[1:]:
        with open(input_file, 'r') as f:
            lines = f.readlines()
            
            # Skip import lines and CLI definitions
            start_line = 0
            for i, line in enumerate(lines):
                if "import" in line or "from " in line or line.strip() == "":
                    start_line = i + 1
                else:
                    break
            
            # Add the remaining content
            content_parts.append("".join(lines[start_line:]))
    
    # Write the merged content to the output file
    with open(output_file, 'w') as f:
        f.write("\n\n".join(content_parts))
    
    # Replace the original cli.py with the merged file
    os.rename(output_file, module_dir / "cli.py")
    
    # Remove the part files
    for part_file in input_files[1:]:
        if part_file.exists():
            os.remove(part_file)
    
    print("CLI files successfully merged!")
    return True

if __name__ == "__main__":
    if merge_cli_files():
        sys.exit(0)
    else:
        sys.exit(1)
