# Brand Style Guide

When the user requests "branded", "on-brand", "brand colors", "brand style", or similar, apply this guide instead of the default styling.

## Font Setup

Download and register fonts at the top of the plotting script:

```python
import os, urllib.request
from matplotlib.font_manager import FontProperties, fontManager

FONT_DIR = "/tmp/_brand_fonts"
FONT_BASE_URL = "https://github.com/google/fonts/raw/main/ofl/poppins"
FONT_WEIGHTS = ["Regular", "Medium", "SemiBold"]

os.makedirs(FONT_DIR, exist_ok=True)
for weight in FONT_WEIGHTS:
    path = f"{FONT_DIR}/Poppins-{weight}.ttf"
    if not os.path.exists(path):
        urllib.request.urlretrieve(f"{FONT_BASE_URL}/Poppins-{weight}.ttf", path)
    fontManager.addfont(path)

# Font properties for reuse
FONT_TITLE = FontProperties(family="Poppins", weight="semibold", size=14)
FONT_LABEL = FontProperties(family="Poppins", weight="medium", size=12)
FONT_TICK  = FontProperties(family="Poppins", size=10)
FONT_ANNO  = FontProperties(family="Poppins", size=9)
FONT_LEGEND = FontProperties(family="Poppins", size=10)
```

Apply fonts explicitly via `fontproperties=` on text elements:
- `ax.set_title(..., fontproperties=FONT_TITLE)`
- `ax.set_xlabel(..., fontproperties=FONT_LABEL)`
- `ax.set_ylabel(..., fontproperties=FONT_LABEL)`
- `ax.legend(prop=FONT_LEGEND)`
- Tick labels: `for lbl in ax.get_xticklabels() + ax.get_yticklabels(): lbl.set_fontproperties(FONT_TICK)`

## Color Palette

### Primary (main data series, key highlights)
| Hex       | Role         |
|-----------|-------------|
| `#3E62D0` | Primary blue — use for the most important data series |

### Secondary (additional series, subtle accents)
| Hex       | Name   |
|-----------|--------|
| `#A8E6CF` | Mint   |
| `#FFE387` | Yellow |
| `#FFC198` | Peach  |
| `#FFB9CD` | Pink   |

Use secondary colors subtly — for fills, backgrounds, or additional series. Do not use them for primary data.

### Text
| Hex       | Use                              |
|-----------|----------------------------------|
| `#1A327B` | Dark navy — headings, axis labels, primary text |
| `#59616F` | Gray — secondary text, tick labels, annotations |

### Backgrounds
| Hex       | Use                     |
|-----------|-------------------------|
| `#FFFFFF` | Default figure/axes     |
| `#F8F6F3` | Warm neutral panels     |
| `#EEF2FF` | Light blue tint panels  |

### Multi-Series Color Order

When plotting multiple data series, use this order:
1. `#3E62D0` (primary blue)
2. `#59616F` (gray)
3. `#A8E6CF` (mint)
4. `#FFC198` (peach)
5. `#FFB9CD` (pink)
6. `#FFE387` (yellow — use last, low contrast on white)

### Annotation Boxes
- Primary series box: `facecolor="#EEF2FF"`, `edgecolor="#3E62D0"`
- Secondary series box: `facecolor="#F8F6F3"`, `edgecolor="#59616F"`

## General Rules

- Use `#1A327B` for all text (titles, labels, annotations) instead of black
- Spines: hide top and right; color left and bottom `#AAAAAA`
- Grid: `alpha=0.2`, color `#AAAAAA`
- Line widths: primary series `2.5`, secondary `2.0`
- Markers: primary `o` size 5, secondary `s` size 4
- Figure background: `#FFFFFF`
