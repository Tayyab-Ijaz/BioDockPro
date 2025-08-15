# convert_sdf_to_pdb.py  (run with Python 3: vizdock env)
import os
from pathlib import Path
from rdkit import Chem

SDF_DIR  = Path("data/ligands")
OUT_DIR  = Path("data/ligands_pdb")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def convert_one(sdf_path: Path) -> bool:
    # Read first molecule from SDF
    suppl = Chem.SDMolSupplier(str(sdf_path), removeHs=False)
    mol = suppl[0] if suppl and len(suppl) > 0 else None
    if mol is None:
        print(f"[WARN] RDKit could not read {sdf_path.name}")
        return False

    # Ensure we keep 3D coords if present; write PDB
    pdb_path = OUT_DIR / (sdf_path.stem + ".pdb")
    ok = Chem.MolToPDBFile(mol, str(pdb_path))
    # RDKit returns None; check the file
    if pdb_path.exists() and pdb_path.stat().st_size > 0:
        print(f"[OK] {sdf_path.name} -> {pdb_path}")
        return True
    print(f"[ERR] Failed to write PDB for {sdf_path.name}")
    return False

def main():
    sdf_files = sorted([p for p in SDF_DIR.glob("*.sdf")])
    if not sdf_files:
        print(f"[INFO] No SDF files in {SDF_DIR}")
        return
    ok = 0
    for sdf in sdf_files:
        if convert_one(sdf):
            ok += 1
    print(f"[DONE] Converted {ok}/{len(sdf_files)} SDF to PDB in {OUT_DIR}")

if __name__ == "__main__":
    main()
