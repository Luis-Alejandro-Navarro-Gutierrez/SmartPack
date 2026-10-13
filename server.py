import os
import json
from mcp.server.fastmcp import FastMCP
from core.compressor import pack
from core.extractor import unpack_all, extract_file
from core.inspector import list_contents
from core.media_optimizer import optimize_image

# Inicializar el servidor MCP
mcp = FastMCP("SmartPack Server")

@mcp.tool()
def compress_directory(source_dir: str, output_spk_path: str) -> str:
    """
    Comprime un directorio completo en formato .spk usando compresión sólida Zstandard ultra-eficiente en CPU.
    
    Args:
        source_dir: Ruta absoluta de la carpeta a comprimir.
        output_spk_path: Ruta destino del archivo .spk a generar.
    """
    if not os.path.isdir(source_dir):
        return f"Error: El directorio '{source_dir}' no existe."
    
    raw_s, comp_s, count = pack(source_dir, output_spk_path)
    pct = (1 - (comp_s / raw_s)) * 100 if raw_s else 0
    return (
        f"Compresión exitosa.\n"
        f"Archivos procesados: {count}\n"
        f"Tamaño original: {raw_s / 1024 / 1024:.2f} MB\n"
        f"Tamaño empaquetado: {comp_s / 1024 / 1024:.2f} MB\n"
        f"Ahorro de espacio: {pct:.2f}%"
    )

@mcp.tool()
def list_spk_contents(archive_path: str, filter_query: str = "") -> str:
    """
    Lista el contenido de un archivo .spk sin descomprimirlo en disco.
    
    Args:
        archive_path: Ruta absoluta al archivo .spk.
        filter_query: (Opcional) Texto para filtrar nombres o extensiones de archivos.
    """
    if not os.path.isfile(archive_path):
        return f"Error: El archivo '{archive_path}' no existe."
    
    try:
        manifest = list_contents(archive_path, filter_query)
        res = [f"- {item['path']} ({item['size']} bytes)" for item in manifest]
        return f"Total archivos: {len(manifest)}\n" + "\n".join(res)
    except Exception as e:
        return f"Error leyendo el paquete: {str(e)}"

@mcp.tool()
def extract_single_file_from_spk(archive_path: str, filename: str, output_directory: str = ".") -> str:
    """
    Extrae instantáneamente un solo archivo de un paquete .spk sin descomprimir el resto.
    
    Args:
        archive_path: Ruta al archivo .spk.
        filename: Nombre o ruta relativa del archivo dentro del paquete.
        output_directory: Directorio donde se guardará el archivo extraído.
    """
    if not os.path.isfile(archive_path):
        return f"Error: El archivo '{archive_path}' no existe."
    
    out = extract_file(archive_path, filename, output_directory)
    if out:
        return f"Archivo extraído exitosamente en: {out}"
    return f"No se encontró el archivo '{filename}' dentro del paquete."

@mcp.tool()
def extract_all_spk(archive_path: str, destination_dir: str) -> str:
    """
    Extrae todo el contenido de un archivo .spk en el directorio indicado.
    
    Args:
        archive_path: Ruta al archivo .spk.
        destination_dir: Carpeta destino donde se extraerán los archivos.
    """
    if not os.path.isfile(archive_path):
        return f"Error: El archivo '{archive_path}' no existe."
    
    count = unpack_all(archive_path, destination_dir)
    return f"Extracción completa: {count} archivos restaurados en '{destination_dir}'."

@mcp.tool()
def optimize_image_file(image_path: str, quality: int = 80) -> str:
    """
    Optimiza una imagen reduciendo su tamaño drásticamente preservando transparencia.
    
    Args:
        image_path: Ruta absoluta de la imagen (PNG, JPG, WEBP).
        quality: Calidad de compresión (1 a 100, recomendado 80).
    """
    if not os.path.isfile(image_path):
        return f"Error: La imagen '{image_path}' no existe."
    
    out_f, orig, new, pct = optimize_image(image_path, quality=quality)
    return (
        f"Imagen optimizada: {out_f}\n"
        f"Tamaño original: {orig / 1024:.2f} KB\n"
        f"Tamaño final: {new / 1024:.2f} KB\n"
        f"Reducción: {pct:.2f}%"
    )

if __name__ == "__main__":
    # Inicia el transporte stdio para clientes MCP (Cursor, Claude, etc.)
    mcp.run(transport="stdio")