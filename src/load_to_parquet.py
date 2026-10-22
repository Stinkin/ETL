import os
import pandas as pd
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
