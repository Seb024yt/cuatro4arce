import os
import pandas as pd
import glob

def consolidate_data(download_dir: str, output_file: str):
    """
    Reads all downloaded files in download_dir, consolidates them,
    and saves to output_file (Excel).
    """
    writer = pd.ExcelWriter(output_file, engine='openpyxl')
    
    # 1. Process Compras (CSV)
    compras_files = glob.glob(os.path.join(download_dir, "*Compra*.csv"))
    if compras_files:
        # Assuming last modified is the one we want or merge all?
        # User said "Iterar desde Enero hasta Mes M", so likely multiple files.
        all_compras = []
        for f in compras_files:
            try:
                df = pd.read_csv(f, sep=';', encoding='latin-1') # SII often uses ; and latin-1
                all_compras.append(df)
            except:
                pass
        
        if all_compras:
            df_compras = pd.concat(all_compras)
            df_compras.to_excel(writer, sheet_name='Compras', index=False)
            
            # Create Summary/Pivot
            if 'Monto Total' in df_compras.columns:
                 # Clean data if necessary (remove dots, replace comma with dot)
                pass

    # 2. Process Ventas (CSV)
    ventas_files = glob.glob(os.path.join(download_dir, "*Venta*.csv"))
    if ventas_files:
        all_ventas = []
        for f in ventas_files:
            try:
                df = pd.read_csv(f, sep=';', encoding='latin-1')
                all_ventas.append(df)
            except:
                pass
        
        if all_ventas:
            df_ventas = pd.concat(all_ventas)
            df_ventas.to_excel(writer, sheet_name='Ventas', index=False)

    # 3. Process Honorarios (Excel/CSV)
    honorarios_files = glob.glob(os.path.join(download_dir, "*Honorarios*.xls*")) # or csv
    # Note: Logic depends on actual file name pattern
    
    writer.close()
    return output_file
