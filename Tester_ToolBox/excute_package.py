import subprocess
import os
import re
import shutil
import threading
import sys
import markdown
import pdfkit

def output_reader(pipe, prefix=''):
    """Helper function to read and print output from pipe"""
    for line in iter(pipe.readline, ''):
        if line:
            print(f"{prefix}{line.strip()}")

def build_package():
    # Execute packaging command
    print("Executing packaging operation...")
    process = subprocess.Popen(
        ["pyinstaller", "package.spec", "--clean", "--noconfirm"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        universal_newlines=True,
        bufsize=1  # Line buffering
    )
    
    # Create threads to handle output
    stdout_thread = threading.Thread(target=output_reader, args=(process.stdout,))
    stderr_thread = threading.Thread(target=output_reader, args=(process.stderr, 'Error: '))
    
    # Start threads and wait for process to complete
    stdout_thread.start()
    stderr_thread.start()
    process.wait()
    
    # Wait for output threads to complete
    stdout_thread.join()
    stderr_thread.join()
    
    # Get the final return code
    if process.returncode != 0:
        print("Package failed")
        return
    
    # Parse spec file to get version information
    with open("package.spec", "r") as f:
        spec_content = f.read()
    
    # Use regular expression to extract version information
    collect_name_match = re.search(r"name='(.*?)'\s*\)", spec_content)  # Match name in COLLECT section
    version_match = re.search(r"version='(.*?)'", spec_content)
    
    if not collect_name_match or not version_match:
        print("Failed to parse version information from spec file")
        return
    
    folder_name = collect_name_match.group(1)  
    log_path = os.path.join("dist", folder_name, "log")
    print(f"Creating log directory: {log_path}")
    os.makedirs(log_path, exist_ok=True)
    
    license_src = "LICENSE"
    license_dst = os.path.join("dist", folder_name, "LICENSE")
    if os.path.exists(license_src):
        print(f"Copying LICENSE file to: {license_dst}")
        shutil.copy2(license_src, license_dst)
    else:
        print("Warning: LICENSE file not found in source directory")

    pdf_src = "readme.pdf"
    pdf_dst = os.path.join("dist", folder_name, "readme.pdf")
    if os.path.exists(pdf_src):
        print(f"Copying readme.pdf file to: {pdf_dst}")
        shutil.copy2(pdf_src, pdf_dst)
    else:
        print("Warning: readme.pdf file not found in source directory")

    print("Operation completed")

if __name__ == "__main__":
    build_package()
    input("Press Enter to exit...")