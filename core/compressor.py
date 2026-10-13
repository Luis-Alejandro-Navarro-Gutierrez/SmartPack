import os
import struct
import json
import zstandard as zstd

MAGIC_HEADER = b"SPK4"

def pack(source_dir: str, output_file: str, level: int = 22):
    source_dir = os.path.abspath(source_dir)
    all_files = []
    
    for root, _, files in os.walk(source_dir):
        for f in files:
            fp = os.path.join(root, f)
            try:
                size = os.path.getsize(fp)
                all_files.append((fp, os.path.relpath(fp, source_dir), size))
            except Exception:
                continue

    # Ordenamiento por extensión para agrupar patrones similares contiguamente
    all_files.sort(key=lambda x: (os.path.splitext(x[1])[1].lower(), x[1].lower()))

    raw_stream = bytearray()
    manifest = []
    
    for full_path, rel_path, size in all_files:
        if size == 0:
            manifest.append({"path": rel_path.replace("\\", "/"), "offset": 0, "size": 0})
            continue
        with open(full_path, "rb") as f:
            data = f.read()
        offset = len(raw_stream)
        raw_stream.extend(data)
        manifest.append({"path": rel_path.replace("\\", "/"), "offset": offset, "size": size})

    # Compresión sólida continua con Zstandard
    cctx = zstd.ZstdCompressor(level=level, write_checksum=True)
    compressed_payload = cctx.compress(bytes(raw_stream))
    
    meta_json = json.dumps(manifest).encode('utf-8')
    meta_compressed = zstd.ZstdCompressor(level=9).compress(meta_json)
    
    with open(output_file, "wb") as out:
        out.write(MAGIC_HEADER)
        out.write(struct.pack("<I", len(meta_compressed)))
        out.write(meta_compressed)
        out.write(compressed_payload)
        
    return len(raw_stream), len(compressed_payload) + len(meta_compressed) + 8, len(all_files)