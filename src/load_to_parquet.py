import os
import sys
import pandas as pd
from pathlib import Path
import logging

def load_all_to_parquet(processed_datasets: dict[str, pd.DataFrame], output_dir: str) -> None:
    """
    Guarda cada DataFrame procesado como un archivo Parquet (Snappy) para Power BI.
    """
    logging.info("--- INICIANDO CARGA A PARQUET ---")
    os.makedirs(output_dir, exist_ok=True)

    if not processed_datasets:
        logging.warning("⚠️ No hay DataFrames procesados para guardar.")
        return

    for table_name, df in processed_datasets.items():
        output_file = os.path.join(output_dir, f"{table_name}.parquet")
        logging.info(f"💾 Exportando [{table_name}] -> {output_file}")
        
        try:
            df.to_parquet(
                output_file,
                index=False,
                engine='pyarrow',
                compression='snappy'
            )
        except Exception as e:
            logging.error(f"❌ Error guardando {table_name}: {e}")

    logging.info(f"✅ Proceso de carga finalizado. Archivos en '{output_dir}'.")

def clear_parquets(directory) -> None:

    data_dir = Path(directory)

    if not data_dir.exists():
        return

    locked_files: list[str] = []

    for filepath in data_dir.glob("*"):
        if filepath.suffix in {".parquet",}:
            try:
                if filepath.stem.lower() != "bajadaproyectos":
                    filepath.unlink()
            except (PermissionError, OSError):
                locked_files.append(filepath.name)

    if locked_files:
        files_list = ", ".join(locked_files)
        msg = (
            f"⛔ Pipeline abortado: No se pueden eliminar los archivos de salida previos. "
            f"Por favor cierra los siguientes archivos en PowerBI u otro programa:\n\n"
            f"{files_list}\n"
        )
        logging.error(msg)
        sys.exit()