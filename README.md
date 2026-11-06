# ETL: archivos a Data Pond (Parquet)

Procesa los archivos fuente (Excel, CSV, Parquet y MS Project) y genera dimensiones y tablas de hechos en formato Parquet. Esos archivos son la fuente de los reportes de Power BI.

## Requisitos

- Windows (el módulo de extracción importa `win32com`).
- Python con las librerías de `requirements.txt`: `pip install -r requirements.txt`.
- MS Project instalado solo si se procesan archivos `.mpp`.

## Cómo ejecutarlo

```
python main.py
```

1. Limpia los archivos de auditoría de `data/`.
2. Lee las fuentes de `config/input_sources.txt`, limpia, construye dimensiones y hechos.
3. Justo antes de escribir, borra los `.parquet` anteriores de `data/processed/` (conserva `bajadaproyectos.parquet`) y escribe los nuevos.

Si algún archivo está abierto en Excel o Power BI, la corrida se detiene y lo indica. Cerrarlo y volver a ejecutar.

## Cómo saber si salió bien

- La consola termina con `FASES COMPLETADAS EXITOSAMENTE` solo si no hubo un error crítico. Un archivo faltante o una tabla vacía aparecen como advertencias en la consola, así que conviene leerla.
- Revisar la carpeta `data/`: los archivos `*_Error.txt` y `*_Faltantes.csv` listan lo que requiere corrección manual (los `*_OK.txt` indican que no hubo desvíos).
- Los parquet anteriores se borran recién al llegar a la carga. Si la consola muestra `Error crítico` antes de ese punto, los parquet de `data/processed/` son los de la corrida anterior.

## Estructura

| Carpeta / archivo | Contenido |
| ----------------- | --------- |
| `main.py` | Punto de entrada y orquestación |
| `src/` | Extracción, limpieza, transformaciones, auditoría y carga |
| `config/input_sources.txt` | Fuentes de la ejecución normal (`key|folder|filename_pattern|mode`; mode: LAST, ALL o UNIQUE) |
| `config/extra_sources.txt` | Fuentes del paso de proyectos (`.mpp`); no se cargan en la ejecución normal |
| `data/raw/` | Archivos de origen |
| `data/processed/` | Parquet generados (los consume Power BI) |
| `data/` | Archivos de auditoría de la última corrida |
| `docs/` | Documentación del modelo |

## Tests

Desde la carpeta del proyecto (no necesita instalar nada, usa `unittest` de Python):

```
python -m unittest discover -s tests
```

Para ver el detalle de cada test, agregar `-v`. Con pytest también funcionan (`pytest tests`).

| Archivo | Qué verifica |
| ------- | ------------ |
| `tests/test_proyecto_rules.py` | Reglas de estado y situación de proyectos, horas, porcentaje, fechas y filtro "No" |
| `tests/test_clean_engine.py` | Higiene de datos (formato Título, nulos) y mayúsculas |
| `tests/test_fechas.py` | Conversión de fechas de Project y de Service Desk |
| `tests/test_load_to_parquet.py` | Limpieza previa de parquets y carga ante errores |
| `tests/test_guards.py` | Sin comparaciones con "NO"/"SI", sin años fijos, y documentación sincronizada con el código |

Los tests no tocan la carpeta real: trabajan en una carpeta temporal. Conviene correrlos antes de cambiar una regla y después de actualizar la documentación.

## Documentación

- `docs/Modelo Arquitectura.md`: principios del diseño.
- `docs/Modelo Dimensional.md`: tablas de dimensiones y hechos.
- `docs/Modelo ETL.md`: reglas de transformación de cada tabla.
- `docs/Modelo Modulos.md`: módulos, funciones y flujo de ejecución.

Regla del proyecto: si cambia una regla de negocio en el código, se actualiza `Modelo ETL.md` en el mismo cambio.
