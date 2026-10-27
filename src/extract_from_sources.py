import os
import logging
import pandas as pd
import warnings
import win32com.client

from datetime import datetime

ALIAS_TABLAS = {
    "horas_reporte_hs_semanal_-_planning_(": "RegistroHoras",
    "proyectos_hoja1": "BajadaProyectos",
    "maestros_equipos": "DimEquipo",
    "maestros_perfiles": "DimRecursoPerfil",
    "maestros_skills": "DimRecursoSkill",
    "maestros_origenes": "DimRecursoOrigen",
    "maestros_vinculos": "DimRecursoVinculo",
    "maestros_categorias": "DimRequerimientoCategoria",
    "maestros_clasificaciones": "DimTareaClasificacion",
    "maestros_direcciones": "DimDireccion",
    "maestros_bolsas": "DimBolsa",
    "maestros_ciclos": "DimCiclo",
    "maestros_recursos": "TablaRecursos",
    "maestros_estadosproyecto": "DimProyectoEstado",
    "maestros_situacionesproyecto": "DimProyectoSituacion",
    "maestros_asignacionbolsa":"AsignacionBolsa",
    "maestros_mapeodireccionbolsa":"MapeoDireccionBolsa",
    "recurosdisponibilidad_disponibilidad": "TablaCapacity",
    "registroplanificacion_asignacion": "RegistroPlanificacion",
    "mapeorequerimiento_hoja1": "MapeoRequerimientos",
    "mapeotareas_hoja1": "MapeoTareas",
    "homologacion_direcciones": "HomologacionDireccion",
    "homologacion_equipos": "HomologacionEquipo",
    "homologacion_recursos": "HomologacionRecurso",
    "homologacion_sd":"HomologacionSD",
    "servicedesk_worksheet": "ServiceDesk",
    "archivoproyect":"bajadaproyectos",
    "bajadaasignacion":"RegistroPlanificacion2",
    "proyAcumu_hoja1":"AcumuladoProyectos"
}

def read_proyect(mpp_file_path):
    """
    Optimized COM pipeline function that skips zero-work assignments,
    caches task hierarchies, and disables screen rendering for maximum speed.
    """
    pjAssignmentTimescaledWork = 8  # Enumerable value for Work
    pjTimescaleDays = 4             # Enumerable value for Daily breakdown

    if not os.path.exists(mpp_file_path):
        raise FileNotFoundError(f"The file path {mpp_file_path} does not exist.")

    print("Launching MS Project background application...")
    pj_app = win32com.client.Dispatch("MSProject.Application")
    
    # Performance boost: Disable UI rendering and alert popups
    try:
        pj_app.ScreenUpdating = False
        pj_app.DisplayAlerts = False
    except Exception:
        pass

    extracted_data = []
    task_cache = {}  # Cache to eliminate redundant hierarchical COM lookups

    try:
        pj_app.FileOpen(mpp_file_path)
        pj = pj_app.ActiveProject

        def obtener_padre_con_condicion(tsk):
            """
            Replicates 'ObtenerPadreConCondicion2' with high-speed memoization caching.
            """
            if tsk is None:
                return "", ""
            
            try:
                task_uid = tsk.UniqueID
                if task_uid in task_cache:
                    return task_cache[task_uid]
            except Exception:
                task_uid = None

            nombre_padre = ""
            segundo_campo = ""
            curr_task = tsk
            path_tasks = []

            while curr_task is not None:
                try:
                    path_tasks.append(curr_task)
                    valor_campo = str(curr_task.Text6).strip() if curr_task.Text6 else ""
                    
                    if valor_campo != "":
                        nombre_padre = str(curr_task.Name).strip() if curr_task.Name else ""
                        segundo_campo = str(curr_task.Text10).strip() if curr_task.Text10 else ""
                        break
                    
                    if curr_task.OutlineParent is not None:
                        if curr_task.OutlineParent.UniqueID == curr_task.UniqueID:
                            break
                    
                    curr_task = curr_task.OutlineParent
                except Exception:
                    break
            
            result = (nombre_padre, segundo_campo)
            
            if task_uid is not None:
                for pt in path_tasks:
                    try:
                        task_cache[pt.UniqueID] = result
                    except Exception:
                        pass

            return result

        print("Processing resources and time-phased assignments...")
        total_resources = pj.Resources.Count
        resource_counter = 0

        for R in pj.Resources:
            if R is None:
                continue
                
            resource_counter += 1
            
            try:
                r_name = R.Name if R.Name else "Unnamed Resource"
                r_group = R.Group if R.Group else ""
                
                # Skip resources with no assignments immediately
                if R.Assignments.Count == 0:
                    continue
                assignments = R.Assignments
            except Exception:
                continue

            print(f"[{resource_counter}/{total_resources}] Processing resource: {r_name[:30]:<30}", end="\r", flush=True)

            for A in assignments:
                try:
                    if A is None or A.Task is None:
                        continue
                    
                    # SPEED OPTIMIZATION: Skip assignments with 0 work instantly
                    if hasattr(A, 'Work') and A.Work == 0:
                        continue

                    task = A.Task
                    tarea_padre, codigo_padre = obtener_padre_con_condicion(task)

                    # Extract time-phased allocation metrics per day
                    tsv_collection = A.TimeScaleData(
                        A.Start, 
                        A.Finish, 
                        pjAssignmentTimescaledWork, 
                        pjTimescaleDays
                    )

                    for T in tsv_collection:
                        val = T.Value
                        if val is not None and val != "":
                            try:
                                minutos = float(val)
                                if minutos > 0:
                                    extracted_data.append({
                                        "Responsable": r_name,
                                        "Fecha": pd.to_datetime(str(T.StartDate)).strftime('%d/%m/%Y'),
                                        "Minutos": minutos,
                                        "TaskUID": task.UniqueID,
                                        "Tarea": task.Name,
                                        "Equipo": r_group,
                                        "Cod Proy.": codigo_padre,
                                        "Proyecto": tarea_padre if tarea_padre else task.Name
                                    })
                            except ValueError:
                                continue
                except Exception:
                    continue

        print("\n")

    finally:
        # Always restore application state and close cleanly
        print("Closing MS Project application...")
        try:
            pj_app.ScreenUpdating = True
            pj_app.DisplayAlerts = True
            pj_app.FileClose(2) # 2 = pjDoNotSave
            pj_app.Quit()
        except Exception:
            pass

    df = pd.DataFrame(extracted_data)
    print(f"Export finished successfully. Extracted {len(df)} rows.")
    return df

def adjust_registro_horas(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Ajusta RegistroHoras localizando 'Apeynom' en las filas del DataFrame leído.

    Descarta los metadatos superiores y promueve la fila encontrada como
    cabecera real.
    """
    logging.info("🔧 [Adjust] Corrigiendo estructura de [RegistroHoras]...")

    if df_raw is None or df_raw.empty:
        logging.warning("⚠️ [Adjust] El DataFrame recibido está vacío.")
        return pd.DataFrame()

    # 1. Localizar la fila que contiene 'Apeynom' en la primera columna
    col_a = df_raw.iloc[:, 0].astype(str).str.strip().str.lower()
    header_mask = col_a == "apeynom"

    if not header_mask.any():
        logging.error(
            "❌ [Adjust] No se encontró 'Apeynom' en la primera columna del DataFrame."
        )
        return pd.DataFrame()

    # argmax() devuelve la posición, que es lo que necesitamos para .iloc
    header_idx = header_mask.to_numpy().argmax()

    # 2. Extraer y sanitizar la fila de cabecera real
    raw_headers = df_raw.iloc[header_idx].values

    clean_headers = [
        str(col).strip()
        if pd.notna(col) and str(col).strip().lower() != "nan"
        else f"Columna_{i}"
        for i, col in enumerate(raw_headers)
    ]

    # 3. Recortar desde la fila posterior a la cabecera
    df = df_raw.iloc[header_idx + 1 :].copy()
    df.columns = clean_headers

    # 4. Eliminar filas con cabeceras repetidas
    primera_col = df.columns[0]

    df = df[
        df[primera_col].astype(str).str.strip().str.lower() != "apeynom"
    ]

    # 5. Reiniciar índice y asignar ID
    df = df.reset_index(drop=True)
    df.insert(0, "ID", range(1, len(df) + 1))

    logging.info(
        f"🔧 [Adjust] RegistroHoras reestructurado correctamente ({len(df)} filas)."
    )

    return df

def read_single_file(file_path: str, dataset_key: str) -> dict[str, pd.DataFrame]:
    df : dict[str, pd.DataFrame] = {}
    key_name= str(ALIAS_TABLAS.get(dataset_key, dataset_key))
    
    if not os.path.exists(file_path):
        logging.warning(f"⚠️ Archivo no encontrado: '{file_path}' (). Omitiendo...")
        return df
    try:
        if file_path.endswith(".csv"):
            df[key_name] = pd.read_csv(file_path)

        elif file_path.endswith((".xlsx", ".xls")):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="Data Validation extension is not supported")
                excel_sheets = pd.read_excel(file_path, sheet_name=None)
            for sheet_name, df_sheet in excel_sheets.items():
                sheet_name_str = str(sheet_name)
                clean_sheet_name = sheet_name_str.strip().lower().replace(" ", "_")
                raw_key = f"{dataset_key}_{clean_sheet_name}"
                key_name = ALIAS_TABLAS.get(raw_key, raw_key)
                df[key_name] = df_sheet
                logging.info(f"   ↳ Solapa extraída: '{sheet_name}' -> Clave en memoria: [{key_name}] ({len(df_sheet)} filas)")              

        elif file_path.endswith(".parquet"):
            df[key_name] = pd.read_parquet(file_path)
            logging.info(f"   ↳ Archivo leido: '{file_path}' -> Clave en memoria: [{key_name}]")
#===================================================================================================
        elif file_path.endswith(".mpp"):
            df[key_name] = read_proyect(file_path)
            logging.info(f"   ↳ Archivo leido: '{file_path}' -> Clave en memoria: [{key_name}]")
#===================================================================================================
        else:
            logging.warning(f"Formato no soportado para '{file_path}'. Se omite.")
    except Exception as e:
        logging.error(f"❌ Error al leer {file_path}: {e}")
    return df

def read_all_files(dataset_key: str, file_list: list[str]) -> dict[str, list[pd.DataFrame]]:
    """
    Recibe la clave del modelo (dataset_key) y su lista de archivos asociados.
    Itera cada archivo llamando a read_single_file y acumula los DataFrames
    obtenidos en listas por clave destino.

    """
    buffer: dict[str, list[pd.DataFrame]] = {}

    if not file_list:
        logging.warning(f"💥 La lista de archivos para la fuente '{dataset_key}' está vacía.")
        return buffer

    for file_path in file_list:
        file_date = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
        for key_name, df in read_single_file(file_path, dataset_key).items():
            df_new = df.copy()
            df_new["FileDate"] = file_date
            buffer.setdefault(key_name, []).append(df_new)
    return buffer

def build_file_info(input_sources: dict[str, list[str]]) -> pd.DataFrame:
    records = []
    fecha_snapshot = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # same for all rows

    for alias, files in input_sources.items():
        for file_path in files:
            if os.path.exists(file_path):
                fecha_crea_str = datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                fecha_mod_str = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
            else:
                fecha_crea_str = None   # sentinel: file not found
                fecha_mod_str = None

            records.append(
                {
                    "Alias": str(alias).strip(),
                    "Archivo": os.path.basename(file_path),
                    "RutaCompleta": str(file_path),
                    "FechaSnapshot": fecha_snapshot,
                    "FechaCreacion": fecha_crea_str,
                    "FechaModificacion": fecha_mod_str,
                }
            )

    return pd.DataFrame(records)

def extract_all_sources(sources_config: dict[str, list[str]]) -> dict[str, pd.DataFrame]:
    """
    Lee dinámicamente todos los archivos de origen especificados.
    Si encuentra un archivo Excel, extrae automáticamente CADA SOLAPA 
    como una dimensión independiente en el diccionario de datos.
    """
    raw_datasets: dict[str, pd.DataFrame] = {}
    logging.info("--- INICIANDO EXTRACCIÓN MASIVA ---")

    raw_datasets["FactFileInfo"] = build_file_info(sources_config)  
    
    for dataset_key, files in sources_config.items():
        for key_name, dfs in read_all_files(dataset_key, files).items():
            raw_datasets[key_name] = pd.concat(dfs, ignore_index=True)
 
    if "RegistroHoras" in raw_datasets:
        raw_datasets["RegistroHoras"] = adjust_registro_horas(raw_datasets["RegistroHoras"])
    logging.info(f"✅ EXTRACCIÓN finalizada. Total de tablas/solapas en memoria: {len(raw_datasets)}")
    return raw_datasets
