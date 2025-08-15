# -*- coding: utf-8 -*-

import os
import sys
import subprocess

VINA_EXECUTABLE = r"C:\Program Files\AutoDock Vina\vina_1.2.7_win.exe"

BASE_DIR = "results/docking"
RECEPTOR_DIR = os.path.join(BASE_DIR, "receptors")
LIGAND_DIR   = os.path.join(BASE_DIR, "ligands")
DOCKING_RESULTS_DIR = os.path.join(BASE_DIR, "vina_outputs")

# Fallback box if parsing fails (Angstroms)
DEFAULT_CENTER = (0.0, 0.0, 0.0)
DEFAULT_SIZE   = (24.0, 24.0, 24.0)

# Optional manual boxes: receptor stem -> ((cx,cy,cz), (sx,sy,sz))
MANUAL_BOX = {
    # "5CRB": ((11.9145, 38.904, 40.986), (28.0, 28.0, 28.0)),
}

if not os.path.exists(DOCKING_RESULTS_DIR):
    os.makedirs(DOCKING_RESULTS_DIR)

def compute_box_from_receptor(receptor_pdbqt_path, margin=8.0, min_size=20.0, max_size=28.0):
    """Build a search box from receptor coordinates."""
    coords = []
    try:
        f = open(receptor_pdbqt_path)
        try:
            for line in f:
                if line.startswith("ATOM") or line.startswith("HETATM"):
                    try:
                        x = float(line[30:38]); y = float(line[38:46]); z = float(line[46:54])
                        coords.append((x, y, z))
                    except:
                        pass
        finally:
            f.close()
    except Exception as e:
        print("[WARN] Could not read receptor coords (%s): %s" % (receptor_pdbqt_path, e))

    if not coords:
        print("[WARN] No receptor coords parsed; using DEFAULT box.")
        return DEFAULT_CENTER + DEFAULT_SIZE

    xs, ys, zs = zip(*coords)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    cz = (min_z + max_z) / 2.0

    sx = max(min_size, min((max_x - min_x) + margin, max_size))
    sy = max(min_size, min((max_y - min_y) + margin, max_size))
    sz = max(min_size, min((max_z - min_z) + margin, max_size))

    return (cx, cy, cz, sx, sy, sz)

def run_docking(receptor_path, ligand_path):
    receptor_name = os.path.splitext(os.path.basename(receptor_path))[0]
    ligand_name   = os.path.splitext(os.path.basename(ligand_path))[0]

    if receptor_name in MANUAL_BOX:
        (cx, cy, cz), (sx, sy, sz) = MANUAL_BOX[receptor_name]
    else:
        cx, cy, cz, sx, sy, sz = compute_box_from_receptor(receptor_path)

    out_pdbqt = os.path.join(DOCKING_RESULTS_DIR, "%s__%s_out.pdbqt" % (receptor_name, ligand_name))
    log_file  = os.path.join(DOCKING_RESULTS_DIR, "%s__%s.log" % (receptor_name, ligand_name))

    cmd = [
        VINA_EXECUTABLE,
        "--receptor", receptor_path,
        "--ligand",   ligand_path,
        "--center_x", str(cx), "--center_y", str(cy), "--center_z", str(cz),
        "--size_x",   str(sx), "--size_y",   str(sy), "--size_z",   str(sz),
        "--exhaustiveness", "8",
        "--verbosity", "2",
        "--out", out_pdbqt,
    ]

    print("\nRunning docking: %s + %s" % (receptor_name, ligand_name))
    print(" Search box: center=(%.2f, %.2f, %.2f), size=(%.2f, %.2f, %.2f)" % (cx, cy, cz, sx, sy, sz))

    try:
        # Capture stdout/stderr and tee to our own log
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        lf = open(log_file, "w")
        try:
            for line in p.stdout:
                sys.stdout.write(line)
                lf.write(line)
        finally:
            lf.close()
        p.wait()
        if p.returncode != 0:
            print("[ERROR] Docking failed for %s + %s (exit %d)" % (receptor_name, ligand_name, p.returncode))
            return None
        print("[OK] Docking complete. Output: %s" % out_pdbqt)
        return log_file
    except OSError as e:
        print("[ERROR] Could not execute Vina at '%s': %s" % (VINA_EXECUTABLE, e))
        return None

def parse_binding_affinity(log_file):
    """Parse 'REMARK VINA RESULT:' from our captured log (if present)."""
    affinity = None
    try:
        f = open(log_file)
        try:
            for line in f:
                s = line.strip()
                if s.startswith("REMARK VINA RESULT:"):
                    parts = s.split()
                    if len(parts) >= 4:
                        affinity = float(parts[3])
                    break
        finally:
            f.close()
    except Exception as e:
        print("[WARN] Could not parse affinity from %s: %s" % (log_file, e))
    return affinity

if __name__ == "__main__":
    if not os.path.exists(VINA_EXECUTABLE):
        sys.stderr.write("[ERROR] Vina executable not found at: %s\n" % VINA_EXECUTABLE); sys.exit(1)
    if not os.path.isdir(RECEPTOR_DIR) or not os.path.isdir(LIGAND_DIR):
        sys.stderr.write("[ERROR] Expected receptor/ligand folders:\n  %s\n  %s\n" % (RECEPTOR_DIR, LIGAND_DIR)); sys.exit(1)

    receptors = [os.path.join(RECEPTOR_DIR, f) for f in os.listdir(RECEPTOR_DIR) if f.lower().endswith(".pdbqt")]
    ligands   = [os.path.join(LIGAND_DIR,   f) for f in os.listdir(LIGAND_DIR)   if f.lower().endswith(".pdbqt")]
    if not receptors:
        sys.stderr.write("[ERROR] No receptor PDBQT files found in %s\n" % RECEPTOR_DIR); sys.exit(1)
    if not ligands:
        sys.stderr.write("[ERROR] No ligand PDBQT files found in %s\n" % LIGAND_DIR); sys.exit(1)

    results = []
    for rec in receptors:
        for lig in ligands:
            log_path = run_docking(rec, lig)
            if log_path:
                aff = parse_binding_affinity(log_path)
                results.append((os.path.basename(rec), os.path.basename(lig), aff))

    print("\n=== Docking Summary ===")
    print("{:<30} {:<30} {:>20}".format('Protein', 'Ligand', 'Affinity (kcal/mol)'))
    print("-" * 80)
    for rec, lig, aff in results:
        aff_str = ("%.2f" % aff) if (aff is not None) else "N/A"
        print("{:<30} {:<30} {:>20}".format(rec, lig, aff_str))
