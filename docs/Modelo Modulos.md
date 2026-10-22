# Modelo Modulos
Version 0.1.20261021
## Alcance
Este documento describe los módulos Python que implementan el proceso ETL definido en Modelo ETL. No redefine reglas de negocio ni de transformación, que se establecen en Modelo Dimensional y Modelo ETL: indica qué módulo ejecuta cada etapa, sus funciones con los argumentos exactos, sus entradas y salidas, y los archivos de configuración y auditoría que utiliza.
## Estructura del Repositorio
| Ruta | Descripción |
| ---- | ----------- |
| `main.py` | Punto de entrada del pipeline. |
| `src/` | Módulos de extracción, limpieza, transformación, auditoría y carga. |
| `config/input_sources.txt` | Fuentes de datos que consume el pipeline. |
| `config/extra_sources.txt` | Fuentes auxiliares (archivo de Project y asignación en Parquet). No es leído por `main.py`. |
| `data/raw` | Carpeta de archivos de origen indicada en la configuración. |
| `data/processed` | Carpeta de salida de los archivos Parquet. |
| `Data` | Carpeta de archivos de auditoría y control (`.txt` y `.csv`). |
| `docs` | Documentación del modelo. |
| `compile.bat` | Compila un archivo Python como ejecutable único con Nuitka (`compile main.py`). |
| `requirements.txt` | Dependencias: pandas, pyarrow, openpyxl, ordered-set, pyinstaller, nuitka y pywin32. |
## Configuracion de Fuentes
`config/input_sources.txt` es un archivo de texto con separador `|` y las columnas `key`, `folder`, `filename_pattern` y `mode`.
| Key | Carpeta | Patrón de archivo | Modo | Tablas que genera |
| --- | ------- | ----------------- | ---- | ----------------- |
| `maestros` | data/raw | `ETL - Maestro.xlsx` | UNIQUE | Dimensiones maestras, TablaRecursos, AsignacionBolsa y MapeoDireccionBolsa |
| `homologacion` | data/raw | `ETL - Homologacion.xlsx` | UNIQUE | HomologacionDireccion, HomologacionEquipo, HomologacionRecurso y HomologacionSD |
| `mapeotareas` | data/raw | `Mapeo Tarea-Clasificacion.xlsx` | UNIQUE | MapeoTareas |
| `mapeorequerimiento` | data/raw | `Mapeo Requerimiento-Proyecto.xlsx` | UNIQUE | MapeoRequerimientos |
| `registroplanificacion` | data/raw | `Recursos - Planificacion.xlsx` | UNIQUE | RegistroPlanificacion |
| `recurosdisponibilidad` | data/raw | `Recursos - Disponibilidad.xlsx` | UNIQUE | TablaCapacity |
| `proyectos` | data/raw | `DTI 2026 - *.xlsx` | LAST | BajadaProyectos |
| `horas` | data/raw | `Reporte Kairos *.xlsx` | LAST | RegistroHoras |
| `servicedesk` | data/raw | `DTI-Calidad*.xlsx` | ALL | ServiceDesk |
Modos: LAST procesa el archivo más reciente que coincide con el patrón, ALL procesa y consolida todos los que coinciden y UNIQUE procesa el archivo indicado. La key `recurosdisponibilidad` se escribe así en la configuración y en `ALIAS_TABLAS`.
`config/extra_sources.txt` define `archivoproyect` (archivo `.mpp` leído con MS Project) y `bajadaasignacion` (`bajadaproyectos.parquet`). Ninguna de las dos se carga en la ejecución normal: `main.py` solo lee `input_sources.txt`.
## Flujo de Ejecucion
Al iniciar `main.py` se limpia la carpeta `Data` (`_clear_logs`), se cargan las fuentes (`load_input_sources`) y se ejecuta `run_pipeline`, que realiza en orden:
1. `extract_from_sources.extract_all_sources`: Lee todas las fuentes y agrega FactFileInfo.
2. `clean_engine.clean_dataframes`: Aplica la higiene de datos a todas las tablas.
3. `transform_base_dims.transform_base_dimensions`: Promueve las dimensiones maestras.
4. `transform_conf_dims.transform_conformed_dimensions`: Construye las dimensiones conformadas sobre las dimensiones base.
5. `audit_homologation_tables.audit_homologation_tables`: Audita las homologaciones contra las dimensiones.
6. `transform_fact_tabl.transform_fact_tables`: Construye las tablas de hechos.
7. `clean_engine.capitalize_fields`: Convierte a mayúsculas las columnas definidas.
8. `load_to_parquet.load_all_to_parquet`: Exporta todas las tablas a `data/processed`.
Las dimensiones base, las dimensiones conformadas y las tablas de hechos se reúnen en un único conjunto de tablas (data mart) y se exportan juntas. Las tablas auxiliares (mapeos, homologaciones, TablaRecursos, TablaCapacity, etc.) no se exportan.
## Modulos
### main.py
#### Definicion
**Objetivo**
Punto de entrada. Carga la configuración de fuentes y ejecuta el pipeline completo.
**Ruta**
`main.py`
**Constantes**
`OUTPUT_DIR` = `data/processed`.
#### Funciones
| Función | Argumentos | Retorno | Descripción |
| ------- | ---------- | ------- | ----------- |
| `get_latest_file` | `pattern_path: str` | `str` | Devuelve la ruta del archivo más reciente (por fecha de modificación) que coincide con el patrón. Si no hay coincidencias registra una advertencia y devuelve el patrón recibido. |
| `get_all_files` | `pattern_path: str` | `list[str]` | Devuelve todas las rutas que coinciden con el patrón, ordenadas por fecha de modificación ascendente. Lista vacía si no hay coincidencias. |
| `load_input_sources` | `config_path: str = os.path.join('config', 'input_sources.txt')` | `dict[str, list[str]]` | Lee el archivo de configuración (separador `\|`, columnas `key`, `folder`, `filename_pattern`, `mode`) y devuelve un diccionario `{key: [rutas]}`. Con `mode` = LAST usa `get_latest_file`, con ALL usa `get_all_files` y con cualquier otro valor (UNIQUE) usa el patrón tal cual. Si el archivo de configuración no existe finaliza el proceso. |
| `run_pipeline` | `input_sources` | — | Orquesta el pipeline completo (ver Flujo de Ejecución). Cualquier excepción se registra como error crítico y no se propaga. |
| `run_proyect_export` | `input_sources` | — | Exporta a Parquet las fuentes limpias sin transformarlas (uso manual para archivos de Project). Su invocación está comentada en el bloque principal. |
### extract_from_sources.py
#### Definicion
**Objetivo**
Extracción: lectura de los archivos de origen y alta de la tabla de metadatos de archivos.
**Ruta**
`src/extract_from_sources.py`
**Constantes**
`ALIAS_TABLAS` traduce `<key de configuración>_<hoja>` al nombre final de la tabla. La hoja de RegistroHoras se identifica por el prefijo truncado `horas_reporte_hs_semanal_-_planning_(`.
**Dependencias externas**
`pywin32` y Microsoft Project instalado (solo para `.mpp`), `openpyxl` (Excel) y `pyarrow` (Parquet).
#### Funciones
| Función | Argumentos | Retorno | Descripción |
| ------- | ---------- | ------- | ----------- |
| `read_proyect` | `mpp_file_path` | — | Abre un archivo `.mpp` mediante COM (`MSProject.Application`, requiere Windows y MS Project) y devuelve un DataFrame con el trabajo diario por asignación: Responsable, Fecha, Minutos, TaskUID, Tarea, Equipo, Cod Proy. y Proyecto. Omite asignaciones sin trabajo y cachea la jerarquía de tareas. |
| `read_proyect.obtener_padre_con_condicion` | `tsk` | — | Recorre la jerarquía de esquema de una tarea hasta encontrar el ancestro con el campo de usuario Text6 informado y devuelve su nombre y Text10 (con caché). |
| `adjust_registro_horas` | `df_raw: pd.DataFrame` | `pd.DataFrame` | Ubica la fila del Reporte Kairos cuya primera columna es `Apeynom` y la promueve a encabezado (las columnas sin nombre se llaman `Columna_<n>`). Descarta las filas previas y las de encabezado repetido, y agrega la columna `ID` secuencial desde 1. Devuelve un DataFrame vacío si no encuentra `Apeynom`. |
| `read_single_file` | `file_path: str, dataset_key: str` | `dict[str, pd.DataFrame]` | Lee un archivo según su extensión (`.csv`, `.xlsx`/`.xls`, `.parquet`, `.mpp`). Cada hoja de Excel se publica como `<dataset_key>_<hoja>` y se traduce a su nombre final mediante `ALIAS_TABLAS`. Devuelve `{nombre: DataFrame}`. |
| `read_all_files` | `dataset_key: str, file_list: list[str]` | `dict[str, list[pd.DataFrame]]` | Aplica `read_single_file` a cada archivo de un dataset y agrupa los DataFrames por nombre de tabla. |
| `build_file_info` | `input_sources: dict[str, list[str]]` | `pd.DataFrame` | Construye la tabla `FactFileInfo` (Alias, Archivo, RutaCompleta, FechaSnapshot, FechaCreacion, FechaModificacion) a partir de los archivos configurados. FechaSnapshot es la fecha y hora de ejecución. |
| `extract_all_sources` | `sources_config: dict[str, list[str]]` | `dict[str, pd.DataFrame]` | Lee todas las fuentes configuradas, concatena los archivos de un mismo dataset, aplica `adjust_registro_horas` a RegistroHoras y agrega `FactFileInfo`. Devuelve `{tabla: DataFrame}`. |
### clean_engine.py
#### Definicion
**Objetivo**
Limpieza e higiene de datos antes y después de las transformaciones.
**Ruta**
`src/clean_engine.py`
#### Funciones
| Función | Argumentos | Retorno | Descripción |
| ------- | ---------- | ------- | ----------- |
| `clean_registro_horas` | `df: pd.DataFrame` | `pd.DataFrame` | Convierte la columna `Horas` a numérico (la coma decimal se reemplaza por punto). |
| `sanitize_dataframe` | `df: pd.DataFrame` | `pd.DataFrame` | Aplica la higiene de datos descripta en Modelo ETL: limpia encabezados, elimina filas vacías y duplicados exactos, normaliza texto a formato Título, reemplaza nulos de texto por cadena vacía y nulos numéricos por 0. |
| `clean_dataframes` | `raw_data: dict[str, pd.DataFrame]` | `dict[str, pd.DataFrame]` | Aplica `sanitize_dataframe` a cada tabla extraída (las vacías se conservan como DataFrame vacío) y `clean_registro_horas` a RegistroHoras. Consume el diccionario de entrada. |
| `capitalize_fields` | `input_df: dict[str, pd.DataFrame]` | `dict[str, pd.DataFrame]` | Convierte a mayúsculas las columnas definidas del modelo final (ver Modelo ETL, Higiene de Datos). Se ejecuta sobre el data mart antes de exportar. |
| `capitalize_specific_words` | `input_df: dict[str, pd.DataFrame]` | `dict[str, pd.DataFrame]` | Fuerza a mayúsculas las siglas OV, SAR, SAP, BI y AYSA en DimProyecto, DimTarea y DimRequerimiento. No es invocada por `main.py`. |
| `clean_up_columns` | `input_df: dict[str, pd.DataFrame]` | `dict[str, pd.DataFrame]` | Aplica `capitalize_fields` y `capitalize_specific_words` sobre una copia del diccionario. No es invocada por `main.py`. |
### transform_base_dims.py
#### Definicion
**Objetivo**
Dimensiones maestras (Fase 1).
**Ruta**
`src/transform_base_dims.py`
**Constantes**
`PURE_BASE_KEYS` (definida dentro de `transform_base_dimensions`): DimEquipo, DimRecursoPerfil, DimRecursoSkill, DimRecursoOrigen, DimRecursoVinculo, DimRequerimientoCategoria, DimTareaClasificacion, DimDireccion, DimBolsa, DimCiclo, DimProyectoEstado y DimProyectoSituacion.
Las tablas AsignacionBolsa y MapeoDireccionBolsa no se promueven: permanecen en los datos limpios y son consumidas por FactBolsaDeHoras.
#### Funciones
| Función | Argumentos | Retorno | Descripción |
| ------- | ---------- | ------- | ----------- |
| `standardize_dim_columns` | `df: pd.DataFrame, dim_name: str` | `pd.DataFrame` | Renombra la primera columna a `Key<Entidad>` y la segunda a `<Entidad>`, donde `<Entidad>` es el nombre de la dimensión sin el prefijo `Dim`. |
| `transform_base_dimensions` | `clean_data: dict[str, pd.DataFrame]` | `dict[str, pd.DataFrame]` | Promueve las 12 dimensiones maestras (`PURE_BASE_KEYS`) desde los datos limpios hacia las dimensiones base y les aplica `standardize_dim_columns`. Advierte si falta alguna. |
### transform_conf_dims.py
#### Definicion
**Objetivo**
Dimensiones conformadas (DimRecurso, DimFecha, DimProyecto, DimRequerimiento y DimTarea).
**Ruta**
`src/transform_conf_dims.py`
**Constantes**
`CONFORMED_BUILDERS` define el orden de construcción: DimRecurso, DimFecha, DimProyecto, DimRequerimiento y DimTarea.
#### Funciones
| Función | Argumentos | Retorno | Descripción |
| ------- | ---------- | ------- | ----------- |
| `_build_dim_recurso` | `clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]` | `pd.DataFrame` | Construye DimRecurso desde TablaRecursos. Valida claves externas contra las dimensiones base (reemplaza por 0 las inválidas), asigna "Sin Nombre" a nombres vacíos y descarta KeyRecurso nulos o duplicados. |
| `_build_dim_fecha` | `clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]` | `pd.DataFrame` | Genera DimFecha con un registro por día entre el 1 de enero de (año actual − 3) y el 31 de diciembre de (año actual + 3). |
| `_build_dim_proyecto` | `clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]` | `pd.DataFrame` | Construye DimProyecto desde BajadaProyectos: filtra proyectos, homologa Dirección y Equipo, valida Ciclo, resuelve las claves y agrega el registro default `KeyProyecto = "0"`. |
| `_build_dim_requerimiento` | `clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]` | `pd.DataFrame` | Construye DimRequerimiento en dos fases: MapeoRequerimientos (catalogados) y RegistroHoras (nuevos, categoría 0). Exporta los nuevos a `DimRequerimiento_Faltantes.csv`. |
| `_build_dim_tarea` | `clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]` | `pd.DataFrame` | Construye DimTarea en dos fases: MapeoTareas (catalogadas) y RegistroPlanificacion (nuevas, clasificación 0). Exporta las nuevas a `DimTarea_Faltantes.csv`. |
| `transform_conformed_dimensions` | `clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]` | `dict[str, pd.DataFrame]` | Ejecuta en orden los constructores de `CONFORMED_BUILDERS` y devuelve las dimensiones conformadas construidas. Cada dimensión queda disponible para las siguientes. |
### audit_homologation_tables.py
#### Definicion
**Objetivo**
Auditoría de las tablas de homologación contra las dimensiones.
**Ruta**
`src/audit_homologation_tables.py`
**Constantes**
`HOMOLOGATION_BUILDERS`: Recursos, Direcciones y Equipos.
#### Funciones
| Función | Argumentos | Retorno | Descripción |
| ------- | ---------- | ------- | ----------- |
| `_audit_homologacion_recurso` | `clean_data: dict[str, pd.DataFrame], data_mart: dict[str, pd.DataFrame]` | `bool` | Verifica que cada KeyRecurso de HomologacionRecurso exista en DimRecurso e informa los registros mapeados a Key 0 o a claves inexistentes. Devuelve `False` si la tabla está vacía o no tiene la columna `KeyRecurso`. |
| `_audit_homologacion_direccion` | `clean_data: dict[str, pd.DataFrame], data_mart: dict[str, pd.DataFrame]` | `bool` | Verifica que cada DireccionHomologada de HomologacionDireccion exista en DimDireccion. Devuelve `False` si la tabla está vacía o le faltan columnas. |
| `_audit_homologacion_equipo` | `clean_data: dict[str, pd.DataFrame], data_mart: dict[str, pd.DataFrame]` | `bool` | Verifica que cada EquipoHomologado de HomologacionEquipo exista en DimEquipo. Devuelve `False` si la tabla está vacía o le faltan columnas. |
| `audit_homologation_tables` | `clean_data: dict[str, pd.DataFrame], data_mart: dict[str, pd.DataFrame]` | `None` | Ejecuta las auditorías de `HOMOLOGATION_BUILDERS` (Recursos, Direcciones, Equipos) e informa cuántas pudieron realizarse. No modifica datos. |
### transform_fact_tabl.py
#### Definicion
**Objetivo**
Tablas de hechos.
**Ruta**
`src/transform_fact_tabl.py`
**Constantes**
`FACT_BUILDERS` define el orden de construcción: FactSeguimientoProyecto, FactRegistroHoras, FactAsignacionRecursos, FactBolsaDeHoras, FactSeguimientoRecurso, FactFileInformation y FactSD.
`ANIO_ACTUAL` (definida dentro de `_build_fact_bolsa_de_horas`) = 2026. Limita las horas consumidas y programadas al año vigente.
`CLAVE`, `COLS_RAW`, `COL_MAP`, `SIN_MATCH` y `EQUIPO_EXCLUIDO` (definidas dentro de `_build_fact_sd`): "Mesa de ayuda"; ["ID", "Tipo", "Fecha de cierre"]; "Equipo"; "None"; "Filtrar".
#### Funciones
| Función | Argumentos | Retorno | Descripción |
| ------- | ---------- | ------- | ----------- |
| `_to_datetime_text` | `series: pd.Series` | `pd.Series` | Elimina el texto previo al primer espacio de cada valor (por ejemplo, el día de la semana) y convierte el resto, con formato dd/mm/aa, a fecha. Los valores no interpretables quedan vacíos. |
| `_to_datetime` | `series: pd.Series` | `pd.Series` | Normaliza fechas con formato d/m/aa o d/m/aaaa (se ignora la hora o el texto posterior a una coma o espacio) y las convierte a fecha con día primero. Los valores no interpretables quedan vacíos. |
| `_build_fact_seguimiento_proyecto` | `clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]` | `pd.DataFrame` | Construye FactSeguimientoProyecto desde BajadaProyectos (fechas, horas, avance, estado y situación). |
| `_build_fact_registro_horas` | `clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]` | `pd.DataFrame` | Construye FactRegistroHoras desde RegistroHoras, resolviendo recurso por HomologacionRecurso y requerimiento por DimRequerimiento. Las claves no resueltas se cargan con 0 y se informan. |
| `_build_fact_asignacion_recursos` | `clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]` | `pd.DataFrame` | Construye FactAsignacionRecursos desde RegistroPlanificacion (minutos a horas, claves de tarea, proyecto, recurso y fecha). |
| `_build_fact_bolsa_de_horas` | `clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]` | `pd.DataFrame` | Construye FactBolsaDeHoras consolidando horas asignadas (AsignacionBolsa), consumidas (FactRegistroHoras) y programadas (FactAsignacionRecursos) por bolsa y año. |
| `_build_fact_bolsa_de_horas.obtener_key_bolsa_proyecto` | `key_proyecto` | — | Devuelve el KeyBolsa de un proyecto a partir de su dirección (DimProyecto y MapeoDireccionBolsa). Devuelve 0 si no hay bolsa mapeada. |
| `_build_fact_seguimiento_recurso` | `clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]` | `pd.DataFrame` | Construye FactSeguimientoRecurso desde TablaCapacity (capacidad, estado y costo mensual por recurso). Descarta los recursos no homologados. |
| `_build_fact_file_information` | `clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]` | `pd.DataFrame` | Construye FactFileInformation desde FactFileInfo, convirtiendo FechaCreacion, FechaModificacion y FechaSnapshot a fecha y hora. |
| `_build_fact_sd` | `clean_data: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]` | `pd.DataFrame` | Construye FactSD desde ServiceDesk: homologa `Mesa de ayuda` a `Equipo` mediante HomologacionSD (sin coincidencia = "None"), elimina los registros con equipo "Filtrar" y agrega `Fecha` a partir de `Fecha de cierre`. Columnas finales: ID, Tipo, Fecha de cierre, Equipo y Fecha. |
| `transform_fact_tables` | `clean_data: dict[str, pd.DataFrame], base_dims: dict[str, pd.DataFrame]` | `dict[str, pd.DataFrame]` | Ejecuta en orden los constructores de `FACT_BUILDERS`. Cada tabla construida queda disponible para las siguientes. Las tablas vacías se omiten con una advertencia. |
### load_to_parquet.py
#### Definicion
**Objetivo**
Carga: exportación de todas las tablas a Parquet.
**Ruta**
`src/load_to_parquet.py`
#### Funciones
| Función | Argumentos | Retorno | Descripción |
| ------- | ---------- | ------- | ----------- |
| `load_all_to_parquet` | `processed_datasets: dict[str, pd.DataFrame], output_dir: str` | `None` | Exporta cada tabla como `<nombre>.parquet` (pyarrow, compresión snappy, sin índice) en el directorio indicado. Un error en una tabla se registra y no detiene las demás. |
### logs_manager.py
#### Definicion
**Objetivo**
Archivos de auditoría y control en la carpeta `Data`.
**Ruta**
`src/logs_manager.py`
#### Funciones
| Función | Argumentos | Retorno | Descripción |
| ------- | ---------- | ------- | ----------- |
| `_clear_logs` | — | `None` | Elimina los `.txt` y `.csv` de la carpeta `Data` al iniciar. Si alguno está bloqueado (abierto en Excel) informa los archivos y finaliza el proceso. |
| `_generate_logs` | `module_name: str, pending_items: list[str]` | `None` | Escribe `Data/<modulo>_Error.txt` con los pendientes, o `Data/<modulo>_OK.txt` si no hay ninguno. |
| `_save_structured_audit_csv` | `module_name: str, df: pd.DataFrame` | `None` | Exporta un DataFrame de faltantes a `Data/<modulo>_Faltantes.csv` (separador `;`, UTF-8 con BOM). No genera archivo si el DataFrame está vacío. Lanza `TypeError` si no recibe un DataFrame. |
## Archivos de Auditoria
Los módulos escriben en la carpeta `Data`, que se limpia al iniciar cada ejecución.
| Archivo | Generado por | Contenido |
| ------- | ------------ | --------- |
| `<Modulo>_Error.txt` / `<Modulo>_OK.txt` | `_generate_logs` | Pendientes de corrección del módulo (Error) o confirmación de ausencia de desvíos (OK). Módulos: DimRecurso, DimProyecto, DimRequerimiento, DimTarea, HomologacionRecurso, HomologacionDireccion, HomologacionEquipo, FactSeguimientoProyecto, FactRegistroHoras, FactAsignacionRecursos, FactBolsaDeHoras y FactSeguimientoRecurso. |
| `<Modulo>_Faltantes.csv` | `_save_structured_audit_csv` | Registros que requieren acción manual (separador `;`, UTF-8 con BOM). Incluye DimRequerimiento_Faltantes y DimTarea_Faltantes (nuevos a clasificar) y los faltantes de homologación de las tablas de hechos. |
El docstring de `_build_dim_recurso` menciona `Error_DimRecurso.txt`; el nombre real generado es `DimRecurso_Error.txt`.
## Observaciones de Implementacion
- `clean_up_columns` y `capitalize_specific_words` existen en `clean_engine.py` pero no forman parte del pipeline.
- `run_proyect_export` espera la key `archivoproyect`, que no figura en `input_sources.txt`; su uso requiere cargar `extra_sources.txt` manualmente.
- `FactFileInfo` es una tabla de origen generada en la extracción; se publica como `FactFileInformation`.
- `FactSD` y `FactFileInformation` no cuentan con definición funcional en Modelo Dimensional ni en Modelo ETL.
- Las rutas `Data` (auditoría) y `data/processed` (salida) se resuelven de forma relativa al directorio de ejecución.