import pandas as pd
import logging
from datetime import datetime
from src.logs_manager import _generate_logs, _save_structured_audit_csv

# =============================================================================
# FUNCIONES ESPECÍFICAS DE CONSTRUCCIÓN POR DIMENSIÓN
# =============================================================================

def _build_dim_recurso(clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Construcción y validación para DimRecurso:
    - Conserva siempre las entidades válidas a nivel de PK (KeyRecurso).
    - Valida integridad referencial contra dimensiones base sin alterar los tipos de datos originales.
    - Captura en pending_items todos los desvíos (FKs inexistentes) imputándolos al valor centinela 0.
    - Genera el log de auditoría 'Error_DimRecurso.txt' vía _save_log.
    """
    df_raw = clean_data.get("TablaRecursos", pd.DataFrame()).copy()
    pending_items = []

    if df_raw.empty:
        logging.warning("⚠️ 'TablaRecursos' está vacío o no se encontró en clean_data.")
        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # 0. SELECCIÓN SEGURA DE COLUMNAS (PROYECCIÓN)
    # -------------------------------------------------------------------------
    cols = [
        "KeyRecurso",
        "NombreRecurso",
        "Activo",
        "KeyRecursoPerfil",
        "KeyRecursoSkill",
        "KeyEquipo",
        "KeyRecursoVinculo",
        "KeyRecursoOrigen",
    ]
    
    # Solo seleccionamos las columnas del contrato que SI vinieron en el archivo
    columnas_presentes = [c for c in cols if c in df_raw.columns]
    df = df_raw[columnas_presentes].copy()

    # -------------------------------------------------------------------------
    # 1. VALIDACIÓN DE CONTRATO Y PK (DESCARTE INNEGOCIABLE)
    # -------------------------------------------------------------------------
    if "KeyRecurso" in df.columns:
        # Registros con PK nula o vacía
        mask_valid_key = df["KeyRecurso"].notna() & (df["KeyRecurso"] != "")
        invalid_keys_cnt = (~mask_valid_key).sum()
        if invalid_keys_cnt > 0:
            logging.error(f"❌ [DimRecurso] Se descartaron {invalid_keys_cnt} registros por 'KeyRecurso' nulo o vacío.")
            df = df[mask_valid_key]

        # Registros duplicados por PK
        duplicated_mask = df.duplicated(subset=["KeyRecurso"], keep="first")
        duplicated_cnt = duplicated_mask.sum()
        if duplicated_cnt > 0:
            logging.error(f"❌ [DimRecurso] Se descartaron {duplicated_cnt} registros duplicados por 'KeyRecurso'.")
            df = df[~duplicated_mask]
    else:
        logging.error("❌ [DimRecurso] Columna 'KeyRecurso' no encontrada en el origen.")
        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # 2. VALIDACIÓN DE ATRIBUTOS OBLIGATORIOS (NombreRecurso)
    # -------------------------------------------------------------------------
    if "NombreRecurso" in df.columns:
        mask_sin_nombre = df["NombreRecurso"].isna() | (df["NombreRecurso"] == "")
        if mask_sin_nombre.any():
            for idx, row in df[mask_sin_nombre].iterrows():
                key_rec = row["KeyRecurso"]
                pending_items.append(f"KeyRecurso {key_rec}: NombreRecurso nulo o vacío (Asignado a 'Sin Nombre')")
            
            logging.warning(f"⚠️ [DimRecurso] {mask_sin_nombre.sum()} recursos sin nombre válido.")
            df["NombreRecurso"] = df["NombreRecurso"].fillna("Sin Nombre").replace("", "Sin Nombre")

    # -------------------------------------------------------------------------
    # 3. INTEGRIDAD REFERENCIAL DE FKs (NOMBRES EXPLÍCITOS Y SIN CASTEO DEFENSIVO)
    # -------------------------------------------------------------------------
    fk_validations = [
        ("KeyEquipo", "DimEquipo", "KeyEquipo"),
        ("KeyRecursoPerfil", "DimRecursoPerfil", "KeyRecursoPerfil"),
        ("KeyRecursoSkill", "DimRecursoSkill", "KeyRecursoSkill"),
        ("KeyRecursoOrigen", "DimRecursoOrigen", "KeyRecursoOrigen"),
        ("KeyRecursoVinculo", "DimRecursoVinculo", "KeyRecursoVinculo"),
    ]

    for fk_col, target_table, target_pk in fk_validations:
        if fk_col in df.columns:
            dim_df = base_dims.get(target_table, pd.DataFrame())

            if not dim_df.empty and target_pk in dim_df.columns:
                valid_keys = set(dim_df[target_pk].dropna().unique())
                
                # Evaluación directa respetando los tipos de datos nativos
                mask_valido = df[fk_col].notna() & df[fk_col].isin(valid_keys)
            else:
                # Si la dimensión base no existe o no tiene registros, solo el valor centinela 0 es válido
                mask_valido = df[fk_col].isin({0})

            mask_invalido = ~mask_valido

            if mask_invalido.any():
                df_invalidos = df[mask_invalido]
                for idx, row in df_invalidos.iterrows():
                    key_rec = row["KeyRecurso"]
                    val_err = row[fk_col]
                    pending_items.append(
                        f"KeyRecurso {key_rec}: Valor inválido '{val_err}' en FK '{fk_col}' "
                        f"(no existe en '{target_table}').(Asignado a Key '0')"
                    )

                logging.warning(
                    f"⚠️ [DimRecurso] {mask_invalido.sum()} registros con '{fk_col}' inválido. "
                )

                # Imputación del centinela 0 respetando la serie
                df[fk_col] = df[fk_col].where(mask_valido, 0)
        else:
            msg = f"Columna '{fk_col}' no presente en TablaRecursos. (Asignados a Key '0')"
            logging.warning(f"⚠️ [DimRecurso] {msg}")
            pending_items.append(msg)
            df[fk_col] = 0

    # -------------------------------------------------------------------------
    # 4. AUDITORÍA Y SALIDA
    # -------------------------------------------------------------------------
    logging.info(f"  ↳ [DimRecurso] Procesamiento finalizado. {len(df)} recursos consolidados.")
    _generate_logs("DimRecurso", pending_items)
    
    return df

def _build_dim_fecha(clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Genera sintéticamente la Dimensión Tiempo/Fecha (3 años al pasado, 3 años al futuro).
    No consume fuentes externas de clean_data ni base_dims.
    """
    meses_espanol = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    dias_espanol = {
        0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
        4: "Viernes", 5: "Sábado", 6: "Domingo"
    }
    
    current_year = datetime.now().year
    start_date = f"{current_year - 3}-01-01"
    end_date = f"{current_year + 3}-12-31"

    # Generar serie continua de fechas
    date_series = pd.date_range(start=start_date, end=end_date, freq='D')
    df = pd.DataFrame({"Fecha_dt": date_series})

    # -------------------------------------------------------------------------
    # CONSTRUCCIÓN DE ATRIBUTOS DIMENSIONALES
    # -------------------------------------------------------------------------
    df["KeyFecha"] = df["Fecha_dt"].dt.strftime("%Y%m%d").astype(int)
    df["Fecha"] = df["Fecha_dt"].dt.date
    df["Año"] = df["Fecha_dt"].dt.year
    df["Trimestre"] = df["Fecha_dt"].dt.quarter
    df["Mes"] = df["Fecha_dt"].dt.strftime("%m")
    df["NombreMes"] = df["Fecha_dt"].dt.month.map(meses_espanol)
    df["Semana"] = df["Fecha_dt"].dt.isocalendar().week.astype(int)
    
    # Ajustes en los días:
    df["DiaDelMes"] = df["Fecha_dt"].dt.strftime("%d")
    df["DiaSemana"] = df["Fecha_dt"].dt.dayofweek + 1  # 1 (Lunes) a 7 (Domingo)
    df["NombreDiaSemana"] = df["Fecha_dt"].dt.dayofweek.map(dias_espanol)

    # Limpieza de columna auxiliar
    df.drop(columns=["Fecha_dt"], inplace=True)

    logging.info(f"  ↳ [DimFecha] Generados {len(df)} días ({start_date} a {end_date}).")
    return df

def _build_dim_proyecto(clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Construcción y validación de DimProyecto (Fase 2):
    - Filtra registros válidos (Proyecto != 'NO' y no vacíos).
    - Mapea FKs (KeyDireccion, KeyEquipo, KeyCiclo) vía diccionarios puros (evitando merges).
    - Genera logs de auditoría para entidades no homologadas.
    - Asigna clave centinela (0 o "0") a las FKs no resueltas.
    """
    df_raw = clean_data.get("BajadaProyectos", pd.DataFrame()).copy()
    pending_items = []
    
    if df_raw.empty:
        logging.warning("⚠️ 'BajadaProyectos' está vacío o no se encontró en raw_data.")
        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # 1. FILTRO DE NEGOCIO PRINCIPAL
    # -------------------------------------------------------------------------
    # Confiamos en el contrato de clean_data: no hay falsos nulos en string.
    # Solo aplicamos la regla de negocio explícita: excluir los que no son proyectos ("NO").

    if "Proyecto" in df_raw.columns:
        # Regla de negocio y contrato: Proyecto debe tener un nombre válido, no nulo y distinto de 'NO'
        mask_valido = (
            (df_raw["Proyecto"] != "No") & 
            df_raw["Proyecto"].notna() & 
            (df_raw["Proyecto"] != "")
        )
        df = df_raw[mask_valido].copy()
        descartados_negocio =  len(df_raw) - len(df)
        if descartados_negocio > 0:
            logging.info(f"  ↳ [DimProyecto] {descartados_negocio} registros excluidos por 'Proyecto' inválido (NO, nulo o vacío).")
    else:
        df = df_raw.copy()

    df["KeyProyecto"] = df.get("Cod Proy.")
    df["NombreProyecto"] = df.get("Nombre de tarea")
    df["Sistema"] = df.get("Sistemas")

    # -------------------------------------------------------------------------
    # 2. VALIDACIONES DE OBLIGATORIEDAD Y CONTRATO (DESCARTE)
    # -------------------------------------------------------------------------
    # Aquí validamos la integridad. Si clean_data dejó pasar verdaderos nulos (NaN o ""), 
    # se descartan y se levanta el log de error para auditar la falla.
    for col, nombre_log in [("KeyProyecto", "Cod Proy."), ("NombreProyecto", "Nombre de tarea")]:
        mask_ok = df[col].notna() & (df[col] != "")
        invalid_cnt = (~mask_ok).sum()
        if invalid_cnt > 0:
            logging.error(f"❌ [DimProyecto] Se descartaron {invalid_cnt} registros por '{nombre_log}' nulo o vacío.")
            df = df[mask_ok]


    # -------------------------------------------------------------------------
    # 3. RESOLUCIÓN DE CLAVES EXTERNAS Y AUDITORÍA
    # -------------------------------------------------------------------------
    
    # -------------------------------------------------------------------------
    # A) KeyDireccion (vía HomologacionDireccion -> DimDireccion)
    # -------------------------------------------------------------------------
    df_homolog_dir = clean_data.get("HomologacionDireccion", pd.DataFrame())
    dim_direccion = base_dims.get("DimDireccion", pd.DataFrame())

    if not df_homolog_dir.empty and not dim_direccion.empty and "Dirección Solicitante" in df.columns:
        # Diccionarios de mapeo directo
        map_homolog_dir = dict(zip(df_homolog_dir["DireccionOrigen"], df_homolog_dir["DireccionHomologada"]))
        col_desc_dir = "Direccion" if "Direccion" in dim_direccion.columns else dim_direccion.columns[1]
        map_dim_dir = dict(zip(dim_direccion[col_desc_dir], dim_direccion["KeyDireccion"]))

        # Mapeo en cascada (Origen -> Homologación -> Dimensión)
        s_dir_homologada = df["Dirección Solicitante"].map(map_homolog_dir)
        s_key_dir = s_dir_homologada.map(map_dim_dir)

        # Identificación de desvíos consolidada por KeyProyecto
        mask_sin_dir = s_key_dir.isna()
        unique_prods = sorted(list(set(df[mask_sin_dir]["KeyProyecto"].dropna().tolist())))

        # Log de auditoría estandarizado
        for p in unique_prods:
            pending_items.append(f"KeyProyecto {p}: Dirección Solicitante no homologada (Asignada a Key 0)")
        
        if unique_prods:
            logging.warning(f"⚠️ [DimProyecto] {len(unique_prods)} proyectos sin dirección homologada.")

        # Imputación a la clave centinela 0
        df["KeyDireccion"] = s_key_dir.fillna(0).astype(int)
    else:
        df["KeyDireccion"] = 0

    # B) KeyEquipo
    df_homolog_eq = clean_data.get("HomologacionEquipo", pd.DataFrame())
    dim_equipo = base_dims.get("DimEquipo", pd.DataFrame())

    if not df_homolog_eq.empty and not dim_equipo.empty and "Grupo de recursos" in df.columns:
        map_homolog_eq = dict(zip(df_homolog_eq["EquipoOrigen"], df_homolog_eq["EquipoHomologado"]))
        map_dim_eq = dict(zip(dim_equipo["Equipo"], dim_equipo["KeyEquipo"]))

        s_sigla_eq = df["Grupo de recursos"].map(map_homolog_eq)
        s_key_eq = s_sigla_eq.map(map_dim_eq)

        # Captura y log de desvíos para auditoría
        mask_sin_eq = s_key_eq.isna()
        if mask_sin_eq.any():
            unique_prods_eq = sorted(list(set(df[mask_sin_eq]["KeyProyecto"].dropna().tolist())))
            for p in unique_prods_eq:
                pending_items.append(f"KeyProyecto {p}: Grupo de recursos no homologado (Asignado a Key 0)")

            logging.warning(f"⚠️ [DimProyecto] {len(unique_prods_eq)} proyectos sin equipo homologado.")

        df["KeyEquipo"] = s_key_eq.fillna(0).astype(int)
    else:
        df["KeyEquipo"] = 0

    # C) KeyCiclo (Vectorizado, sin apply)
    dim_ciclo = base_dims.get("DimCiclo", pd.DataFrame())
    if "Ciclo" in df.columns and not dim_ciclo.empty and "KeyCiclo" in dim_ciclo.columns:
        valid_ciclos = set(dim_ciclo["KeyCiclo"].dropna())
        
        # Un ciclo es válido si no es nulo/vacío y está en el catálogo maestro
        mask_valido = df["Ciclo"].notna() & (df["Ciclo"] != "") & df["Ciclo"].isin(valid_ciclos)
        mask_sin_ciclo = ~mask_valido

        if mask_sin_ciclo.any():
            unique_prods_ciclo = sorted(list(set(df[mask_sin_ciclo]["KeyProyecto"].dropna().tolist())))
            for p in unique_prods_ciclo:
                pending_items.append(f"KeyProyecto {p}: Ciclo no asignado o inválido (Asignado a Key '0')")

            logging.warning(f"⚠️ [DimProyecto] {len(unique_prods_ciclo)} proyectos sin ciclo válido.")

        # .where() mantiene el ciclo si es válido, de lo contrario aplica la clave centinela "0"
        df["KeyCiclo"] = df["Ciclo"].where(mask_valido, "0")
    else:
        df["KeyCiclo"] = "0"

    # -------------------------------------------------------------------------
    # 4. SALIDA
    # -------------------------------------------------------------------------
    selected_columns = ["KeyProyecto", "Cod Proy.", "NombreProyecto", "Sistema","KeyDireccion", "KeyEquipo", "KeyCiclo","RM"]
    df_final = df[selected_columns].copy()

    proyecto0 = pd.DataFrame([{
        "KeyProyecto": "0",
        "Cod Proy.":"0",
        "NombreProyecto": "Sin Proyecto",
        "Sistema":"Sin Sistema",
        "KeyDireccion": 0,
        "KeyEquipo": 0,
        "KeyCiclo": "0",
    }])
    if "0" not in set(df_final["KeyProyecto"]):
        df_final = pd.concat([df_final, proyecto0], ignore_index=True)

    logging.info(f"  ↳ [DimProyecto] Procesamiento finalizado. {len(df_final)} proyectos consolidados.")
    _generate_logs("DimProyecto", pending_items)
    return df_final

def _build_dim_requerimiento(clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Construcción de DimRequerimiento respetando el contrato estricto de datos:
    - Fase 1: Carga desde MapeoRequerimientos.
      * Descarta registros sin 'Requerimiento'.
      * Valida existencia de Categoría contra DimRequerimientoCategoria (desvíos a pending_items).
      * Valida FK KeyProyecto contra DimProyecto cuando la categoría es Proyecto (desvíos a pending_items).
    - Fase 2: Descubrimiento de requerimientos no catalogados desde RegistroHoras.
    - Exporta la bitácora de desvíos vía _save_log sin alterar tipos de datos originales.
    """
    df_mapeo = clean_data.get("MapeoRequerimientos", pd.DataFrame())
    df_registro = clean_data.get("RegistroHoras", pd.DataFrame()).copy()
    df_dim_proy = base_dims.get("DimProyecto", pd.DataFrame())
    df_cat = base_dims.get("DimRequerimientoCategoria", pd.DataFrame())

    pending_items = []
    fase2_items_req = pd.DataFrame()

    # Universos de validación desde dimensiones maestras
    valid_projects = set()
    if not df_dim_proy.empty and "KeyProyecto" in df_dim_proy.columns:
        valid_projects = set(df_dim_proy["KeyProyecto"].dropna().unique())

    valid_categories = set()
    ids_cat_proyecto = set()

    if not df_cat.empty and "KeyRequerimientoCategoria" in df_cat.columns:
        valid_categories = set(df_cat["KeyRequerimientoCategoria"].dropna().unique())
        
        if "Categoria" in df_cat.columns:
            mask_proy_cat = df_cat["Categoria"] == "Proyecto"
            ids_cat_proyecto = set(df_cat.loc[mask_proy_cat, "KeyRequerimientoCategoria"])

    # =========================================================================
    # FASE 1: REQUERIMIENTOS CATALOGADOS (MapeoRequerimientos)
    # =========================================================================
    df_fase1 = pd.DataFrame()

    if not df_mapeo.empty:
        df_p1 = df_mapeo.copy()

        # Validar y filtrar registros sin 'Requerimiento'
        if "Requerimiento" in df_p1.columns:
            mask_valid = df_p1["Requerimiento"].notna() & (df_p1["Requerimiento"] != "")
            invalid_cnt = (~mask_valid).sum()
            if invalid_cnt > 0:
                logging.error(f"❌ [DimRequerimiento - Fase 1] Se descartaron {invalid_cnt} registros por 'Requerimiento' nulo o vacío.")
                df_p1 = df_p1[mask_valid]

        if not df_p1.empty:
            # Control y auditoría de duplicados en el maestro de origen
            dup_p1_mask = df_p1.duplicated(subset=["Requerimiento"], keep="first")
            if dup_p1_mask.any():
                for _, row in df_p1[dup_p1_mask].iterrows():
                    req_name = row.get("Requerimiento", "Desconocido")
                    pending_items.append(f"Requerimiento duplicado en MapeoRequerimientos: '{req_name}' (Se descarta ocurrencia repetida)")
                df_p1 = df_p1[~dup_p1_mask].copy()
        
        if not df_p1.empty:
            # KeyRequerimiento dinámica
            if "ID" in df_p1.columns and df_p1["ID"].notna().any():
                s_id = df_p1["ID"]
                mask_invalido = df_p1["ID"].isna() | (s_id == "")
                if mask_invalido.any():
                    df_p1["KeyRequerimiento"] = pd.Series(range(1, len(df_p1) + 1), index=df_p1.index)
                else:
                    df_p1["KeyRequerimiento"] = s_id
            else:
                df_p1["KeyRequerimiento"] = pd.Series(range(1, len(df_p1) + 1), index=df_p1.index)

            df_p1["NombreRequerimiento"] = df_p1["Requerimiento"]

            # -----------------------------------------------------------------
            # Validar Categoría
            # -----------------------------------------------------------------
            if "Categoria" in df_p1.columns:
                df_p1["KeyRequerimientoCategoria"] = df_p1["Categoria"].fillna(0)

                if valid_categories:
                    cat_invalida_mask = ~df_p1["KeyRequerimientoCategoria"].isin(valid_categories)
                    if cat_invalida_mask.any():
                        for _, row in df_p1[cat_invalida_mask].iterrows():
                            req_name = row.get("NombreRequerimiento", "Desconocido")
                            cat_val = row.get("Categoria", "Nulo")
                            pending_items.append(
                                f"Requerimiento: '{req_name}' | Categoria Inválida: '{cat_val}' (Asignado KeyRequerimientoCategoria=0)"
                            )
                        df_p1.loc[cat_invalida_mask, "KeyRequerimientoCategoria"] = 0
            else:
                df_p1["KeyRequerimientoCategoria"] = 0

            # -----------------------------------------------------------------
            # Validar Código de Proyecto (cuando corresponde según Categoría)
            # -----------------------------------------------------------------
            df_p1["KeyProyecto"] = "0"

            if "Cod Proy." in df_p1.columns:
                if ids_cat_proyecto:
                    es_cat_proyecto = df_p1["KeyRequerimientoCategoria"].isin(ids_cat_proyecto)
                else:
                    es_cat_proyecto = df_p1["KeyRequerimientoCategoria"] == 1

                # Para los de categoría Proyecto, verificar si el código provisto es válido
                for idx, row in df_p1[es_cat_proyecto].iterrows():
                    cod_proy = row.get("Cod Proy.")
                    req_name = row.get("NombreRequerimiento", "Desconocido")

                    if pd.notna(cod_proy) and cod_proy != "" and cod_proy in valid_projects:
                        df_p1.at[idx, "KeyProyecto"] = cod_proy
                    else:
                        # Registro de falla de mapeo/validación de proyecto
                        cod_str = str(cod_proy) if pd.notna(cod_proy) else "Nulo/Vacío"
                        pending_items.append(
                            f"Requerimiento (Cat. Proyecto): '{req_name}' | Cod Proy. Inválido/Inexistente: '{cod_str}' (Asignado KeyProyecto='0')"
                        )
                        df_p1.at[idx, "KeyProyecto"] = "0"

            df_fase1 = df_p1[["KeyRequerimiento", "NombreRequerimiento", "KeyRequerimientoCategoria", "KeyProyecto"]].copy()

    logging.info(f"  ↳ [DimRequerimiento - Fase 1] Se incorporaron {len(df_fase1)} requerimientos desde MapeoRequerimientos.")

    # =========================================================================
    # FASE 2: NUEVOS REQUERIMIENTOS SIN CATALOGAR (RegistroHoras)
    # =========================================================================
    df_fase2 = pd.DataFrame(
        columns=[
            "KeyRequerimiento",
            "NombreRequerimiento",
            "KeyRequerimientoCategoria",
            "KeyProyecto"
        ]
    )

    if not df_registro.empty and "Requerimiento" in df_registro.columns:
        df_p2_raw = df_registro[["Requerimiento","Sdreq"]].dropna().copy()
        df_p2_raw = df_p2_raw[df_p2_raw["Requerimiento"] != ""].drop_duplicates()

        if not df_fase1.empty:
            existing_reqs = set(df_fase1["NombreRequerimiento"])
            mask_new = ~df_p2_raw["Requerimiento"].isin(existing_reqs)
            df_p2_new = df_p2_raw[mask_new].copy()
        else:
            df_p2_new = df_p2_raw.copy()

        if not df_p2_new.empty:
            start_id = df_fase1["KeyRequerimiento"].max() + 1 if not df_fase1.empty else 1

            df_p2_new["KeyRequerimiento"] = pd.Series(
                range(start_id, start_id + len(df_p2_new)),
                index=df_p2_new.index,
            )

            df_p2_new.rename(columns={"Requerimiento": "NombreRequerimiento"}, inplace=True)
            df_p2_new.rename(columns={"Sdreq": "KeyProyecto"}, inplace=True)
            df_p2_new["KeyRequerimientoCategoria"] = 0

            fase2_items_req = pd.DataFrame({
                "Requerimiento": df_p2_new["NombreRequerimiento"],
                "Proyecto": "",
                "Cod Proy.": df_p2_new["KeyProyecto"].replace("", "0").fillna("0"),
                "Categoria": df_p2_new["KeyRequerimientoCategoria"],
            })
            df_fase2 = df_p2_new[["KeyRequerimiento", "NombreRequerimiento", "KeyRequerimientoCategoria", "KeyProyecto"]].copy()

        logging.info(f"  ↳ [DimRequerimiento - Fase 2] Se incorporaron {len(df_fase2)}/{len(df_registro)} requerimientos nuevos desde RegistroHoras.")

    # =========================================================================
    # CONSOLIDACIÓN Y AUDITORÍA
    # =========================================================================
    if df_fase2.empty:
        df_dim_req = df_fase1
    else:
        df_dim_req = pd.concat([df_fase1, df_fase2], ignore_index=True)

    if df_dim_req.empty:
            logging.warning("⚠️ DimRequerimiento quedó vacía tras procesar ambas fases.")

    _generate_logs("DimRequerimiento", pending_items)
    _save_structured_audit_csv("DimRequerimiento", fase2_items_req)    

    return df_dim_req

def _build_dim_tarea(clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Construcción de DimTarea replicando la gobernanza exacta de DimRequerimiento:
    - Fase 1: Carga desde MapeoTareas.
      * Descarta registros sin 'Tarea'.
      * Valida existencia de Clasificación contra DimTareaClasificacion (desvíos a pending_items).
      * Valida existencia de Proyecto contra DimProyecto (desvíos a pending_items).
    - Fase 2: Descubrimiento de tareas no catalogadas desde RegistroPlanificacion.
    - Exporta la bitácora de desvíos vía _save_log y utiliza claves sintéticas secuenciales (KeyTarea).
    """
    df_mapeo = clean_data.get("MapeoTareas", pd.DataFrame())
    df_planif = clean_data.get("RegistroPlanificacion", pd.DataFrame()).copy()
    df_dim_proy = base_dims.get("DimProyecto", pd.DataFrame())
    df_clasif = base_dims.get("DimTareaClasificacion", pd.DataFrame())

    pending_items = []
    fase2_items_tarea = pd.DataFrame()
    
    # Universos de validación desde dimensiones maestras
    valid_projects = set()
    if not df_dim_proy.empty:
        valid_projects = set(df_dim_proy["KeyProyecto"])
        
    valid_clasif = set()
    if not df_clasif.empty:
        valid_clasif = set(df_clasif["KeyTareaClasificacion"])

    # =========================================================================
    # FASE 1: TAREAS CATALOGADAS (MapeoTareas)
    # =========================================================================
    df_fase1 = pd.DataFrame()

    if not df_mapeo.empty:
        df_p1 = df_mapeo.copy()

        # Validar y filtrar registros sin 'Tarea'
        if "Tarea" in df_p1.columns:
            mask_valid = df_p1["Tarea"].notna() & (df_p1["Tarea"] != "")
            invalid_cnt = (~mask_valid).sum()
            if invalid_cnt > 0:
                logging.error(f"❌ [DimTarea - Fase 1] Se descartaron {invalid_cnt} registros por 'Tarea' nula o vacía.")
                df_p1 = df_p1[mask_valid]

            df_p1["NombreTarea"] = df_p1["Tarea"]

            # -----------------------------------------------------------------
            # Validar Clasificación 
            # -----------------------------------------------------------------
            if "KeyTareaClasificacion" in df_p1.columns:
                clasif_invalida_mask = ~df_p1["KeyTareaClasificacion"].isin(valid_clasif)
                if clasif_invalida_mask.any():
                    for _, row in df_p1[clasif_invalida_mask].iterrows():
                        clasif_val = row.get("KeyTareaClasificacion")
                        clasif_str = str(clasif_val) if pd.notna(clasif_val) else "Nulo/Vacío"
                        pending_items.append(
                            f"Tarea: '{row['NombreTarea']}' | KeyTareaClasificacion Inválida/Inexistente: '{clasif_str}' (Asignado 0)"
                        )
                    df_p1.loc[clasif_invalida_mask, "KeyTareaClasificacion"] = 0
            else:
                msg = (f"La columna 'KeyTareaClasificacion' no existe en MapeoTareas. Se asigna 0 por defecto.")
                logging.warning(f"⚠️ [DimTarea - Fase 1] {msg}")
                pending_items.append(msg)
                df_p1["KeyTareaClasificacion"] = 0

            # Forzado por los NaN en Pandas, con esto se alinea.
            df_p1["KeyTareaClasificacion"] = df_p1["KeyTareaClasificacion"].astype(int)

            # -----------------------------------------------------------------
            # Validar Proyecto
            # -----------------------------------------------------------------
            if "KeyProyecto" in df_p1.columns:
                proy_invalida_mask = ~df_p1["KeyProyecto"].isin(valid_projects)
                if proy_invalida_mask.any():
                    for _, row in df_p1[proy_invalida_mask].iterrows():
                        proy_val = row.get("KeyProyecto")
                        proy_str = str(proy_val) if pd.notna(proy_val) else "Nulo/Vacío"
                        pending_items.append(
                            f"Tarea: '{row['NombreTarea']}' | KeyProyecto Inválida/Inexistente: '{proy_str}' (Asignado 0)"
                        )
                    df_p1.loc[proy_invalida_mask, "KeyProyecto"] = "0"
            else:
                msg = "La columna 'KeyProyecto' no existe en MapeoTareas. Se asigna 0 por defecto."
                logging.warning(f"⚠️ [DimTarea - Fase 1] {msg}")
                pending_items.append(msg)
                df_p1["KeyProyecto"] = "0"

            # -----------------------------------------------------------------
            # Unicidad de registros
            # -----------------------------------------------------------------
            # 1. Ordenar descendente para que los valores con datos válidos queden arriba 
            # y los '0' (fallback) queden al fondo por cada NombreTarea
            df_p1 = df_p1.sort_values(
                by=["NombreTarea", "KeyProyecto", "KeyTareaClasificacion"], 
                ascending=False
            )

            # 2. Detectar los registros que van a ser descartados por ser duplicados
            subset_duplicados = ["NombreTarea", "KeyProyecto"]
            duplicadas_mask = df_p1.duplicated(subset=subset_duplicados, keep="first")
            
            if duplicadas_mask.any():
                for _, row in df_p1[duplicadas_mask].iterrows():
                    pending_items.append(
                        f"Conflicto de Unicidad: Tarea '{row['NombreTarea'],row['KeyProyecto'],row['KeyTareaClasificacion']}' duplicada en origen. Se descarta la variante con datos inválidos/fallback."
                    )
                logging.warning(f"⚠️ [DimTarea] Registros duplicados omitidos")

            # 3. Eliminar duplicados conservando el registro con la información prioritaria
            df_p1 = df_p1.drop_duplicates(subset=subset_duplicados, keep="first")

        if not df_p1.empty:
            # KeyTarea dinámica
            if "ID" in df_p1.columns and df_p1["ID"].notna().any():
                s_id = df_p1["ID"]
                mask_invalido = df_p1["ID"].isna() | (s_id == "")
                if mask_invalido.any():
                    df_p1["KeyTarea"] = pd.Series(range(1, len(df_p1) + 1), index=df_p1.index)
                else:
                    df_p1["KeyTarea"] = s_id
            else:
                df_p1["KeyTarea"] = pd.Series(range(1, len(df_p1) + 1), index=df_p1.index)



        df_fase1 = df_p1[["KeyTarea", "NombreTarea", "KeyTareaClasificacion", "KeyProyecto"]].copy()

    logging.info(f"  ↳ [DimTarea - Fase 1] Se incorporaron {len(df_fase1)} tareas desde MapeoTareas.")

    # =========================================================================
    # FASE 2: NUEVAS TAREAS SIN CATALOGAR (RegistroPlanificacion)
    # =========================================================================
    df_fase2 = pd.DataFrame(columns=["KeyTarea", "NombreTarea", "KeyTareaClasificacion", "KeyProyecto"])

    if not df_planif.empty and "Tarea" in df_planif.columns:
        df_p2_raw = df_planif[["Tarea", "Cod Proy.","Proyecto"]].dropna().copy()
        df_p2_raw = df_p2_raw[df_p2_raw["Tarea"] != ""].drop_duplicates()
        
        proyectos_validos = df_dim_proy["Cod Proy."].unique()
        df_p2_raw = df_p2_raw[df_p2_raw["Cod Proy."].isin(proyectos_validos)].copy()


        if not df_fase1.empty:
            existing_tareas = set(df_fase1["NombreTarea"])
            mask_new = ~df_p2_raw["Tarea"].isin(existing_tareas)
            df_p2_new = df_p2_raw[mask_new].copy()
        else:
            df_p2_new = df_p2_raw.copy()

        if not df_p2_new.empty:
            start_id = df_fase1["KeyTarea"].max() + 1 if not df_fase1.empty else 1

            df_p2_new["KeyTarea"] = pd.Series(
                range(start_id, start_id + len(df_p2_new)),
                index=df_p2_new.index,
            )
            df_p2_new.rename(columns={"Tarea": "NombreTarea"}, inplace=True)
            df_p2_new["KeyTareaClasificacion"] = 0
            df_p2_new["KeyProyecto"] = df_p2_new["Cod Proy."]

            fase2_items_tarea = pd.DataFrame({
                "Tarea": df_p2_new["NombreTarea"],
                "Proyecto": df_p2_new["Proyecto"],
                "KeyProyecto": df_p2_new["KeyProyecto"],
                "KeyTareaClasificacion": df_p2_new["KeyTareaClasificacion"]
            })
            df_fase2 = df_p2_new[["KeyTarea", "NombreTarea", "KeyTareaClasificacion", "KeyProyecto"]].copy()

        logging.info(f"  ↳ [DimTarea - Fase 2] Se incorporaron {len(df_fase2)}/{len(df_planif)} tareas nuevas desde RegistroPlanificacion.")

    # =========================================================================
    # CONSOLIDACIÓN Y AUDITORÍA
    # =========================================================================
    if df_fase2.empty:
        dim_tarea = df_fase1
    else:
        dim_tarea = pd.concat([df_fase1, df_fase2], ignore_index=True)

    if dim_tarea.empty:
        logging.warning("⚠️ DimTarea quedó vacía tras procesar ambas fases.")

    _generate_logs("DimTarea", pending_items)
    _save_structured_audit_csv("DimTarea", fase2_items_tarea)    

    return dim_tarea


# =============================================================================
# MAPEO EXPLICITO DE DIMENSIONES CONFORMADAS (.parquet)
# "clave_origen_en_memoria": "Nombre_Final_Parquet"
# =============================================================================
CONFORMED_BUILDERS = {
    "DimRecurso": _build_dim_recurso,
    "DimFecha":_build_dim_fecha,
    "DimProyecto": _build_dim_proyecto,
    "DimRequerimiento":_build_dim_requerimiento,
    "DimTarea": _build_dim_tarea,
}

# =============================================================================
# FUNCIÓN MAESTRA ORQUESTADORA DE LA FASE 2
# =============================================================================

def transform_conformed_dimensions(clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    logging.info("--- INICIANDO TRANSFORMACIÓN DE DIMENSIONES CONFORMADAS ---")
    conformed_dims = {}
    base_acum_dims = {k: v.copy() for k, v in base_dims.items()}
    for dim_name, builder_func in CONFORMED_BUILDERS.items():
        df_built = builder_func(clean_data, base_acum_dims)
        
        if df_built is not None and not df_built.empty:
            conformed_dims[dim_name] = df_built
            base_acum_dims[dim_name] = df_built
            logging.info(f"  ↳ [{dim_name}] -> Dimensión conformada construida ({len(df_built)} filas)")
        else:
            logging.warning(f"⚠️ No se pudo generar la dimensión conformada: '{dim_name}'")

    logging.info(f"✅ DIMENSIONES CONFORMADAS finalizadas. Dimensiones conformadas listas: {len(conformed_dims)}")

    return conformed_dims