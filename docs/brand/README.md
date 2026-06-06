# Brand assets

| File                    | Use                                                                         |
| ----------------------- | --------------------------------------------------------------------------- |
| `microbricks-logo.jpg`  | Full lockup (icon + wordmark + "powered by databricks"). README hero.       |
| `microbricks-logo.psd`  | Photoshop source. Edit here, then re-export the JPG.                        |
| `microbricks-icon.png`  | Icon-only (no wordmark). Use in places that already have the project name.  |

For app/UI usage the icon also lives at `frontend/hc-portal/src/hc_portal/ui/public/logo.png` (256×256, served at `/logo.png` and used as the favicon).

When updating the logo, edit the `.psd`, export a new `microbricks-logo.jpg`, then re-run the icon crop:

```bash
uv run --with Pillow python3 - <<'PY'
from PIL import Image
img = Image.open('docs/brand/microbricks-logo.jpg')
W, H = img.size
icon = img.crop((int(W*0.22), int(H*0.22), int(W*0.78), int(H*0.61)))
size = max(icon.size); pad = int(size * 0.06)
canvas = Image.new('RGB', (size + pad*2, size + pad*2), (255, 255, 255))
canvas.paste(icon, ((canvas.size[0]-icon.size[0])//2, (canvas.size[1]-icon.size[1])//2))
canvas.save('docs/brand/microbricks-icon.png', 'PNG', optimize=True)
canvas.resize((256, 256), Image.LANCZOS).save('frontend/hc-portal/src/hc_portal/ui/public/logo.png', 'PNG', optimize=True)
PY
```
