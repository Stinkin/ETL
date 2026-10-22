# Modelo ETL
Version 0.4.20261021
## Reglas Generales
Estas reglas se aplican a todas las dimensiones, salvo que explicitamente se definan nuevas en la dimension
### Validaciones
Toda dependencia debe existir.
Toda clave referenciada debe existir en su dimensión.
### Manejo de Errores
Salvo que la transformación o regla específica indique algo diferente, si alguna validación falla:
- El registro rechazado no será cargado.
- Registrar el error.
- Informar el registro afectado.
- Procesar proximo registro.
Implementación actual: los errores y desvíos se registran en la carpeta `Data` (`<Modulo>_Error.txt` o `<Modulo>_OK.txt` y, cuando corresponde, `<Modulo>_Faltantes.csv`). Las claves externas no resueltas se reemplazan por 0 en lugar de rechazar el registro, salvo que la tabla indique otra cosa.
### Precondiciones
Para cada archivo requerido:
- El archivo debe encontrarse disponible.
- La estructura del archivo corresponde a la versión vigente.
- El archivo esta actualizado.
### Higiene de Datos
Antes de cualquier transformación, todas las fuentes reciben la siguiente higiene:
- Se limpian los encabezados de columna (espacios y espacios de no separación).
- Se eliminan las filas completamente vacías y los registros duplicados exactos.
- Los valores de texto se normalizan: espacios múltiples colapsados, comas estandarizadas y formato Título (ej.: "NO" se procesa como "No"). Los textos nulos se reemplazan por cadena vacía.
- Los valores numéricos nulos se reemplazan por 0.
Al finalizar el proceso, se convierten a mayúsculas las columnas Ciclo (DimCiclo), Direccion (DimDireccion), Equipo y Gerencia (DimEquipo), Cod Proy. y KeyProyecto (DimProyecto), KeyProyecto (FactSeguimientoProyecto) y Equipo (FactSD).
## Origenes de datos - Archivos de Origen

El proceso ETL consume un total de 9 archivos de origen, clasificados según su naturaleza y frecuencia de actualización. Los archivos se localizan mediante `config/input_sources.txt` (columnas `key`, `folder`, `filename_pattern` y `mode`): con `mode = LAST` se procesa únicamente el archivo más reciente (por fecha de modificación) que coincide con el patrón, con `mode = ALL` se procesan y consolidan todos los archivos que coinciden y con `mode = UNIQUE` se procesa el archivo indicado.

### 1. Bajadas Operativas Semanales (3 Archivos)
Archivos dinámicos de extracción operativa que alimentan las dimensiones construidas, el seguimiento semanal y el consumo de horas.

* **`DTI 2026 - *.xlsx`** (`BajadaProyectos`)
  * **Frecuencia:** Semanal.
  * **Uso:** Carga `DimProyecto` y la tabla de hechos `FactSeguimientoProyecto`.
* **`Reporte Kairos *.xlsx`** (`RegistroHoras`)
  * **Frecuencia:** Semanal.
  * **Uso:** Carga la tabla de hechos `FactRegistroHoras` y detecta nuevos requerimientos para `DimRequerimiento`.
* **`DTI-Calidad*.xlsx`** (`ServiceDesk`)
  * **Frecuencia:** Sin definir (se procesan todos los archivos que coinciden con el patrón).
  * **Uso:** Carga la tabla de hechos `FactSD`.

### 2. Archivos Estáticos y Gobernados (6 Archivos)
Archivos de soporte, catálogos maestros, mapeos, homologaciones y presupuestos administrados por el negocio.

* **`ETL - Maestro.xlsx`**
  * **Frecuencia:** Semestral / Anual.
  * **Uso:** Contiene las tablas de Dimensiones Maestras, la hoja de mapeo `MapeoDireccionBolsa` y la hoja de asignación presupuestaria `AsignacionBolsa`.
* **`Recursos - Disponibilidad.xlsx`** (`TablaCapacity`)
  * **Frecuencia:** Mensual.
  * **Uso:** Carga la capacidad, estado y costo mensual en `FactSeguimientoRecurso`.
* **`Recursos - Planificacion.xlsx`** (`RegistroPlanificacion`)
  * **Frecuencia:** Mensual.
  * **Uso:** Carga la asignación y planificación futura de horas en `FactAsignacionRecursos` y detecta nuevas tareas para `DimTarea`.
* **`Mapeo Requerimiento-Proyecto.xlsx`** (`MapeoRequerimientos`)
  * **Frecuencia:** Semanal.
  * **Uso:** Mapeo explícito entre Requerimientos de Kairos y Proyectos para la carga de `DimRequerimiento`.
* **`Mapeo Tarea-Clasificacion.xlsx`** (`MapeoTareas`)
  * **Frecuencia:** Semanal.
  * **Uso:** Mapeo explícito entre Tareas de planificacion y Categorias para la carga de `DimTarea`.
* **`ETL - Homologacion.xlsx`** 
  * **Frecuencia:** Eventual.
  * **Uso:** Normaliza equivalencias de texto mediante las tablas `HomologacionDireccion`, `HomologacionEquipo`, `HomologacionRecurso` y `HomologacionSD` (Mesa de ayuda a Equipo, utilizada por `FactSD`).
## Origenes de datos - Dimensiones Maestras
Implementación actual: las dimensiones maestras se incorporan al modelo sin filtrado de registros. Las validaciones indicadas en cada dimensión no se ejecutan en el proceso vigente; la única transformación aplicada es la estandarización de nombres de columna indicada en cada dimensión.
### DimEquipo
#### Definicion
**Objetivo**
Listado maestro de los equipos de desarrollo
**Grano**
Cada fila representa un equipo de desarrollo.
**Destino**
DimEquipo
#### Origen
**Fuente(s) de datos.**
Maestro de Equipos
**Implementación actual.**
ETL - Maestro.xlsx / Hoja Equipos
#### Referencias
No Aplica
#### Validaciones.
KeyEquipo obligatorio
KeyEquipo único
NombreEquipo obligatorio.
#### Proceso de carga.
Cada registro válido del Maestro Equipos genera exactamente un registro en DimEquipo.
#### Transformaciones.
La primera columna del maestro se publica como KeyEquipo y la segunda como Equipo (NombreEquipo en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores.**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
### DimRecursoPerfil
#### Definicion
**Objetivo**
Listado maestro de los perfiles de los recursos
**Grano**
Cada fila representa un perfil de recurso 
**Destino**
DimRecursoPerfil
#### Origen
**Fuente(s) de datos**
Maestro de Perfiles
**Implementación actual**
ETL - Maestro.xlsx / Hoja Perfiles
#### Referencias
No Aplica
#### Validaciones.
KeyRecursoPerfil obligatorio
KeyRecursoPerfil único
NombreRecursoPerfil obligatorio.
#### Proceso de carga.
Cada registro válido del Maestro Perfiles genera exactamente un registro en DimRecursoPerfil
#### Transformaciones.
La primera columna del maestro se publica como KeyRecursoPerfil y la segunda como RecursoPerfil (NombreRecursoPerfil en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores.**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
### DimRecursoSkill
#### Definicion
**Objetivo**
Listado maestro de los skills de los recursos
**Grano**
Cada fila representa un skill de recurso 
**Destino**
DimRecursoSkill
#### Origen
**Fuente(s) de datos**
Maestro de Skills
**Implementación actual**
ETL - Maestro.xlsx / Hoja Skills
#### Referencias
No Aplica
#### Validaciones.
KeyRecursoSkill obligatorio
KeyRecursoSkill único
NombreRecursoSkill obligatorio.
#### Proceso de carga.
Cada registro válido del Maestro Skills genera exactamente un registro en DimRecursoSkill
#### Transformaciones.
La primera columna del maestro se publica como KeyRecursoSkill y la segunda como RecursoSkill (NombreRecursoSkill en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
### DimRecursoOrigen
#### Definicion
**Objetivo**
Listado maestro de los Origenes de los recursos
**Grano**
Cada fila representa un origen de recurso 
**Destino**
DimRecursoOrigen
#### Origen
**Fuente(s) de datos**
Maestro de Origenes
**Implementación actual**
ETL - Maestro.xlsx / Hoja Origenes
#### Referencias
No Aplica
#### Validaciones.
- KeyRecursoOrigen obligatorio
- KeyRecursoOrigen único
- NombreRecursoOrigen obligatorio.
#### Proceso de carga.
Cada registro válido del Maestro Origenes genera exactamente un registro en DimRecursoOrigen
#### Transformaciones.
La primera columna del maestro se publica como KeyRecursoOrigen y la segunda como RecursoOrigen (NombreRecursoOrigen en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
### DimRecursoVinculo
#### Definicion
**Objetivo**
Listado maestro de los Vinculos de los recursos
**Grano**
Cada fila representa un Vinculo de recurso 
**Destino**
DimRecursoVinculo
##### Origen
**Fuente(s) de datos**
Maestro de Vinculos
**Implementación actual**
ETL - Maestro.xlsx / Hoja Vinculos
#### Referencias
No Aplica
#### Validaciones.
- KeyRecursoVinculo obligatorio
- KeyRecursoVinculo único
- NombreRecursoVinculo obligatorio.
#### Proceso de carga.
Cada registro válido del Maestro Vinculos genera exactamente un registro en DimRecursoVinculo
#### Transformaciones.
La primera columna del maestro se publica como KeyRecursoVinculo y la segunda como RecursoVinculo (NombreRecursoVinculo en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
### DimRequerimientoCategoria
#### Definicion
**Objetivo**
Listado maestro de las categorias de Requerimientos
**Grano**
Cada fila representa una categoria de Requerimientos
**Destino**
DimRequerimientoCategoria
#### Origen
**Fuente(s) de datos**
Maestro de Categorias
**Implementación actual**
ETL - Maestro.xlsx / Hoja Categorias
#### Referencias
No Aplica
#### Validaciones.
- KeyRequerimientoCategoria obligatorio
- KeyRequerimientoCategoria único
- NombreRequerimientoCategoria obligatorio.
#### Proceso de carga.
Cada registro válido del Maestro Categorias genera exactamente un registro en DimRequerimientoCategoria
#### Transformaciones.
La primera columna del maestro se publica como KeyRequerimientoCategoria y la segunda como RequerimientoCategoria (NombreRequerimientoCategoria en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
### DimTareaClasificacion
#### Definicion
**Objetivo**
Listado maestro de las clasificaciones de Tareas
**Grano**
Cada fila representa una clasificacion de Tareas
**Destino**
DimTareaClasificacion
#### Origen
**Fuente(s) de datos**
Maestro de Clasificaciones
**Implementación actual**
ETL - Maestro.xlsx / Hoja Clasificaciones
#### Referencias
No Aplica
#### Validaciones.
- KeyTareaClasificacion obligatorio
- KeyTareaClasificacion único
- NombreTareaClasificacion obligatorio.
#### Proceso de carga.
Cada registro válido del Maestro Clasificaciones genera exactamente un registro en DimTareaClasificacion
#### Transformaciones.
La primera columna del maestro se publica como KeyTareaClasificacion y la segunda como TareaClasificacion (NombreTareaClasificacion en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
### DimDireccion
#### Definicion
**Objetivo**
Listado maestro de las Direcciones
**Grano**
Cada fila representa una Direccion
**Destino**
DimDireccion
#### Origen
**Fuente(s) de datos**
Maestro de Direcciones
**Implementación actual**
ETL - Maestro.xlsx / Hoja Direcciones
#### Referencias
No Aplica
#### Validaciones.
- KeyDireccion obligatorio.
- KeyDireccion único.
- SiglaDireccion obligatorio.
- SiglaDireccion único.
- NombreDireccion obligatorio.
#### Proceso de carga.
Cada registro válido del Maestro Direcciones genera exactamente un registro en DimDireccion
#### Transformaciones.
La primera columna del maestro se publica como KeyDireccion y la segunda como Direccion (NombreDireccion en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
### DimBolsa
#### Definicion
**Objetivo**
Listado maestro de las Bolsas de Horas de Desarrollo
**Grano**
Cada fila representa una Bolsa de Horas
**Destino**
DimBolsa
#### Origen
**Fuente(s) de datos**
Maestro de Bolsas
**Implementación actual**
ETL - Maestro.xlsx / Hoja Bolsas
#### Referencias
No Aplica
#### Validaciones.
- KeyBolsa obligatorio.
- KeyBolsa único.
- NombreBolsa obligatorio.
- ActivoBolsa obligatorio (0/1)
#### Proceso de carga.
Cada registro válido del Maestro Bolsas genera exactamente un registro en DimBolsa
#### Transformaciones.
La primera columna del maestro se publica como KeyBolsa y la segunda como Bolsa (NombreBolsa en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
### DimCiclo
#### Definicion
**Objetivo**
Listado maestro de los Ciclos de Desarrollo
**Grano**
Cada fila representa un Ciclo de Desarrollo
**Destino**
DimCiclo
#### Origen
**Fuente(s) de datos**
Maestro de Ciclos
**Implementación actual**
ETL - Maestro.xlsx / Hoja Ciclos
#### Referencias
No Aplica
#### Validaciones.
- KeyCiclo obligatorio.
- KeyCiclo único.
- NombreCiclo obligatorio.
- AñoCiclo obligatorio
- EsVentana obligatorio (0/1)
#### Proceso de carga.
Cada registro válido del Maestro de Ciclos genera exactamente un registro en DimCiclo
#### Transformaciones.
La primera columna del maestro se publica como KeyCiclo y la segunda como Ciclo (NombreCiclo en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
### DimProyectoEstado
#### Definicion
**Objetivo**
Listado maestro de los Estados de un Desarrollo
**Grano**
Cada fila representa un Estado
**Destino**
DimProyectoEstado
#### Origen
**Fuente(s) de datos**
Maestro de Estados
**Implementación actual**
ETL - Maestro.xlsx / Hoja EstadosProyecto
#### Referencias
No Aplica
#### Validaciones.
- KeyProyectoEstado obligatorio.
- KeyProyectoEstado único.
- NombreProyectoEstado obligatorio.
#### Proceso de carga.
Cada registro válido del Maestro de Estados genera exactamente un registro en DimProyectoEstado
#### Transformaciones.
La primera columna del maestro se publica como KeyProyectoEstado y la segunda como ProyectoEstado (NombreProyectoEstado en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
### DimProyectoSituacion
#### Definicion
**Objetivo**
Listado maestro de las Situaciones de un Desarrollo
**Grano**
Cada fila representa una Situacion
**Destino**
DimProyectoSituacion
#### Origen
**Fuente(s) de datos**
Maestro de Situaciones
**Implementación actual**
ETL - Maestro.xlsx / Hoja SituacionesProyecto
#### Referencias
No Aplica
#### Validaciones.
- KeyProyectoSituacion obligatorio.
- KeyProyectoSituacion único.
- NombreSituacionProyecto obligatorio.
#### Proceso de carga.
Cada registro válido del Maestro de SituacionesProyecto genera exactamente un registro en DimProyectoSituacion
#### Transformaciones.
La primera columna del maestro se publica como KeyProyectoSituacion y la segunda como ProyectoSituacion (NombreProyectoSituacion en el Modelo Dimensional). Las demás columnas se conservan sin cambios.
#### Controles
**Manejo de errores**
Aplican Reglas Generales
**Precondiciones**
Aplican Reglas Generales
## Origenes de datos - Dimensiones Conformadas
### DimRecurso
#### Definicion
**Objetivo**
Listado de todos los recursos que participan en desarrollos
**Grano**.
Cada fila representa un recurso
**Destino**
DimRecurso
#### Origen
**Fuente(s) de datos**
Maestro de Recursos
**Implementación actual**
ETL - Maestro.xlsx / Hoja Recursos
#### Referencias
**Dimensiones Utilizadas**
DimRecursoPerfil
DimRecursoSkill
DimRecursoOrigen
DimEquipo
DimRecursoVinculo
#### Validaciones
- KeyRecurso obligatorio.
- KeyRecurso único.
- NombreRecurso obligatorio.
- KeyEquipo existe en DimEquipo.
- KeyRecursoPerfil existe en DimRecursoPerfil.
- KeyRecursoSkill existe en DimRecursoSkill.
- KeyRecursoOrigen existe en DimRecursoOrigen.
- KeyRecursoVinculo existe en DimRecursoVinculo.
Aplican Reglas Generales para KeyRecurso: los registros con KeyRecurso nulo, vacío o duplicado son descartados.
Si NombreRecurso es nulo o vacío, se asigna "Sin Nombre" y se registra el error.
Si falla alguna clave externa (KeyEquipo, KeyRecursoPerfil, KeyRecursoSkill, KeyRecursoOrigen, KeyRecursoVinculo), se reemplaza por 0 la key fallida y se registra el error. Si la columna no existe en el origen, se asigna 0 a todos los registros.
#### Proceso de carga.
Cada registro valido de Maestro de Recursos genera exactamente un registro en DimRecurso
#### Transformaciones
Se proyectan las columnas KeyRecurso, NombreRecurso, Activo, KeyRecursoPerfil, KeyRecursoSkill, KeyEquipo, KeyRecursoVinculo y KeyRecursoOrigen del Maestro de Recursos.
#### Controles
**Manejo de errores**
Los desvíos se registran en Data/DimRecurso_Error.txt (Data/DimRecurso_OK.txt si no hay desvíos).
### DimFecha
#### Definicion
**Objetivo**
Catalogo de todas las Dimensiones temporales usando ISO 8601
**Grano**
Cada registro corresponde a un dia calendario
**Destino**
DimFecha
#### Origen
**Fuente(s) de datos**
No Aplica
**Implementación actual**
Generada automáticamente por el ETL.
NO se hacen busquedas, la construccion de una fecha usando el formato ISO 8601 garantiza la existencia de un registro en DimFecha
#### Referencias
No Aplica
#### Validaciones
- KeyFecha unica
- Fecha corresponde a una fecha calendario valida
#### Proceso de carga
Se genera un registro por cada fecha comprendida entre el 1 de enero del año actual menos 3 años y el 31 de diciembre del año actual más 3 años.
#### Transformaciones
KeyFecha es el valor único de la fecha en formato YYYYMMDD
Fecha es la fecha calendario
Año es el año en formato YYYY
Trimestre es el trimestre segun ISO 8601-2:2019
Mes es el mes en formato MM
NombreMes es el nombre del mes en español (Enero, Febrero, ...)
Semana es el numero de semana segun ISO 8601
DiaDelMes es el dia del mes en formato DD
DiaSemana es el numero de dia de la semana (1 = Lunes, 7 = Domingo)
NombreDiaSemana es el nombre del dia de la semana en español (Lunes, Martes, ...)
#### Controles
No Aplica
### DimProyecto
#### Definicion
**Objetivo**
Catalogo de los proyectos
**Grano**
Cada registro representa un proyecto
**Destino**
DimProyecto
#### Origen
**Fuente(s) de datos**
Situacion Semanal - Proyectos
**Implementación actual**
DTI 2026 - *.xlsx
#### Referencias
**Homologaciones Utilizadas***
HomologacionDireccion
HomologacionEquipo
**Dimensiones Utilizadas**
DimDireccion
DimEquipo
DimCiclo
#### Validaciones
- KeyProyecto obligatorio.
- KeyProyecto único.
- NombreProyecto obligatorio.
####  Proceso de carga
Cada registro válido del catálogo de proyectos genera exactamente un registro en DimProyecto.
#### Transformaciones
Solo se procesan los registros cuyo campo "Proyecto" tenga un valor distinto de "NO" y no vacío. Los registros con valor "NO" no representan proyectos y son descartados del proceso.
Se almacena el valor de la columna "Cod Proy." en los campos KeyProyecto y Cod Proy.
Se almacena el valor de la columna "Nombre de tarea" en el campo NombreProyecto. (Representa el proyecto en el sistema origen)
Se almacena el valor de la columna "Sistemas" en el campo Sistema.
Se conserva la columna "RM".
Se busca el valor de la columna "Dirección Solicitante" en la tabla HomologacionDireccion (DireccionOrigen), se busca la DireccionHomologada en DimDireccion y se carga el key en KeyDireccion.
Se busca el valor de la columna "Grupo de recursos" en HomologacionEquipo (EquipoOrigen) y se carga el EquipoHomologado en TempEquipo
Se busca TempEquipo en DimEquipo y se almacena en KeyEquipo.
Se verifica que el valor de la columna "Ciclo" exista como KeyCiclo en DimCiclo. Si existe se almacena en KeyCiclo; si está vacío o no existe se almacena "0".
#### Controles
**Registro Default**
Se agrega el registro KeyProyecto = "0", Cod Proy. = "0", NombreProyecto = "Sin Proyecto", Sistema = "Sin Sistema", KeyDireccion = 0, KeyEquipo = 0 y KeyCiclo = "0", si no existe ya un proyecto con KeyProyecto "0". Ante errores de resolución de claves externas se utiliza el Registro Default de la dimensión correspondiente.
**Manejo de errores**
Si falla KeyProyecto o NombreProyecto, Aplican Reglas Generales.
Si falla en otro campo, se reemplaza por 0 la key fallida.
Los proyectos con claves no resueltas se registran en Data/DimProyecto_Error.txt.
### DimTarea
#### Definicion
**Objetivo**
Catalogo de las tareas, con su categoria y proyecto
**Grano**
Cada registro representa una tarea programada
**Destino**
DimTarea
#### Origen
**Fuente(s) de datos**
MapeoTareas
RegistroPlanificacion
**Implementación actual**
MapeoTareas: Mapeo Tarea-Clasificacion.xlsx
RegistroPlanificacion: Recursos - Planificacion.xlsx
#### Referencias
**Dimensiones Utilizadas**
DimTareaClasificacion
DimProyecto
#### Validaciones
- KeyTarea obligatorio.
- KeyTarea único.
- NombreTarea obligatorio.
- NombreTarea + KeyProyecto único.
####  Proceso de carga
Cada registro válido de MapeoTareas genera exactamente un registro en DimTarea.
Cada registro unico de RegistroPlanificacion se transforma en un registro, ya sea gobernado o se agrega al final

#### Transformaciones
Primera fase: (Tareas previamente catalogadas)
Sobre MapeoTareas:
Se descartan los registros sin valor en la columna "Tarea".
Se almacena el valor de la columna "ID" en el campo KeyTarea. Si la columna no existe o algún ID es nulo o vacío, se asignan claves secuenciales a partir de 1.
Se almacena el valor de la columna "Tarea" en el campo NombreTarea
Se valida el valor de la columna "KeyTareaClasificacion" contra DimTareaClasificacion y se almacena en KeyTareaClasificacion. Si no existe se almacena 0.
Se valida el valor de la columna "KeyProyecto" contra DimProyecto y se almacena en KeyProyecto. Si no existe se almacena "0".
Se garantiza la unicidad de NombreTarea + KeyProyecto: ante duplicados se conserva el registro con datos válidos (los valores 0 de respaldo quedan en último lugar) y se registra el conflicto.

Segunda fase: (nuevas tareas sin catalogar)
Las tareas detectadas automáticamente se incorporan con valores por defecto hasta ser clasificadas en el catálogo MapeoTareas mediante el proceso manual correspondiente.
Sobre RegistroPlanificacion:
Se eliminan todas las columnas salvo "Tarea", "Cod Proy." y "Proyecto"
Se eliminan los registros duplicados, conservando un único registro por Tarea, Cod Proy. y Proyecto.
Solo se consideran los registros cuyo "Cod Proy." exista en DimProyecto.
Se busca el valor de la columna "Tarea" en NombreTarea de las tareas de la primera fase:
- Si la Tarea ya existe en MapeoTareas, se considera previamente gobernada y no genera modificaciones en DimTarea.
- Si no existe, se agrega un nuevo registro almacenando los valores en los campos:
    Se asigna el siguiente KeyTarea disponible (máximo KeyTarea + 1), garantizando unicidad dentro de la dimensión.
    NombreTarea con el valor de la columna "Tarea"
    KeyProyecto con el valor de la columna "Cod Proy."
    KeyTareaClasificacion = 0
Las tareas nuevas se exportan a Data/DimTarea_Faltantes.csv para su clasificación manual.
#### Controles
**Registro Default**
No posee Registro Default propio. Ante errores de resolución de claves externas se utiliza el Registro Default de la dimensión correspondiente.
**Manejo de errores**
MapeoTareas:
Si falla KeyTarea o NombreTarea, Aplican Reglas Generales.
Si falla en otro campo, se reemplaza por 0 la key fallida.
RegistroPlanificacion:
Aplican Reglas Generales.
Los desvíos se registran en Data/DimTarea_Error.txt (Data/DimTarea_OK.txt si no hay desvíos).
### DimRequerimiento
#### Definicion
**Objetivo**
Catalogo de los requerimientos, con su categoria y proyecto de existir
**Grano**
Cada registro representa un requerimiento
**Destino**
DimRequerimiento
#### Origen
**Fuente(s) de datos**
RegistroHoras
MapeoRequerimientos
**Implementación actual**
MapeoRequerimientos: Mapeo Requerimiento-Proyecto.xlsx
RegistroHoras: Reporte Kairos *.xlsx
#### Referencias
**Dimensiones Utilizadas**
DimRequerimientoCategoria
#### Validaciones
- KeyRequerimiento obligatorio.
- KeyRequerimiento único.
- NombreRequerimiento obligatorio.
- NombreRequerimiento único.
####  Proceso de carga
Cada registro válido de MapeoRequerimientos genera exactamente un registro en DimRequerimiento.
Cada registro de RegistroHoras que no se encuentre en MapeoRequerimientos genera exactamente un registro en DimRequerimiento
#### Transformaciones
Primera fase: (requerimientos previamente catalogados)
Sobre MapeoRequerimientos:
Se descartan los registros sin valor en la columna "Requerimiento" y los duplicados de "Requerimiento" (se conserva la primera ocurrencia y se registra el duplicado).
Se almacena el valor de la columna "ID" en el campo KeyRequerimiento. Si la columna no existe o algún ID es nulo o vacío, se asignan claves secuenciales a partir de 1.
Se almacena el valor de la columna "Requerimiento" en el campo NombreRequerimiento
Se valida el valor de la columna "Categoria" contra las claves de DimRequerimientoCategoria y se almacena en KeyRequerimientoCategoria. Si no existe o la columna no está presente se almacena 0.
Se valida el valor de la columna "Cod Proy." contra DimProyecto y se almacena en KeyProyecto si Categoria = Proyecto (en la implementación actual, KeyRequerimientoCategoria = 1). Si no existe se almacena "0".
Se almacena "0" en KeyProyecto si Categoria ≠ Proyecto

Segunda fase: (nuevos requerimientos sin catalogar)
Los requerimientos detectados automáticamente se incorporan con valores por defecto hasta ser clasificados en el catálogo MapeoRequerimientos mediante el proceso manual correspondiente.
Sobre RegistroHoras:
Se eliminan todas las columnas salvo "Requerimiento" y "Sdreq"
Se eliminan los registros duplicados, conservando un único registro por Requerimiento y Sdreq.
Se busca el valor de "Requerimiento" en el campo NombreRequerimiento de los requerimientos de la primera fase:
- Si ya existe en MapeoRequerimientos, se considera previamente gobernado y no genera modificaciones en DimRequerimiento.
- Si no existe, se agrega un nuevo registro almacenando los valores en los campos:
    Se asigna el siguiente KeyRequerimiento disponible (máximo KeyRequerimiento + 1), garantizando unicidad dentro de la dimensión.
    NombreRequerimiento con el valor de la columna "Requerimiento"
    KeyRequerimientoCategoria = 0
    KeyProyecto con el valor de la columna "Sdreq"
Los requerimientos nuevos se exportan a Data/DimRequerimiento_Faltantes.csv para su clasificación manual.
#### Controles
**Registro Default**
No posee Registro Default propio. Ante errores de resolución de claves externas se utiliza el Registro Default de la dimensión correspondiente.
**Manejo de errores**
MapeoRequerimientos:
Si falla KeyRequerimiento o NombreRequerimiento, Aplican Reglas Generales.
Si falla en otro campo, se reemplaza por 0 la key fallida.
RegistroHoras:
Aplican Reglas Generales.
Los desvíos se registran en Data/DimRequerimiento_Error.txt (Data/DimRequerimiento_OK.txt si no hay desvíos).
## Origenes de datos - Tablas de Hechos
### FactSeguimientoProyecto
#### Definicion
**Objetivo**
Estado de situacion de un proyecto en el Snapshot semanal
**Grano**
Cada fila representa la situacion de un proyecto en el Snapshot de esa semana
**Destino**
FactSeguimientoProyecto
#### Origen
**Fuente(s) de datos**
BajadaProyectos
**Implementación actual**.
DTI 2026 - *.xlsx
#### Referencias
**Dimensiones utilizadas**
DimFecha
DimProyecto
DimProyectoSituacion
DimProyectoEstado
#### Validaciones.
Aplican Reglas Generales.
#### Proceso de carga.
Cada registro válido de BajadaProyectos genera exactamente un registro en FactSeguimientoProyecto.
#### Transformaciones.
Se obtiene FechaSnapshot de la fecha y hora de ejecución de la extracción del archivo de Proyectos (FactFileInfo, Alias "Proyectos"). Si no se encuentra, se asigna 0 y se registra el error.
Solo se procesan los registros cuyo campo "Proyecto" tenga un valor distinto de "NO". Los registros con valor "NO" no representan proyectos y son descartados del proceso.
Se almacena el valor de la columna "Cod Proy." en el campo KeyProyecto.
Se convierte la columna "Comienzo_Programado" (formato dd/mm/aa) a fecha y se almacena en FechaInicioPlan.
Se convierte la columna "Fin_Programo" (formato dd/mm/aa) a fecha y se almacena en FechaFinPlan.
Se convierte la columna "Comienzo" (formato dd/mm/aa) a fecha y se almacena en FechaInicioReal.
Se convierte la columna "Fin" (formato dd/mm/aa) a fecha y se almacena en FechaFinReal.
Se almacena la columna "% trabajo completado" en el campo PorcentajeDeAvance convirtiendolo en un valor entre 0 y 1 con dos decimales
Se obtiene el valor numérico de la columna "Trabajo" (se descarta el texto de unidad y el separador de miles, la coma se interpreta como decimal) y se almacena en HorasPlanificadas redondeado a entero.
Se almacena la columna "Cant. Reprogramaciones" en el campo CantidadReplanificaciones.

Se determina el valor de KeyProyectoEstado aplicando las siguientes reglas en orden:

Si el valor de la columna "Proyecto" es "Si", el estado se determina por el avance:
- Si PorcentajeDeAvance >= 1, se carga "Terminado" en TempEstado
- Si PorcentajeDeAvance esta entre 0 y 1, se carga "En Proceso" en TempEstado
- En cualquier otro caso, se carga "Sin Iniciar" en TempEstado
Si no, el valor de la columna "Proyecto" se carga en TempEstado

Se busca TempEstado en DimProyectoEstado (columna ProyectoEstado) y se almacena en KeyProyectoEstado

Se determina el valor de KeyProyectoSituacion usando las siguientes reglas en orden:
- Si PorcentajeDeAvance = 0:
- - Si (FechaSnapshot > FechaInicioPLan), se carga "Atrasado" en TempSituacion
- - Si (FechaSnapshot <= FechaInicioPlan), se carga "En Fecha" en TempSituacion.
- Si PorcentajeDeAvance = 1:
- - Si (FechaFinReal <= FechaFinPlan), se carga "En Fecha" en TempSituacion.
- - Si (FechaFinReal > FechaFinPlan), se carga "Atrasado" en TempSituacion.
- Si 0 < PorcentajeDeAvance < 1:
- - Si (FechaSnapshot < FechaInicioPlan), se carga "Adelantado" en TempSituacion.
- - Si (FechaSnapshot > FechaFinPlan), se carga "Atrasado" en TempSituacion.
- - Sino, se carga "En Fecha" en "TempSituacion"
- Se busca el valor de TempSituacion en DimProyectoSituacion y se almacena la KeyProyectoSituacion correspondiente.
- En cualquier otro caso, se almacena 0.
#### Controles
**Manejo de errores**
Aplican Reglas Generales.
**Precondiciones**
Aplican Reglas Generales.
### FactRegistroHoras
#### Definicion
**Objetivo**
Registros de consumo de horas en tareas
**Grano**
Cada registro es la cantidad de horas aplicadas a una tarea dentro de una semana
**Destino**
FactRegistroHoras
#### Origen
**Fuente(s) de datos**
RegistroHoras
**Implementación actual**.
Reporte Kairos *.xlsx
#### Referenciasrenglo
**Homologaciones utilizadas**
HomologacionRecurso
HomologacionEquipo
**Dependencias**
DimFecha
DimRecurso
DimRequerimiento
#### Validaciones.
Aplican Reglas Generales.
#### Proceso de carga.
Cada combinación única de TempRecurso, TempEquipo, TempRequerimiento y KeyFecha genera exactamente un registro en FactRegistroHoras, luego de consolidar las horas correspondientes.
#### Transformaciones.
Se lee el valor de "Requerimiento" y se obtiene TempRequerimiento.
Se lee la columna "Apeynom" y se obtiene TempRecurso.
Se busca la columna "Equipo" en HomologacionEquipo (EquipoOrigen) y se obtiene TempEquipo (EquipoHomologado)
Se transforma la columna "Periodo" (formato AAAA-MM-DD) a formato YYYYMMDD y se almacena en KeyFecha. No se ajusta al primer día de la semana. La fecha calendario se conserva en el campo Fecha.
Se consolida la información agrupando por TempRecurso, TempEquipo, TempRequerimiento y KeyFecha, sumando las horas (columna "Horas") de todos los registros pertenecientes al mismo grupo en HorasConsumidas.
Se busca TempRecurso y TempEquipo en HomologacionRecurso (NombreRecurso y EquipoHomologado) y se almacena KeyRecurso. Si no se encuentra se almacena 0.
Se busca TempRequerimiento en el campo NombreRequerimiento de DimRequerimiento y se almacena el resultado en KeyRequerimiento. Si no se encuentra se almacena 0.
#### Controles
**Manejo de errores**
Los registros sin homologación de Recurso o Equipo se cargan con Key 0 y se informan en Data/FactRegistroHoras_Error.txt, Data/FactRegistroHoras_HomologacionEquipos_Faltantes.csv y Data/FactRegistroHoras_HomologacionRecurso_Faltantes.csv.
**Precondiciones**
Aplican Reglas Generales.
### FactAsignacionRecursos
#### Definicion
**Objetivo**
Una fila representa las horas asignadas a un recurso para trabajar en un proyecto durante una fecha determinada.
**Grano**
Cada registro es la cantidad de horas aplicadas a tareas de un Proyecto por un recurso en una fecha determinada
**Destino**
FactAsignacionRecursos
#### Origen
**Fuente(s) de datos**
RegistroPlanificacion
**Implementación actual**.
Recursos - Planificacion.xlsx
#### Referencias
**Homologaciones utilizadas**
HomologacionRecurso
HomologacionEquipo
**Dimensiones Utilizadas**
DimFecha
DimRecurso
DimTarea
DimProyecto
#### Validaciones.
Aplican Reglas Generales.
#### Proceso de carga.
Cada combinación única de TempRecurso, TempEquipo, KeyTarea, KeyProyecto y KeyFecha genera exactamente un registro en FactAsignacionRecursos
#### Transformaciones.
Se busca la columna "Tarea" en el campo NombreTarea de DimTarea y se almacena KeyTarea. Si no se encuentra se almacena 0.
Se busca la columna "Proyecto" en el campo NombreProyecto de DimProyecto y se almacena en KeyProyecto. Si no se encuentra se almacena "0".
Se lee la columna "Responsable" y se obtiene TempRecurso.
Se busca la columna "Equipo" en HomologacionEquipo y se obtiene TempEquipo. Si no se encuentra se asigna "sin_homologar".

Se transforma la columna "Fecha" (formato dd/mm/aaaa) en formato YYYYMMDD y se almacena en KeyFecha.
Se consolida RegistroPlanificacion agrupando por TempRecurso, TempEquipo, KeyTarea, KeyProyecto y KeyFecha, sumando el valor de "Minutos" en TempMinutosTotales
Se busca TempRecurso y TempEquipo en HomologacionRecurso (NombreRecurso y EquipoHomologado) y se almacena KeyRecurso. Si no se encuentra se almacena 0.

Se toma TempMinutosTotales se divide por 60 y se almacena como numero con dos decimales en el campo "HorasAsignadas" 
#### Controles
**Manejo de errores**
Los registros sin homologación de Recurso se cargan con KeyRecurso 0 y se informan en Data/FactAsignacionRecursos_Error.txt y Data/FactAsignacionRecursos_Recurso_Faltantes.csv.
**Precondiciones**
Aplican Reglas Generales.
### FactBolsaDeHoras
#### Definicion
**Objetivo**
Una fila representa la situacion de una bolsa de horas 
FactBolsaDeHoras materializa indicadores derivados para desacoplar el acceso a información sensible y reducir el costo de cálculo de indicadores agregados.
FactBolsaDeHoras es una Tabla de Hechos Consolidada, requiere la existencia y valides de las fuetnes de datos previa su carga.
**Grano**
Cada registro es una bolsa de horas en un año determinado
**Destino**
FactBolsaDeHoras
#### Origen
**Fuente(s) de datos**
AsignacionBolsa
FactRegistroHoras
FactAsignacionRecursos
**Implementación actual**.
ETL - Maestro.xlsx / Hoja AsignacionBolsa
#### Referencias
**Homologaciones utilizadas**
No Aplica
**Dimensiones Utilizadas**
DimProyecto
DimBolsa
DimRequerimiento
DimFecha
**Mapeos utilizados**
MapeoDireccionBolsa
#### Validaciones.
Aplican Reglas Generales.
#### Proceso de carga.
Cada registro válido de AsignacionBolsa genera exactamente un registro en FactBolsaDeHoras
#### Transformaciones.
Se genera un registro por cada registro de AsignacionBolsa.

Se busca el valor de la columna "NombreBolsa" en DimBolsa (columna Bolsa) y se almacena en KeyBolsa. Si no se encuentra se almacena 0.
Se obtiene el valor de la columna "Año" en formato YYYY y se almacena directamente en AnioBolsa.
Se obtiene el valor numérico de la columna "Horas" y se almacena en HorasAsignadas.

Se obtiene el valor de KeyProyecto vinculando FactRegistroHoras con DimRequerimiento. Solo se consideran los requerimientos de categoría Proyecto (KeyRequerimientoCategoria = 1).
Se obtiene el valor de TempTareaAño a partir del año de KeyFecha de FactRegistroHoras. Solo se consideran los registros del año en curso definido en la implementación (2026).
Se consolida FactRegistroHoras agrupando por KeyProyecto y TempTareaAño, sumando las TempHorasProyectoAño.
Se obtiene KeyDireccion de cada proyecto desde DimProyecto.  
Se busca KeyDireccion en MapeoDireccionBolsa para obtener KeyBolsa. 
Se consolidan TempHorasProyectoAño agrupando por KeyBolsa y TempTareaAño, haciendo coincidir este último con el AnioBolsa, y se almacena el resultado+0 en el campo HorasConsumidas

Se obtiene el valor de TempPlanificacionAño a partir del año de KeyFecha de FactAsignacionRecursos. Solo se consideran los registros del año en curso definido en la implementación (2026).
Se consolida FactAsignacionRecursos agrupando por KeyProyecto y TempPlanificacionAño, obteniendo TempHorasProgramadasProyecto.
Se obtiene KeyDireccion de cada proyecto desde DimProyecto.
Se busca KeyDireccion en MapeoDireccionBolsa y se obtiene KeyBolsa.
Se consolidan TempHorasProgramadasProyecto agrupando por KeyBolsa y TempPlanificacionAño, haciendo coincidir este último con el AnioBolsa, y se almacena el resultado+0 en el campo HorasProgramadas

Se almacena en HorasDisponibles el resultado de 0+HorasAsignadas − HorasConsumidas.
Se almacena en HorasRestantes el resultado de 0+HorasAsignadas − HorasConsumidas − HorasProgramadas.

#### Controles
**Manejo de errores**
Aplican Reglas Generales.
Las direcciones de proyectos sin bolsa mapeada no se consolidan en ninguna bolsa (KeyBolsa 0) y se informan en Data/FactBolsaDeHoras_Error.txt y Data/FactBolsaDeHoras_DireccionBolsa_Faltantes.csv.
**Precondiciones**
Aplican Reglas Generales.
Carga exitosa de FactRegistroHoras y FactAsignacionRecursos de los periodos a evaluar.
### FactSeguimientoRecurso
#### Definicion
**Objetivo**
Registro del estado de un recurso
**Grano**
Cada registro es la situacion de un recurso durante un mes
**Destino**
FactSeguimientoRecurso
#### Origen
**Fuente(s) de datos**
TablaCapacity
**Implementación actual**.
Recursos - Disponibilidad.xlsx
#### Referencias
**Homologaciones utilizadas**
HomologacionRecurso
HomologacionEquipo
**Dimensiones utilizadas**
DimRecurso
DimFecha
#### Validaciones.
Aplican Reglas Generales.
#### Proceso de carga.
Cada registro válido de TablaCapacity genera exactamente un registro en FactSeguimientoRecurso.
#### Transformaciones.
Se descartan los registros con "Año" = 1900 (registro marcador).
Se busca la columna "Recurso" en HomologacionRecurso y se obtiene TempRecurso.
Se busca la columna "Equipo" en HomologacionEquipo y se obtiene TempEquipo
Se busca TempRecurso y TempEquipo en HomologacionRecurso (NombreRecurso y EquipoHomologado) y se almacena KeyRecurso. (Persona + Equipo = Recurso)
Se descartan los registros cuyo KeyRecurso = 0 (recurso no homologado) para asegurar la integridad referencial.
Se obtiene el mes y año de las columnas "Mes" y "Año" y se calcula el primer dia del mes en formato YYYYMMDD, se almacena en KeyFecha (FechaMes)
Se lee el valor de la columna "KeyEstadoRecurso" y se almacena en Activo como un valor 0 o 1
Se transforma la columna "% Asignacion" a un numero entre 0 y 100 (los valores fuera de rango se acotan), y se almacena en PorcentajeDeAsignacion.
Se almacena la columna "Costo Hora" como numero con dos decimales en CostoPorHora
#### Controles
**Manejo de errores**
Los recursos y equipos sin homologación se informan en Data/FactSeguimientoRecurso_Error.txt, Data/FactSeguimientoRecurso_Recurso_Faltantes.csv, Data/FactSeguimientoRecurso_Equipo_Faltantes.csv y Data/FactSeguimientoRecurso_ROTO_Faltantes.csv (registros descartados).
**Precondiciones**
Aplican Reglas Generales.