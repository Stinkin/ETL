import logging
import pandas as pd
from src.logs_manager import _generate_logs

def _audit_homologacion_recurso(clean_data: dict[str, pd.DataFrame], data_mart: dict[str, pd.DataFrame]) -> bool:
    logging.info("⚙️ Auditando [HomologacionRecurso]...")
    pending_items: list[str] = []
    
    df_homolog = clean_data.get("HomologacionRecurso", pd.DataFrame())
    df_dim_rec = data_mart.get("DimRecurso", pd.DataFrame())
    
    if df_homolog.empty:
        logging.warning("⚠️ 'HomologacionRecurso' viene vacío o no se encontró.")
        return False

    # 1. Obtener conjunto de llaves válidas oficiales desde DimRecurso
    valid_keys = set(df_dim_rec["KeyRecurso"].dropna().unique()) if not df_dim_rec.empty and "KeyRecurso" in df_dim_rec.columns else set()

    df = df_homolog.copy()
    
    # 2. Asegurar tipado numérico para la llave evaluada
    if "KeyRecurso" in df.columns:
        df["KeyRecurso"] = pd.to_numeric(df["KeyRecurso"], errors="coerce").fillna(0).astype(int)
    else:
        logging.error("❌ [HomologacionRecurso] Columna 'KeyRecurso' no encontrada en la tabla de homologación.")
        return False

    # 3. Separar desvíos: Asignados al centinela (0) vs Huérfanos/Inexistentes
    mask_cero = df["KeyRecurso"] == 0
    mask_inexistentes = ~df["KeyRecurso"].isin(valid_keys) & (df["KeyRecurso"] != 0)

    df_ceros = df[mask_cero].copy()
    df_inexistentes = df[mask_inexistentes].copy()

    # 4. Registrar pendientes para el log general y auditorías estructuradas
    if not df_ceros.empty:
        msg = f"Se detectaron {len(df_ceros)} registro(s) en HomologacionRecurso mapeadas a Key 0."
        logging.warning(f" ⚠️ {msg}")
        for _, row in df_ceros.iterrows():
            nombre_orig = row.get("NombreRecurso", row.get("Recurso", "Desconocido"))
            pending_items.append(f"Key0 - Recurso '{nombre_orig}' mapeado a Key 0 en Homologacion >> Recursos")

    if not df_inexistentes.empty:
        msg = f"Se detectaron {len(df_inexistentes)} registro(s) apuntando a KeyRecurso inexistentes en DimRecurso."
        logging.warning(f" ⚠️ {msg}")
        for _, row in df_inexistentes.iterrows():
            nombre_orig = row.get("NombreRecurso", row.get("Recurso", "Desconocido"))
            key_invalida = row.get("KeyRecurso")
            pending_items.append(f"Asociacion - Recurso '{nombre_orig}' apunta a la Key '{key_invalida}' que NO existe en DimRecurso.")

    # 5. Guardar archivos de auditoría estructurada nivel 3
    _generate_logs("HomologacionRecurso", pending_items)

    logging.info("⚙️ [HomologacionRecurso] Auditoría finalizada con éxito.")
    return True

def _audit_homologacion_direccion(clean_data: dict[str, pd.DataFrame], data_mart: dict[str, pd.DataFrame]) -> bool:
    logging.info("⚙️ Auditando [HomologacionDireccion]...")
    pending_items: list[str] = []
    
    df_homolog = clean_data.get("HomologacionDireccion", pd.DataFrame())
    df_dim_dir = data_mart.get("DimDireccion", pd.DataFrame())
    
    if df_homolog.empty:
        logging.warning("⚠️ 'HomologacionDireccion' viene vacío o no se encontró.")
        return False

    # 1. Obtener conjunto de direcciones válidas oficiales desde DimDireccion (ya normalizadas previamente)
    valid_direcciones = set(df_dim_dir["Direccion"].dropna().unique()) if not df_dim_dir.empty and "Direccion" in df_dim_dir.columns else set()

    df = df_homolog.copy()
    
    # 2. Validar existencia de columnas necesarias
    if "DireccionOrigen" in df.columns and "DireccionHomologada" in df.columns:
        pass
    else:
        logging.error("❌ [HomologacionDireccion] Faltan columnas requeridas ('DireccionOrigen' o 'DireccionHomologada').")
        return False

    # 3. Detectar desvíos: Direcciones homologadas que NO existen en DimDireccion
    mask_inexistentes = ~df["DireccionHomologada"].isin(valid_direcciones)
    df_inexistentes = df[mask_inexistentes].copy()

    # 4. Registrar pendientes para el log general
    if not df_inexistentes.empty:
        msg = f"Se detectaron {len(df_inexistentes)} registro(s) con 'DireccionHomologada' inexistentes en DimDireccion."
        logging.warning(f" ⚠️ {msg}")
        for _, row in df_inexistentes.iterrows():
            orig = row.get("DireccionOrigen", "Desconocido")
            homolog = row.get("DireccionHomologada", "Desconocido")
            pending_items.append(f"DireccionInexistente - La direccion '{orig}' apunta a '{homolog}' que NO existe en DimDireccion.")

    # 5. Generar log unificado
    _generate_logs("HomologacionDireccion", pending_items)

    logging.info("⚙️ [HomologacionDireccion] Auditoría finalizada con éxito.")
    return True

def _audit_homologacion_equipo(clean_data: dict[str, pd.DataFrame], data_mart: dict[str, pd.DataFrame]) -> bool:
    logging.info("⚙️ Auditando [HomologacionDireccion]...")
    pending_items: list[str] = []
    
    df_homolog = clean_data.get("HomologacionEquipo", pd.DataFrame())
    df_dim_eq = data_mart.get("DimEquipo", pd.DataFrame())
    
    if df_homolog.empty:
        logging.warning("⚠️ 'HomologacionEquipo' viene vacío o no se encontró.")
        return False

    valid_equipos = set(df_dim_eq["Equipo"].dropna().unique()) if not df_dim_eq.empty and "Equipo" in df_dim_eq.columns else set()

    df = df_homolog.copy()
    
    # 2. Validar existencia de columnas necesarias
    if "EquipoOrigen" in df.columns and "EquipoHomologado" in df.columns:
        pass
    else:
        logging.error("❌ [HomologacionEquipos] Faltan columnas requeridas ('EquipoOrigen' o 'EquipoHomologado').")
        return False

    # 3. Detectar desvíos: Direcciones homologadas que NO existen en DimDireccion
    mask_inexistentes = ~df["EquipoHomologado"].isin(valid_equipos)
    df_inexistentes = df[mask_inexistentes].copy()

    # 4. Registrar pendientes para el log general
    if not df_inexistentes.empty:
        msg = f"Se detectaron {len(df_inexistentes)} registro(s) con 'EquipoHomologado' inexistentes en DimEquipo."
        logging.warning(f" ⚠️ {msg}")
        for _, row in df_inexistentes.iterrows():
            orig = row.get("EquipoOrigen", "Desconocido")
            homolog = row.get("EquipoHomologado", "Desconocido")
            pending_items.append(f"EquipoInexistente - El equipo '{orig}' apunta a '{homolog}' que NO existe en DimEquipo.")

    # 5. Generar log unificado
    _generate_logs("HomologacionEquipo", pending_items)

    logging.info("⚙️ [HomologacionEquipo] Auditoría finalizada con éxito.")
    return True

# =============================================================================
# MAPEO EXPLICITO DE DIMENSIONES CONFORMADAS (.parquet)
# "clave_origen_en_memoria": "Nombre_Final_Parquet"
# =============================================================================
HOMOLOGATION_BUILDERS = {
    "Recursos": _audit_homologacion_recurso,
    "Direcciones": _audit_homologacion_direccion,
    "Equipos": _audit_homologacion_equipo,
}

# =============================================================================
# FUNCIÓN MAESTRA ORQUESTADORA DE LA FASE 2
# =============================================================================

def audit_homologation_tables(clean_data: dict[str, pd.DataFrame], data_mart: dict[str, pd.DataFrame]) -> None:
    logging.info("--- INICIANDO VALIDACION DE HOMOLOGACIONES ---")
    checks_done = 0
    tests = 0
    for dim_name, audit_func in HOMOLOGATION_BUILDERS.items():
        if audit_func(clean_data, data_mart) :
            logging.info(f"  ↳ [{dim_name}] -> Verificada")
            checks_done += 1
        else:
            logging.warning(f"⚠️ No se pudo validar: '{dim_name}'")
        tests += 1

    logging.info(f"✅ HOMOLOGACIONES finalizadas. Verificaciones realizadas: {checks_done}/{tests}")
