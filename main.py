import sys
import os
import time
import zipfile
from core.compressor import pack
from core.extractor import unpack_all, extract_file
from core.inspector import list_contents

def print_banner():
    print("""
  ██████  ███▄ ▄███▓ ▄▄▄       ██▀███  ▄▄▄█████▓ ██▓███   ▄▄▄       ▄████▄   ██ ▄█▀
▒██    ▒ ▓██▒▀█▀ ██▒▒████▄    ▓██ ▒ ██▒▓  ██▒ ▓▒▓██░  ██▒▒████▄    ▒██▀ ▀█   ██▄█▒ 
░ ▓██▄   ▓██    ▓██░▒██  ▀█▄  ▓██ ░▄█ ▒▒ ▓██░ ▒░▓██░ ██▓▒▒██  ▀█▄  ▒▓█    ▄ ▓███▄░ 
  ▒   ██▒▒██    ▒██ ░██▄▄▄▄██ ▒██▀▀█▄  ░ ▓██▓ ░ ▒██▄█▓▒ ▒░██▄▄▄▄██ ▒▓▓▄ ▄██▒▓██ █▄  
▒██████▒▒▒██▒   ░██▒ ▓█   ▓██▒░██▓ ▒██▒  ▒██▒ ░ ▒██▒ ░  ░ ▓█   ▓██▒▒ ▓███▀ ░▒██▒ █▄ 
 
      Compresor Inteligente Ultra-Rápido por CPU (Zstandard Solid Engine)
    """)

def run():
    if len(sys.argv) < 2:
        print_banner()
        print("Comandos disponibles:")
        print("  python main.py pack <carpeta> <archivo.spk>      -> Comprimir carpeta")
        print("  python main.py unpack <archivo.spk> <destino>    -> Descomprimir todo")
        print("  python main.py list <archivo.spk> [filtro]       -> Ver contenido sin descomprimir")
        print("  python main.py get <archivo.spk> <archivo>       -> Extraer un solo archivo al instante")
        print("  python main.py bench <carpeta>                   -> Medir contra ZIP en vivo")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "pack":
        src, out = sys.argv[2], sys.argv[3]
        t0 = time.perf_counter()
        raw_s, comp_s, count = pack(src, out)
        elapsed = time.perf_counter() - t0
        ratio = (1 - (comp_s / raw_s)) * 100 if raw_s else 0
        print(f"[+] Empaquetado completado en {elapsed:.2f}s")
        print(f"    Archivos : {count}")
        print(f"    Tamaño   : {raw_s/1024/1024:.2f} MB -> {comp_s/1024/1024:.2f} MB ({ratio:.2f}% de reducción)")

    elif cmd == "unpack":
        archive, dest = sys.argv[2], sys.argv[3]
        t0 = time.perf_counter()
        count = unpack_all(archive, dest)
        elapsed = time.perf_counter() - t0
        print(f"[+] {count} archivos extraídos exitosamente en '{dest}' ({elapsed:.2f}s)")

    elif cmd == "list":
        archive = sys.argv[2]
        query = sys.argv[3] if len(sys.argv) > 3 else ""
        items = list_contents(archive, query)
        print(f"\n{'Ruta del archivo':<60} | {'Tamaño':<10}")
        print("-" * 75)
        for item in items:
            print(f"{item['path']:<60} | {item['size']:<10} B")
        print(f"\nTotal: {len(items)} archivos listados.")

    elif cmd == "get":
        archive, filename = sys.argv[2], sys.argv[3]
        res = extract_file(archive, filename)
        if res:
            print(f"[+] Archivo extraído instantáneamente: {res}")
        else:
            print(f"[-] No se encontró '{filename}' en el paquete.")

    elif cmd == "bench":
        folder = os.path.abspath(sys.argv[2])
        zip_temp = "bench_temp.zip"
        spk_temp = "bench_temp.spk"

        print(f"[*] Evaluando: {folder}")
        
        # Benchmark ZIP
        t0 = time.perf_counter()
        with zipfile.ZipFile(zip_temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for r, _, files in os.walk(folder):
                for f in files:
                    fp = os.path.join(r, f)
                    zf.write(fp, os.path.relpath(fp, folder))
        zip_time = time.perf_counter() - t0
        zip_size = os.path.getsize(zip_temp)

        # Benchmark SPK
        t0 = time.perf_counter()
        raw_s, spk_size, _ = pack(folder, spk_temp)
        spk_time = time.perf_counter() - t0

        print("\n" + "="*55)
        print(f"{'Formato':<12} | {'Tamaño':<12} | {'Tiempo':<10} | {'Eficiencia'}")
        print("-" * 55)
        print(f"{'ZIP':<12} | {zip_size/1024/1024:6.2f} MB    | {zip_time:5.2f}s    | Base")
        diff = zip_size - spk_size
        pct = (diff / zip_size) * 100
        sign = "+" if diff > 0 else ""
        print(f"{'SmartPack':<12} | {spk_size/1024/1024:6.2f} MB    | {spk_time:5.2f}s    | {sign}{pct:.2f}% mejor")
        print("="*55)

        for f in [zip_temp, spk_temp]:
            if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    run()