import os

def cargar_configuracion(archivo_cfg):
    # 1. Definir los valores por defecto iniciales
    logs_dir = "logsOsofia"
    config_dir = "config"
    output_dir = os.path.join("data", "processed")
    
    # 2. Verificar si el archivo existe
    if os.path.exists(archivo_cfg):
        try:
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
                    elif clave == "CONFIG_DIR":
                        config_dir = valor
                    elif clave == "OUTPUT_DIR":
                        output_dir = valor
        except Exception as e:
            print(f"Aviso: No se pudo leer '{archivo_cfg}' ({e}). Usando valores por defecto.")
            
    return logs_dir, config_dir, output_dir

# Esta línea se ejecuta una sola vez cuando haces "import config" por primera vez
LOGS_DIR, CONFIG_DIR, OUTPUT_DIR = cargar_configuracion("main.cfg")