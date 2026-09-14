import os
from PIL import Image

logo_dir = r"c:\Users\HP\AirSense-v2\assets\logo-files"

for f in sorted(os.listdir(logo_dir)):
    p = os.path.join(logo_dir, f)
    if f.endswith(".png") or f.endswith(".ico"):
        img = Image.open(p)
        print(f"File: {f}")
        print(f"  Format: {img.format}, Size: {img.size}, Mode: {img.mode}")
        if img.mode == 'RGBA':
            # Check if transparent pixels exist
            extrema = img.getextrema()
            alpha_extrema = extrema[3] if len(extrema) == 4 else None
            print(f"  Alpha range: {alpha_extrema} (has transparency: {alpha_extrema[0] < 255 if alpha_extrema else False})")
