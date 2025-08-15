import os
import requests

# Create directories for files
os.makedirs('data/proteins', exist_ok=True)
os.makedirs('data/ligands', exist_ok=True)

# Mapping proteins to their PDB IDs (you can add/change these)
protein_pdb_map = {
    'IL1B': '4G6J',
    'CD163': '5CRB',
    'ACY3': '1IVS',
    'P2RY12': '4NTJ',
    'TNF': '2AZ5',
}

# List of ligands, antibodies will be skipped for ligand download
ligands = {
    'CANAKINUMAB': None,
    'PENTAMIDINE': None,
    'GLUCOSAMINE': None,
    'FLUTICASONE': None,
    'BISOPROLOL': None,
    'ATENOLOL': None,
    'CANGRELOR': None,
    'PRASUGREL': None,
    'GOLIMUMAB': None,
    'MEROPENEM': None,
}

def download_pdb(pdb_id):
    url = f'https://files.rcsb.org/download/{pdb_id}.pdb'
    print(f"Downloading PDB for {pdb_id}...")
    r = requests.get(url)
    if r.status_code == 200:
        path = os.path.join('data', 'proteins', f'{pdb_id}.pdb')
        with open(path, 'wb') as f:
            f.write(r.content)
        print(f"Saved {path}")
    else:
        print(f"Failed to download PDB {pdb_id}")

def get_pubchem_cid(drug_name):
    url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug_name}/cids/JSON'
    print(f"Searching CID for {drug_name}...")
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        cids = data.get('IdentifierList', {}).get('CID', [])
        if cids:
            return cids[0]
    print(f"CID not found for {drug_name}")
    return None

def download_sdf(cid, drug_name):
    url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/SDF?record_type=3d'
    print(f"Downloading SDF for CID {cid} ({drug_name})...")
    r = requests.get(url)
    if r.status_code == 200:
        path = os.path.join('data', 'ligands', f'{drug_name}.sdf')
        with open(path, 'wb') as f:
            f.write(r.content)
        print(f"Saved {path}")
    else:
        print(f"Failed to download SDF for {drug_name}")

def main():
    # Download protein PDB files
    for protein, pdb_id in protein_pdb_map.items():
        download_pdb(pdb_id)

    # Download ligand files (skip antibodies)
    antibodies = ['CANAKINUMAB', 'GOLIMUMAB']
    for drug in ligands.keys():
        if drug.upper() in antibodies:
            print(f"Skipping antibody ligand {drug}")
            continue
        cid = get_pubchem_cid(drug)
        if cid:
            download_sdf(cid, drug)
        else:
            print(f"Skipping {drug} due to missing CID")

if __name__ == '__main__':
    main()
