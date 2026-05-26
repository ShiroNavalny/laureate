"""
fill_diploma_fdo.py — Заполнение Сертификата педагогической переподготовки (ФДО).

Шаблон: diplomas/Сертификат ФДО 2025.pdf — горизонтальный (907×638 pt),
на одной странице — три языковых блока (каз / рус / англ), идущих сверху вниз.

Каждый блок содержит:
  • дату заседания Аттестационной комиссии (день, месяц, год, № протокола)
  • ФИО и период обучения «с... по...»
  • образовательную программу и количество кредитов

Сверху — серия и номер сертификата (CPR № …),
снизу — Тіркеу нөмірі + дата выдачи на казахском.
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
    # Fallback если font_utils.py отсутствует
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
    """Ищем чистый шаблон в нескольких типовых местах.

    Тест по умолчанию запускается из laureate_test/, но рабочие чистые шаблоны
    лежат в laureate/diplomas/. Если кто-то положил шаблон рядом в diplomas/ —
    берём оттуда; иначе спускаемся к sibling-проекту laureate.
    """
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
    # Возвращаем первый кандидат — fill_diploma_fdo() сам выкинет FileNotFoundError
    return candidates[0]


INPUT_FILE = _resolve_template(
    "diplomas/Сертификат ФДО 2025.pdf",
)

COLOR_DARK = (0.106, 0.106, 0.102)
COLOR_GREY = (0.427, 0.431, 0.439)

PAD = 0.25   # отступ при редактировании (не задеваем рамку)

# ── Линии (точные координаты из анализа шаблона) ────────────────────────────

LINE_CPR_NUMBER = 207.0   # baseline для номера CPR

# КАЗ блок
LINE_KAZ_COUNCIL = 242.8
LINE_KAZ_FIO     = 261.7
LINE_KAZ_PROGRAM = 281.3
LINE_KAZ_CREDITS = 301.1

# РУС блок
LINE_RUS_COUNCIL = 345.2
LINE_RUS_FIO     = 362.7
LINE_RUS_PROGRAM = 396.4

# АНГЛ блок
LINE_ENG_COUNCIL = 446.1
LINE_ENG_FIO     = 463.0
LINE_ENG_PROGRAM = 496.7

# Нижний блок
LINE_BOTTOM = 587.4


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
    w = font.text_length(text, fontsize=base_size)
    return max(base_size * (max_width / w) * 0.98, min_size)


def _draw_text(page, text, *, line_x, line_y, size, font_path,
               color=COLOR_DARK, on_underline=True,
               align="center", min_size=6.0, label=""):
    """
    Рисует текст в заданной зоне с корректной очисткой через redact.

    on_underline=True  — baseline = line_y - 1.5  (текст стоит НА «____»)
    on_underline=False — baseline = line_y - 0.5  (обычная графическая линия)
    align: 'center' | 'left' | 'right'
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

    # ── Erase через redaction (чисто, без цветных прямоугольников) ───────────
    erase_top = baseline - size * 0.95
    erase_bot = baseline + size * 0.20
    erase_l = max(x0 + PAD, x - 0.5)
    erase_r = min(x1 - PAD, x + text_w + 0.5)
    if erase_r > erase_l:
        page.add_redact_annot(
            fitz.Rect(erase_l, erase_top, erase_r, erase_bot),
            fill=None   # прозрачно — удаляет контент, не рисует фон
        )
        page.apply_redactions(graphics=0)  # graphics=0 — НЕ трогает рамки/линии

    # ── Вставляем текст ──────────────────────────────────────────────────────
    tw = fitz.TextWriter(page.rect)
    tw.append((x, baseline), text, font=font, fontsize=size)
    tw.write_text(page, color=color)


def fill_diploma_fdo(data, output_path, qr_text=None):
    """Заполняет Сертификат ФДО."""
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Шаблон не найден: {INPUT_FILE}")

    doc = fitz.open(INPUT_FILE)
    page = doc[0]

    # ── 1. Серия и номер сертификата (CPR № 00000000000) ─────────────────────
    cert_series = (data.get("cert_series") or "CPR").strip()
    cert_number = (data.get("cert_number") or "").strip()

    if cert_number:
        # Стираем старый номер через redact
        page.add_redact_annot(fitz.Rect(360, 196, 560, 213), fill=None)
        page.apply_redactions(graphics=0)

        buf = _font_buf(FONT_BD)
        font = fitz.Font(fontbuffer=buf)
        full_text = f"{cert_series} № {cert_number}"
        size = 12.0
        text_w = font.text_length(full_text, fontsize=size)
        x = 453.5 - text_w / 2
        tw = fitz.TextWriter(page.rect)
        tw.append((x, LINE_CPR_NUMBER), full_text, font=font, fontsize=size)
        tw.write_text(page, color=COLOR_GREY)

    # ── 2. КАЗ: заседание совета ─────────────────────────────────────────────
    # «…20___ жылғы «___» __________ шешімімен (№___ хаттама)»
    if data.get("council_year_kaz"):
        year = str(data["council_year_kaz"])[-2:]
        _draw_text(page, year,
                   line_x=(380.3, 397.4), line_y=LINE_KAZ_COUNCIL,
                   size=9.0, font_path=FONT_CAPTION, label="council_year_kaz")
    if data.get("council_day_kaz"):
        _draw_text(page, data["council_day_kaz"],
                   line_x=(433.6, 458.0), line_y=LINE_KAZ_COUNCIL,
                   size=9.0, font_path=FONT_CAPTION, label="council_day_kaz")
    if data.get("council_month_kaz"):
        _draw_text(page, data["council_month_kaz"],
                   line_x=(463.3, 540.7), line_y=LINE_KAZ_COUNCIL,
                   size=9.0, font_path=FONT_CAPTION, label="council_month_kaz")
    if data.get("protocol_kaz"):
        _draw_text(page, data["protocol_kaz"],
                   line_x=(601.4, 615.2), line_y=LINE_KAZ_COUNCIL,
                   size=9.0, font_path=FONT_CAPTION, label="protocol_kaz")

    # ── 3. КАЗ: ФИО + период «с-по» ─────────────────────────────────────────
    if data.get("fio_kaz"):
        _draw_text(page, data["fio_kaz"],
                   line_x=(143.8, 464.9), line_y=LINE_KAZ_FIO,
                   size=10.0, font_path=FONT_CAPTION, label="fio_kaz")
    if data.get("from_day_kaz"):
        _draw_text(page, data["from_day_kaz"],
                   line_x=(473.9, 491.6), line_y=LINE_KAZ_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="from_day_kaz")
    if data.get("from_month_kaz"):
        _draw_text(page, data["from_month_kaz"],
                   line_x=(498.0, 556.4), line_y=LINE_KAZ_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="from_month_kaz")
    if data.get("from_year_kaz") or data.get("issue_year"):
        ys = str(data.get("from_year_kaz") or data.get("issue_year") or "")[-2:]
        _draw_text(page, ys,
                   line_x=(566.5, 580.1), line_y=LINE_KAZ_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="from_year_kaz")
    if data.get("to_day_kaz"):
        _draw_text(page, data["to_day_kaz"],
                   line_x=(598.9, 616.6), line_y=LINE_KAZ_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="to_day_kaz")
    if data.get("to_month_kaz"):
        _draw_text(page, data["to_month_kaz"],
                   line_x=(623.0, 681.4), line_y=LINE_KAZ_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="to_month_kaz")
    if data.get("to_year_kaz") or data.get("issue_year"):
        ys = str(data.get("to_year_kaz") or data.get("issue_year") or "")[-2:]
        _draw_text(page, ys,
                   line_x=(691.5, 705.1), line_y=LINE_KAZ_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="to_year_kaz")

    # ── 4. КАЗ: программа + кредиты ─────────────────────────────────────────
    if data.get("program_kaz"):
        _draw_text(page, data["program_kaz"],
                   line_x=(143.8, 588.0), line_y=LINE_KAZ_PROGRAM,
                   size=9.5, font_path=FONT_CAPTION, label="program_kaz")
    if data.get("credits_kaz"):
        _draw_text(page, data["credits_kaz"],
                   line_x=(419.6, 459.7), line_y=LINE_KAZ_CREDITS,
                   size=9.0, font_path=FONT_CAPTION,
                   on_underline=False, label="credits_kaz")

    # ── 5. РУС: заседание совета ─────────────────────────────────────────────
    if data.get("council_day_rus"):
        _draw_text(page, data["council_day_rus"],
                   line_x=(358.2, 376.4), line_y=LINE_RUS_COUNCIL,
                   size=9.0, font_path=FONT_CAPTION, label="council_day_rus")
    if data.get("council_month_rus"):
        _draw_text(page, data["council_month_rus"],
                   line_x=(381.1, 445.7), line_y=LINE_RUS_COUNCIL,
                   size=9.0, font_path=FONT_CAPTION, label="council_month_rus")
    if data.get("council_year_rus"):
        ys = str(data["council_year_rus"])[-2:]
        _draw_text(page, ys,
                   line_x=(455.9, 469.5), line_y=LINE_RUS_COUNCIL,
                   size=9.0, font_path=FONT_CAPTION, label="council_year_rus")
    if data.get("protocol_rus"):
        _draw_text(page, data["protocol_rus"],
                   line_x=(545.0, 562.0), line_y=LINE_RUS_COUNCIL,
                   size=9.0, font_path=FONT_CAPTION, label="protocol_rus")

    # ── 6. РУС: ФИО + период ─────────────────────────────────────────────────
    if data.get("fio_rus"):
        _draw_text(page, data["fio_rus"],
                   line_x=(143.8, 520.2), line_y=LINE_RUS_FIO,
                   size=10.0, font_path=FONT_CAPTION, label="fio_rus")
    if data.get("from_day_rus"):
        _draw_text(page, data["from_day_rus"],
                   line_x=(531.6, 549.2), line_y=LINE_RUS_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="from_day_rus")
    if data.get("from_month_rus"):
        _draw_text(page, data["from_month_rus"],
                   line_x=(554.3, 607.2), line_y=LINE_RUS_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="from_month_rus")
    if data.get("from_year_rus") or data.get("issue_year"):
        ys = str(data.get("from_year_rus") or data.get("issue_year") or "")[-2:]
        _draw_text(page, ys,
                   line_x=(616.9, 632.9), line_y=LINE_RUS_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="from_year_rus")
    if data.get("to_day_rus"):
        _draw_text(page, data["to_day_rus"],
                   line_x=(658.0, 675.2), line_y=LINE_RUS_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="to_day_rus")
    if data.get("to_month_rus"):
        _draw_text(page, data["to_month_rus"],
                   line_x=(681.3, 733.0), line_y=LINE_RUS_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="to_month_rus")
    if data.get("to_year_rus") or data.get("issue_year"):
        ys = str(data.get("to_year_rus") or data.get("issue_year") or "")[-2:]
        _draw_text(page, ys,
                   line_x=(743.5, 758.0), line_y=LINE_RUS_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="to_year_rus")

    # ── 7. РУС: программа + кредиты ─────────────────────────────────────────
    if data.get("program_rus"):
        _draw_text(page, data["program_rus"],
                   line_x=(143.8, 656.5), line_y=LINE_RUS_PROGRAM,
                   size=9.5, font_path=FONT_CAPTION, label="program_rus")
    if data.get("credits_rus"):
        _draw_text(page, data["credits_rus"],
                   line_x=(695.2, 724.9), line_y=LINE_RUS_PROGRAM,
                   size=9.0, font_path=FONT_CAPTION, label="credits_rus")

    # ── 8. АНГЛ: заседание комиссии ──────────────────────────────────────────
    if data.get("council_day_eng"):
        _draw_text(page, data["council_day_eng"],
                   line_x=(407.2, 425.4), line_y=LINE_ENG_COUNCIL,
                   size=9.0, font_path=FONT_CAPTION, label="council_day_eng")
    if data.get("council_month_eng"):
        _draw_text(page, data["council_month_eng"],
                   line_x=(431.6, 496.2), line_y=LINE_ENG_COUNCIL,
                   size=9.0, font_path=FONT_CAPTION, label="council_month_eng")
    if data.get("council_year_eng"):
        ys = str(data["council_year_eng"])[-2:]
        _draw_text(page, ys,
                   line_x=(509.3, 522.8), line_y=LINE_ENG_COUNCIL,
                   size=9.0, font_path=FONT_CAPTION, label="council_year_eng")

    # ── 9. АНГЛ: ФИО + период ────────────────────────────────────────────────
    if data.get("fio_eng"):
        _draw_text(page, data["fio_eng"],
                   line_x=(143.8, 515.7), line_y=LINE_ENG_FIO,
                   size=10.0, font_path=FONT_CAPTION, label="fio_eng")
    if data.get("from_day_eng"):
        _draw_text(page, data["from_day_eng"],
                   line_x=(542.8, 560.4), line_y=LINE_ENG_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="from_day_eng")
    if data.get("from_month_eng"):
        _draw_text(page, data["from_month_eng"],
                   line_x=(565.7, 602.3), line_y=LINE_ENG_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="from_month_eng")
    if data.get("from_year_eng") or data.get("issue_year"):
        ys = str(data.get("from_year_eng") or data.get("issue_year") or "")[-2:]
        _draw_text(page, ys,
                   line_x=(612.7, 628.7), line_y=LINE_ENG_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="from_year_eng")
    if data.get("to_day_eng"):
        _draw_text(page, data["to_day_eng"],
                   line_x=(662.3, 679.5), line_y=LINE_ENG_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="to_day_eng")
    if data.get("to_month_eng"):
        _draw_text(page, data["to_month_eng"],
                   line_x=(685.5, 722.0), line_y=LINE_ENG_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="to_month_eng")
    if data.get("to_year_eng") or data.get("issue_year"):
        ys = str(data.get("to_year_eng") or data.get("issue_year") or "")[-2:]
        _draw_text(page, ys,
                   line_x=(733.6, 748.0), line_y=LINE_ENG_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="to_year_eng")

    # ── 10. АНГЛ: программа + кредиты ────────────────────────────────────────
    if data.get("program_eng"):
        _draw_text(page, data["program_eng"],
                   line_x=(143.8, 638.5), line_y=LINE_ENG_PROGRAM,
                   size=9.5, font_path=FONT_CAPTION, label="program_eng")
    if data.get("credits_eng"):
        _draw_text(page, data["credits_eng"],
                   line_x=(705.1, 734.8), line_y=LINE_ENG_PROGRAM,
                   size=9.0, font_path=FONT_CAPTION, label="credits_eng")

    # ── 11. Нижний блок: Тіркеу нөмірі + дата ────────────────────────────────
    if data.get("reg_number"):
        _draw_text(page, data["reg_number"],
                   line_x=(270.7, 341.2), line_y=LINE_BOTTOM,
                   size=9.0, font_path=FONT_CAPTION, label="reg_number")
    if data.get("issue_year"):
        _draw_text(page, str(data["issue_year"]),
                   line_x=(378.4, 412.1), line_y=LINE_BOTTOM,
                   size=9.0, font_path=FONT_CAPTION, label="issue_year")
    if data.get("issue_day"):
        _draw_text(page, data["issue_day"],
                   line_x=(448.4, 465.6), line_y=LINE_BOTTOM,
                   size=9.0, font_path=FONT_CAPTION, label="issue_day")
    if data.get("issue_month_kaz"):
        _draw_text(page, data["issue_month_kaz"],
                   line_x=(473.0, 528.6), line_y=LINE_BOTTOM,
                   size=9.0, font_path=FONT_CAPTION, label="issue_month_kaz")
    _draw_text(page, "Қарағанды",
               line_x=(584.8, 679.8), line_y=LINE_BOTTOM,
               size=9.0, font_path=FONT_CAPTION, align="right", label="city")

    # ── 12. QR (опционально) ─────────────────────────────────────────────────
    if qr_text and qr_text.strip() and _QR_AVAILABLE:
        QR_RECT = fitz.Rect(750, 525, 825, 600)
        try:
            insert_qr_on_page(page, qr_text.strip(), rect=QR_RECT)
        except Exception:
            pass

    doc.save(output_path, garbage=4, deflate=True, deflate_images=True,
             deflate_fonts=True, clean=True)
    doc.close()
    print(f"✓ Сохранено → {output_path} (тип: ФДО)")


if __name__ == "__main__":
    sample = {
        "cert_series": "CPR",
        "cert_number": "00000626724",
        "reg_number": "0004",
        "council_day_kaz": "01", "council_month_kaz": "маусымдағы",
        "council_year_kaz": "2024", "protocol_kaz": "02",
        "fio_kaz": "Даншина Светлана Анатольевна",
        "from_day_kaz": "15", "from_month_kaz": "қаңтар",
        "from_year_kaz": "24",
        "to_day_kaz": "01", "to_month_kaz": "маусым",
        "to_year_kaz": "24",
        "program_kaz": "\"6B01705-Шетел тілі: екі шет тілі (ағылшын)\"",
        "credits_kaz": "40",
        "council_day_rus": "01", "council_month_rus": "июня",
        "council_year_rus": "2024", "protocol_rus": "02",
        "fio_rus": "Даншиной Светлане Анатольевне",
        "from_day_rus": "15", "from_month_rus": "января",
        "from_year_rus": "24",
        "to_day_rus": "01", "to_month_rus": "июня",
        "to_year_rus": "24",
        "program_rus": "\"6B01705-Иностранный язык: два иностранных языка (английский)\"",
        "credits_rus": "40",
        "council_day_eng": "01", "council_month_eng": "june",
        "council_year_eng": "2024",
        "fio_eng": "Danshina Svetlana",
        "from_day_eng": "15", "from_month_eng": "January",
        "from_year_eng": "24",
        "to_day_eng": "01", "to_month_eng": "June",
        "to_year_eng": "24",
        "program_eng": "\"6B01705-Foreign language: two foreign languages (English)\"",
        "credits_eng": "40",
        "issue_year": "2024", "issue_day": "05", "issue_month_kaz": "маусым",
    }
    fill_diploma_fdo(sample, "/tmp/test_fdo_fixed.pdf")
    print("Test done → /tmp/test_fdo_fixed.pdf")
