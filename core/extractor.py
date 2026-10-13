import os
import struct
import json
import zstandard as zstd
from .compressor import MAGIC_HEADER

def unpack_all(archive_path: str, target_dir: str):
    target_dir = os.path.abspath(target_dir)
    dctx = zstd.ZstdDecompressor()
    
    with open(archive_path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC_HEADER:
            raise ValueError("Archivo .spk incompatible o corrupto.")
            
        meta_len = struct.unpack("<I", f.read(4))[0]
        meta_json = dctx.decompress(f.read(meta_len)).decode('utf-8')
        manifest = json.loads(meta_json)
        
        compressed_payload = f.read()
        raw_stream = dctx.decompress(compressed_payload)
        
    for item in manifest:
        dest_path = os.path.join(target_dir, item["path"].replace("/", os.sep))
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        if item["size"] == 0:
            with open(dest_path, "wb") as out:
                pass
            continue
            
        data = raw_stream[item["offset"] : item["offset"] + item["size"]]
        with open(dest_path, "wb") as out:
            out.write(data)
            
    return len(manifest)

def extract_file(archive_path: str, filename: str, output_path: str = "."):
    dctx = zstd.ZstdDecompressor()
    filename_norm = filename.replace("\\", "/").lower()
    
    with open(archive_path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC_HEADER:
            raise ValueError("Archivo inválido.")
            
        meta_len = struct.unpack("<I", f.read(4))[0]
        meta_json = dctx.decompress(f.read(meta_len)).decode('utf-8')
        manifest = json.loads(meta_json)
        
        target = next((item for item in manifest if item["path"].lower().endswith(filename_norm)), None)
        if not target:
            return None
            
        raw_stream = dctx.decompress(f.read())
        data = raw_stream[target["offset"] : target["offset"] + target["size"]]
        
    out_file = os.path.join(output_path, os.path.basename(target["path"]))
    with open(out_file, "wb") as out:
        out.write(data)
        
    return out_file