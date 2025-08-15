import os
import csv

LOG_DIR = "results/docking/vina_outputs"
OUTPUT_CSV = "results/binding_energies.csv"

def parse_binding_affinity(log_file):
    affinity = None
    try:
        with open(log_file) as f:
            for line in f:
                if line.strip().startswith("REMARK VINA RESULT:"):
                    parts = line.strip().split()
                    affinity = float(parts[3])
                    break
    except Exception, e:
        print("[WARN] Could not parse %s: %s" % (log_file, e))
    return affinity

def main():
    if not os.path.exists(LOG_DIR):
        print("[ERROR] Log directory %s not found." % LOG_DIR)
        return

    log_files = [f for f in os.listdir(LOG_DIR) if f.endswith(".log")]
    if not log_files:
        print("[INFO] No log files found in %s" % LOG_DIR)
        return

    results = []
    for log_file in log_files:
        full_path = os.path.join(LOG_DIR, log_file)
        affinity = parse_binding_affinity(full_path)
        # split protein and ligand by __ separator in filename
        try:
            protein, ligand = log_file.replace(".log", "").split("__")
        except ValueError:
            protein = ligand = log_file.replace(".log", "")
        results.append([protein, ligand, affinity])

    if not os.path.exists(os.path.dirname(OUTPUT_CSV)):
        os.makedirs(os.path.dirname(OUTPUT_CSV))

    with open(OUTPUT_CSV, "wb") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Protein", "Ligand", "Binding Affinity (kcal/mol)"])
        for row in results:
            writer.writerow(row)

    print("[OK] Binding affinities saved to %s" % OUTPUT_CSV)

if __name__ == "__main__":
    main()
