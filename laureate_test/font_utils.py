"""
font_utils.py — Общий модуль для разрешения путей к шрифтам.

Ищет шрифт в следующем порядке:
  1. Локальная папка fonts/ рядом со скриптом
  2. Системные пути (paratype, Ubuntu)
  3. Fallback на стандартный PyMuPDF-шрифт

Использование:
    from font_utils import FONT_CAPTION, FONT_BOLD, FONT_BD
"""

import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def _find(candidates):
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None

FONT_CAPTION = _find([
    os.path.join(_SCRIPT_DIR, "fonts", "PTSerifCaption-Regular.ttf"),
    "/usr/share/fonts/truetype/paratype/PTZ55F.ttf",   # PT Serif Caption Regular (apt fonts-paratype)
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
])

FONT_BOLD = _find([
    os.path.join(_SCRIPT_DIR, "fonts", "PTSerif-Bold.ttf"),
    "/usr/share/fonts/truetype/paratype/PTF75F.ttf",   # PT Serif Bold
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
])

FONT_BD = _find([
    "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
])

if not FONT_CAPTION:
    raise FileNotFoundError(
        "Шрифт PTSerifCaption не найден. Установите: sudo apt install fonts-paratype\n"
        "Или положите fonts/PTSerifCaption-Regular.ttf рядом со скриптами."
    )
if not FONT_BOLD:
    raise FileNotFoundError(
        "Шрифт PTSerifBold не найден. Установите: sudo apt install fonts-paratype"
    )
if not FONT_BD:
    raise FileNotFoundError(
        "Шрифт Carlito не найден. Установите: sudo apt install fonts-crosextra-carlito"
    )
