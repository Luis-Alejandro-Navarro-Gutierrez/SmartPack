import struct
import json
import zstandard as zstd
from .compressor import MAGIC_HEADER

def list_contents(archive_path: str, query: str = ""):
    dctx = zstd.ZstdDecompressor()
    with open(archive_path, "rb") as f:
        if f.read(4) != MAGIC_HEADER:
            raise ValueError("No es un archivo .spk válido.")
            
        meta_len = struct.unpack("<I", f.read(4))[0]
        manifest = json.loads(dctx.decompress(f.read(meta_len)).decode('utf-8'))
        
    if query:
        query = query.lower()
        manifest = [m for m in manifest if query in m["path"].lower()]
        
    return manifest