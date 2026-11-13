import os

def cargar_configuracion(archivo_cfg):
    logs_dir = None
    config_dir = None
    output_dir = None
    
    # Conjunto para rastrear qué claves se encontraron realmente en el archivo
    claves_encontradas = set()

    if not os.path.exists(archivo_cfg):
        raise FileNotFoundError(
            f"No se encontró '{archivo_cfg}' en {os.getcwd()}. Ejecutar desde la carpeta del proyecto.")
    with open(archivo_cfg, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            
            clave, valor = linea.split("=", 1)
            clave = clave.strip()
            valor = valor.strip().strip('"\'')
            
            if clave == "LOGS_DIR":
                logs_dir = valor
                claves_encontradas.add("LOGS_DIR")
            elif clave == "CONFIG_DIR":
                config_dir = valor
                claves_encontradas.add("CONFIG_DIR")
            elif clave == "OUTPUT_DIR":
                output_dir = valor
                claves_encontradas.add("OUTPUT_DIR")
                
    # 1. Control: Error si falta alguna clave obligatoria en el archivo
    claves_requeridas = {"LOGS_DIR", "CONFIG_DIR", "OUTPUT_DIR"}
    faltantes = claves_requeridas - claves_encontradas
    if faltantes:
        raise KeyError(f"Error de estructura: Faltan las siguientes claves obligatorias en '{archivo_cfg}': {list(faltantes)}")
        
    # 2. Control: Error diferente si alguna clave está presente pero vacía (sin valor)
    if not logs_dir:
        raise ValueError(f"Error de valor: La opción 'LOGS_DIR' en '{archivo_cfg}' no puede estar vacía.")
    if not config_dir:
        raise ValueError(f"Error de valor: La opción 'CONFIG_DIR' en '{archivo_cfg}' no puede estar vacía.")
    if not output_dir:
        raise ValueError(f"Error de valor: La opción 'OUTPUT_DIR' en '{archivo_cfg}' no puede estar vacía.")
        
    return logs_dir, config_dir, output_dir

# Esta línea se ejecuta una sola vez cuando haces "import config" por primera vez
LOGS_DIR, CONFIG_DIR, OUTPUT_DIR = cargar_configuracion("main.cfg")