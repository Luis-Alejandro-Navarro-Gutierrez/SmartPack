import os
from PIL import Image

def optimize_image(image_path: str, output_path: str = None, target_format: str = "WEBP", quality: int = 80):
    image_path = os.path.abspath(image_path)
    orig_size = os.path.getsize(image_path)
    
    img = Image.open(image_path)
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    
    if not output_path:
        base, _ = os.path.splitext(image_path)
        output_path = f"{base}_smartopt.webp"
        
    temp_candidates = []

    # 1. Estrategia A: WebP con método de compresión profunda (method=6)
    temp_a = output_path + ".a.webp"
    save_kwargs = {
        "format": "WEBP",
        "quality": quality,
        "method": 6,
    }
    
    # Si tiene transparencia, optimizar específicamente el canal alpha
    if has_alpha:
        save_kwargs["alpha_quality"] = max(quality - 10, 60)
        img_work = img.convert("RGBA")
    else:
        img_work = img.convert("RGB")
        
    img_work.save(temp_a, **save_kwargs)
    temp_candidates.append(temp_a)

    # 2. Estrategia B: Paleta adaptativa cuantizada (si tiene transparencia)
    if has_alpha:
        temp_b = output_path + ".b.webp"
        try:
            # Cuantizar colores a 256 paletas inteligentes manteniendo transparencia limpia
            img_quant = img_work.quantize(colors=256, method=Image.Quantize.FASTOCTREE)
            img_quant.save(temp_b, format="WEBP", quality=quality, method=6)
            temp_candidates.append(temp_b)
        except Exception:
            pass

    # Elegir el archivo más pequeño resultante
    best_file = min(temp_candidates, key=lambda f: os.path.getsize(f))
    best_size = os.path.getsize(best_file)

    # Regla de Oro: Si la optimización pesa más o casi igual, avisar
    if os.path.exists(output_path):
        os.remove(output_path)
    os.rename(best_file, output_path)

    # Limpiar temporales restantes
    for f in temp_candidates:
        if os.path.exists(f):
            os.remove(f)

    savings = orig_size - best_size
    pct = (savings / orig_size) * 100
    return output_path, orig_size, best_size, pct