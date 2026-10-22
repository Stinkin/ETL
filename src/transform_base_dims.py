import pandas as pd
import logging

def standardize_dim_columns(df: pd.DataFrame, dim_name: str) -> pd.DataFrame:
    """Estandariza automáticamente las columnas de cualquier tabla Dim.

    Convierte la primera columna (PK) en 'Key<NombreDim>' y la segunda (NK) en
    '<NombreDim>'.
    """
    if df.empty or len(df.columns) < 2:
        return df

    # Extraer nombre base: 'DimProyectoEstado' -> 'ProyectoEstado'
    entity_name = dim_name.replace("Dim", "").strip()

    expected_pk = f"Key{entity_name}"  # KeyProyectoEstado
    expected_desc = entity_name  # ProyectoEstado

    # Renombrar las dos primeras columnas por posición (PK y NK/Descripción)
    col_mapping = {
        df.columns[0]: expected_pk,
        df.columns[1]: expected_desc,
    }

    return df.rename(columns=col_mapping)

def transform_base_dimensions(clean_data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    Fase 3: Extrae únicamente las dimensiones base puras de clean_data usando .pop().
    
    Las tablas de homologación e insumos operativos no se tocan y permanecen
    en clean_data para ser consumidas posteriormente por Conformed y Facts.
    """
    logging.info("--- INICIANDO CONSTRUCCION DE DIMENSIONES BASE ---")
    base_dims = {}

    # Solo dimensiones base puras que se promueven y se sacan de memoria intermedia
    PURE_BASE_KEYS = [
    'DimEquipo', 
    'DimRecursoPerfil', 
    'DimRecursoSkill', 
    'DimRecursoOrigen', 
    'DimRecursoVinculo', 
    'DimRequerimientoCategoria', 
    'DimTareaClasificacion', 
    'DimDireccion', 
    'DimBolsa', 
    'DimCiclo', 
    'DimProyectoEstado', 
    'DimProyectoSituacion', 
    ]

    for key in PURE_BASE_KEYS:
        if key in clean_data:
            base_dims[key] = clean_data.pop(key)
            logging.info(f"  ↳ [{key}] -> Promovida a base_dims y removida de clean_data ({len(base_dims[key])} filas)")
        else:
            logging.warning(f"⚠️ No se encontró la dimensión base esperada: '{key}'")

    # Estandarización automática de columnas (Key<Entidad> / <Entidad>)
    for key in base_dims:
        base_dims[key] = standardize_dim_columns(base_dims[key], key)

    logging.info(f"✅ DIMENSIONES BASE finalizada. Dimensiones base listas: {len(base_dims)}")
    return base_dims