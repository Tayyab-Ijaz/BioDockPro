# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import glob

# =======================
# Base paths anchored to this script's folder
# =======================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def A(*parts):
    """Join to absolute path under script dir."""
    return os.path.abspath(os.path.join(SCRIPT_DIR, *parts))

# =======================
# Configuration (EDIT if needed)
# =======================
MGLTOOLS_PYTHON    = r"C:\Program Files (x86)\MGLTools-1.5.7\python.exe"
MGLTOOLS_UTILS_DIR = r"C:\Program Files (x86)\MGLTools-1.5.7\Lib\site-packages\AutoDockTools\Utilities24"

# Input folders (both are searched; ligands_pdb takes priority if both contain same stem)
INPUT_PROTEIN_DIR  = A("data", "proteins")
INPUT_LIGAND_DIRS  = [A("data", "ligands_pdb"), A("data", "ligands")]  # order matters

# Output folders (ABSOLUTE)
OUTPUT_DIR            = A("results", "docking")
OUTPUT_RECEPTOR_DIR   = A("results", "docking", "receptors")
OUTPUT_LIGAND_DIR     = A("results", "docking", "ligands")

# Behavior
FORCE_REBUILD       = os.environ.get("FORCE_REBUILD", "0") in ("1", "true", "True")
LIGAND_ADD_FLAG     = os.environ.get("LIGAND_ADD_FLAG", "checkhydrogens")  # or "hydrogens"
RECEPTOR_CLEAN_FLAG = os.environ.get("RECEPTOR_CLEAN_FLAG", "nphs_lps_waters")  # cleanup for receptor

# =======================
# Helpers
# =======================
def _ensure_dirs():
    for d in [OUTPUT_DIR, OUTPUT_RECEPTOR_DIR, OUTPUT_LIGAND_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

def _check_tools():
    if not os.path.isfile(MGLTOOLS_PYTHON):
        sys.stderr.write("[ERROR] MGLTools python not found at: %s\n" % MGLTOOLS_PYTHON); sys.exit(1)
    prep_rec = os.path.join(MGLTOOLS_UTILS_DIR, "prepare_receptor4.py")
    prep_lig = os.path.join(MGLTOOLS_UTILS_DIR, "prepare_ligand4.py")
    split_alt = os.path.join(MGLTOOLS_UTILS_DIR, "prepare_pdb_split_alt_confs.py")
    for p in [prep_rec, prep_lig, split_alt]:
        if not os.path.isfile(p):
            sys.stderr.write("[ERROR] Missing utility under %s: %s\n" % (MGLTOOLS_UTILS_DIR, os.path.basename(p))); sys.exit(1)

def _list_files(dirname, exts):
    if not os.path.isdir(dirname):
        return []
    exts = tuple([e.lower() for e in exts])
    return [f for f in os.listdir(dirname) if f and f[0] != '.' and f.lower().endswith(exts)]

def _unique_ligand_paths():
    """
    Return a list of absolute ligand paths with unique stems,
    preferring earlier dirs in INPUT_LIGAND_DIRS.
    """
    seen = {}
    for d in INPUT_LIGAND_DIRS:
        for f in _list_files(d, (".pdb", ".mol2", ".sdf", ".PDB", ".MOL2", ".SDF")):
            stem = os.path.splitext(f)[0]
            if stem not in seen:
                seen[stem] = os.path.join(d, f)
    keys = sorted(seen.keys())
    return [seen[k] for k in keys]

def _maybe_split_altloc(pdb_path):
    """
    If alt locations are present, attempt to split and prefer *_split.pdb_A.pdb,
    else *_split.pdb_B.pdb, else first split match. If none produced, return original.
    """
    base = os.path.splitext(os.path.basename(pdb_path))[0]  # e.g., 5CRB
    # Output naming observed from MGLTools on Windows:
    #   <stem>_split.pdb_A.pdb and <stem>_split.pdb_B.pdb
    # The splitter is idempotent; running again just rewrites.
    split_prefix = os.path.join(os.path.dirname(pdb_path), base + "_split.pdb")
    split_A = split_prefix + "_A.pdb"
    split_B = split_prefix + "_B.pdb"

    try:
        subprocess.check_call([
            MGLTOOLS_PYTHON,
            os.path.join(MGLTOOLS_UTILS_DIR, "prepare_pdb_split_alt_confs.py"),
            "-r", pdb_path,
            "-o", split_prefix  # tool appends _A/_B itself
        ])
    except Exception as e:
        # If splitting fails, fall back silently
        return pdb_path

    # Prefer A, then B, else any split file matching pattern
    if os.path.isfile(split_A):
        return split_A
    if os.path.isfile(split_B):
        return split_B

    matches = glob.glob(os.path.join(os.path.dirname(pdb_path), base + "_split*.pdb"))
    if matches:
        # pick the newest split file
        matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return matches[0]

    return pdb_path

# =======================
# Preparers
# =======================
def prepare_receptor(pdb_file_path):
    """Convert receptor PDB -> PDBQT with alt-loc handling and cleanup."""
    if not os.path.exists(pdb_file_path):
        print("[ERROR] Protein not found: %s" % pdb_file_path); return False

    pdb_file_path = os.path.abspath(pdb_file_path)
    file_name = os.path.basename(pdb_file_path)

    # Split alt conformers if any; prefer the A conformer
    split_pdb = _maybe_split_altloc(pdb_file_path)
    if split_pdb != pdb_file_path:
        print("[INFO] Using split alt-loc file: %s" % os.path.basename(split_pdb))

    # Output name follows the original stem (not the split suffix)
    out_name = os.path.splitext(file_name)[0] + ".pdbqt"
    out_pdbqt = os.path.join(OUTPUT_RECEPTOR_DIR, out_name)

    if (not FORCE_REBUILD) and os.path.isfile(out_pdbqt):
        print("[SKIP] Receptor exists -> %s" % out_pdbqt)
        return True

    cmd = [
        MGLTOOLS_PYTHON,
        os.path.join(MGLTOOLS_UTILS_DIR, "prepare_receptor4.py"),
        "-r", split_pdb,
        "-o", out_pdbqt,
        "-A", "hydrogens",
        "-U", RECEPTOR_CLEAN_FLAG
    ]
    try:
        subprocess.check_call(cmd)
        print("[OK] Receptor -> %s" % out_pdbqt)
        return True
    except subprocess.CalledProcessError as e:
        print("[ERROR] prepare_receptor failed for %s: %s" % (file_name, e)); return False
    except OSError as e:
        print("[ERROR] Could not run MGLTools: %s" % e); return False

def prepare_ligand(ligand_file_path):
    """
    Convert ligand (PDB/SDF/MOL2) -> PDBQT.
    Workaround for MolKit on Windows: run in the ligand's folder and pass only basename.
    Use ABSOLUTE output path so cwd changes don't break the -o destination.
    """
    if not os.path.exists(ligand_file_path):
        print("[ERROR] Ligand not found: %s" % ligand_file_path); return False

    ligand_file_path = os.path.abspath(ligand_file_path)
    lig_dir  = os.path.dirname(ligand_file_path)
    fname    = os.path.basename(ligand_file_path)
    base     = os.path.splitext(fname)[0]
    out_pdbqt = os.path.join(OUTPUT_LIGAND_DIR, "%s.pdbqt" % base)  # ABSOLUTE

    if (not FORCE_REBUILD) and os.path.isfile(out_pdbqt):
        print("[SKIP] Ligand exists -> %s" % out_pdbqt)
        return True

    if not os.path.exists(OUTPUT_LIGAND_DIR):
        os.makedirs(OUTPUT_LIGAND_DIR)

    cmd = [
        MGLTOOLS_PYTHON,
        os.path.join(MGLTOOLS_UTILS_DIR, "prepare_ligand4.py"),
        "-l", fname,                 # basename only (MolKit friendly)
        "-o", out_pdbqt,             # absolute output path
        "-A", LIGAND_ADD_FLAG        # default: checkhydrogens (override via env)
    ]
    try:
        subprocess.check_call(cmd, cwd=lig_dir)
        print("[OK] Ligand  -> %s" % out_pdbqt)
        return True
    except subprocess.CalledProcessError as e:
        print("[ERROR] prepare_ligand failed for %s: %s" % (fname, e)); return False
    except OSError as e:
        print("[ERROR] Could not run MGLTools: %s" % e); return False

# =======================
# Main
# =======================
if __name__ == "__main__":
    print("--- Starting Molecular File Preparation ---")
    _ensure_dirs()
    _check_tools()

    # Receptors
    print("\nProcessing protein files from: %s" % INPUT_PROTEIN_DIR)
    proteins = _list_files(INPUT_PROTEIN_DIR, (".pdb", ".PDB"))
    if not proteins:
        print("[INFO] No .pdb files found in %s." % INPUT_PROTEIN_DIR)
    ok_rec = 0
    for f in sorted(proteins):
        if prepare_receptor(os.path.join(INPUT_PROTEIN_DIR, f)): ok_rec += 1

    # Ligands (merge from both folders)
    print("\nProcessing ligand files from (priority): %s" % " , ".join(INPUT_LIGAND_DIRS))
    ligand_paths = _unique_ligand_paths()
    if not ligand_paths:
        print("[INFO] No ligand files (.pdb/.mol2/.sdf) found in %s." % " , ".join(INPUT_LIGAND_DIRS))
    ok_lig = 0
    for p in ligand_paths:
        if prepare_ligand(p): ok_lig += 1

    # Summary & exit code
    print("\n--- File Preparation Complete ---")
    print("Receptors prepared: %d / %d  ->  %s" % (ok_rec, len(proteins), OUTPUT_RECEPTOR_DIR))
    print("Ligands prepared:   %d / %d  ->  %s" % (ok_lig, len(ligand_paths), OUTPUT_LIGAND_DIR))
    if (ok_rec == 0 and len(proteins) > 0) or (ok_lig == 0 and len(ligand_paths) > 0):
        # If nothing succeeded while inputs existed, return non-zero so the pipeline can stop early
        sys.exit(2)
