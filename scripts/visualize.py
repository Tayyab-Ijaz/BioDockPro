#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Visualize docking results:
 - 2D PNGs from original SDF/MOL2 ligands (RDKit)
 - 3D PNGs of receptor + docked pose (PyMOL, ray traced, perspective)
 - Flat 2D-style PNGs of receptor + docked pose (PyMOL, no ray, orthoscopic)
Requirements (same environment): pymol, rdkit (vizdock env)
"""

import os
import sys

# ==== Enforce the right interpreter (vizdock) ====
EXPECTED_PY = r"C:\Users\Tayyab\miniconda3\envs\vizdock\python.exe"
if os.environ.get("VIZ_IGNORE_PY_CHECK", "0") not in ("1", "true", "True"):
    if os.path.abspath(sys.executable) != os.path.abspath(EXPECTED_PY):
        sys.stderr.write(
            "[ERROR] visualize.py must be run with the vizdock Python:\n"
            f'  "{EXPECTED_PY}" visualize.py <ligand_folder> <docking_folder> <output_folder>\n'
            f"  (Got: {sys.executable})\n"
            "To override this check (not recommended), set VIZ_IGNORE_PY_CHECK=1.\n"
        )
        sys.exit(2)

# ==== Imports (must succeed in vizdock) ====
try:
    from pymol import cmd
except Exception as e:
    sys.stderr.write("[ERROR] Could not import PyMOL 'cmd'. Is PyMOL installed in vizdock? %s\n" % e)
    sys.exit(3)

try:
    from rdkit import Chem
    from rdkit.Chem import Draw
except Exception as e:
    sys.stderr.write("[ERROR] Could not import RDKit. Is RDKit installed in vizdock? %s\n" % e)
    sys.exit(4)

# ==== Paths (for matching receptors) ====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
A = lambda *p: os.path.abspath(os.path.join(SCRIPT_DIR, *p))

RECEPTOR_PDB_DIR   = A("data", "proteins")                      # preferred (cartoon quality)
RECEPTOR_PDBQT_DIR = A("results", "docking", "receptors")       # fallback

# ---------- 2D LIGAND IMAGES ----------
def generate_2d_images(ligand_folder, out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    ligs = [f for f in os.listdir(ligand_folder)
            if f.lower().endswith((".sdf", ".mol2"))]
    if not ligs:
        print("No ligand files found in %s" % ligand_folder)
        return

    for fname in sorted(ligs):
        path = os.path.join(ligand_folder, fname)
        mols = []

        if fname.lower().endswith(".sdf"):
            suppl = Chem.SDMolSupplier(path, removeHs=False, sanitize=True)
            if suppl:
                for m in suppl:
                    if m: mols.append(m)
        else:  # .mol2
            m = Chem.MolFromMol2File(path, sanitize=True, removeHs=False)
            if m: mols.append(m)

        if not mols:
            print("Failed to read ligand:", fname)
            continue

        # Save ONE PNG per file (first molecule)
        mol = mols[0]
        try:
            Chem.Kekulize(mol, clearAromaticFlags=True)
        except:
            pass
        try:
            Chem.rdDepictor.Compute2DCoords(mol)
        except:
            pass

        img_path = os.path.join(out_dir, os.path.splitext(fname)[0] + ".png")
        img = Draw.MolToImage(mol, size=(500, 500))
        img.save(img_path)
        print("Saved 2D image:", img_path)

# ---------- Helpers for receptor ↔ vina_out mapping ----------
def _find_receptor_for_vina_out(vina_out_path):
    """
    vina out file name format: <REC>__<LIG>_out.pdbqt
    Returns (rec_name, receptor_path or None)
    """
    base = os.path.basename(vina_out_path)
    stem = os.path.splitext(base)[0]              # e.g. 5CRB__PRASUGREL_out
    parts = stem.split("__")
    if len(parts) < 2:
        return None, None
    rec_name = parts[0]

    pdb = os.path.join(RECEPTOR_PDB_DIR, rec_name + ".pdb")
    if os.path.isfile(pdb):
        return rec_name, pdb

    pdbqt = os.path.join(RECEPTOR_PDBQT_DIR, rec_name + ".pdbqt")
    if os.path.isfile(pdbqt):
        return rec_name, pdbqt

    return rec_name, None

# ---------- Scene styles ----------
def _style_flat_2d():
    """Flat, publication-style look (orthoscopic, no ray/shadows)."""
    cmd.bg_color("white")
    cmd.set("orthoscopic", 1)
    cmd.set("ray_opaque_background", 0)
    cmd.set("antialias", 2)

    # kill 3D lighting/shadows
    cmd.set("ambient", 1.0)
    cmd.set("specular", 0.0)
    cmd.set("shininess", 0)
    cmd.set("light_count", 1)
    cmd.set("depth_cue", 0)
    cmd.set("ray_shadows", 0)
    cmd.set("ray_trace_fog", 0)

def _style_3d():
    """Nicely lit 3D scene (perspective + ray)."""
    cmd.bg_color("white")
    cmd.set("orthoscopic", 0)  # perspective
    cmd.set("ray_opaque_background", 0)
    cmd.set("antialias", 2)

    try:
        cmd.set("ambient", 0.15)
        cmd.set("specular", 0.6)
        cmd.set("shininess", 60)
    except:
        pass
    cmd.set("light_count", 8)
    cmd.set("depth_cue", 1)
    cmd.set("ray_shadows", 1)
    cmd.set("ray_trace_fog", 1)

def _load_complex(rec_path, vina_out_path, receptor_rep="cartoon", receptor_color="gray80"):
    """Load receptor (if path given) + docked ligand pose, and style them."""
    if rec_path:
        cmd.load(rec_path, "rec")
        try:
            cmd.dss("rec")  # assign secondary structure when possible
        except:
            pass
        cmd.hide("everything", "rec")
        cmd.show(receptor_rep, "rec")
        cmd.color(receptor_color, "rec")
    cmd.load(vina_out_path, "lig")
    cmd.hide("everything", "lig")
    cmd.show("sticks", "lig")
    cmd.set("stick_radius", 0.18, "lig")
    cmd.color("marine", "lig")
    # focus camera
    try:
        cmd.zoom("lig", 10)
    except:
        cmd.zoom()
    # keep near/far clipping reasonable for headless renders
    cmd.clip("slab", 40)

# ---------- Rendering ----------
def visualize_docking(docking_folder, out_dir_3d, out_dir_flat):
    if not os.path.exists(out_dir_3d):
        os.makedirs(out_dir_3d)
    if not os.path.exists(out_dir_flat):
        os.makedirs(out_dir_flat)

    vina_files = [f for f in os.listdir(docking_folder)
                  if f.lower().endswith("_out.pdbqt") and "__" in f]
    if not vina_files:
        print("No vina output files (*__*_out.pdbqt) found in %s" % docking_folder)
        return

    for f in sorted(vina_files):
        path = os.path.join(docking_folder, f)
        rec_name, rec_path = _find_receptor_for_vina_out(path)
        base = os.path.splitext(f)[0]

        # ---------- Flat 2D snapshot ----------
        cmd.reinitialize()
        _style_flat_2d()
        if rec_path:
            _load_complex(rec_path, path, receptor_rep="lines", receptor_color="gray50")
            cmd.set("line_width", 2.0, "rec")
        else:
            _load_complex(None, path)
        flat_png = os.path.join(out_dir_flat, base + "__flat.png")
        cmd.png(flat_png, width=1400, height=1000, dpi=220, ray=0)  # no ray
        print("  Saved 2D-style complex image:", flat_png)

        # ---------- Ray-traced 3D render ----------
        cmd.reinitialize()
        _style_3d()
        if rec_path:
            _load_complex(rec_path, path, receptor_rep="cartoon", receptor_color="gray80")
            # Optional: translucent surface around ligand neighborhood
            try:
                cmd.show("surface", "rec and byres (lig expand 4)")
                cmd.set("surface_quality", 1)
                cmd.set("transparency", 0.35, "rec")
            except:
                pass
        else:
            _load_complex(None, path)
        ray_png = os.path.join(out_dir_3d, base + ".png")
        cmd.png(ray_png, width=1000, height=750, dpi=150, ray=1)  # ray on
        print("  Saved 3D docking image:", ray_png)

# ---------- CLI ----------
def main():
    if len(sys.argv) < 4:
        print("Usage: python visualize.py <ligand_folder> <docking_folder> <output_folder>")
        sys.exit(1)

    ligand_folder  = sys.argv[1]
    docking_folder = sys.argv[2]
    output_folder  = sys.argv[3]

    out2d       = os.path.join(output_folder, "2D")
    out3d       = os.path.join(output_folder, "3D")
    out2d_cpx   = os.path.join(output_folder, "2D_complex")

    print("Generating 2D ligand images...")
    generate_2d_images(ligand_folder, out2d)

    print("Generating complex images (flat 2D + ray-traced 3D)...")
    visualize_docking(docking_folder, out3d, out2d_cpx)

    print("Visualization complete.")

if __name__ == "__main__":
    main()
