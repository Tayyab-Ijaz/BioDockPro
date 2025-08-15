import os
import re
import subprocess
import sys

def find_imports_from_file(filepath):
    imports = set()
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            # Match import statements: import x or from x import y
            m = re.match(r'^\s*(?:import|from)\s+([\w\.]+)', line)
            if m:
                pkg = m.group(1).split('.')[0]  # get top-level package
                # Ignore relative imports and built-in modules
                if pkg and not pkg.startswith('.'):
                    imports.add(pkg)
    return imports

def find_all_imports(root_dir):
    all_imports = set()
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                full_path = os.path.join(dirpath, filename)
                all_imports.update(find_imports_from_file(full_path))
    return all_imports

def is_package_installed(pkg):
    # Run python -c "import pkg"
    result = subprocess.run(
        [sys.executable, '-c', f'import {pkg}'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return result.returncode == 0

def install_package(pkg):
    print(f"Installing package: {pkg}")
    result = subprocess.run([sys.executable, '-m', 'pip', 'install', pkg])
    return result.returncode == 0

if __name__ == "__main__":
    root = '.'  # scan current directory recursively
    print("Scanning for imported packages...")
    imports = find_all_imports(root)
    # Filter out standard library and known packages you do NOT want to install:
    # Here you can add built-in modules you want to skip (like os, sys, re, subprocess, etc)
    stdlib_modules = {
        'os', 'sys', 're', 'subprocess', 'math', 'time', 'json', 'logging',
        'pathlib', 'threading', 'collections', 'functools', 'itertools',
        'shutil', 'tempfile', 'unittest', 'enum', 'argparse', 'typing'
    }

    to_install = [pkg for pkg in imports if pkg not in stdlib_modules]

    if not to_install:
        print("No third-party packages found to install.")
    else:
        print(f"Packages to check/install: {to_install}")

    for pkg in to_install:
        if not is_package_installed(pkg):
            print(f"Package '{pkg}' not found.")
            success = install_package(pkg)
            if not success:
                print(f"Failed to install package '{pkg}'. Aborting.")
                sys.exit(1)
        else:
            print(f"Package '{pkg}' is already installed.")

    print("All required packages are installed.")
