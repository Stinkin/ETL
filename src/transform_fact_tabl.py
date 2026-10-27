import logging
import pandas as pd
from src.logs_manager import _generate_logs, _save_structured_audit_csv

def _to_datetime_text(series: pd.Series) -> pd.Series:
    clean_dates = (
        series.astype(str)
        .str.replace(r"^\S*\s+", "", regex=True)
        .str.strip()
    )
    dt_series = pd.to_datetime(clean_dates, format="%d/%m/%y", errors="coerce")
    return dt_series

def _to_datetimeSD(series: pd.Series) -> pd.Series:
    """
    Normaliza fechas y las convierte a datetime.

    Acepta formatos como:
        '27/04/2026'
        '27/04/2026, 15:43'
        '27/04/26'
    """

    dates = (
        series.astype(str)
        .str.strip()
        .str.replace(r"[,\s].*$", "", regex=True)
    )

    parts = dates.str.extract(
        r"^(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})$"
    )

    day = parts[0].str.zfill(2)
    month = parts[1].str.zfill(2)

    year = parts[2].where(
        parts[2].str.len() == 4,
        "20" + parts[2]
    )

    standardized = day + "/" + month + "/" + year

    # Si no coincide con el patrón, conserva el valor original
    standardized = standardized.where(
        parts[0].notna(),
        dates
    )

    return pd.to_datetime(
        standardized,
        format="%d/%m/%Y",
        errors="coerce"
    )

def _build_fact_seguimiento_proyectoN(clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:

    logging.info("⚙️ Construyendo [FactSeguimientoProyecto]...")
    pending_items: list[str] = []

    # 1. Lectura segura con .get() (preserva trazabilidad)
    df_raw = clean_data.get("BajadaProyectos", pd.DataFrame()).copy()
    df_file_info = clean_data.get("FactFileInfo", pd.DataFrame())

    if df_raw.empty:
        logging.warning(
            "⚠️ [FactSeguimientoProyecto] BajadaProyectos está vacía."
        )
        _generate_logs("FactSeguimientoProyecto", pending_items)
        return pd.DataFrame()


    # Obtención segura de FechaSnapshot
    fecha_snapshot = 0
    if not df_file_info.empty and "Alias" in df_file_info.columns:
        match_snap = df_file_info.loc[
            df_file_info["Alias"] == "Proyectos", "FechaSnapshot"
        ]
        if not match_snap.empty:
            fecha_snapshot = match_snap.item()

    if fecha_snapshot == 0:
        msg = "No se encontró FechaSnapshot para 'Proyectos' en FactFileInfo. Se asigna 0 por defecto."
        logging.warning(f"⚠️ [FactSeguimientoProyecto] {msg}")
        pending_items.append(msg)

    # 2. Filtrado de registros válidos
    mask_valid = (
        (df_raw["Proyecto"] != "NO")
        & df_raw["Proyecto"].notna()
        & (df_raw["Proyecto"] != "")
    )
    df = df_raw[mask_valid].copy()

    if df.empty:
        logging.warning(
            "⚠️ [FactSeguimientoProyecto] No quedan registros tras aplicar filtros de validez."
        )
        _generate_logs("FactSeguimientoProyecto", pending_items)
        return pd.DataFrame()

    # 3. Mapeo de Atributos Base y Fechas (YYYYMMDD)
    df["KeyProyecto"] = df["Cod Proy."]
    df["FechaSnapshot"] = pd.to_datetime(fecha_snapshot)
    df["FechaInicioPlan"] = _to_datetime_text(df["Comienzo_Programado"])
    df["FechaFinPlan"] = _to_datetime_text(df["Fin_Programo"])
    df["FechaInicioReal"] = _to_datetime_text(df["Comienzo"])
    df["FechaFinReal"] = _to_datetime_text(df["Fin"])

    # 4. Métricas Numéricas Vectorizadas
    clean_hours = (
        df["Trabajo"]
        .astype(str)
        .str.replace(", ", ",", regex=False)
        .str.split(" ")       # 1. Separamos primero por espacio para quitar "horas"
        .str[0]
        .str.replace(".", "", regex=False)  # 2. Eliminamos el punto de los miles (1.187 -> 1187)
        .str.replace(",", ".", regex=False)  # 3. Cambiamos la coma decimal por punto (1187,51 -> 1187.51)
    )

    df["HorasPlanificadas"] = (
        pd.to_numeric(clean_hours, errors="coerce").fillna(0.0).round().astype(int)
    )

    pct_raw = df["% trabajo completado"]
    df["PorcentajeDeAvance"] = (
        pct_raw.mask(pct_raw > 1.0, pct_raw / 100.0).round(2)
    )
    df["CantidadReplanificaciones"] = df["Cant. Reprogramaciones"]
    # 5. KeyProyectoEstado

    # Diccionario de mapeo Texto -> Key
    dim_estado = dimensions["DimProyectoEstado"]
    estado_map = dict(zip(dim_estado["ProyectoEstado"], dim_estado["KeyProyectoEstado"]))

    # Identificar registros con estado determinado por porcentaje ("SI")
    es_por_porcentaje = df["Proyecto"] == "Si"
    estado_explicito = df["Proyecto"].where(~es_por_porcentaje)

    # Cálculo del texto de estado por porcentaje de avance
    pct = df["PorcentajeDeAvance"]
    calc_estado = pd.Series("Sin Iniciar", index=df.index)
    calc_estado.loc[pct >= 1] = "Terminado"
    calc_estado.loc[(pct > 0) & (pct < 1)] = "En Proceso"

    # Resolución del texto de estado final
    estado_final_str = estado_explicito.fillna(calc_estado)

    # Mapeo final a KeyProyectoEstado
    df["KeyProyectoEstado"] = estado_final_str.map(estado_map)

    # 6. KeyProyectoSituacion (Pandas Nativo con resguardo contra fechas -1)
    dim_situacion = dimensions.get("DimProyectoSituacion", pd.DataFrame())
    situacion_map = (
        dict(
            zip(
                dim_situacion["ProyectoSituacion"],
                dim_situacion["KeyProyectoSituacion"],
            )
        )
        if not dim_situacion.empty
        else {}
    )

    pct = df["PorcentajeDeAvance"]
    snap = df["FechaSnapshot"]
    ini_p = df["FechaInicioPlan"]
    fin_p = df["FechaFinPlan"]
    fin_r = df["FechaFinReal"]

    valid_ini_p = ini_p != 0
    valid_fin_p = fin_p != 0

    temp_situaciones = pd.Series("en fecha", index=df.index)

    # Caso A: Porcentaje == 0
    m_pct_0 = pct == 0
    temp_situaciones.loc[m_pct_0 & valid_ini_p & (snap > ini_p)] = "atrasado"

    # Caso B: Porcentaje == 1
    m_pct_1 = pct == 1
    temp_situaciones.loc[m_pct_1] = "atrasado"
    temp_situaciones.loc[
        m_pct_1 & (fin_r != "") & valid_fin_p & (fin_r <= fin_p)
    ] = "en fecha"

    # Caso C: 0 < Porcentaje < 1
    m_pct_mid = (pct > 0) & (pct < 1)
    temp_situaciones.loc[m_pct_mid & valid_ini_p & (snap < ini_p)] = (
        "adelantado"
    )
    temp_situaciones.loc[m_pct_mid & valid_fin_p & (snap > fin_p)] = (
        "atrasado"
    )

    df["KeyProyectoSituacion"] = (
        temp_situaciones.map(situacion_map).fillna(0).astype(int)
    )

    # 7. Selección de Columnas del Grano Final
    cols_finales = [
        "KeyProyecto",
        "FechaSnapshot",
        "FechaInicioPlan",
        "FechaFinPlan",
        "FechaInicioReal",
        "FechaFinReal",
        "PorcentajeDeAvance",
        "HorasPlanificadas",
        "CantidadReplanificaciones",
        "KeyProyectoEstado",
        "KeyProyectoSituacion",
    ]

    # Auditoría Nivel 2 (Siempre presente)
    _generate_logs("FactSeguimientoProyecto", pending_items)

    logging.info(
        f"⚙️ [FactSeguimientoProyecto] Generada con éxito ({len(df)} registros)."
    )
    return df[cols_finales].reset_index(drop=True)

def _build_fact_registro_horas(clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Construcción de FactRegistroHoras respetando la gobernanza de datos:

    - Lectura segura con .get() preservando trazabilidad.
    - Manejo independiente de faltantes para HomologacionRecurso y HomologacionEquipo.
    - Asignación de Key 0 a registros sin homologación.
    - Ejecución obligatoria de _generate_logs y llamadas limpias a save_structured_audit_csv.
    """
    logging.info("⚙️ Construyendo [FactRegistroHoras]...")
    pending_items: list[str] = []

    # 1. Extracción segura con .get() (Preserva trazabilidad)
    df_raw = clean_data.get("RegistroHoras", pd.DataFrame()).copy()

    if df_raw.empty:
        logging.warning("⚠️ 'RegistroHoras' viene vacío o no se encontró.")
        _generate_logs("FactRegistroHoras", pending_items)
        return pd.DataFrame(
            columns=[
                "KeyRecurso",
                "KeyRequerimiento",
                "KeyFecha",
                "HorasConsumidas",
            ]
        )

    df = df_raw.copy()

    # Tablas de homologación y dimensiones
    df_homolog_rec = clean_data.get("HomologacionRecurso", pd.DataFrame())
    df_homolog_eq = clean_data.get("HomologacionEquipo", pd.DataFrame())
    dim_requerimiento = dimensions.get("DimRequerimiento", pd.DataFrame())

    # 2. Atributos base
    df["TempTarea"] = df["Requerimiento"]

    # 3. Validación y Mapeo TempRecurso (HomologacionRecurso)
    df["TempRecurso"] = df["Apeynom"]

    # 4. Validación y Mapeo TempEquipo (HomologacionEquipo)
    eq_map = dict(
        zip(
            df_homolog_eq.get("EquipoOrigen", pd.Series()),
            df_homolog_eq.get("EquipoHomologado", pd.Series()),
        )
    )
    s_temp_eq = df["Equipo"].map(eq_map)
    df["TempEquipo"] = s_temp_eq

    # Faltantes específicos de Equipos
    equipos_sin_homologar = (
        df[s_temp_eq.isna()][["Equipo"]]
        .drop_duplicates()
        .rename(columns={"Equipo": "EquipoOrigen"})
        .assign(KeyEquipo=0)
    )
    #########################################################################################################
    #########################################################################################################

    # 5. Cálculo de KeyFecha (Formato YYYYMMDD)
    anio = df["Periodo"].str[0:4]
    mes = df["Periodo"].str[5:7]
    dia = df["Periodo"].str[8:10]
    
    df["KeyFecha"] = (
        (pd.to_numeric(anio, errors="coerce").fillna(1900) * 10000)
        + (pd.to_numeric(mes, errors="coerce").fillna(1) * 100)
        + dia.fillna(1).astype(int)
    ).astype(int)

    df['Fecha'] = pd.to_datetime(anio + '-' + mes + '-' + dia)
    #########################################################################################################
    #########################################################################################################
    # 6. Agrupamiento y Consolidación
    df["HorasConsumidas"] = pd.to_numeric(
        df["Horas"], errors="coerce"
    ).fillna(0.0)

    df_grouped = (
        df.groupby(
            ["TempRecurso", "TempEquipo", "TempTarea", "KeyFecha", "Fecha"],
            as_index=False,
        )[["HorasConsumidas"]]
        .sum()
    )

    # 7. Asignación de KeyRecurso (Clave Compuesta: Recurso + Equipo Homologado)
    rec_key_map = dict(
        zip(
            zip(
                df_homolog_rec.get("NombreRecurso", pd.Series()),
                df_homolog_rec.get("EquipoHomologado", pd.Series()),
            ),
            df_homolog_rec.get("KeyRecurso", pd.Series()),
        )
    )

    tuples_origen = list(
        zip(df_grouped["TempRecurso"], df_grouped["TempEquipo"])
    )
    
    # Mapeamos a una serie temporal para detectar los que no hacen match (devuelven NaN)
    s_temp_rec = pd.Series(tuples_origen, index=df_grouped.index).map(rec_key_map)

    # Extraemos los recursos sin homologar (simétrico a equipos_sin_homologar)
    recursos_sin_homologar = (
        df_grouped[s_temp_rec.isna()][["TempRecurso", "TempEquipo"]]
        .drop_duplicates()
        .rename(columns={"TempRecurso": "NombreRecurso", "TempEquipo": "EquipoHomologado"})
        .assign(KeyRecurso=0)
    )

    # Asignación final con Key 0 para los faltantes
    df_grouped["KeyRecurso"] = s_temp_rec.fillna(0).astype(int)

    # 8. Asignación directa de KeyRequerimiento
    req_key_map = dict(
        zip(
            dim_requerimiento.get("NombreRequerimiento", pd.Series()),
            dim_requerimiento.get("KeyRequerimiento", pd.Series()),
        )
    )
    df_grouped["KeyRequerimiento"] = (
        df_grouped["TempTarea"].map(req_key_map).fillna(0).astype(int)
    )

    # 9. Consolidación de Bitácoras y Auditoría Nivel 3

    if not equipos_sin_homologar.empty:
        pending_items.append(
            f"Se encontraron {len(equipos_sin_homologar)} errores en HomologacionEquipo."
        )

    if not recursos_sin_homologar.empty:
        pending_items.append(
            f"Se encontraron {len(recursos_sin_homologar)} errores en HomologacionRecurso."
        )

    _generate_logs("FactRegistroHoras", pending_items)
    _save_structured_audit_csv("FactRegistroHoras_HomologacionEquipos", equipos_sin_homologar)
    _save_structured_audit_csv("FactRegistroHoras_HomologacionRecurso", recursos_sin_homologar)
    # 10. Salida Final al Grano Estricto
    cols_finales = [
        "KeyRecurso",
        "KeyRequerimiento",
        "KeyFecha",
        "Fecha",
        "HorasConsumidas",
    ]
    df_fact = df_grouped[cols_finales].copy()

    logging.info(
        f"⚙️ [FactRegistroHoras] Generada con éxito ({len(df_fact)} registros)."
    )
    return df_fact

def _build_fact_asignacion_recursos(clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Construcción de FactAsignacionRecursos respetando la gobernanza de datos:

    - Lectura segura con .get() preservando trazabilidad.
    - Manejo independiente de faltantes exclusivamente para Recursos/Equipos.
    - Asignación de Key 0 a registros sin homologación (con tipado entero).
    - Ejecución obligatoria de _generate_logs y llamada a save_structured_audit_csv de recursos.
    """
    logging.info("⚙️ Construyendo [FactAsignacionRecursos]...")
    pending_items: list[str] = []

    # 1. Extracción segura con .get() (Preserva trazabilidad)
    df_raw = clean_data.get("RegistroPlanificacion", pd.DataFrame()).copy()

    if df_raw.empty:
        logging.warning("⚠️ 'RegistroPlanificacion' viene vacío o no se encontró.")
        _generate_logs("FactAsignacionRecursos", pending_items)
        return pd.DataFrame(
            columns=[
                "KeyRecurso",
                "KeyTarea",
                "KeyProyecto",
                "KeyFecha",
                "HorasAsignadas",
            ]
        )

    df = df_raw.copy()

    df_homolog_rec = clean_data.get("HomologacionRecurso", pd.DataFrame())
    df_homolog_eq = clean_data.get("HomologacionEquipo", pd.DataFrame())
    dim_tarea = dimensions.get("DimTarea", pd.DataFrame())
    dim_proyecto = dimensions.get("DimProyecto", pd.DataFrame())

    # 2. Transformación estricta de Fecha -> KeyFecha (YYYYMMDD)
    fechas_dt = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
    df["KeyFecha"] = (
        (fechas_dt.dt.year.fillna(1900) * 10000)
        + (fechas_dt.dt.month.fillna(1) * 100)
        + fechas_dt.dt.day.fillna(1)
    ).astype(int)

    # 3. Métrica Minutos
    df["Minutos"] = pd.to_numeric(df["Minutos"], errors="coerce").fillna(0.0)

    # 4. Normalización y Homologación de Equipo
    eq_map = dict(
        zip(
            df_homolog_eq.get("EquipoOrigen", pd.Series()),
            df_homolog_eq.get("EquipoHomologado", pd.Series()),
        )
    )
    df["TempEquipo"] = df["Equipo"].map(eq_map).fillna("sin_homologar")

    # 5. Normalización de Recurso
    df["TempRecurso"] = df["Responsable"]

    # 6. Mapeo KeyTarea contra DimTarea
    tarea_map = dict(
        zip(
            dim_tarea.get("NombreTarea", pd.Series()),
            dim_tarea.get("KeyTarea", pd.Series()),
        )
    )
    df["KeyTarea"] = df["Tarea"].map(tarea_map).fillna(0).astype(int)

    # 7. Mapeo KeyProyecto contra DimProyecto (Origen compartido)
    proy_map = dict(
        zip(
            dim_proyecto.get("NombreProyecto", pd.Series()),
            dim_proyecto.get("KeyProyecto", pd.Series()),
        )
    )
    df["KeyProyecto"] = df["Proyecto"].map(proy_map).fillna(0).astype(str)

    # 8. Consolidación al Grano
    df_grouped = (
        df.groupby(
            ["TempRecurso", "TempEquipo", "KeyTarea", "KeyProyecto", "KeyFecha"],
            as_index=False,
        )[["Minutos"]]
        .sum()
        .rename(columns={"Minutos": "TempMinutosTotales"})
    )

    # 9. Mapeo de KeyRecurso por Tupla Compuesta (Recurso + Equipo Homologado)
    rec_key_map = dict(
        zip(
            zip(
                df_homolog_rec.get("NombreRecurso", pd.Series()),
                df_homolog_rec.get("EquipoHomologado", pd.Series()),
            ),
            df_homolog_rec.get("KeyRecurso", pd.Series()),
        )
    )

    tuples_origen = list(
        zip(df_grouped["TempRecurso"], df_grouped["TempEquipo"])
    )
    s_key_rec = pd.Series(tuples_origen, index=df_grouped.index).map(
        rec_key_map
    )

    # Captura de recursos/equipos faltantes estructurados
    recursos_sin_homologar = (
        df_grouped[s_key_rec.isna()][["TempRecurso", "TempEquipo"]]
        .drop_duplicates()
        .rename(
            columns={
                "TempRecurso": "NombreRecursoOrigen",
                "TempEquipo": "EquipoOrigen",
            }
        )
        .assign(KeyRecurso=0)
    )

    if not recursos_sin_homologar.empty:
        pending_items.append(
            f"Se encontraron {len(recursos_sin_homologar)} recurso(s) sin registro en HomologacionRecurso."
        )

    df_grouped["KeyRecurso"] = s_key_rec.fillna(0).astype(int)

    # 10. Cálculo de HorasAsignadas
    df_grouped["HorasAsignadas"] = (
        df_grouped["TempMinutosTotales"] / 60.0
    ).round(2)

    # 11. Invocación de Auditoría N2 y N3 (Solo Recursos)
    _generate_logs("FactAsignacionRecursos", pending_items)
    _save_structured_audit_csv("FactAsignacionRecursos_Recurso", recursos_sin_homologar)

    # 12. Salida al Grano Final
    cols_finales = [
        "KeyRecurso",
        "KeyTarea",
        "KeyProyecto",
        "KeyFecha",
        "HorasAsignadas",
    ]
    df_fact = df_grouped[cols_finales].copy()

    logging.info(
        f"⚙️ [FactAsignacionRecursos] Generada con éxito ({len(df_fact)} registros)."
    )
    return df_fact

def _build_fact_bolsa_de_horas(clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Construcción de FactBolsaDeHoras acotada al año en curso (2026):

    - Lectura segura con .get() preservando trazabilidad.
    - Auditoría enfocada en direcciones sin bolsa mapeada (DimProyecto controla dirección).
    - Asignación estricta de Key 0 y control tipado originado por Pandas.
    """
    logging.info("⚙️ Construyendo [FactBolsaDeHoras]...")
    pending_items: list[str] = []
    dir_sin_bolsa = []

    # 1. Extracción de fuentes
    df_raw_bolsa = clean_data.get("AsignacionBolsa", pd.DataFrame())
    if df_raw_bolsa.empty:
        logging.warning("⚠️ 'AsignacionBolsa' viene vacío o no se encontró.")
        _generate_logs("FactBolsaDeHoras", pending_items)
        return pd.DataFrame(
            columns=[
                "KeyBolsa",
                "AnioBolsa",
                "HorasAsignadas",
                "HorasConsumidas",
                "HorasProgramadas",
                "HorasDisponibles",
                "HorasRestantes",
            ]
        )

    df_bolsa = df_raw_bolsa.copy()

    # 2. Extracción de dimensiones y hechos
    dim_bolsa = dimensions.get("DimBolsa", pd.DataFrame())
    dim_proyecto = dimensions.get("DimProyecto", pd.DataFrame())
    dim_requerimiento = dimensions.get("DimRequerimiento", pd.DataFrame())
    mapeo_dir_bolsa = clean_data.get("MapeoDireccionBolsa", pd.DataFrame())
    fact_reg_horas = dimensions.get("FactRegistroHoras", pd.DataFrame())
    fact_asig_rec = dimensions.get("FactAsignacionRecursos", pd.DataFrame())

    # Mapas de relación
    proy_dir_map = dict(
        zip(
            dim_proyecto.get("KeyProyecto", pd.Series()),
            dim_proyecto.get("KeyDireccion", pd.Series()),
        )
    )

    dir_bolsa_map = {}
    if not mapeo_dir_bolsa.empty:
        dir_bolsa_map = dict(
            zip(
                mapeo_dir_bolsa.get("KeyDireccion", pd.Series()),
                mapeo_dir_bolsa.get("KeyBolsa", pd.Series()),
            )
        )

    # 3. Normalización de AsignacionBolsa (Grano: Una bolsa por año)
    bolsa_map = dict(
        zip(
            dim_bolsa.get("Bolsa", pd.Series()),
            dim_bolsa.get("KeyBolsa", pd.Series()),
        )
    )
    df_bolsa["KeyBolsa"] = (
        df_bolsa["NombreBolsa"].map(bolsa_map).fillna(0).astype(int)
    )
    df_bolsa["AnioBolsa"] = df_bolsa["Año"]
    df_bolsa["HorasAsignadas"] = pd.to_numeric(
        df_bolsa["Horas"], errors="coerce"
    ).fillna(0.0)

    # 5. Procesamiento de FactRegistroHoras (Consumidas)
    ANIO_ACTUAL = 2026

    consumidas_agg = pd.DataFrame({
        "KeyBolsa": pd.Series(dtype="int"),
        "AnioBolsa": pd.Series(dtype="int"),
        "HorasConsumidas": pd.Series(dtype="float"),
    })

    if not fact_reg_horas.empty and "KeyFecha" in fact_reg_horas.columns:
        df_rh = fact_reg_horas.copy()

        if (
            not dim_requerimiento.empty
            and "KeyRequerimiento" in df_rh.columns
            and "KeyRequerimiento" in dim_requerimiento.columns
        ):
            cols_to_drop = [
                c
                for c in ["KeyProyecto", "KeyRequerimientoCategoria"]
                if c in df_rh.columns
            ]
            df_rh = df_rh.drop(columns=cols_to_drop, errors="ignore")

            df_rh = df_rh.merge(
                dim_requerimiento[[
                    "KeyRequerimiento",
                    "KeyProyecto",
                    "KeyRequerimientoCategoria",
                ]],
                on="KeyRequerimiento",
                how="left",
            )

        df_rh["Anio"] = (df_rh["KeyFecha"] // 10000).astype(int)

        mask_anio = df_rh["Anio"] == ANIO_ACTUAL
        mask_es_proyecto = (
            df_rh["KeyRequerimientoCategoria"] == 1
            if "KeyRequerimientoCategoria" in df_rh.columns
            else False
        )

        df_rh = df_rh[mask_anio & mask_es_proyecto].copy()
        if not df_rh.empty:
            key_direccion = df_rh["KeyProyecto"].map(proy_dir_map).fillna(0)
            key_bolsa = key_direccion.map(dir_bolsa_map).fillna(0)
            sin_bolsa = key_direccion[(key_direccion != 0) & (key_bolsa == 0)]
            dir_sin_bolsa.extend(sin_bolsa.unique())
            df_rh["KeyBolsa"] = key_bolsa

            temp_agg = (
                df_rh[df_rh["KeyBolsa"] != 0]
                .groupby(["KeyBolsa", "Anio"], as_index=False)[
                    ["HorasConsumidas"]
                ]
                .sum()
                .rename(columns={"Anio": "AnioBolsa"})
            )

            if not temp_agg.empty:
                temp_agg["KeyBolsa"] = temp_agg["KeyBolsa"].astype(int)
                temp_agg["AnioBolsa"] = temp_agg["AnioBolsa"].astype(int)
                temp_agg["HorasConsumidas"] = temp_agg[
                    "HorasConsumidas"
                ].astype(float)
                consumidas_agg = temp_agg

    # 6. Procesamiento de FactAsignacionRecursos (Programadas)
    if not fact_asig_rec.empty and "KeyFecha" in fact_asig_rec.columns:
        df_ar = fact_asig_rec.copy()
        df_ar["Anio"] = (df_ar["KeyFecha"] // 10000).astype(int)

        df_ar = df_ar[df_ar["Anio"] == ANIO_ACTUAL].copy()
        if not df_ar.empty:
            df_ar_agrupado = (
                df_ar.groupby(["KeyProyecto", "Anio"], as_index=False)[
                    ["HorasAsignadas"]
                ]
                .sum()
            )

            key_direccion = df_ar_agrupado["KeyProyecto"].map(proy_dir_map).fillna(0)
            key_bolsa = key_direccion.map(dir_bolsa_map).fillna(0)
            sin_bolsa = key_direccion[(key_direccion != 0) & (key_bolsa == 0)]
            dir_sin_bolsa.extend(sin_bolsa.unique())
            df_ar_agrupado["KeyBolsa"] = key_bolsa

            programadas_agg = (
                df_ar_agrupado.groupby(["KeyBolsa", "Anio"], as_index=False)[
                    ["HorasAsignadas"]
                ]
                .sum()
                .rename(
                    columns={
                        "Anio": "AnioBolsa",
                        "HorasAsignadas": "HorasProgramadas",
                    }
                )
            )
        else:
            programadas_agg = pd.DataFrame(
                columns=["KeyBolsa", "AnioBolsa", "HorasProgramadas"]
            )
    else:
        programadas_agg = pd.DataFrame(
            columns=["KeyBolsa", "AnioBolsa", "HorasProgramadas"]
        )

    # 7. Consolidación de Auditorías Nivel 2 y Estructuradas Nivel 3
    unique_dirs_sin_bolsa = sorted(list(set(dir_sin_bolsa)))

    df_audit_dir = (
        pd.DataFrame({"KeyDireccion": unique_dirs_sin_bolsa})
        .assign(KeyBolsa=0)
        if unique_dirs_sin_bolsa
        else pd.DataFrame(columns=["KeyDireccion", "KeyBolsa"])
    )

    if unique_dirs_sin_bolsa:
        pending_items.append(
            f"Se encontraron {len(unique_dirs_sin_bolsa)} dirección(es) sin bolsa mapeada."
        )

    # 8. Consolidación y cálculos finales
    df_final = df_bolsa.merge(
        consumidas_agg, on=["KeyBolsa", "AnioBolsa"], how="left"
    )
    df_final = df_final.merge(
        programadas_agg, on=["KeyBolsa", "AnioBolsa"], how="left"
    )

    df_final["HorasConsumidas"] = df_final["HorasConsumidas"].fillna(0.0)
    #df_final["HorasProgramadas"] = df_final["HorasProgramadas"].fillna(0.0)
    df_final["HorasProgramadas"] = pd.to_numeric(df_final["HorasProgramadas"], errors="coerce").fillna(0.0)

    df_final["HorasDisponibles"] = (
        df_final["HorasAsignadas"] - df_final["HorasConsumidas"]
    ).round(2)
    df_final["HorasRestantes"] = (
        df_final["HorasAsignadas"]
        - df_final["HorasConsumidas"]
        - df_final["HorasProgramadas"]
    ).round(2)

    cols_fact = [
        "KeyBolsa",
        "AnioBolsa",
        "HorasAsignadas",
        "HorasConsumidas",
        "HorasProgramadas",
        "HorasDisponibles",
        "HorasRestantes",
    ]
    df_fact = df_final[cols_fact].copy()

    _generate_logs("FactBolsaDeHoras", pending_items)
    _save_structured_audit_csv("FactBolsaDeHoras_DireccionBolsa", df_audit_dir)

    logging.info(
        f"⚙️ [FactBolsaDeHoras] Construida con éxito ({len(df_fact)} registros)."
    )
    return df_fact

def _build_fact_seguimiento_recurso(clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Construcción de FactSeguimientoRecurso respetando la gobernanza de datos:

    - Lectura segura con .get() preservando trazabilidad.
    - Manejo independiente de faltantes para HomologacionRecurso y HomologacionEquipo.
    - Cálculo de KeyFecha (primer día del mes) a partir de mes y año.
    - Asignación estricta de Key 0 y control tipado originado por Pandas.
    - Ejecución obligatoria de _generate_logs y llamadas a save_structured_audit_csv.
    """
    logging.info("⚙️ Construyendo [FactSeguimientoRecurso]...")
    pending_items: list[str] = []

    # 1. Extracción segura con .get() (Preserva trazabilidad)
    df_raw = clean_data.get("TablaCapacity", pd.DataFrame()).copy()
    if df_raw.empty:
        logging.warning("⚠️ 'TablaCapacity' viene vacío o no se encontró.")
        _generate_logs("FactSeguimientoRecurso", pending_items)
        return pd.DataFrame(
            columns=[
                "KeyRecurso",
                "KeyFecha",
                "Activo",
                "PorcentajeDeAsignacion",
                "CostoPorHora",
                "Capacity",
            ]
        )

    # Filtro el registro "flag"
    df = df_raw[df_raw["Año"] != 1900].copy()

    # Tablas de homologación
    df_homolog_rec = clean_data.get("HomologacionRecurso", pd.DataFrame())
    df_homolog_eq = clean_data.get("HomologacionEquipo", pd.DataFrame())

    # 2. Validación y Mapeo TempRecurso (HomologacionRecurso)
    rec_map = dict(
        zip(
            df_homolog_rec.get("NombreRecurso", pd.Series()),
            df_homolog_rec.get("NombreRecurso", pd.Series()),
        )
    )
    s_temp_rec = df["Recurso"].map(rec_map)
    df["TempRecurso"] = s_temp_rec

    recursos_sin_homologar = (
        df[s_temp_rec.isna()][["Recurso", "Equipo"]]
        .drop_duplicates()
        .rename(
            columns={
                "Recurso": "NombreRecursoOrigen",
                "Equipo": "EquipoOrigen",
            }
        )
        .assign(KeyRecurso=0)
    )

    # 3. Validación y Mapeo TempEquipo (HomologacionEquipo)
    eq_map = dict(
        zip(
            df_homolog_eq.get("EquipoOrigen", pd.Series()),
            df_homolog_eq.get("EquipoHomologado", pd.Series()),
        )
    )
    s_temp_eq = df["Equipo"].map(eq_map)
    df["TempEquipo"] = s_temp_eq

    equipos_sin_homologar = (
        df[s_temp_eq.isna()][["Equipo"]]
        .drop_duplicates()
        .rename(columns={"Equipo": "EquipoOrigen"})
        .assign(KeyEquipo=0)
    )

    # 4. Asignación de KeyRecurso (Clave Compuesta: Recurso + Equipo Homologado)
    rec_key_map = dict(
        zip(
            zip(
                df_homolog_rec.get("NombreRecurso", pd.Series()),
                df_homolog_rec.get("EquipoHomologado", pd.Series()),
            ),
            df_homolog_rec.get("KeyRecurso", pd.Series()),
        )
    )

    tuples_origen = list(zip(df["TempRecurso"], df["TempEquipo"]))
    df["KeyRecurso"] = (
        pd.Series(tuples_origen, index=df.index)
        .map(rec_key_map)
        .fillna(0)
        .astype(int)
    )

    # 5. Cálculo de KeyFecha (Primer día del mes en formato YYYYMMDD)
    # Soporta tanto meses numéricos como nombres de meses estándar si es necesario
    anio_num = pd.to_numeric(df["Año"], errors="coerce").fillna(1900).astype(int)
    
    # Si 'mes' viene como texto o número, manejamos la conversión a entero de forma segura
    if df["Mes"].dtype == object:
        mes_map = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
            "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
            "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
        }
        mes_limpio = df["mes"].str.strip().str.lower().map(mes_map)
        mes_num = pd.to_numeric(mes_limpio, errors="coerce").fillna(1).astype(int)
    else:
        mes_num = pd.to_numeric(df["Mes"], errors="coerce").fillna(1).astype(int)

    df["KeyFecha"] = ((anio_num * 10000) + (mes_num * 100) + 1).astype(int)

    # 6. Transformación de Atributos de Estado, Asignación y Costo
    # Estado (0 o 1)
    if df["KeyEstadoRecurso"].dtype == object:
        df["Activo"] = (
            df["KeyEstadoRecurso"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["1", "activo", "true", "si"])
            .astype(int)
        )
    else:
        df["Activo"] = pd.to_numeric(df["KeyEstadoRecurso"], errors="coerce").fillna(0).astype(int)

    # Porcentaje de Asignación (0 a 100)
    df["PorcentajeDeAsignacion"] = pd.to_numeric(
        df["% Asignacion"], errors="coerce"
    ).fillna(0.0).clip(lower=0, upper=100)

    # Costo por Hora (Numérico con 2 decimales)
    df["CostoPorHora"] = pd.to_numeric(
        df["Costo Hora"], errors="coerce"
    ).fillna(0.0).round(2)

    df["Capacity"]  = pd.to_numeric(
        df["KeyCapacity"], errors="coerce"
    ).fillna(0)

    # 7. Auditoría Nivel 2 y Estructurada Nivel 3
    if not recursos_sin_homologar.empty:
        pending_items.append(
            f"Se encontraron {len(recursos_sin_homologar)} recurso(s) sin registro en HomologacionRecurso."
        )

    if not equipos_sin_homologar.empty:
        pending_items.append(
            f"Se encontraron {len(equipos_sin_homologar)} equipo(s) sin registro en HomologacionEquipo."
        )

    # 8. Filtrar registros no homologados (KeyRecurso == 0) para asegurar integridad referencial
    registros_iniciales = len(df)
    rotos = df[df["KeyRecurso"] == 0].copy()
    df = df[df["KeyRecurso"] != 0].copy()
    registros_filtrados = registros_iniciales - len(df)
    
    if registros_filtrados > 0:
        logging.warning(f"⚠️ Se descartaron {registros_filtrados} registro(s) de FactSeguimientoRecurso por tener KeyRecurso = 0 (no homologados).")
    
    # 9. Salida Final al Grano Estricto
    cols_finales = [
        "KeyRecurso",
        "KeyFecha",
        "Activo",
        "PorcentajeDeAsignacion",
        "CostoPorHora",
        "Capacity",
    ]
    df_fact = df[cols_finales].copy()

    _generate_logs("FactSeguimientoRecurso", pending_items)
    _save_structured_audit_csv("FactSeguimientoRecurso_Recurso", recursos_sin_homologar)
    _save_structured_audit_csv("FactSeguimientoRecurso_Equipo", equipos_sin_homologar)
    _save_structured_audit_csv("FactSeguimientoRecurso_ROTO", rotos)

    logging.info(
        f"⚙️ [FactSeguimientoRecurso] Generada con éxito ({len(df_fact)} registros)."
    )

    return df_fact

def _build_fact_file_information(clean_data: dict[str, pd.DataFrame],dimensions: dict[str, pd.DataFrame],) -> pd.DataFrame:

    logging.info("⚙️ Construyendo [FactFileInformation]...")

    df_source = clean_data["FactFileInfo"]
    df_fact = df_source.copy()

    date_fields = [
        "FechaCreacion",
        "FechaModificacion",
        "FechaSnapshot",
    ]

    for field in date_fields:
        df_fact[field] = pd.to_datetime(
            df_fact[field],
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce",
        )

    logging.info(
        f"⚙️ [FactFileInformation] Generada con éxito ({len(df_fact)} registros)."
    )
    return df_fact

def _build_fact_sd(clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame],) -> pd.DataFrame:

    CLAVE = "Mesa de ayuda"
    COLS_RAW = ["ID", "Tipo", "Fecha de cierre"]
    COL_MAP = "Equipo"
    SIN_MATCH = "None"
    EQUIPO_EXCLUIDO = "Filtrar"

    logging.info("⚙️ Construyendo [FactSD]...")
    pending_items: list[str] = []

    # 1. Extracción segura con .get() (Preserva trazabilidad)
    df_raw = clean_data.get("ServiceDesk", pd.DataFrame()).copy()
    df_map = clean_data.get("HomologacionSD", pd.DataFrame()).copy()

        # Estructura incorrecta = error
    faltan_raw = [c for c in COLS_RAW + [CLAVE] if c not in df_raw.columns]
    faltan_map = [c for c in (CLAVE, COL_MAP) if c not in df_map.columns]
    if faltan_raw or faltan_map:
        raise KeyError(
            f"[FactSeguimientoRecurso] columnas faltantes. "
            f"ServiceDesk: {faltan_raw} | HomologacionSD: {faltan_map}"
        )

    mapa = df_map.drop_duplicates(subset=CLAVE).set_index(CLAVE)[COL_MAP]
    df_raw[COL_MAP] = df_raw[CLAVE].map(mapa).fillna(SIN_MATCH)

    # Reporte de lo que quedó sin homologar
    sin_mapa = df_raw.loc[df_raw[COL_MAP] == SIN_MATCH, CLAVE].unique()
    if len(sin_mapa):
        logging.warning(
            f"⚠️ {len(sin_mapa)} valor(es) de [{CLAVE}] sin homologación: {[str(x) for x in sin_mapa]}"
        )
    
    # Eliminar los registros cuyo equipo homologado es "Filtrar"
    n_antes = len(df_raw)
    df_raw = df_raw[df_raw[COL_MAP] != EQUIPO_EXCLUIDO]
    logging.info(f"⚙️ [FactSD] {n_antes - len(df_raw)} registro(s) eliminados.")

    df_raw["Fecha"] = _to_datetimeSD(df_raw["Fecha de cierre"])

    df_fact = df_raw[COLS_RAW + [COL_MAP] + ["Fecha"]]

    logging.info(
        f"⚙️ [FactSD] Generada con éxito ({len(df_fact)} registros)."
    )

    return df_fact

def _build_fact_acumulado_proyectos(clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame],) -> pd.DataFrame:
    process_name = "FactSeguimientoProyectoAcumulado"
    logging.info(f"⚙️ Construyendo [{process_name}]...")    
    
    pending_items = []
    df_raw = clean_data.get("AcumuladoProyectos", pd.DataFrame()).copy()
      
    if df_raw.empty:
        logging.warning(
            f"⚠️ [{process_name}] AcumuladoProyectos está vacía."
        )
        _generate_logs(f"[{process_name}]", pending_items)
        return pd.DataFrame()
    
    data = {}
    data["Proyectos"] = df_raw
    data["DimProyectoEstado"] = dimensions["DimProyectoEstado"]
    data["DimProyectoSituacion"] = dimensions["DimProyectoSituacion"]

    df = _process_proyect_files(data, process_name)


    return df

def _build_fact_seguimiento_proyecto(clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]) -> pd.DataFrame:
    process_name = "FactSeguimientoProyecto"
    logging.info(f"⚙️ Construyendo [{process_name}]...")    
    
    pending_items: list[str] = []
    df_raw = clean_data.get("BajadaProyectos", pd.DataFrame()).copy()
      
    if df_raw.empty:
        logging.warning(
            f"⚠️ [{process_name}] BajadaProyectos está vacía."
        )
        _generate_logs(f"[{process_name}]", pending_items)
        return pd.DataFrame()

    # Obtención segura de FechaSnapshot
    df_file_info = clean_data.get("FactFileInfo", pd.DataFrame())
    fecha_snapshot = 0
    if not df_file_info.empty and "Alias" in df_file_info.columns:
        match_snap = df_file_info.loc[
            df_file_info["Alias"] == "Proyectos", "FechaSnapshot"
        ]
        if not match_snap.empty:
            fecha_snapshot = match_snap.item()

    if fecha_snapshot == 0:
        msg = "No se encontró FechaSnapshot para 'Proyectos' en FactFileInfo. Se asigna 0 por defecto."
        logging.warning(f"⚠️ [{process_name}] {msg}")
        pending_items.append(msg)

    data={}
    df_raw["FileDate"] = fecha_snapshot
    df_raw["FileDate"] = df_raw["FileDate"].astype("string")
    data["Proyectos"] = df_raw
    data["DimProyectoEstado"] = dimensions["DimProyectoEstado"]
    data["DimProyectoSituacion"] = dimensions["DimProyectoSituacion"]

    df = _process_proyect_files(data, process_name)

    return df

def _process_proyect_files( dimensions: dict[str, pd.DataFrame], process: str) -> pd.DataFrame:

    pending_items: list[str] = []

    # 1. Lectura segura con .get() (preserva trazabilidad)
    df_raw = dimensions.get("Proyectos", pd.DataFrame()).copy()

    # 2. Filtrado de registros válidos
    mask_valid = (
        (df_raw["Proyecto"] != "NO")
        & df_raw["Proyecto"].notna()
        & (df_raw["Proyecto"] != "")
    )
    df = df_raw[mask_valid].copy()

    if df.empty:
        logging.warning(
            f"⚠️ [{process}] No quedan registros tras aplicar filtros de validez."
        )
        _generate_logs(f"{process}", pending_items)
        return pd.DataFrame()

    # 3. Mapeo de Atributos Base y Fechas (YYYYMMDD)
    df["KeyProyecto"] = df["Cod Proy."]
    df["FechaSnapshot"] = pd.to_datetime(df["FileDate"], errors="coerce")
    df["FechaInicioPlan"] = _to_datetime_text(df["Comienzo_Programado"])
    df["FechaFinPlan"] = _to_datetime_text(df["Fin_Programo"])
    df["FechaInicioReal"] = _to_datetime_text(df["Comienzo"])
    df["FechaFinReal"] = _to_datetime_text(df["Fin"])

    # 4. Métricas Numéricas Vectorizadas
    clean_hours = (
        df["Trabajo"]
        .astype(str)
        .str.replace(", ", ",", regex=False)
        .str.split(" ")       # 1. Separamos primero por espacio para quitar "horas"
        .str[0]
        .str.replace(".", "", regex=False)  # 2. Eliminamos el punto de los miles (1.187 -> 1187)
        .str.replace(",", ".", regex=False)  # 3. Cambiamos la coma decimal por punto (1187,51 -> 1187.51)
    )

    df["HorasPlanificadas"] = (
        pd.to_numeric(clean_hours, errors="coerce").fillna(0.0).round().astype(int)
    )

    pct_raw = df["% trabajo completado"]
    df["PorcentajeDeAvance"] = (
        pct_raw.mask(pct_raw > 1.0, pct_raw / 100.0).round(2)
    )
    df["CantidadReplanificaciones"] = df["Cant. Reprogramaciones"]
    # 5. KeyProyectoEstado

    # Diccionario de mapeo Texto -> Key
    dim_estado = dimensions["DimProyectoEstado"]
    estado_map = dict(zip(dim_estado["ProyectoEstado"], dim_estado["KeyProyectoEstado"]))

    # Identificar registros con estado determinado por porcentaje ("SI")
    es_por_porcentaje = df["Proyecto"] == "Si"
    estado_explicito = df["Proyecto"].where(~es_por_porcentaje)

    # Cálculo del texto de estado por porcentaje de avance
    pct = df["PorcentajeDeAvance"]
    calc_estado = pd.Series("Sin Iniciar", index=df.index)
    calc_estado.loc[pct >= 1] = "Terminado"
    calc_estado.loc[(pct > 0) & (pct < 1)] = "En Proceso"

    # Resolución del texto de estado final
    estado_final_str = estado_explicito.fillna(calc_estado)

    # Mapeo final a KeyProyectoEstado
    df["KeyProyectoEstado"] = estado_final_str.map(estado_map)

    # 6. KeyProyectoSituacion (Basado en el Estado del Proyecto)
    dim_situacion = dimensions.get("DimProyectoSituacion", pd.DataFrame())
    situacion_map = (
        dict(
            zip(
                dim_situacion["ProyectoSituacion"],
                dim_situacion["KeyProyectoSituacion"],
            )
        )
        if not dim_situacion.empty
        else {}
    )

    snap = df["FechaSnapshot"]
    ini_p = df["FechaInicioPlan"]
    fin_p = df["FechaFinPlan"]
    fin_r = df["FechaFinReal"]

    valid_ini_p = ini_p.notna()
    valid_fin_p = fin_p.notna()
    valid_fin_r = (fin_r != "") & fin_r.notna()

    # 1. Partimos de la base de que todo está "en fecha" por defecto
    temp_situaciones = pd.Series("En Fecha", index=df.index)

    # 2. Aplicamos las excepciones según el estado
    temp_situaciones.loc[
        (estado_final_str == "Sin Iniciar") & valid_ini_p & (snap > ini_p)
    ] = "Demorado"

    temp_situaciones.loc[
        (estado_final_str == "En Proceso") & valid_fin_p & (snap > fin_p)
    ] = "Demorado"

    temp_situaciones.loc[
        (estado_final_str == "En Proceso") & valid_ini_p & (snap < ini_p)
    ] = "adelantado"

    temp_situaciones.loc[
        (estado_final_str == "Terminado") & valid_fin_p & valid_fin_r & (fin_r > fin_p)
    ] = "Demorado"

    # 3. Mapeo final a Key
    df["KeyProyectoSituacion"] = (
        temp_situaciones.map(situacion_map).fillna(0).astype(int)
    )

    # 7. Selección de Columnas del Grano Final
    cols_finales = [
        "KeyProyecto",
        "FechaSnapshot",
        "FechaInicioPlan",
        "FechaFinPlan",
        "FechaInicioReal",
        "FechaFinReal",
        "PorcentajeDeAvance",
        "HorasPlanificadas",
        "CantidadReplanificaciones",
        "KeyProyectoEstado",
        "KeyProyectoSituacion",
    ]

    # Auditoría Nivel 2 (Siempre presente)
    _generate_logs(process, pending_items)

    logging.info(
        f"⚙️ [{process}] Generada con éxito ({len(df)} registros)."
    )
    return df[cols_finales].reset_index(drop=True)

# =============================================================================
# MAPEO EXPLICITO DE DIMENSIONES CONFORMADAS (.parquet)
# "clave_origen_en_memoria": "Nombre_Final_Parquet"
# =============================================================================
FACT_BUILDERS = {
    "FactSeguimientoProyecto": _build_fact_seguimiento_proyecto,
    "FactRegistroHoras": _build_fact_registro_horas,
    "FactAsignacionRecursos": _build_fact_asignacion_recursos,
    "FactBolsaDeHoras": _build_fact_bolsa_de_horas, 
    "FactSeguimientoRecurso": _build_fact_seguimiento_recurso,
    "FactFileInformation":_build_fact_file_information,
    "FactSD":_build_fact_sd,
    "FactSeguimientoProyectoAcumulado": _build_fact_acumulado_proyectos,
}

# =============================================================================
# FUNCIÓN MAESTRA ORQUESTADORA DE LA FASE 2
# =============================================================================

def transform_fact_tables(clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    logging.info("--- INICIANDO TRANSFORMACIÓN DE FACT TABLES ---")
    fact_dims = {}
    base_acum_dims = {k: v.copy() for k, v in base_dims.items()}
    for dim_name, builder_func in FACT_BUILDERS.items():
        df_built = builder_func(clean_data, base_acum_dims)
        
        if df_built is not None and not df_built.empty:
            fact_dims[dim_name] = df_built
            base_acum_dims[dim_name] = df_built
            logging.info(f"  ↳ [{dim_name}] -> Fact Table construida ({len(df_built)} filas)")
        else:
            logging.warning(f"⚠️ No se pudo generar la Fact Table : '{dim_name}'")

    logging.info(f"✅ FACT TABLES finalizadas. Fact Tables listas: {len(fact_dims)}")

    return fact_dims