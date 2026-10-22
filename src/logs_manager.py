import pandas as pd
import csv
from pathlib import Path
import logging
import sys 

def _clear_logs() -> None:
    """Limpia el directorio Data.

    Si algún archivo está bloqueado, interrumpe el pipeline lanzando una
    excepción personalizada de negocio.
    """
    data_dir = Path("Data")

    if not data_dir.exists():
        return

    locked_files: list[str] = []

    for filepath in data_dir.glob("*"):
        if filepath.suffix in {".txt", ".csv"}:
            try:
                filepath.unlink()
            except (PermissionError, OSError):
                locked_files.append(filepath.name)

    if locked_files:
        files_list = ", ".join(locked_files)
        msg = (
            f"⛔ Pipeline abortado: No se pueden regenerar los archivos de auditoría. "
            f"Por favor cierra las siguientes planillas en Excel u otro programa:\n\n"
            f"{files_list}\n"
        )
        logging.error(msg)
        sys.exit()

def _generate_logs(module_name: str, pending_items: list[str]) -> None:
    data_dir = Path("Data")
    data_dir.mkdir(exist_ok=True)

    status = "Error" if pending_items else "OK"
    filepath = data_dir / f"{module_name}_{status}.txt"

    with filepath.open("w", encoding="utf-8") as f:
        f.write(f"REGISTROS PENDIENTES DE CORRECCIÓN - {module_name.upper()}\n")
        f.write("=" * 60 + "\n")

        if pending_items:
            f.writelines(f"- {item}\n" for item in pending_items)
        else:
            f.write("ESTADO: Sin errores.\n")

def _save_structured_audit_csv(module_name: str, df: pd.DataFrame) -> None:
    """Exporta un DataFrame de auditoría directamente a un archivo CSV compatible con Excel.

    Exige estrictamente un pd.DataFrame para garantizar la integridad del
    contrato.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"❌ [Contrato Violado] 'save_structured_audit_csv' en módulo '{module_name}' "
            f"esperaba un pd.DataFrame, pero recibió: {type(df).__name__}."
        )

    data_dir = Path("Data")
    data_dir.mkdir(parents=True, exist_ok=True)

    filepath = data_dir / f"{module_name}_Faltantes.csv"

    if not df.empty:
        df.to_csv(
            filepath,
            index=False,
            sep=";",
            encoding="utf-8-sig",
            quoting=csv.QUOTE_NONNUMERIC,
        )
        msg = f"Archivo de faltantes generado con {len(df)} registros."
        logging.warning(f" ⚠️ [{module_name}] {msg}")


    