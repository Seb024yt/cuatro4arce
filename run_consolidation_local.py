import os
import sys
from app.data_processor import consolidate_data

job_id = "test_job_manual_047"
base_dir = "sii_data"
download_dir = os.path.join(base_dir, "descargados", job_id)
output_dir = os.path.join(base_dir, "generados")
output_file = os.path.join(output_dir, f"Planilla_{job_id}_v3.xlsx")

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print(f"Consolidating {download_dir} to {output_file}...")
try:
    consolidate_data(download_dir, output_file)
    print("Consolidation complete.")
except Exception as e:
    print(f"Error: {e}")
