# Modelo Dimensional
Modelo Dimensional v1.1.20261021
## Procesos 
Proceso de seguimiento de consumo de horas  
Proceso de planificación/asignación de recursos  
Proceso de seguimiento y proyeccion de Recursos  
Proceso de seguimiento de Proyectos   
Proceso de seguimiento de consumo de horas de desarrollo por bolsa
### Proceso de Seguimiento de Consumo de horas

#### Grano
Representa las horas consumidas por un recurso en un requerimiento único durante una semana calendario.

#### Tabla de hechos
FactRegistroHoras

#### Dimensiones
DimRequerimiento
DimRecurso
DimFecha (Semana)  
DimFecha (Mes)
DimFecha (KeyFecha)

#### Hechos
HorasConsumidas

#### Diccionario de Hechos
HorasConsumidas: cantidad de horas imputadas al requerimiento. Numerico con dos decimales.

#### Reglas de Negocio
- Toda tarea es única. 
- Una requerimiento no puede cambiar de categoría. 
- Las requerimiento de categoría "Proyecto" deben estar asociadas a un proyecto. 
- Las requerimiento de otras categorías no requieren asociación a proyectos. 
- Una requerimiento no puede estar asociada a más de un proyecto.

#### Preguntas de negocio
Cuantas horas se consumieron en esta requerimiento?  
Cuanto trabajo ejecuto X en esta requerimiento?  
Cual es el consumo de requerimiento de categoría X entre los recursos?  
¿Cuántas horas se consumieron por proyecto?  
¿Cuántas horas se consumieron por categoría?  
¿Cuál es la distribución de tiempo entre actividades de proyecto y actividades de apoyo?
### Proceso de Planificación/Asignación de recursos

#### Grano
Una fila representa las horas asignadas a un recurso para trabajar en una tarea durante una fecha determinada.

#### Tabla de Hechos
FactAsignacionRecursos

#### Dimensiones
DimRecurso  
DimFecha (Dia)  
DimTarea
DimProyecto
#### Hechos
HorasAsignadas

#### Diccionario de Hechos
HorasAsignadas: valor numerico de horas asignadas. Dos decimales.

#### Reglas de Negocio
- Se puede asignar un recurso a multiples tareas en la misma fecha
- Multiples recursos pueden estar asignados a una misma tarea.
- La asignacion es de granularidad diaria

#### Preguntas de negocio
¿Qué tiene asignado este recurso en una fecha determinada?  
¿Cuál es la disponibilidad futura de un recurso?  
¿Cuál es el porcentaje de carga de cada recurso?  
¿Existen recursos sobreasignados?  
¿Existen recursos subutilizados?  
¿Se está utilizando al máximo la capacidad disponible?
### Proceso de Seguimiento y Proyeccion de Recursos

#### Grano
Una fila representa el estado organizacional y la capacidad de un recurso durante un mes determinado.

#### Tabla de Hechos
FactSeguimientoRecurso
#### Dimensiones
DimRecurso  
DimFecha  (FechaMes)  
#### Hechos
PorcentajeDeAsignacion  
CostoPorHora  
Activo (0/1)

#### Diccionario de Hechos
PorcentajedeAsignacion: valor de 0 a 100. Representa el porcentaje del tiempo asignable a proyectos del recurso.
CostoporHora: valor economico de una hora del recurso.
Activo: si el recurso se encontro activo durante ese mes.

#### Reglas de negocio
- Cada registro es único por mes para cada recurso
- Un cambio de equipo genera un nuevo registro de recurso.
- Los meses en el pasado representan asignacion real
- Los meses en el futuro representan planificacion.

#### Preguntas de Negocio
¿Cuántos recursos tiene disponible cada equipo?  
¿Cuál es la capacidad disponible el próximo mes?  
¿Qué porcentaje de capacidad está comprometido?  
¿Qué recursos cambiaron de equipo?  
¿Qué recursos dejaron de estar disponibles?  
### Proceso de Seguimiento de Proyectos

#### Grano
Cada fila representa el estado de un proyecto durante una semana determinada.

#### Tabla de Hechos
FactSeguimientoProyecto

#### Dimensiones
DimProyecto  
DimFecha 
<br>• FechaSnapshot (semana)
<br>• FechaInicioPlan (dia)
<br>• FechaFinPlan (dia)
<br>• FechaInicioReal (dia)
<br>• FechaFinReal  (dia)
DimProyectoEstado  
DimProyectoSituacion  

Las cinco referencias corresponden a la misma DimFecha utilizada en distintos roles (Role-Playing Dimension).

#### Hechos
PorcentajeDeAvance  
HorasPlanificadas
CantidadReplanificaciones

#### Diccionario de Hechos
Porcentaje de Avance: Valor numerico con 2 decimales entre 0 y 1. 0 representa 0% y 1 el 100%
Horas Planificadas: cantidad total de horas planificadas del proyecto al momento del snapshot.
Cantidad de Replanificaciones: cantidad acumulada de replanificaciones del proyecto.

#### Reglas de Negocio
- Existe un único registro por proyecto para cada semana informada.
- Los proyectos pueden cambiar su estado entre snapshots.
- Los proyectos mantienen el mismo identificador durante todo su ciclo de vida.
- Los snapshots representan el estado vigente al momento de la captura.
- Horas planificadas son las horas totales cargadas en la planificacion asociadas ese proyecto al momento del SnapShot

#### Preguntas de Negocio
Cuales son los proyectos atrasados  
Cuales proyectos estan exhedidos en horas consumidas  
Que proyectos aun no comenzaron  
Que proyectos estan activos  
### Proceso de seguimiento de consumo de horas de desarrollo por bolsa

#### Grano
Cada fila representa una bolsa de horas en un año determinado.

#### Tabla de Hechos
FactBolsaDeHoras

#### Dimensiones
DimBolsa  
AñoBolsa

#### Hechos
HorasAsignadas
HorasConsumidas
HorasProgramadas  
HorasDisponibles  
HorasRestantes  

#### Diccionario de Hechos

HorasAsignadas: Cantidad de horas asignadas a la bolsa para el período anual.  
HorasConsumidas: Cantidad de horas efectivamente consumidas por tareas de proyectos pertenecientes a direcciones asociadas a la bolsa.  
HorasProgramadas: Cantidad de horas asignadas a tareas de ejecucion futura de proyectos pertenecientes a direcciones asociadas a la bolsa.  
HorasDisponibles: Cantidad de horas disponibles para consumo real. _(HorasAsignadas - HorasConsumidas )_  
HorasRestantes: Cantidad de horas no comprometidas considerando consumo efectivo y asignaciones futuras. _(HorasAsignadas - HorasConsumidas - HorasProgramadas.)_

#### Reglas de Negocio
- La bolsa se asigna una vez al año
- Las direcciones dentro de la bolsa consumen las horas, pero el saldo solo se aplica a la bolsa

##### Preguntas de Negocio
¿Cuál es la utilización de cada bolsa?  
¿Qué bolsas están próximas a agotarse?  
¿Qué consumo futuro está comprometido?  
¿Qué porcentaje de la capacidad ya fue consumida?  
## Dimensiones
### Definiciones de Dimensiones
#### DimEquipo

Representa tanto al equipo de desarrollo al cual pertenece un recurso como el equipo de desarrollo que lidera un proyecto.

KeyEquipo  
NombreEquipo  
Gerencia  
Lider  
#### DimRecursoVinculo

Representa el tipo de relación contractual existente entre el recurso y la organización.

KeyRecursoVinculo
NombreRecursoVinculo
#### DimRecursoOrigen

Representa la organización de procedencia del recurso.

KeyRecursoOrigen
NombreRecursoOrigen
#### DimRecursoPerfil

Representa el nivel de experiencia y categoria profesional principal del recurso

KeyRecursoPerfil
NombreRecursoPerfil
#### DimRecursoSkill

Representa las ramas del desarrollo en las cuales puede contribuir un recurso

KeyRecursoSkill
NombreRecursoSkill
#### DimRecurso

Representa una persona a la cual se le pueden programar tareas de proyectos y que puede cargar consumo de horas en su ejecucion    
En caso de cambiar de equipo, por motivos analiticos debe volver a ser definido.
Cada recurso tiene cargado solo su perfil y  skill principal 

KeyRecurso  
NombreRecurso  
KeyRecursoPerfil
KeyRecursoSkill
KeyRecursoOrigen
KeyRecursoVinculo
KeyEquipo
Activo 
#### DimBolsa

Representa una asignación anual de capacidad expresada en horas.

KeyBolsa
NombreBolsa
ActivoBolsa
#### DimDireccion

Representa una direccion solicitante de proyectos

KeyDireccion  
NombreDireccion  
SiglaDireccion  
DirectorACargo  
UsuarioClave
#### DimProyectoEstado

Representa el estado operativo del proyecto, informa un valor de proceso

KeyProyectoEstado
NombreProyectoEstado
#### DimProyectoSituacion

Representa la situacion del proyecto, informa un valor cualitativo.

KeyProyectoSituacion
NombreProyectoSituacion
#### DimCiclo

Representa los ciclos de carga de proyectos en la organizacion

KeyCiclo
NombreCiclo
AñoCiclo
EsVentana
#### DimProyecto

Representa un proyecto de desarrollo
Los valores son fijos y no cambian despues de su creacion.

KeyProyecto  
Cod Proy.  
NombreProyecto  
Sistema  
RM  
KeyDireccion  
KeyEquipo
KeyCiclo
#### DimTareaClasificacion

Representa la clasificacion a la cual se alinea una tarea planificada

KeyTareaClasificacion
NombreTareaClasificacion
#### DimTarea

Representa una actividad planificada sobre la cual se asignan horas a los recursos.

KeyTarea  
NombreTarea  
KeyTareaClasificacion  
KeyProyecto
#### DimRequerimientoCategoria

Representa la categoria a la cual se alinea un requerimiento

KeyRequerimientoCategoria
NombreRequerimientoCategoria
#### DimRequerimiento

Representa una actividad (requerimiento) sobre la cual los recursos registran consumo de horas.

KeyRequerimiento  
NombreRequerimiento  
KeyRequerimientoCategoria  
KeyProyecto  (Solo si Categoria = Proyecto)
#### DimFecha

Representa todos las dimensiones temporales del modelo.

KeyFecha  
Fecha  
Año  
Mes  
NombreMes  
Semana  
Trimestre  
DiaDelMes  
DiaSemana  
NombreDiaSemana  
### Dimensiones Conformadas Transversales
| Dimensión | Horas | Asignación | Recursos | Proyectos | Bolsa |
| --------- | ----- | ---------- | -------- | --------- | ----- |
| Fecha     | X     | X          | X        | X         |       |
| Recurso   | X     | X          | X        |           |       |
| Proyecto  |       | X          |          | X         |       |
| Dirección |       |            |          | X         | X     |
| Equipo    | X     | X          | X        |           |       |

DimEquipo participa directamente en algunos procesos e indirectamente a través de DimProyecto en otros.
### Relaciones Dimensionales

#### Relaciones de Pertenencia / Jerarquías (Atributos Directos)
- **DimTarea** pertenece a una **DimTareaClasificacion**.
- **DimRequerimiento** pertenece a una **DimRequerimientoCategoria**.
- **DimProyecto** pertenece a una **DimDireccion**.
- **DimProyecto** pertenece a un **DimCiclo**.
- **DimProyecto** pertenece a un **DimEquipo**.
- Todas las dimensiones temporales utilizan **DimFecha**.

#### Relaciones mediante Mapeos (Entre Entidades Distintas)
Cuando la relación entre dos entidades no es una pertenencia directa o puede variar de manera explícita sin formar una jerarquía rígida, se resuelve a través de un Mapeo:

- **Mapeo Dirección → Bolsa (`MapeoDireccionBolsa`):**
  Relaciona `DimDireccion` con `DimBolsa`. Permite consolidar y aplicar el control de horas consumidas y programadas por las direcciones asociadas a cada bolsa anual.
  *(Implementación: Hoja `MapeoDireccionBolsa` en `ETL - Maestro.xlsx`)*.

- **Mapeo Requerimiento → Proyecto (`MapeoRequerimientos`):**
  Relaciona `DimRequerimiento` con `DimProyecto` (exclusivamente cuando la categoría del requerimiento es "Proyecto"). Permite asociar consumos de horas a proyectos específicos de la organización.
  *(Implementación: Archivo `Mapeo Requerimiento-Proyecto.xlsx`)*.

#### Roles de análisis de DimEquipo
DimEquipo representa una unidad organizacional, pero puede ser analizada desde diferentes relaciones según el proceso:
- **Equipo del Recurso:** Corresponde al equipo al que pertenece el recurso que ejecuta el trabajo (análisis de consumo, capacidad y asignaciones).
- **Equipo del Proyecto:** Corresponde al equipo responsable del proyecto (análisis de cartera, planificación y seguimiento de proyectos).

Los reportes deben definir explícitamente qué relación de DimEquipo utilizan según la pregunta de negocio.
### Dimensiones de Analisis
#### Proceso de Consumo de Horas
- Fecha

- Recurso
  - Equipo

- Requerimiento
  - Categoria
  - Proyecto
    - Direccion
       - Bolsa
    - Ciclo
#### Proceso de planificacion/asignacion de Recursos
- Fecha
- Recurso
  - Equipo
- Proyecto
  - Direccion
    - Bolsa
    - Ciclo
#### Proceso de Seguimiento y Proyeccion de Recursos
- Fecha

- Recurso
  - Equipo

- VinculoRecurso
- OrigenRecurso
#### Proceso de Seguimiento de Proyectos
- FechaSnapshot
- Proyecto
  - Direccion
    - Bolsa
- Ciclo
- Equipo
- ProyectoEstado
- ProyectoSituacion
#### Proceso de Seguimiento de Consumo de Horas de Desarrollo por Bolsa
- N/A. Por su grano, todo el analisis se ejecuta en los otros procesos.