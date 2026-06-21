import os

def archivo_tiene_contenido(ruta_archivo):
    """Devuelve True si el archivo tiene contenido no vacío."""
    try:
        if os.path.getsize(ruta_archivo) == 0:
            return False

        with open(ruta_archivo, "r", encoding="utf-8") as f:
            return bool(f.read().strip())
    except Exception:
        return False

def exportar_por_carpetas_principales(directorio_raiz, directorio_salida=None):
    """
    Recorre solo las carpetas que cuelgan directamente de directorio_raiz.
    Para cada carpeta principal:
    - crea una carpeta de salida con su mismo nombre
    - busca recursivamente archivos .py dentro de esa carpeta
    - ignora archivos vacíos
    - exporta todo el contenido a un único .txt dentro de esa carpeta de salida
    """
    if directorio_salida is None:
        directorio_salida = os.path.join(directorio_raiz, "exportados_txt")

    os.makedirs(directorio_salida, exist_ok=True)

    total_generados = 0

    for nombre_carpeta in sorted(os.listdir(directorio_raiz)):
        ruta_carpeta = os.path.join(directorio_raiz, nombre_carpeta)

        if not os.path.isdir(ruta_carpeta):
            continue

        # Evitar procesar la propia carpeta de salida si está dentro del raíz
        if os.path.abspath(ruta_carpeta) == os.path.abspath(directorio_salida):
            continue

        archivos_validos = []

        # Busca .py dentro de la carpeta principal y todas sus subcarpetas
        for ruta_actual, _, archivos in os.walk(ruta_carpeta):
            for archivo in sorted(archivos):
                if not archivo.endswith(".py"):
                    continue

                ruta_archivo = os.path.join(ruta_actual, archivo)

                if not archivo_tiene_contenido(ruta_archivo):
                    continue

                archivos_validos.append(ruta_archivo)

        if not archivos_validos:
            continue

        carpeta_salida = os.path.join(directorio_salida, nombre_carpeta)
        os.makedirs(carpeta_salida, exist_ok=True)

        ruta_txt = os.path.join(carpeta_salida, f"{nombre_carpeta}.txt")

        with open(ruta_txt, "w", encoding="utf-8") as salida:
            salida.write(f"Carpeta principal: {nombre_carpeta}\n")
            salida.write(f"Ruta: {ruta_carpeta}\n")
            salida.write("=" * 80 + "\n\n")

            for ruta_archivo in archivos_validos:
                ruta_relativa = os.path.relpath(ruta_archivo, ruta_carpeta)

                salida.write("-" * 80 + "\n")
                salida.write(f"Archivo: {ruta_relativa}\n")
                salida.write("-" * 80 + "\n\n")

                try:
                    with open(ruta_archivo, "r", encoding="utf-8") as f:
                        contenido = f.read()
                    salida.write(contenido)
                except Exception as e:
                    salida.write(f"[Error al leer el archivo: {e}]\n")

                salida.write("\n\n")

        total_generados += 1
        print(f"Creado: {ruta_txt} ({len(archivos_validos)} archivos .py con contenido)")

    return total_generados


if __name__ == "__main__":

    if not os.path.isdir("."):
        print(f"Error: no es un directorio válido.")
    else:
        salida = os.path.join(".", "exportados_txt")
        total = exportar_por_carpetas_principales(".", salida)

        print(f"\nProceso completado. {total} carpeta(s) exportada(s).")
        print(f"Resultados guardados en: {salida}")
