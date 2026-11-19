from pathlib import Path
import sys
from PIL import Image, ImageChops

mask_a = Path(sys.argv[1])
mask_b = Path(sys.argv[2])
output = Path(sys.argv[3])

a = Image.open(mask_a).convert("L")
b = Image.open(mask_b).convert("L")

if a.size != b.size:
    raise ValueError(f"Mask sizes do not match: {a.size} and {b.size}")

combined = ImageChops.lighter(a, b)
output.parent.mkdir(parents=True, exist_ok=True)
combined.save(output)

print(f"Saved combined mask: {output}")