import pandas as pd
import re
import logging

def clean_registro_horas(df: pd.DataFrame) -> pd.DataFrame:

    df["Horas"] = (
        df["Horas"]
        .astype(str)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    return df

def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Higienización base estándar para el 100% de las fuentes.
    Garantiza salida estricta: sin tipos 'object', sin valores 'NAType' ni 'NaN'.
    """
    df_clean = df.copy()

    # 0. Limpieza de cabeceras de columnas (headers)
    df_clean.columns = (
        df_clean.columns.astype(str)
        .str.replace("\xa0", " ", regex=False)
        .str.strip()
    )

    # 1. Eliminar filas donde todos los valores sean nulos
    df_clean.dropna(how='all', inplace=True)

    # 2. Erradicar el tipo 'object' inicial
    # Se llenan nulos con cadena vacía ANTES de convertir, para evitar inyectar pd.NA
    object_cols = df_clean.select_dtypes(include=['object']).columns
    for col in object_cols:
        df_clean[col] = df_clean[col].astype("string").fillna("")

    # 3. Normalización de columnas de texto (ahora identificadas como 'string')
    string_cols = df_clean.select_dtypes(include=['string']).columns
    for col in string_cols:
        s = (
            df_clean[col]
            .str.replace("\xa0", " ", regex=False)      # Espacio de no separación
            .str.replace(r"\s+", " ", regex=True)        # Colapsa espacios múltiples
            .str.replace(r"\s*,\s*", ", ", regex=True)    # Estandariza comas
            .str.strip()    # Elimina espacios
            .str.title()   # Ajusta mayusculas, minusculas antes era .capitalize()
        )
        
        # Limpiar textos residuales
        s = s.replace(['nan', 'none', '<na>'], '')
        
        # Última barrera de seguridad: asegurar "" y forzar tipo string explícito
        df_clean[col] = s.fillna("").astype("string")

    # 4. Normalización de columnas numéricas (int / float / nullable ints)
    numeric_cols = df_clean.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        df_clean[col] = df_clean[col].fillna(0)

    # 5. Eliminar duplicados exactos
    df_clean.drop_duplicates(inplace=True)
    
    return df_clean

def clean_dataframes(raw_data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    Procesa la higiene base de todos los datasets crudos (Fase 1).
    Aplica sanitize_dataframe a cada fuente conservando sus claves canónicas en PascalCase.
    """
    logging.info("--- INICIANDO FASE HIGIENE UNIVERSAL DE DATASETS CRUDOS ---")
    cleaned_dims = {}


    for key in list(raw_data.keys()):
        df_raw = raw_data.pop(key)
        if df_raw is None or df_raw.empty:
            logging.warning(f"⚠️ El dataset '{key}' viene vacío en raw_data.")
            cleaned_dims[key] = pd.DataFrame()
            continue

        # 1. Aplicar higiene universal (remueve .0, limpia strings y nulos)
        df_clean = sanitize_dataframe(df_raw)        
        # 2. Asignar conservando la clave canónica normalizada
        cleaned_dims[key] = df_clean
        logging.info(f"  ↳ [{key}] -> Higienizado y listo en memoria ({len(df_clean)} filas)")

    if "RegistroHoras" in cleaned_dims:
        cleaned_dims["RegistroHoras"] = clean_registro_horas(cleaned_dims["RegistroHoras"])
        logging.info(f" 🔧 [Adjust] RegistroHoras reestructurado correctamente)")
      
    logging.info(f"✅ FASE HIGIENE finalizada. Datasets limpios listos: {len(cleaned_dims)}")

    return cleaned_dims

def capitalize_fields(input_df:dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    cols_to_upper = {
        "DimCiclo": {"Ciclo",},
        "DimDireccion": {"Direccion", },
        "DimEquipo": {"Equipo","Gerencia"},
        "DimProyecto": {"Cod Proy.","KeyProyecto"},
        "DimTarea":{"KeyProyecto"},
        "DimRecursoOrigen":{"RecursoOrigen"},
        "FactSeguimientoProyecto":{"KeyProyecto"},
        "FactSD":{"Equipo"},
    }

    # Apply row-value capitalization
    for df_key, columns in cols_to_upper.items():
        if df_key in input_df:
            df = input_df[df_key]
            for col in columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.upper()
    return input_df

def capitalize_specific_words(input_df: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Busca y fuerza la misma lista de palabras clave a mayúsculas 
       en múltiples DataFrames y columnas sin repetir código."""
    
    # 1. Definimos la lista única de palabras clave
    keywords = ["OV", "SAR", "SAP", "BI", "AYSA"]
    
    # 2. Configuramos el mapeo: { "DataFrame": ["columna1", "columna2", ...] }
    targets = {
        "DimProyecto": ["Nombre Proyecto"],
        "DimTarea": ["Tarea"],
        "DimRequerimiento": ["Requerimiento"]
    }
    
    # Compilamos las expresiones regulares una sola vez para mejorar el rendimiento
    patterns = [(word, re.compile(rf'\b{re.escape(word)}\b', re.IGNORECASE)) for word in keywords]
    
    for df_key, columns in targets.items():
        if df_key in input_df:
            df = input_df[df_key]
            for col in columns:
                if col in df.columns:
                    df[col] = df[col].astype(str)
                    # Aplicamos cada patrón de nuestra lista única
                    for word, pattern in patterns:
                        df[col] = df[col].str.replace(pattern, word.upper(), regex=True)
                        
    return input_df

def clean_up_columns(input_df: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    cleaned_dfs = {k: v.copy() for k, v in input_df.items()}
    cleaned_dfs = capitalize_fields(cleaned_dfs)
    cleaned_dfs = capitalize_specific_words(cleaned_dfs)
    return cleaned_dfs