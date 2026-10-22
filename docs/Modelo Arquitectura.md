# Arquitectura de Gestión de Datos

## 0. Alcance

Este documento define los principios, patrones y convenciones generales utilizados para el diseño de soluciones de Data Warehouse. No documenta reglas específicas del negocio ni procedimientos de implementación ETL.

## 1. Filosofía de Arquitectura

### 1.1 Independencia de la herramienta

El modelo dimensional constituye la definición oficial del Data
Warehouse. La implementación debe ajustarse al modelo y no modificarlo.

### 1.2 El Modelo Dimensional es el contrato funcional

Toda implementación debe producir los mismos indicadores definidos por
el modelo.

### 1.3 El ETL construye, no define.

La Especificación ETL documenta el procedimiento mediante el cual se implementa el Modelo Dimensional, respetando los principios definidos por la Arquitectura.

### 1.4 La capa analítica consume, no transforma

La herramienta BI sólo consume el modelo dimensional.

### 1.5 Responsabilidad de control

Las validaciones de un proceso ETL se aplican exclusivamente sobre los datos de entrada consumidos por dicho proceso. La integridad referencial se verifica en el proceso que consume la entidad, no en el que la construye.

### 1.6 Consulta de Keys

Toda tabla ETL (Dim o Fact) puede depender de otras dimensiones para resolver claves. Las dependencias no constituyen fuentes de datos.

### 1.7 Principio de construcción del ETL

Cada proceso sólo puede consumir datos generados por procesos previamente ejecutados o por fuentes externas. Ningún proceso puede depender de resultados definidos posteriormente en el flujo.
Las tablas de hechos de tipo Snapshot Consolidado (ej. FactBolsaDeHoras) pueden nutrirse de otras Tablas de Hechos atómicas ya procesadas, siempre que se ejecuten en una fase posterior dentro del pipeline de orquestación y respeten su propia frecuencia de refresco.

### 1.8 Centralización de reglas de negocio

Toda regla de negocio se implementa exactamente una vez dentro del proceso ETL. La capa analítica consume dichas reglas sin reinterpretarlas ni recalcularlas.

### 1.9 Unicidad de implementacion

No dependemos de la herramienta, sino que el ETL tiene las reglas para generar conversiones claves.

------------------------------------------------------------------------

## 2. Principios de Diseño

### Entidades Canónicas

Toda entidad permanente posee una representación oficial.

### Maestros

Los maestros contienen exclusivamente entidades canónicas.

### Homologaciones

Transforman distintas representaciones de una misma entidad en una
identidad canónica.

Sistema → Homologación → Maestro → Dimensión

### Mapeos

Establecen relaciones entre entidades diferentes cuando no pueden
inferirse automáticamente.

Ejemplos: - Tarea → Proyecto - Dirección → Bolsa

### Orígenes Controlados

Archivos operativos administrados por el negocio que utilizan claves
canónicas.

### Temporalidad
oda entidad permanente gestionada por la organización posee un maestro. 
Todo atributo temporal se administra mediante un origen controlado.

------------------------------------------------------------------------

## 3. Patrones Arquitectónicos

### Construcción de Dimensiones

Sistema Origen → Homologación → Maestro → Dimensión

### Construcción de Hechos

Origen Controlado → Validación → Transformación → Tabla de Hechos

### Relaciones

Entidad → Mapeo → Entidad

------------------------------------------------------------------------

## 4. Convenciones

-   Un archivo, un propósito.
-   Un responsable por archivo.
-   Toda homologación referencia un único maestro.
-   Los mapeos no crean entidades.
-   Toda validación ocurre antes de la carga.
-   Toda decisión no deducible del modelo debe documentarse.

------------------------------------------------------------------------

## 5. Gobierno del Dato

### Validaciones mínimas

-   Existencia de claves.
-   Integridad referencial.
-   Períodos válidos.
-   Ausencia de duplicados.
-   Rangos válidos.

### Documentación

1.  Arquitectura.
2.  Modelo Dimensional.
3.  Especificación ETL.

------------------------------------------------------------------------

## 6. Glosario

**Entidad Canónica:** representación oficial utilizada por el modelo.

**Maestro:** repositorio oficial de entidades canónicas.

**Homologación:** normaliza distintas representaciones de una misma
entidad.

**Mapeo:** relación explícita entre entidades distintas.

**Origen Controlado:** origen operativo administrado por el negocio que
utiliza claves canónicas.

**Grano:** nivel mínimo de detalle de una fila.

**Snapshot:** estado de una entidad en un instante.
