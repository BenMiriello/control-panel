#!/usr/bin/env python3

import os
import sys
from pathlib import Path

def merge_web_ui_files():
    """
    Merge all the web UI part files into a single web_ui.py file.
    This resolves the imports and prevents circular dependencies.
    """
    # Get the directory containing the script
    module_dir = Path(__file__).parent
    
    # Input files in order
    input_files = [
        module_dir / "web_ui.py",
        module_dir / "web_ui_part2.py",
        module_dir / "web_ui_part3.py"
    ]
    
    # Ensure all files exist
    missing_files = [f for f in input_files if not f.exists()]
    if missing_files:
        print(f"Error: Missing files: {', '.join(str(f) for f in missing_files)}")
        return False
    
    # Create a temporary file to store the merged content
    output_file = module_dir / "web_ui_merged.py"
    
    # Extract the content from each file
    content_parts = []
    
    # For the first file, extract only up to the @app.route('/services/add')
    with open(input_files[0], 'r') as f:
        lines = f.readlines()
        end_marker = "@app.route('/services/add'"
        
        end_line = len(lines)
        for i, line in enumerate(lines):
            if end_marker in line:
                end_line = i
                break
        
        content_parts.append("".join(lines[:end_line]))
    
    # For the second file, extract the route handlers but skip imports
    with open(input_files[1], 'r') as f:
        lines = f.readlines()
        
        # Skip import lines
        start_line = 0
        for i, line in enumerate(lines):
            if line.startswith("from") or line.startswith("import") or line.strip() == "":
                start_line = i + 1
            elif "@app.route" in line:
                break
        
        content_parts.append("".join(lines[start_line:]))
    
    # For the third file, extract the functions but skip imports and duplicates
    with open(input_files[2], 'r') as f:
        lines = f.readlines()
        
        # Skip import lines and duplicate function definitions
        start_line = 0
        for i, line in enumerate(lines):
            if line.startswith("from") or line.startswith("import") or line.strip() == "":
                start_line = i + 1
            elif "def start_web_ui" in line:
                break
        
        content_parts.append("".join(lines[start_line:]))
    
    # Write the merged content to the output file
    with open(output_file, 'w') as f:
        f.write("\n\n".join(content_parts))
    
    # Replace the original web_ui.py with the merged file
    os.rename(output_file, module_dir / "web_ui.py")
    
    # Remove the part files
    for part_file in input_files[1:]:
        if part_file.exists():
            os.remove(part_file)
    
    print("Web UI files successfully merged!")
    return True

if __name__ == "__main__":
    if merge_web_ui_files():
        sys.exit(0)
    else:
        sys.exit(1)
