"""
fill_diploma_minor.py — Заполнение Сертификата Minor (к диплому бакалавра).

Шаблон: diplomas/Сертификат Минор 2025.pdf — горизонтальный (907×638 pt).
На одной странице — три языковых блока (каз / англ / рус), идущих сверху вниз.

Каждый блок содержит:
  • BD № — номер диплома, к которому прилагается сертификат
  • образовательную программу (код и наименование)
  • ФИО выпускника
  • период обучения «с... по...»
  • наименование Minor

Снизу — Тіркеу нөмірі + дата выдачи на казахском, QR-код в правом нижнем углу.
"""

import fitz
import os

try:
    from qr_diploma import insert_qr_on_page
    _QR_AVAILABLE = True
except ImportError:
    _QR_AVAILABLE = False

INPUT_FILE = "diplomas/Сертификат Минор 2025.pdf"

# Шрифты
FONT_CAPTION = "fonts/PTSerifCaption-Regular.ttf"
FONT_BOLD    = "fonts/PTSerif-Bold.ttf"
FONT_BD      = "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf"

COLOR_DARK = (0.106, 0.106, 0.102)
COLOR_GREY = (0.427, 0.431, 0.439)


# ── Линии ───────────────────────────────────────────────────────────────────
# Все Y — baseline нижнего края подчеркивания (text "_" в шаблоне).
# Координаты измерены через page.get_text("dict") → bbox[3] (y_bottom).

# КАЗ блок
LINE_KAZ_BD       = 162.0  # baseline для BD № в верхней части (y из bbox=151-163)
LINE_KAZ_PROGRAM  = 203.2  # программа (длинная)
LINE_KAZ_FIO      = 217.3  # ФИО (правая часть)
LINE_KAZ_DATES    = 231.9  # даты с-по
LINE_KAZ_MINOR    = 246.5  # название Minor

# АНГЛ блок
LINE_ENG_BD       = 300.0  # baseline для BD № (bbox=288-300)
LINE_ENG_FIO      = 324.9  # после Issued to (bbox=314-325)
LINE_ENG_PROGRAM  = 338.8  # программа
LINE_ENG_MINOR    = 352.8  # name of Minor
LINE_ENG_DATES    = 367.5

# РУС блок
LINE_RUS_BD       = 416.0  # baseline для BD № (bbox=404-416)
LINE_RUS_FIO      = 440.8  # после "Выдан"
LINE_RUS_PROGRAM  = 454.7
LINE_RUS_MINOR    = 468.8
LINE_RUS_DATES    = 483.5

# Подписи
LINE_RECTOR       = 548.0
LINE_DEAN         = 566.3
LINE_BOTTOM       = 584.6

# Зона QR (подсказка из шаблона: справа внизу под "QR")
QR_RECT = fitz.Rect(700, 525, 825, 605)


# ── Кэш шрифтов ─────────────────────────────────────────────────────────────
_FONT_CACHE = {}


def _font_buf(path):
    if path not in _FONT_CACHE:
        with open(path, "rb") as f:
            _FONT_CACHE[path] = f.read()
    return _FONT_CACHE[path]


def _fit_size(text, font, base_size, max_width, min_size=6.0):
    if font.text_length(text, fontsize=base_size) <= max_width:
        return base_size
    w = font.text_length(text, fontsize=base_size)
    scaled = base_size * (max_width / w) * 0.98
    return max(scaled, min_size)


def _draw_text(page, text, *, line_x, line_y, size, font_path,
               color=COLOR_DARK, on_underline=True,
               align="center", min_size=6.0, label=""):
    if not str(text).strip():
        return
    text = str(text).strip()
    buf = _font_buf(font_path)
    font = fitz.Font(fontbuffer=buf)
    x0, x1 = line_x
    max_w = x1 - x0
    size = _fit_size(text, font, size, max_w, min_size)

    if on_underline:
        baseline = line_y - 1.5
    else:
        baseline = line_y - 0.5

    text_w = font.text_length(text, fontsize=size)
    if align == "center":
        x = x0 + (max_w - text_w) / 2
    elif align == "right":
        x = x1 - text_w
    else:
        x = x0

    erase_top = baseline - size * 0.95
    erase_bottom = baseline + size * 0.25
    erase_left = max(x0, x - 0.5)
    erase_right = min(x1, x + text_w + 0.5)
    if erase_right > erase_left:
        page.draw_rect(
            fitz.Rect(erase_left, erase_top, erase_right, erase_bottom),
            color=None, fill=(0.969, 0.949, 0.890), overlay=True,
            width=0,
        )
    tw = fitz.TextWriter(page.rect)
    tw.append((x, baseline), text, font=font, fontsize=size)
    tw.write_text(page, color=color)


def _draw_bd_number(page, number, *, line_x, line_y, label="bd_number"):
    """Рисует номер BD в стиле Calibri-Bold (синий цвет шаблона)."""
    if not number:
        return
    text = str(number).strip()
    buf = _font_buf(FONT_BD)
    font = fitz.Font(fontbuffer=buf)
    x0, x1 = line_x
    size = 12.0
    max_w = x1 - x0
    size = _fit_size(text, font, size, max_w, min_size=8.0)

    text_w = font.text_length(text, fontsize=size)
    x = x0 + (max_w - text_w) / 2
    baseline = line_y

    page.draw_rect(
        fitz.Rect(x0 - 0.5, baseline - size * 0.95,
                  x1 + 0.5, baseline + size * 0.25),
        color=None, fill=(0.969, 0.949, 0.890), overlay=True, width=0,
    )
    tw = fitz.TextWriter(page.rect)
    # Цвет — тёмно-синий (как в шаблоне)
    tw.append((x, baseline), text, font=font, fontsize=size)
    tw.write_text(page, color=(0.122, 0.227, 0.541))


def fill_diploma_minor(data, output_path, qr_text=None):
    """Заполняет Сертификат Минор.

    Ожидаемые ключи в data: см. excel_import.parse_minor_import().
    """
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Шаблон не найден: {INPUT_FILE}")

    doc = fitz.open(INPUT_FILE)
    page = doc[0]

    bd_number = (data.get("bd_number") or "").strip()

    # ── 1. КАЗ: BD № в верхней части ───────────────────────────────────────
    if bd_number:
        _draw_bd_number(page, bd_number,
                        line_x=(358.3, 478.3), line_y=LINE_KAZ_BD)

    # ── 2. КАЗ: Программа (длинная линия x=74.8-831.4 по y=193.2) ──────────
    if data.get("program_kaz"):
        _draw_text(page, data["program_kaz"],
                   line_x=(74.8, 831.4), line_y=LINE_KAZ_PROGRAM,
                   size=10.0, font_path=FONT_CAPTION, label="program_kaz")

    # ── 3. КАЗ: ФИО (правая половина строки y=207.2) ───────────────────────
    if data.get("fio_kaz"):
        _draw_text(page, data["fio_kaz"],
                   line_x=(326.4, 831.4), line_y=LINE_KAZ_FIO,
                   size=10.0, font_path=FONT_CAPTION, label="fio_kaz")

    # ── 4. КАЗ: Даты «с-по» ─────────────────────────────────────────────────
    if data.get("from_year_kaz"):
        ys = str(data["from_year_kaz"])[-2:]
        _draw_text(page, ys,
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
        ys = str(data["to_year_kaz"])[-2:]
        _draw_text(page, ys,
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

    # ── 5. КАЗ: Название Minor (длинная линия x=74.8-619.8) ────────────────
    if data.get("minor_kaz"):
        _draw_text(page, data["minor_kaz"],
                   line_x=(74.8, 619.8), line_y=LINE_KAZ_MINOR,
                   size=10.0, font_path=FONT_CAPTION, label="minor_kaz")

    # ── 6. АНГЛ: BD № ──────────────────────────────────────────────────────
    if bd_number:
        _draw_bd_number(page, bd_number,
                        line_x=(468.7, 588.7), line_y=LINE_ENG_BD)

    # ── 7. АНГЛ: ФИО (после Issued to) ─────────────────────────────────────
    if data.get("fio_eng"):
        _draw_text(page, data["fio_eng"],
                   line_x=(113.3, 593.3), line_y=LINE_ENG_FIO,
                   size=10.0, font_path=FONT_CAPTION, label="fio_eng")

    # ── 8. АНГЛ: Программа ─────────────────────────────────────────────────
    if data.get("program_eng"):
        _draw_text(page, data["program_eng"],
                   line_x=(74.8, 831.5), line_y=LINE_ENG_PROGRAM,
                   size=10.0, font_path=FONT_CAPTION, label="program_eng")

    # ── 9. АНГЛ: Название Minor ────────────────────────────────────────────
    if data.get("minor_eng"):
        _draw_text(page, data["minor_eng"],
                   line_x=(261.6, 831.6), line_y=LINE_ENG_MINOR,
                   size=10.0, font_path=FONT_CAPTION, label="minor_eng")

    # ── 10. АНГЛ: Даты «from-to» ───────────────────────────────────────────
    if data.get("from_day_eng"):
        _draw_text(page, data["from_day_eng"],
                   line_x=(152.6, 167.6), line_y=LINE_ENG_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_day_eng")
    if data.get("from_month_eng"):
        _draw_text(page, data["from_month_eng"],
                   line_x=(174.1, 259.1), line_y=LINE_ENG_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_month_eng")
    if data.get("from_year_eng"):
        ys = str(data["from_year_eng"])[-2:]
        _draw_text(page, ys,
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
        ys = str(data["to_year_eng"])[-2:]
        _draw_text(page, ys,
                   line_x=(420.1, 440.1), line_y=LINE_ENG_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="to_year_eng")

    # ── 11. РУС: BD № ──────────────────────────────────────────────────────
    if bd_number:
        _draw_bd_number(page, bd_number,
                        line_x=(474.3, 594.3), line_y=LINE_RUS_BD)

    # ── 12. РУС: ФИО (после "Выдан") ───────────────────────────────────────
    if data.get("fio_rus"):
        _draw_text(page, data["fio_rus"],
                   line_x=(104.4, 554.4), line_y=LINE_RUS_FIO,
                   size=10.0, font_path=FONT_CAPTION, label="fio_rus")

    # ── 13. РУС: Программа ─────────────────────────────────────────────────
    if data.get("program_rus"):
        _draw_text(page, data["program_rus"],
                   line_x=(74.8, 831.6), line_y=LINE_RUS_PROGRAM,
                   size=10.0, font_path=FONT_CAPTION, label="program_rus")

    # ── 14. РУС: Название Minor ────────────────────────────────────────────
    if data.get("minor_rus"):
        _draw_text(page, data["minor_rus"],
                   line_x=(274.5, 831.6), line_y=LINE_RUS_MINOR,
                   size=10.0, font_path=FONT_CAPTION, label="minor_rus")

    # ── 15. РУС: Даты «с-по» ───────────────────────────────────────────────
    if data.get("from_day_rus"):
        _draw_text(page, data["from_day_rus"],
                   line_x=(132.6, 152.6), line_y=LINE_RUS_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_day_rus")
    if data.get("from_month_rus"):
        _draw_text(page, data["from_month_rus"],
                   line_x=(161.8, 236.8), line_y=LINE_RUS_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="from_month_rus")
    if data.get("from_year_rus"):
        ys = str(data["from_year_rus"])[-2:]
        _draw_text(page, ys,
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
        ys = str(data["to_year_rus"])[-2:]
        _draw_text(page, ys,
                   line_x=(441.1, 456.1), line_y=LINE_RUS_DATES,
                   size=10.0, font_path=FONT_CAPTION, label="to_year_rus")

    # ── 16. Нижний блок: Тіркеу нөмірі + дата выдачи ───────────────────────
    if data.get("reg_number"):
        _draw_text(page, data["reg_number"],
                   line_x=(159.1, 204.1), line_y=LINE_BOTTOM,
                   size=10.0, font_path=FONT_CAPTION, label="reg_number")
    if data.get("issue_year"):
        # Год: в шаблоне "202___" — мы заполняем ПОСЛЕДНЮЮ цифру года
        ys = str(data["issue_year"])
        if len(ys) == 4:
            ys = ys[-1]  # последняя цифра ("6" для 2026)
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

    # ── 17. QR-код ─────────────────────────────────────────────────────────
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
        "bd_number": "00002707224",
        "program_kaz": "6B07105 - Көлік, көліктік техника және технологиялар",
        "fio_kaz": "Байтөре Алмат Сейткеримұлына",
        "from_year_kaz": "20", "from_day_kaz": "25", "from_month_kaz": "тамызы",
        "to_year_kaz": "24", "to_day_kaz": "27", "to_month_kaz": "маусымы",
        "minor_kaz": "Автомобильдерді техникалық пайдалану",
        "program_eng": "6B07105-Transport, transport equipment and technologies",
        "fio_eng": "Baitore Almat",
        "from_day_eng": "25", "from_month_eng": "August", "from_year_eng": "20",
        "to_day_eng": "27", "to_month_eng": "June", "to_year_eng": "24",
        "minor_eng": "Technical operation of cars",
        "program_rus": "6B07105 - Транспорт, транспортная техника и технологии",
        "fio_rus": "Байтөре Алмат Сейткеримұлы",
        "from_day_rus": "25", "from_month_rus": "августа", "from_year_rus": "20",
        "to_day_rus": "27", "to_month_rus": "июня", "to_year_rus": "24",
        "minor_rus": "Организация работы железнодорожного транспорта",
        "issue_year": "2026", "issue_day": "05", "issue_month_kaz": "маусым",
        "reg_number": "0010",
    }
    fill_diploma_minor(sample, "/tmp/test_minor_output.pdf",
                       qr_text="https://ssc.ksu.kz/test")
