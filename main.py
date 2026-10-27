import os
import sys
import glob
import logging
from src.clean_engine import clean_dataframes, capitalize_fields
from src.extract_from_sources import extract_all_sources
from src.transform_base_dims import transform_base_dimensions
from src.transform_conf_dims import transform_conformed_dimensions
from src.transform_fact_tabl import transform_fact_tables
from src.audit_homologation_tables import audit_homologation_tables
from src.load_to_parquet import load_all_to_parquet
from src.logs_manager import _clear_logs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Directorio de salida
OUTPUT_DIR = os.path.join("data", "processed")

def get_latest_file(pattern_path: str) -> str:
    """
    Busca los archivos que coinciden con el patrón especificado
    y retorna la ruta del más reciente por fecha de modificación.
    """
    matching_files = glob.glob(pattern_path)
    if not matching_files:
        logging.warning(f"⚠️ No se encontraron archivos con el patrón: '{pattern_path}'")
        return pattern_path
    
    latest_file = max(matching_files, key=os.path.getmtime)
    logging.info(f"🔎 Archivo detectado más reciente: {latest_file}")
    return latest_file

def get_all_files(pattern_path: str) -> list[str]:
    matching_files = glob.glob(pattern_path)
    if not matching_files:
        logging.warning(f"⚠️ No se encontraron archivos con el patrón: '{pattern_path}'")
        return []
    
    matching_files.sort(key=os.path.getmtime)
    logging.info(f"🔎 Archivos {pattern_path} detectados para procesar: {len(matching_files)}")
    return matching_files

def load_input_sources(config_path: str = os.path.join("config", "input_sources.txt")) -> dict[str, list[str]]:
    """
    Carga la configuración de fuentes desde un archivo TXT separado por '|'.
    """
    if not os.path.exists(config_path):
        sys.exit(f"❌ No se encontró el archivo de configuración: {config_path}")

    input_sources: dict[str, list[str]] = {}

    with open(config_path, "r", encoding="utf-8-sig") as file:

        # Read column names
        headers = [value.strip() for value in file.readline().split("|")]

        for line in file:
            if not line.strip():
                continue

            # Read values and remove surrounding spaces
            values = [value.strip() for value in line.split("|")]
            row = dict(zip(headers, values))

            key = row["key"]
            folder = row["folder"]
            pattern = row["filename_pattern"]

            # Use latest file if explicitly requested or pattern contains '*'
            mode = row.get("mode", "").lower()

            full_pattern = os.path.join(folder, pattern)

            if mode == "last":
                input_sources[key] = [get_latest_file(full_pattern)]
            elif mode == "all":
                input_sources[key] = get_all_files(full_pattern)               
            else:
                input_sources[key] = [full_pattern]

    return input_sources

def run_proyect_export(input_sources):
    try:
        raw_data = extract_all_sources(input_sources)
        clean_data = clean_dataframes(raw_data)
        load_all_to_parquet(clean_data, OUTPUT_DIR)
    except Exception as e:
        logging.critical(f"💥 Error crítico en el pipeline: {e}", exc_info=True)
 
def run_pipeline(input_sources):
    try:
        logging.info("🚀 === INICIANDO PIPELINE ETL (FASES 1 Y 2) ===")
        # 1. Extracción de datos crudos
        data_mart = {} #Shopping cart to check_out
        raw_data = extract_all_sources(input_sources)
        clean_data = clean_dataframes(raw_data)
        base_dims = transform_base_dimensions(clean_data)
        data_mart = data_mart | base_dims
        conformed_dims = transform_conformed_dimensions(clean_data, data_mart)
        data_mart = data_mart | conformed_dims
        audit_homologation_tables(clean_data,data_mart)
        fact_tables = transform_fact_tables(clean_data, data_mart)
        data_mart = data_mart | fact_tables
        data_mart = capitalize_fields(data_mart)

        # Agregar los datos de DEBUG
        #data_mart = data_mart | clean_data

        # Export Shopping cart contents
        load_all_to_parquet(data_mart, OUTPUT_DIR)

        logging.info("🎉 === FASES COMPLETADAS EXITOSAMENTE ===")

    except Exception as e:
        logging.critical(f"💥 Error crítico en el pipeline: {e}", exc_info=True)


if __name__ == "__main__":
    _clear_logs()        
    config_csv = os.path.join("config", "input_sources.txt")
    input_sources = load_input_sources(config_csv)   
    # Solo Proyectos
    # proy = {"archivoproyect": input_sources.pop("archivoproyect")}
    # run_proyect_export(proy)
    # Todo lo demas
    run_pipeline(input_sources)

