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

Автор: для проекта «Лауреат» / КарУ.
"""

import fitz
import os

try:
    from qr_diploma import insert_qr_on_page
    _QR_AVAILABLE = True
except ImportError:
    _QR_AVAILABLE = False

INPUT_FILE = "diplomas/Сертификат ФДО 2025.pdf"

# Шрифты
FONT_CAPTION = "fonts/PTSerifCaption-Regular.ttf"
FONT_BOLD    = "fonts/PTSerif-Bold.ttf"
# Номер CPR в шаблоне в Calibri-Light. Carlito — open-source аналог Calibri.
FONT_BD      = "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf"

COLOR_DARK = (0.106, 0.106, 0.102)
COLOR_GREY = (0.427, 0.431, 0.439)

BASELINE_OFFSET = -0.5

# ── Линии (точные координаты из анализа шаблона) ───────────────────────────

# Номер CPR — в верхней части
LINE_CPR_NUMBER = 207.0   # baseline для номера

# КАЗ блок
LINE_KAZ_COUNCIL = 242.8   # заседание совета
LINE_KAZ_FIO     = 261.7   # ФИО + дата с-по
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

# Нижний блок (Тіркеу нөмірі)
LINE_BOTTOM = 587.4


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
    """Рисует текст внутри подчёркиваемой зоны.

    on_underline=True (для ФДО — почти всегда True) — baseline = y - 1.5
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

    if on_underline:
        baseline = line_y - 1.5
    else:
        baseline = line_y + BASELINE_OFFSET

    text_w = font.text_length(text, fontsize=size)
    if align == "center":
        x = x0 + (max_w - text_w) / 2
    elif align == "right":
        x = x1 - text_w
    else:
        x = x0

    # Erase: накрываем подчеркивающую черту белым прямоугольником,
    # чтобы текст «ехал» поверх — но только под текстом, не всю линию.
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


def fill_diploma_fdo(data, output_path, qr_text=None):
    """Заполняет Сертификат ФДО.

    Ожидаемые ключи в data: см. excel_import.parse_fdo_import().
    """
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Шаблон не найден: {INPUT_FILE}")

    doc = fitz.open(INPUT_FILE)
    page = doc[0]

    # ── 1. Серия и номер сертификата (CPR № 00000000000) ───────────────────
    cert_series = (data.get("cert_series") or "CPR").strip()
    cert_number = (data.get("cert_number") or "").strip()

    if cert_number:
        # В шаблоне уже есть готовый текст "CPR № 00000000000" — закрашиваем
        # эту зону и пишем свой.
        page.draw_rect(
            fitz.Rect(395, 196, 515, 213),
            color=None, fill=(0.969, 0.949, 0.890),
            overlay=True, width=0,
        )
        buf = _font_buf(FONT_BD)
        font = fitz.Font(fontbuffer=buf)
        full_text = f"{cert_series} № {cert_number}"
        size = 12.0
        # центрируем относительно центра шаблона (453.5)
        text_w = font.text_length(full_text, fontsize=size)
        x = 453.5 - text_w / 2
        tw = fitz.TextWriter(page.rect)
        tw.append((x, 207.5), full_text, font=font, fontsize=size)
        tw.write_text(page, color=COLOR_GREY)

    # ── 2. КАЗ блок: заседание совета ──────────────────────────────────────
    # Аттестаттау комиссиясының 20___ жылғы «___» __________ шешімімен (№___ хаттама)
    if data.get("council_year_kaz"):
        # Год — последние 2 цифры
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

    # ── 3. КАЗ блок: ФИО + период «с-по» ───────────────────────────────────
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
    # год — после "20" видно из шаблона "20___" — это 2 цифры
    if data.get("issue_year") or data.get("from_year_kaz"):
        # Берем 2 последние цифры от issue_year (год выдачи) или from_year_kaz
        ys = str(data.get("from_year_kaz") or data.get("issue_year") or "")
        ys = ys[-2:] if len(ys) >= 2 else ys
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
    if data.get("issue_year") or data.get("to_year_kaz"):
        ys = str(data.get("to_year_kaz") or data.get("issue_year") or "")
        ys = ys[-2:] if len(ys) >= 2 else ys
        _draw_text(page, ys,
                   line_x=(691.5, 705.1), line_y=LINE_KAZ_FIO,
                   size=9.0, font_path=FONT_CAPTION, label="to_year_kaz")

    # ── 4. КАЗ блок: программа + кредиты ───────────────────────────────────
    if data.get("program_kaz"):
        _draw_text(page, data["program_kaz"],
                   line_x=(143.8, 588.0), line_y=LINE_KAZ_PROGRAM,
                   size=9.5, font_path=FONT_CAPTION, label="program_kaz")
    if data.get("credits_kaz"):
        _draw_text(page, data["credits_kaz"],
                   line_x=(419.6, 459.7), line_y=LINE_KAZ_CREDITS,
                   size=9.0, font_path=FONT_CAPTION,
                   on_underline=False,
                   label="credits_kaz")

    # ── 5. РУС блок: заседание совета ──────────────────────────────────────
    # от «___» __________ 20___ года (протокол №___)
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

    # ── 6. РУС блок: ФИО + период «с-по» ───────────────────────────────────
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

    # ── 7. РУС блок: программа + кредиты ───────────────────────────────────
    if data.get("program_rus"):
        _draw_text(page, data["program_rus"],
                   line_x=(143.8, 656.5), line_y=LINE_RUS_PROGRAM,
                   size=9.5, font_path=FONT_CAPTION, label="program_rus")
    if data.get("credits_rus"):
        _draw_text(page, data["credits_rus"],
                   line_x=(695.2, 724.9), line_y=LINE_RUS_PROGRAM,
                   size=9.0, font_path=FONT_CAPTION, label="credits_rus")

    # ── 8. АНГЛ блок: заседание совета ─────────────────────────────────────
    # Date «___» __________ 20___
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

    # ── 9. АНГЛ блок: ФИО + период «from-to» ───────────────────────────────
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

    # ── 10. АНГЛ блок: программа + кредиты ─────────────────────────────────
    if data.get("program_eng"):
        _draw_text(page, data["program_eng"],
                   line_x=(143.8, 638.5), line_y=LINE_ENG_PROGRAM,
                   size=9.5, font_path=FONT_CAPTION, label="program_eng")
    if data.get("credits_eng"):
        _draw_text(page, data["credits_eng"],
                   line_x=(705.1, 734.8), line_y=LINE_ENG_PROGRAM,
                   size=9.0, font_path=FONT_CAPTION, label="credits_eng")

    # ── 11. Нижний блок: Тіркеу нөмірі + дата выдачи ───────────────────────
    # Тіркеу нөмірі ___ ___ жылғы «___» ___________ ___ қ.
    if data.get("reg_number"):
        _draw_text(page, data["reg_number"],
                   line_x=(270.7, 341.2), line_y=LINE_BOTTOM,
                   size=9.0, font_path=FONT_CAPTION, label="reg_number")
    if data.get("issue_year"):
        # год выдачи (4 цифры) — линия x=378.4-412.1
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
    # Город — пишем "Қарағанды" перед "қ." на линии x=584.8-679.8
    _draw_text(page, "Қарағанды",
               line_x=(584.8, 679.8), line_y=LINE_BOTTOM,
               size=9.0, font_path=FONT_CAPTION, align="right", label="city")

    # ── 12. QR (опционально) ───────────────────────────────────────────────
    if qr_text and qr_text.strip() and _QR_AVAILABLE:
        # У ФДО нет специального места для QR; помещаем в правый нижний угол
        # рядом с подписями.
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
    # Пример теста
    sample = {
        "cert_series": "CPR",
        "cert_number": "00000627324",
        "reg_number": "0010",
        "council_day_kaz": "01", "council_month_kaz": "маусымдағы",
        "council_year_kaz": "2025", "protocol_kaz": "02",
        "fio_kaz": "Юлдашева София Малкайдаровна",
        "from_day_kaz": "15", "from_month_kaz": "қаңтар",
        "to_day_kaz": "01", "to_month_kaz": "маусым",
        "program_kaz": "6B01705-Шетел тілі: екі шет тілі (ағылшын)",
        "credits_kaz": "40",
        "council_day_rus": "01", "council_month_rus": "июня",
        "council_year_rus": "2025", "protocol_rus": "02",
        "fio_rus": "Юлдашева София Малкайдаровна",
        "from_day_rus": "15", "from_month_rus": "января",
        "to_day_rus": "01", "to_month_rus": "июня",
        "program_rus": "6B01705-Иностранный язык: два иностранных языка (английский)",
        "credits_rus": "40",
        "council_day_eng": "01", "council_month_eng": "june",
        "council_year_eng": "2025",
        "fio_eng": "Yuldasheva Sofiya",
        "from_day_eng": "15", "from_month_eng": "January",
        "to_day_eng": "01", "to_month_eng": "June",
        "program_eng": "6B01705-Foreign language: two foreign languages (English)",
        "credits_eng": "40",
        "issue_year": "2025", "issue_day": "05", "issue_month_kaz": "маусым",
    }
    fill_diploma_fdo(sample, "/tmp/test_fdo_output.pdf")
