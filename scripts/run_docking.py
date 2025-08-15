#!/usr/bin/env python
"""
Unified docking pipeline runner (Python).
- Uses MGLTools Python (2.x) for: prepare_inputs.py, docking.py, extract_results.py
- Uses Python 3 (vizdock env) for: check_install_packages.py, visualize.py
- Uses the current Python (sys.executable) for the downloader (download_data.py OR downlaod_inputs.py)
Writes both console output and a timestamped log file.
"""



import os
import sys
import time
import subprocess
from pathlib import Path

# ======= CONFIGURE THESE PATHS =======
# Absolute path to MGLTools' python.exe (Python 2.x)
MGLTOOLS_PY = r"C:\Program Files (x86)\MGLTools-1.5.7\python.exe"

# Absolute path to your Python 3 interpreter INSIDE the vizdock env
# (Avoids needing 'conda activate' from scripts.)
VIZDOCK_PY3 = r"C:\Users\Tayyab\miniconda3\envs\vizdock\python.exe"

# Folders used by the pipeline (relative to this script's directory)
OUTPUT_DIR = Path("results/docking/vina_outputs")
VIS_DIR    = Path("results/visualizations")

# =====================================

def here() -> Path:
    return Path(__file__).resolve().parent

def timestamp() -> str:
    return time.strftime("%Y-%m-%d_%H%M%S")

LOGFILE = here() / f"pipeline_{timestamp()}.log"

def log(msg: str) -> None:
    print(msg, flush=True)
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def run_cmd(cmd, cwd=None) -> None:
    """Run a command, stream & tee its output to the log; abort on nonzero exit."""
    log(f">>> Running: {' '.join(map(str, cmd))}")
    p = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
    )
    # Stream output line-by-line to console and log
    with open(LOGFILE, "a", encoding="utf-8") as lf:
        for line in p.stdout:
            line = line.rstrip("\n")
            print(line)
            lf.write(line + "\n")
    p.wait()
    if p.returncode != 0:
        log(f"[ERROR] Command failed with code {p.returncode}: {' '.join(map(str, cmd))}")
        sys.exit(p.returncode)


# def main():
#     # Always run from the script's folder so relative paths work
#     os.chdir(here())

#     log("=" * 40)
#     log("AutoDock Vina Pipeline Run")
#     log(f"Started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
#     log("=" * 40)

#     # 1) Downloader (prefer canonical name, fall back to the misspelled one)
#     log("[1/7] Downloading protein and ligand data...")
#     dl = None
#     if Path("download_data.py").exists():
#         dl = "download_data.py"
#     elif Path("downlaod_inputs.py").exists():
#         dl = "downlaod_inputs.py"
#     else:
#         log("ERROR: No downloader found (download_data.py or downlaod_inputs.py).")
#         sys.exit(1)

#     run_cmd([sys.executable, dl])

#     # 2) Prepare inputs with MGLTools (Python 2)
#     log("[2/7] Preparing input files for docking...")
#     if not Path(MGLTOOLS_PY).exists():
#         log(f"ERROR: MGLTools python not found at: {MGLTOOLS_PY}")
#         sys.exit(1)
#     run_cmd([MGLTOOLS_PY, "prepare_inputs.py"])

#     # Ensure output dirs exist
#     OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
#     VIS_DIR.mkdir(parents=True, exist_ok=True)

#     # 3) Docking (MGLTools Python 2)
#     log("[3/7] Running docking...")
#     run_cmd([MGLTOOLS_PY, "docking.py"])

#     if not OUTPUT_DIR.exists():
#         log(f"ERROR: Output folder not found: {OUTPUT_DIR}")
#         sys.exit(1)

#     # 4) Extract results (MGLTools Python 2)
#     log("[4/7] Extracting docking results...")
#     run_cmd([MGLTOOLS_PY, "extract_results.py"])

#     # 5) Check/install packages in Python 3 env
#     log("[5/7] Checking/installing missing Python packages (Py3 env)...")
#     if not Path(VIZDOCK_PY3).exists():
#         log(f"ERROR: Python 3 (vizdock) not found at: {VIZDOCK_PY3}")
#         sys.exit(1)
#     run_cmd([VIZDOCK_PY3, "check_install_packages.py"])

#     # 6) Visualization (Python 3 env)
#     log("[6/7] Running visualization (Py3 env)...")
#     run_cmd([VIZDOCK_PY3, "visualize.py", "data/ligands", str(OUTPUT_DIR), str(VIS_DIR)])

#     # Done
#     log("[7/7] Workflow completed successfully!")
#     log(f"Log saved to {LOGFILE}")

# if __name__ == "__main__":
#     try:
#         main()
#     except KeyboardInterrupt:
#         log("[ABORTED] KeyboardInterrupt")
#         sys.exit(130)
#     except Exception as e:
#         log(f"[FATAL] {e}")
#         sys.exit(1)
def main():
    os.chdir(here())

    log("=" * 40)
    log("AutoDock Vina Pipeline Run")
    log(f"Started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 40)

    # 1) Downloader
    log("[1/7] Downloading protein and ligand data...")
    dl = None
    if Path("download_data.py").exists():
        dl = "download_data.py"
    elif Path("downlaod_inputs.py").exists():
        dl = "downlaod_inputs.py"
    else:
        log("ERROR: No downloader found (download_data.py or downlaod_inputs.py).")
        sys.exit(1)
    run_cmd([sys.executable, dl])

    # 1.5) Convert SDF -> PDB (RDKit, Python 3 env)
    log("[1.5/7] Converting ligand SDF to PDB format...")
    run_cmd([VIZDOCK_PY3, "convert_sdf_to_pdb.py"])

    # 2) Prepare inputs (MGLTools / Py2)
    log("[2/7] Preparing input files for docking...")
    if not Path(MGLTOOLS_PY).exists():
        log(f"ERROR: MGLTools python not found at: {MGLTOOLS_PY}")
        sys.exit(1)
    run_cmd([MGLTOOLS_PY, "prepare_inputs.py"])

    # Ensure output dirs exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIS_DIR.mkdir(parents=True, exist_ok=True)

    # 3) Docking (Py2)
    log("[3/7] Running docking...")
    run_cmd([MGLTOOLS_PY, "docking.py"])

    if not OUTPUT_DIR.exists():
        log(f"ERROR: Output folder not found: {OUTPUT_DIR}")
        sys.exit(1)

    # 4) Extract results (Py2)
    log("[4/7] Extracting docking results...")
    run_cmd([MGLTOOLS_PY, "extract_results.py"])

    # 5) Ensure Py3 deps
    log("[5/7] Checking/installing missing Python packages (Py3 env)...")
    if not Path(VIZDOCK_PY3).exists():
        log(f"ERROR: Python 3 (vizdock) not found at: {VIZDOCK_PY3}")
        sys.exit(1)
    run_cmd([VIZDOCK_PY3, "check_install_packages.py"])

    # 6) Visualization (Py3)
    log("[6/7] Running visualization (Py3 env)...")
    run_cmd([VIZDOCK_PY3, "visualize.py", "data/ligands", str(OUTPUT_DIR), str(VIS_DIR)])

    log("[7/7] Workflow completed successfully!")
    log(f"Log saved to {LOGFILE}")
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("[ABORTED] KeyboardInterrupt")
        sys.exit(130)
    except Exception as e:
        log(f"[FATAL] {e}")
        sys.exit(1)
