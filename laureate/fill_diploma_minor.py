"""
fill_diploma_minor.py — Заполнение Сертификата Minor (к диплому бакалавра).

Шаблон: diplomas/Сертификат Минор 2025.pdf — горизонтальный (907×638 pt).
"""

import fitz
import os

try:
    from qr_diploma import insert_qr_on_page
    _QR_AVAILABLE = True
except ImportError:
    _QR_AVAILABLE = False

try:
    from font_utils import FONT_CAPTION, FONT_BOLD, FONT_BD
except ImportError:
    _DIR = os.path.dirname(os.path.abspath(__file__))
    FONT_CAPTION = (
        os.path.join(_DIR, "fonts", "PTSerifCaption-Regular.ttf")
        if os.path.exists(os.path.join(_DIR, "fonts", "PTSerifCaption-Regular.ttf"))
        else "/usr/share/fonts/truetype/paratype/PTZ55F.ttf"
    )
    FONT_BOLD = (
        os.path.join(_DIR, "fonts", "PTSerif-Bold.ttf")
        if os.path.exists(os.path.join(_DIR, "fonts", "PTSerif-Bold.ttf"))
        else "/usr/share/fonts/truetype/paratype/PTF75F.ttf"
    )
    FONT_BD = "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf"


def _resolve_template(*candidates):
    """Берём чистый шаблон из diplomas/ или из sibling-проекта laureate/."""
    _dir = os.path.dirname(os.path.abspath(__file__))
    search_roots = [
        _dir,
        os.path.join(_dir, ".."),
        os.path.join(_dir, "..", "laureate"),
        os.getcwd(),
    ]
    for root in search_roots:
        for name in candidates:
            p = os.path.normpath(os.path.join(root, name))
            if os.path.exists(p):
                return p
    return candidates[0]


INPUT_FILE = _resolve_template(
    "diplomas/Сертификат Минор 2025.pdf",
)

COLOR_DARK = (0.106, 0.106, 0.102)
COLOR_GREY = (0.427, 0.431, 0.439)
COLOR_BLUE = (0.122, 0.227, 0.541)   # синий номер BD

PAD = 0.25

# ── Линии ────────────────────────────────────────────────────────────────────
LINE_KAZ_BD       = 162.0
LINE_KAZ_PROGRAM  = 203.2
LINE_KAZ_FIO      = 217.3
LINE_KAZ_DATES    = 231.9
LINE_KAZ_MINOR    = 246.5

LINE_ENG_BD       = 300.0
LINE_ENG_FIO      = 324.9
LINE_ENG_PROGRAM  = 338.8
LINE_ENG_MINOR    = 352.8
LINE_ENG_DATES    = 367.5

LINE_RUS_BD       = 416.0
LINE_RUS_FIO      = 440.8
LINE_RUS_PROGRAM  = 454.7
LINE_RUS_MINOR    = 468.8
LINE_RUS_DATES    = 483.5

LINE_BOTTOM       = 584.6

QR_RECT = fitz.Rect(700, 525, 825, 605)


# ── Кэш шрифтов ──────────────────────────────────────────────────────────────
_FONT_CACHE = {}

def _font_buf(path):
    if path not in _FONT_CACHE:
        with open(path, "rb") as f:
            _FONT_CACHE[path] = f.read()
    return _FONT_CACHE[path]


def _fit_size(text, font, base_size, max_width, min_size=6.0):
    if font.text_length(text, fontsize=base_size) <= max_width:
        return base_size
    return max(base_size * (max_width / font.text_length(text, fontsize=base_size)) * 0.98,
               min_size)


def _draw_text(page, text, *, line_x, line_y, size, font_path,
               color=COLOR_DARK, on_underline=True,
               align="center", min_size=6.0, label=""):
    """
    Рисует текст с очисткой через redact (без цветных прямоугольников).
    """
    if not str(text).strip():
        return
    text = str(text).strip()
    buf = _font_buf(font_path)
    font = fitz.Font(fontbuffer=buf)
    x0, x1 = line_x
    max_w = x1 - x0

    size = _fit_size(text, font, size, max_w, min_size)
    baseline = (line_y - 1.5) if on_underline else (line_y - 0.5)

    text_w = font.text_length(text, fontsize=size)
    if align == "center":
        x = x0 + (max_w - text_w) / 2
    elif align == "right":
        x = x1 - text_w
    else:
        x = x0

    erase_top = baseline - size * 0.95
    erase_bot = baseline + size * 0.20
    erase_l = max(x0 + PAD, x - 0.5)
    erase_r = min(x1 - PAD, x + text_w + 0.5)
    if erase_r > erase_l:
        page.add_redact_annot(
            fitz.Rect(erase_l, erase_top, erase_r, erase_bot),
            fill=None
        )
        page.apply_redactions(graphics=0)

    tw = fitz.TextWriter(page.rect)
    tw.append((x, baseline), text, font=font, fontsize=size)
    tw.write_text(page, color=color)


def _draw_bd_number(page, number, *, line_x, line_y, label="bd_number"):
    """Рисует номер BD в стиле синего Carlito."""
    if not number:
        return
    text = str(number).strip()
    buf = _font_buf(FONT_BD)
    font = fitz.Font(fontbuffer=buf)
    x0, x1 = line_x
    size = _fit_size(text, font, 12.0, x1 - x0, min_size=8.0)

    text_w = font.text_length(text, fontsize=size)
    x = x0 + (x1 - x0 - text_w) / 2
    baseline = line_y - 1.5

    erase_top = baseline - size * 0.95
    erase_bot = baseline + size * 0.20
    page.add_redact_annot(
        fitz.Rect(max(x0 + PAD, x - 0.5), erase_top,
                  min(x1 - PAD, x + text_w + 0.5), erase_bot),
        fill=None
    )
    page.apply_redactions(graphics=0)

    tw = fitz.TextWriter(page.rect)
    tw.append((x, baseline), text, font=font, fontsize=size)
    tw.write_text(page, color=COLOR_BLUE)


def fill_diploma_minor(data, output_path, qr_text=None):
    """Заполняет Сертификат Минор."""
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Шаблон не найден: {INPUT_FILE}")

    doc = fitz.open(INPUT_FILE)
    page = doc[0]

    bd_number = (data.get("bd_number") or "").strip()

    # ── 1. КАЗ: BD № ─────────────────────────────────────────────────────────
    if bd_number:
        _draw_bd_number(page, bd_number, line_x=(358.3, 478.3), line_y=LINE_KAZ_BD)

    # ── 2. КАЗ: Программа ────────────────────────────────────────────────────
    if data.get("program_kaz"):
        _draw_text(page, data["program_kaz"],
                   line_x=(74.8, 831.4), line_y=LINE_KAZ_PROGRAM,
                   size=10.0, font_path=FONT_CAPTION, label="program_kaz")

    # ── 3. КАЗ: ФИО ──────────────────────────────────────────────────────────
    if data.get("fio_kaz"):
        _draw_text(page, data["fio_kaz"],
                   line_x=(326.4, 831.4), line_y=LINE_KAZ_FIO,
                   size=10.0, font_path=FONT_CAPTION, label="fio_kaz")

    # ── 4. КАЗ: Даты с-по ────────────────────────────────────────────────────
    if data.get("from_year_kaz"):
        _draw_text(page, str(data["from_year_kaz"])[-2:],
                   line_x=(84.9, 99.9), line_y=LINE_KAZ_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_year_kaz")
    if data.get("from_day_kaz"):
        _draw_text(page, data["from_day_kaz"],
                   line_x=(144.2, 159.2), line_y=LINE_KAZ_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_day_kaz")
    if data.get("from_month_kaz"):
        _draw_text(page, data["from_month_kaz"],
                   line_x=(165.7, 245.7), line_y=LINE_KAZ_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_month_kaz")
    if data.get("to_year_kaz"):
        _draw_text(page, str(data["to_year_kaz"])[-2:],
                   line_x=(275.7, 290.7), line_y=LINE_KAZ_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="to_year_kaz")
    if data.get("to_day_kaz"):
        _draw_text(page, data["to_day_kaz"],
                   line_x=(335.0, 350.0), line_y=LINE_KAZ_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="to_day_kaz")
    if data.get("to_month_kaz"):
        _draw_text(page, data["to_month_kaz"],
                   line_x=(356.4, 426.4), line_y=LINE_KAZ_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="to_month_kaz")

    # ── 5. КАЗ: Minor ────────────────────────────────────────────────────────
    if data.get("minor_kaz"):
        _draw_text(page, data["minor_kaz"],
                   line_x=(74.8, 619.8), line_y=LINE_KAZ_MINOR,
                   size=10.0, font_path=FONT_CAPTION, label="minor_kaz")

    # ── 6. АНГЛ: BD № ────────────────────────────────────────────────────────
    if bd_number:
        _draw_bd_number(page, bd_number, line_x=(468.7, 588.7), line_y=LINE_ENG_BD)

    # ── 7. АНГЛ: ФИО ─────────────────────────────────────────────────────────
    if data.get("fio_eng"):
        _draw_text(page, data["fio_eng"],
                   line_x=(113.3, 593.3), line_y=LINE_ENG_FIO,
                   size=10.0, font_path=FONT_CAPTION, label="fio_eng")

    # ── 8. АНГЛ: Программа ───────────────────────────────────────────────────
    if data.get("program_eng"):
        _draw_text(page, data["program_eng"],
                   line_x=(74.8, 831.5), line_y=LINE_ENG_PROGRAM,
                   size=10.0, font_path=FONT_CAPTION, label="program_eng")

    # ── 9. АНГЛ: Minor ───────────────────────────────────────────────────────
    if data.get("minor_eng"):
        _draw_text(page, data["minor_eng"],
                   line_x=(261.6, 831.6), line_y=LINE_ENG_MINOR,
                   size=10.0, font_path=FONT_CAPTION, label="minor_eng")

    # ── 10. АНГЛ: Даты from-to ───────────────────────────────────────────────
    if data.get("from_day_eng"):
        _draw_text(page, data["from_day_eng"],
                   line_x=(152.6, 167.6), line_y=LINE_ENG_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_day_eng")
    if data.get("from_month_eng"):
        _draw_text(page, data["from_month_eng"],
                   line_x=(174.1, 259.1), line_y=LINE_ENG_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_month_eng")
    if data.get("from_year_eng"):
        _draw_text(page, str(data["from_year_eng"])[-2:],
                   line_x=(270.6, 290.6), line_y=LINE_ENG_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_year_eng")
    if data.get("to_day_eng"):
        _draw_text(page, data["to_day_eng"],
                   line_x=(307.0, 322.0), line_y=LINE_ENG_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="to_day_eng")
    if data.get("to_month_eng"):
        _draw_text(page, data["to_month_eng"],
                   line_x=(328.4, 410.9), line_y=LINE_ENG_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="to_month_eng")
    if data.get("to_year_eng"):
        _draw_text(page, str(data["to_year_eng"])[-2:],
                   line_x=(420.1, 440.1), line_y=LINE_ENG_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="to_year_eng")

    # ── 11. РУС: BD № ────────────────────────────────────────────────────────
    if bd_number:
        _draw_bd_number(page, bd_number, line_x=(474.3, 594.3), line_y=LINE_RUS_BD)

    # ── 12. РУС: ФИО ─────────────────────────────────────────────────────────
    if data.get("fio_rus"):
        _draw_text(page, data["fio_rus"],
                   line_x=(104.4, 554.4), line_y=LINE_RUS_FIO,
                   size=10.0, font_path=FONT_CAPTION, label="fio_rus")

    # ── 13. РУС: Программа ───────────────────────────────────────────────────
    if data.get("program_rus"):
        _draw_text(page, data["program_rus"],
                   line_x=(74.8, 831.6), line_y=LINE_RUS_PROGRAM,
                   size=10.0, font_path=FONT_CAPTION, label="program_rus")

    # ── 14. РУС: Minor ───────────────────────────────────────────────────────
    if data.get("minor_rus"):
        _draw_text(page, data["minor_rus"],
                   line_x=(274.5, 831.6), line_y=LINE_RUS_MINOR,
                   size=10.0, font_path=FONT_CAPTION, label="minor_rus")

    # ── 15. РУС: Даты с-по ───────────────────────────────────────────────────
    if data.get("from_day_rus"):
        _draw_text(page, data["from_day_rus"],
                   line_x=(132.6, 152.6), line_y=LINE_RUS_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_day_rus")
    if data.get("from_month_rus"):
        _draw_text(page, data["from_month_rus"],
                   line_x=(161.8, 236.8), line_y=LINE_RUS_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_month_rus")
    if data.get("from_year_rus"):
        _draw_text(page, str(data["from_year_rus"])[-2:],
                   line_x=(251.0, 271.0), line_y=LINE_RUS_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_year_rus")
    if data.get("to_day_rus"):
        _draw_text(page, data["to_day_rus"],
                   line_x=(317.5, 337.5), line_y=LINE_RUS_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="to_day_rus")
    if data.get("to_month_rus"):
        _draw_text(page, data["to_month_rus"],
                   line_x=(346.7, 429.2), line_y=LINE_RUS_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="to_month_rus")
    if data.get("to_year_rus"):
        _draw_text(page, str(data["to_year_rus"])[-2:],
                   line_x=(441.1, 456.1), line_y=LINE_RUS_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="to_year_rus")

    # ── 16. Нижний блок ───────────────────────────────────────────────────────
    if data.get("reg_number"):
        _draw_text(page, data["reg_number"],
                   line_x=(159.1, 204.1), line_y=LINE_BOTTOM,
                   size=10.0, font_path=FONT_CAPTION, label="reg_number")
    if data.get("issue_year"):
        ys = str(data["issue_year"])
        ys = ys[-1] if len(ys) == 4 else ys  # последняя цифра "202_"
        _draw_text(page, ys,
                   line_x=(221.8, 236.8), line_y=LINE_BOTTOM,
                   size=10.0, font_path=FONT_CAPTION, label="issue_year_last")
    if data.get("issue_day"):
        _draw_text(page, data["issue_day"],
                   line_x=(275.6, 295.6), line_y=LINE_BOTTOM,
                   size=10.0, font_path=FONT_CAPTION, label="issue_day")
    if data.get("issue_month_kaz"):
        _draw_text(page, data["issue_month_kaz"],
                   line_x=(300.8, 395.8), line_y=LINE_BOTTOM,
                   size=10.0, font_path=FONT_CAPTION, label="issue_month_kaz")

    # ── 17. QR ────────────────────────────────────────────────────────────────
    if qr_text and qr_text.strip() and _QR_AVAILABLE:
        try:
            insert_qr_on_page(page, qr_text.strip(), rect=QR_RECT)
            print(f"  ✓ QR вставлен ({len(qr_text)} симв.)")
        except Exception as e:
            print(f"  ⚠ QR не вставлен: {e}")

    doc.save(output_path, garbage=4, deflate=True, deflate_images=True,
             deflate_fonts=True, clean=True)
    doc.close()
    print(f"✓ Сохранено → {output_path} (тип: Минор)")


if __name__ == "__main__":
    sample = {
        "bd_number": "00019006925",
        "program_kaz": "\"6B01501 - Математика\", B009-Математика мұғалімдерін даярлау",
        "fio_kaz": "Абдуманапова Айдана Аскар қызына",
        "from_year_kaz": "21", "from_day_kaz": "28", "from_month_kaz": "тамызы",
        "to_year_kaz": "25", "to_day_kaz": "23", "to_month_kaz": "маусымы",
        "minor_kaz": "Оқу үрдісіндегі ақпараттық технологиялар",
        "program_eng": "\"6B01501 - Mathematics\", B009-Teacher training in mathematics",
        "fio_eng": "Abdumanapova Aidana",
        "from_day_eng": "28", "from_month_eng": "August", "from_year_eng": "21",
        "to_day_eng": "23", "to_month_eng": "June", "to_year_eng": "25",
        "minor_eng": "Information technologies in the educational process",
        "program_rus": "\"6B01501 - Математика\", B009-Подготовка учителей математики",
        "fio_rus": "Абдуманаповой Айдане Аскар кизи",
        "from_day_rus": "28", "from_month_rus": "августа", "from_year_rus": "21",
        "to_day_rus": "23", "to_month_rus": "июня", "to_year_rus": "25",
        "minor_rus": "Информационные технологии в учебном процессе",
        "issue_year": "2025", "issue_day": "23", "issue_month_kaz": "маусым",
        "reg_number": "0010",
    }
    fill_diploma_minor(sample, "/tmp/test_minor_fixed.pdf",
                       qr_text="https://ssc.ksu.kz/test/00019006925")
