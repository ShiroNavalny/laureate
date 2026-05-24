"""
fill_diploma_phd.py — Заполнение диплома доктора PhD КарУ.

Структура шаблона совершенно отличается от бакалавра/магистра:
  • 3 параллельные колонки (kaz / eng / rus), каждая ~227pt шириной
  • В каждой колонке: дата совета, дата приказа, фамилия, имя+отчество,
    программа, тема диссертации (2 строки), научные консультанты (2 строки),
    официальные рецензенты (2 строки), место защиты (2 строки), дата защиты
  • Внизу: серия диплома, PhD №, рег. номер (НЕ заполняем),
    дата выдачи (год/день/месяц), QR (СЛЕВА, не справа!)

Отдельный модуль т.к. геометрия принципиально другая.

Зависимости и шрифты — те же, что у fill_diploma.py для бакалавра.
"""

import fitz
import os
import sys

try:
    from qr_diploma import insert_qr_on_page, generate_qr_image
    _QR_AVAILABLE = True
except ImportError:
    _QR_AVAILABLE = False

_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_template(name: str) -> str:
    """Ищем шаблон в diplomas/ рядом со скриптом, затем в ../laureate/diplomas/."""
    for base in (_DIR, os.path.join(_DIR, "..", "laureate")):
        p = os.path.join(base, "diplomas", name)
        if os.path.exists(p):
            return os.path.abspath(p)
    return os.path.join("diplomas", name)


INPUT_FILE = _resolve_template("ДИПЛОМ_докторанта_2025.pdf")

# Шрифты (те же, что для бакалавра)
# ── Шрифты: приоритет 1 — папка fonts/, 2 — системные paratype ──────────
def _resolve_font(local_name, system_path):
    _dir = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(_dir, "fonts", local_name)
    return local if os.path.exists(local) else system_path

FONT_CAPTION = _resolve_font("PTSerifCaption-Regular.ttf",
                              "/usr/share/fonts/truetype/paratype/PTZ55F.ttf")
FONT_BOLD    = _resolve_font("PTSerif-Bold.ttf",
                              "/usr/share/fonts/truetype/paratype/PTF75F.ttf")


def _find_first(paths, fallback):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return fallback


FONT_BD = _find_first([
    "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
], FONT_BOLD)

COLOR_DARK = (0.106, 0.106, 0.102)
COLOR_GREY = (0.427, 0.431, 0.439)

# Border-padding для erase_bbox (отступ от границ линии вовнутрь)
PAD = 0.25

# baseline = line_y + BASELINE_OFFSET
BASELINE_OFFSET = -0.5

def bl(line_y: float) -> float:
    return line_y + BASELINE_OFFSET


def bl_underline(underline_bottom_y: float) -> float:
    """
    Baseline для текста, который пишется НА текстовой линии подчёркивания.
    Эмпирически: baseline = bottom - 1.5pt — цифры стоят чуть выше нижнего
    края `_____` (визуально совпадают с цифрами в шаблонах строки совета).
    """
    return underline_bottom_y - 1.5


# ── Координаты колонок ──────────────────────────────────────────────────────
COL_KAZ = (76.33, 303.11)
COL_ENG = (339.33, 566.11)
COL_RUS = (604.20, 830.97)

# ── Линии в верхней части каждой колонки (порядок РАЗНЫЙ для каждого языка!) ─
#
# KAZ структура (сверху вниз, как в шаблоне):
#   235.77 → фамилия       лейбл (тегі)            на y=236.55
#   255.61 → имя+отчество  лейбл (аты, әкесінің)   на y=256.39
#   272.94 → программа 1   лейбл (мамандығы)       на y=273.71
#   289.95 → программа 2   (без лейбла, для длинных)
#   ... заголовок «ФИЛОСОФИЯ ДОКТОРЫ (PhD)» y≈310-325 ...
#
# RUS структура:
#   235.77 → фамилия       лейбл (фамилия)
#   255.61 → имя+отчество  лейбл (имя, отчество)
#   ... заголовок «присуждена степень / ДОКТОРА ФИЛОСОФИИ / по специальности» y≈265-289 ...
#   312.62 → программа 1   (без лейбла)
#   329.63 → программа 2   лейбл (код и наименование) под на y=330.40
#
# ENG структура — ЗЕРКАЛЬНАЯ относительно kaz/rus:
#   235.77 → программа 1   лейбл (code and name)
#   253.06 → программа 2   (без лейбла)
#   ... заголовок «the specialty / DOCTOR of PHILOSOPHY / degree is conferred on» y≈258-280 ...
#   309.47 → фамилия       лейбл (surname)
#   329.32 → имя+отчество  лейбл (first name)

LINE_KAZ_SURNAME    = 235.77
LINE_KAZ_FIRSTNAME  = 255.61
LINE_KAZ_PROG_1     = 272.94
LINE_KAZ_PROG_2     = 289.95

LINE_RUS_SURNAME    = 235.77
LINE_RUS_FIRSTNAME  = 255.61
LINE_RUS_PROG_1     = 312.62
LINE_RUS_PROG_2     = 329.63

LINE_ENG_PROG_1     = 235.77
LINE_ENG_PROG_2     = 253.06
LINE_ENG_SURNAME    = 309.47
LINE_ENG_FIRSTNAME  = 329.32

# Эти 9 линий ОДИНАКОВЫ во всех 3 колонках (y совпадает):
LINE_DISSERT_1   = 346.64    # тема диссертации, строка 1
LINE_DISSERT_MID = 355.14    #                    строка 2 (середина)
LINE_DISSERT_2   = 363.65    #                    строка 3
LINE_CONSULT_1   = 380.65    # научные консультанты, строка 1
LINE_CONSULT_MID = 389.15    #                       строка 2 (середина)
LINE_CONSULT_2   = 397.66    #                       строка 3
LINE_REVIEW_1    = 414.67    # официальные рецензенты, строка 1
LINE_REVIEW_MID  = 423.17    #                         строка 2 (середина)
LINE_REVIEW_2    = 431.68    #                         строка 3
LINE_PLACE_1     = 448.69    # место защиты, строка 1
LINE_PLACE_2     = 465.69    #                строка 2
LINE_DATE_DEF    = 482.70    # дата защиты

# Линии в верхней части (даты совета и приказа):
# каз: 195.55 (y совета), 208.00 (y приказа)
# для англ/рус — те же y. Но координаты x (где конкретно даты внутри строки)
# различаются — буду заполнять их отдельно.

# ── Дата заседания совета (одна строка с 4 полями: год, день, месяц) ────────
# Каз: «_____ жылғы «___» ____________ шешімімен»
#       год: x=89.7-115.2,  день: x=154.6-169.9,  месяц: x=177.5-238.7
# Англ: «dated «___» ___________ ____ year»
#       день: x=408.7-424.0, месяц: x=431.6-474, год: x=477-510.6
# Рус: «от «___» ___________ ____ года»
#       день: x=664.6-679.9, месяц: x=687.5-735, год: x=740-766.5

# ── Дата приказа (вторая строка с 5 полями: №, год, день, месяц, год2) ──────
# Каз: «(_____ жылғы «___» _____________ № ____ бұйрық)»
#       год1: x=77.4-102.9, день: x=142.4-157.7, месяц: x=165.2-234.1, №: x=246.8-267.2
# Англ: «(Order № _____ dated «___» ___________ ____ year)»
#       №: x=383.0-408.5, день: x=442.3-457.6, месяц: x=465.1-510, год: x=515-544.1
# Рус: «(Приказ № _____ от «___» ___________ ____ года)»
#       №: x=657.0-682.5, день: x=701.6-716.9, месяц: x=724.4-780.5, год: x=782.9-803.3

# ── Нижний блок ─────────────────────────────────────────────────────────────
LINE_BD_NUMBER  = 539.36   # PhD № — стоит справа внизу (16.32pt, серый)
LINE_TIRKEU     = 553.77   # Тіркеу нөмірі — НЕ заполняем (от руки)
LINE_OUT_YEAR   = 578.59   # год выдачи (правый блок, x=688.95-722.59)
LINE_OUT_DAY    = 578.59   # день выдачи (x=758.97-776.16)
LINE_OUT_MONTH  = 578.59   # месяц выдачи (x=783.49-825.21)
# Города в шаблоне уже есть «Қарағанды қ.» текстом — не заполняем

# QR-зона в докторанте ДРУГАЯ, чем в бакалавре!
QR_RECT_PHD = fitz.Rect(99.01, 494.96, 206.73, 602.68)   # 107.72 × 107.72 pt


# ── Кэш шрифтов ─────────────────────────────────────────────────────────────
_FONT_CACHE = {}

def _font_buf(path):
    if path not in _FONT_CACHE:
        with open(path, "rb") as f:
            _FONT_CACHE[path] = f.read()
    return _FONT_CACHE[path]


# ── Layout: разбивка длинного текста на 2 строки ────────────────────────────
def _try_wrap_2(text, font, size, max_width, min_size=6.0):
    """Разбивка по запятой (предпочтительно) или пробелу на 2 строки.
    Перебирает размеры шрифта от `size` до `min_size`, чтобы для длинных
    подписей (напр. полное название университета) подобрать максимальный
    шрифт, при котором обе строки влезают в колонку.
    """
    def fits_at(s, sz): return font.text_length(s, fontsize=sz) <= max_width
    sizes = []
    s = size
    while s >= min_size - 1e-6:
        sizes.append(round(s, 2))
        s -= 0.5
    for sz in sizes:
        candidates = []
        # Приоритет: разбивка по `;` (для программ и пр. перечислений),
        # затем по `,`, затем по пробелам.
        if ";" in text:
            parts = text.split(";")
            for i in range(1, len(parts)):
                left  = ";".join(parts[:i]).rstrip() + ";"
                right = ";".join(parts[i:]).lstrip()
                if left and right and fits_at(left, sz) and fits_at(right, sz):
                    score = max(font.text_length(left, fontsize=sz),
                                font.text_length(right, fontsize=sz))
                    candidates.append((score, left, right))
        if "," in text:
            parts = text.split(",")
            for i in range(1, len(parts)):
                left  = ",".join(parts[:i]).rstrip() + ","
                right = ",".join(parts[i:]).lstrip()
                if left and right and fits_at(left, sz) and fits_at(right, sz):
                    score = max(font.text_length(left, fontsize=sz),
                                font.text_length(right, fontsize=sz))
                    candidates.append((score, left, right))
        words = text.split(" ")
        if len(words) > 1:
            for i in range(1, len(words)):
                left  = " ".join(words[:i])
                right = " ".join(words[i:])
                if fits_at(left, sz) and fits_at(right, sz):
                    score = max(font.text_length(left, fontsize=sz),
                                font.text_length(right, fontsize=sz))
                    candidates.append((score, left, right))
        if candidates:
            candidates.sort(key=lambda c: c[0])
            return [candidates[0][1], candidates[0][2], sz]
    return None


def _try_wrap_3(text, font, size, max_width):
    """
    Оптимальное разбиение текста на 3 строки.
    Возвращает [l1, l2, l3] или None.
    Пробует уменьшать размер шрифта от size до 6pt.
    """
    words = text.split()
    if len(words) < 3:
        return None
    for sz in [size, size - 0.5, size - 1.0, size - 1.5, size - 2.0]:
        if sz < 6.0:
            sz = 6.0
        best = None
        for i in range(1, len(words) - 1):
            for j in range(i + 1, len(words)):
                l1 = " ".join(words[:i])
                l2 = " ".join(words[i:j])
                l3 = " ".join(words[j:])
                if (font.text_length(l1, fontsize=sz) <= max_width and
                        font.text_length(l2, fontsize=sz) <= max_width and
                        font.text_length(l3, fontsize=sz) <= max_width):
                    score = max(font.text_length(l, fontsize=sz) for l in [l1, l2, l3])
                    if best is None or score < best[0]:
                        best = (score, sz, l1, l2, l3)
        if best:
            return best[1:]   # (size, l1, l2, l3)
        if sz <= 6.0:
            break
    return None



def _fit_size(text, font, base_size, max_width, min_size, label=""):
    """Адаптивно уменьшает размер чтобы текст влез в одну строку."""
    if font.text_length(text, fontsize=base_size) <= max_width:
        return base_size
    w = font.text_length(text, fontsize=base_size)
    scaled = base_size * (max_width / w) * 0.98
    if scaled < min_size:
        preview = text if len(text) <= 40 else text[:37] + "..."
        print(f"  ⚠ {label}: ужат до {scaled:.1f}pt (мин {min_size}) — «{preview}»")
    return scaled


# ── Отрисовка одного текстового поля ────────────────────────────────────────
def _draw_text(page, text, *, line_x, line_y, size, font_path, color=COLOR_DARK,
               wrap=False, line2_y=None, line3_y=None, min_size=None, label="",
               on_underline=False):
    """
    Универсальная функция отрисовки текста на линии подчёркивания.

    line_x = (x0, x1) — границы линии (для центрирования и erase).
    line_y         — y линии подчёркивания.
    on_underline=True — для дат, где «линия» это текстовые символы `_____`
                     в шаблоне. line_y = нижний край символа `_` (y_bottom).
                     baseline цифр устанавливается ровно на этой y, тогда
                     цифры стоят НА линии. Подчёркивания по бокам цифр
                     остаются видимыми (это и есть визуальный «бланк»).
    on_underline=False — обычный режим: baseline = line_y - 0.5
                     (для графических линий из get_drawings).
    """
    if not str(text).strip():
        return
    text = str(text).strip()
    buf = _font_buf(font_path)
    font = fitz.Font(fontbuffer=buf)
    x0, x1 = line_x
    max_w = x1 - x0
    if min_size is None:
        min_size = max(size * 0.7, 6.0)

    # Определяем layout
    if wrap and font.text_length(text, fontsize=size) > max_w:
        # Сначала пробуем 3 строки (если разрешено line3_y)
        if line3_y is not None:
            result3 = _try_wrap_3(text, font, size, max_w)
            if result3:
                size, l1, l2, l3 = result3
                lines = [l1, l2, l3]
            else:
                result2 = _try_wrap_2(text, font, size, max_w, min_size)
                if result2:
                    l1, l2, size = result2
                    lines = [l1, l2]
                else:
                    size = _fit_size(text, font, size, max_w, min_size, label)
                    lines = [text]
        else:
            result2 = _try_wrap_2(text, font, size, max_w, min_size)
            if result2:
                l1, l2, size = result2
                lines = [l1, l2]
            else:
                size = _fit_size(text, font, size, max_w, min_size, label)
                lines = [text]
    else:
        if font.text_length(text, fontsize=size) > max_w:
            size = _fit_size(text, font, size, max_w, min_size, label)
        lines = [text]

    def _baseline_for(y_line):
        return bl_underline(y_line) if on_underline else bl(y_line)

    # Рисуем
    tw = fitz.TextWriter(page.rect)
    y_positions = [line_y, line2_y, line3_y]
    for i, ln in enumerate(lines):
        if i < len(y_positions) and y_positions[i] is not None:
            y = _baseline_for(y_positions[i])
        else:
            y = _baseline_for(line_y) + size * 1.1 * i

        # erase: top — захватывает всю высоту букв (с диакритикой казахских),
        # bot — НЕ ниже baseline. Это гарантирует что лейблы-подсказки
        # `(тегі)`, `(surname)` и т.д. ниже линии (y > baseline) не задеваются.
        # Цифры и кириллица не имеют значимого descender, так что
        # text_bot=baseline визуально безопасно.
        text_top = y - size * 0.95
        text_bot = y + 0.5
        w = font.text_length(ln, fontsize=size)
        cx = (x0 + x1) / 2
        half = w / 2 + 1.5
        eb = fitz.Rect(max(x0 + PAD, cx - half), text_top,
                       min(x1 - PAD, cx + half), text_bot)
        page.add_redact_annot(eb, fill=None)
        page.apply_redactions(graphics=0)

        # Центрирование
        x = max(x0, cx - w / 2)
        tw.append((x, y), ln, font=font, fontsize=size)

    tw.write_text(page, color=color)


def _split_persons(text):
    """Разбивает строку с несколькими людьми/абзацами на список.

    Разделители (в порядке приоритета): `\n`, `;\n`, `;`.
    Возвращает список непустых очищенных строк (длиной 1, 2, 3, 4 ...).
    """
    if not text:
        return []
    # Сначала по переносу строки
    parts = []
    for chunk in str(text).replace("\r\n", "\n").split("\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Внутри каждой строки могут быть несколько через ";"
        # — но только если их явно несколько (есть и "\n", и ";",
        # либо строк всего 1 и она длинная)
        parts.append(chunk)

    # Если всё в одной строке, но через ";" перечислены несколько лиц —
    # разделим по ";"
    if len(parts) == 1 and ";" in parts[0]:
        sub = [p.strip() for p in parts[0].split(";") if p.strip()]
        if len(sub) > 1:
            parts = sub

    # Убираем хвостовые ";" у каждого
    parts = [p.rstrip(";").rstrip() for p in parts if p.strip()]
    return parts


def _best_split(persons, font, size, max_w):
    """
    Оптимальное разбиение списка лиц (3-4) на 2 строки.
    Перебирает все точки разрыва, выбирает максимальный размер шрифта,
    при котором обе строки влезают, и балансирует их длину.
    """
    best = None   # (font_size, balance_score, row1, row2)
    for split in range(1, len(persons)):
        row1 = "; ".join(persons[:split])
        row2 = "; ".join(persons[split:])
        # Подбираем наибольший размер при котором обе строки влезают
        for s in (size - i * 0.5 for i in range(10)):
            s = max(s, 5.5)
            if (font.text_length(row1, fontsize=s) <= max_w and
                    font.text_length(row2, fontsize=s) <= max_w):
                balance = max(font.text_length(row1, fontsize=s),
                              font.text_length(row2, fontsize=s))
                # Предпочитаем максимальный шрифт, при равенстве — лучший баланс
                if best is None or s > best[0] or (s == best[0] and balance < best[1]):
                    best = (s, balance, row1, row2)
                break
    if best is None:
        # Аварийный вариант: все в одну строку с минимальным шрифтом
        return "; ".join(persons[:2]), "; ".join(persons[2:]), 5.5
    return best[2], best[3], best[0]


def _draw_multi_persons(page, text, *, line_x, line_y, line2_y, line3_y=None,
                        size, font_path, color=COLOR_DARK, min_size=6.0,
                        label=""):
    """
    Отрисовка списка лиц (консультанты / рецензенты) — до 4 человек в 2 строки.

    Распределение:
      1 чел. → 1 строка.
      2 чел. → по одному на строку.
      3-4 чел. → оптимальное разбиение: все варианты i+j перебираются,
                  выбирается максимальный шрифт и лучший баланс строк.
    """
    persons = _split_persons(text)
    if not persons:
        return

    buf = _font_buf(font_path)
    font = fitz.Font(fontbuffer=buf)
    x0, x1 = line_x
    max_w = x1 - x0

    if len(persons) == 1:
        rows = [persons[0]]
        cur_size = _fit_size(persons[0], font, size, max_w, min_size, label)
    elif len(persons) == 2:
        rows = [persons[0], persons[1]]
        cur_size = size
        for s in [size - i * 0.5 for i in range(8)]:
            s = max(s, min_size)
            if all(font.text_length(r, fontsize=s) <= max_w for r in rows):
                cur_size = s
                break
        else:
            cur_size = min_size
    elif len(persons) == 3 and line3_y is not None:
        # Три человека — каждый на своей строке
        rows = persons[:3]
        cur_size = size
        for s in [size - i * 0.5 for i in range(8)]:
            s = max(s, min_size)
            if all(font.text_length(r, fontsize=s) <= max_w for r in rows):
                cur_size = s
                break
        else:
            cur_size = min_size
    else:
        # 3+ без 3й линии или 4+ — оптимальное разбиение в 2 строки
        r1, r2, cur_size = _best_split(persons, font, size, max_w)
        rows = [r1, r2]

    # Рисуем
    all_ys = [line_y, line2_y, line3_y]
    line_ys = [y for y in all_ys[:len(rows)] if y is not None]
    for ln, y_line in zip(rows, line_ys):
        actual_size = cur_size
        text_w = font.text_length(ln, fontsize=actual_size)
        if text_w > max_w:
            actual_size = max(actual_size * (max_w / text_w) * 0.98, 5.5)

        baseline = bl(y_line)
        text_top = baseline - actual_size * 0.95
        text_bot = baseline + 0.5
        w = font.text_length(ln, fontsize=actual_size)
        cx = (x0 + x1) / 2
        half = w / 2 + 1.5
        eb = fitz.Rect(max(x0 + PAD, cx - half), text_top,
                       min(x1 - PAD, cx + half), text_bot)
        page.add_redact_annot(eb, fill=None)
        page.apply_redactions(graphics=0)

        x = max(x0, cx - w / 2)
        tw = fitz.TextWriter(page.rect)
        tw.append((x, baseline), ln, font=font, fontsize=actual_size)
        tw.write_text(page, color=color)


# ── Главная функция ─────────────────────────────────────────────────────────
def fill_diploma_phd(data: dict, output_path: str, qr_text: str = ""):
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Шаблон PhD не найден: {INPUT_FILE}")
    for p in (FONT_CAPTION, FONT_BOLD, FONT_BD):
        if not os.path.exists(p):
            raise FileNotFoundError(f"Шрифт не найден: {p}")

    doc = fitz.open(INPUT_FILE)
    page = doc[0]

    # ── 1. PhD № (внизу справа, серый, Carlito 16.32pt) ────────────────────
    if data.get("phd_number"):
        digits = "".join(c for c in str(data["phd_number"]) if c.isdigit())[:11]
        digits = digits.zfill(11)
        # Шаблон содержит «PhD № 00000000000» в y=523.50-539.82, шрифт
        # Calibri Light. Стираем «00000000000» и пишем своё (Carlito).
        # Эмпирически (через сравнение пиксельных bottom'ов): baseline=535.75
        # — низ цифр визуально совпадает с низом букв «PhD».
        # Carlito имеет иную метрику чем Calibri Light, поэтому простое
        # выравнивание по reportedному baseline не работает — делал замер
        # пикселей в финальном PDF.
        page.add_redact_annot(fitz.Rect(719.0, 521.0, 832.0, 542.0), fill=None)
        page.apply_redactions(graphics=0)
        buf = _font_buf(FONT_BD)
        font = fitz.Font(fontbuffer=buf)
        tw = fitz.TextWriter(page.rect)
        text = "№ " + digits
        tw.append((719.79, 535.75), text, font=font, fontsize=16.32)
        tw.write_text(page, color=COLOR_DARK)

    # ── 2. Серия диплома ────────────────────────────────────────────────────
    # Линия y=553.77, x=761.36-830.65 — правее «Тіркеу нөмірі» нет, серия выше.
    # «Диплом сериясы» = заголовок, серия пишется НА линии x=761.36-830.65 y=553.77?
    # Нет — это линия для Тіркеу нөмірі. А серия диплома сама пишется в шаблоне как заголовок.
    # Скорее всего, серия НЕ заполняется автоматически (как и Тіркеу нөмірі).
    # Оставляем в покое.

    # ── 3. Дата заседания диссертационного совета ───────────────────────────
    # Казахская: «_____ жылғы «___» ____________ шешімімен»
    # Каждое поле — отдельная маленькая линия. Использую _draw_text по узкой зоне.

    # Казахская дата совета
    if data.get("council_year_kaz"):
        _draw_text(page, data["council_year_kaz"],
                   line_x=(89.7, 115.2), line_y=205.75,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="council_year_kaz")
    if data.get("council_day"):
        _draw_text(page, data["council_day"],
                   line_x=(154.6, 169.9), line_y=205.75,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="council_day_kaz")
    if data.get("council_month_kaz"):
        _draw_text(page, data["council_month_kaz"],
                   line_x=(177.5, 238.7), line_y=205.75,
                   size=9.0, font_path=FONT_CAPTION,
                   on_underline=True, label="council_month_kaz")

    # Англ. совет: dated «___» ___________ ____ year
    if data.get("council_day"):
        _draw_text(page, data["council_day"],
                   line_x=(408.7, 424.0), line_y=205.75,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="council_day_eng")
    if data.get("council_month_eng"):
        _draw_text(page, data["council_month_eng"],
                   line_x=(431.6, 474.0), line_y=205.75,
                   size=9.0, font_path=FONT_CAPTION,
                   on_underline=True, label="council_month_eng")
    if data.get("council_year_eng"):
        _draw_text(page, data["council_year_eng"],
                   line_x=(477.0, 510.6), line_y=205.75,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="council_year_eng")

    # Рус. совет: от «___» ___________ ____ года
    if data.get("council_day"):
        _draw_text(page, data["council_day"],
                   line_x=(664.6, 679.9), line_y=205.75,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="council_day_rus")
    if data.get("council_month_rus"):
        _draw_text(page, data["council_month_rus"],
                   line_x=(687.5, 735.0), line_y=205.75,
                   size=9.0, font_path=FONT_CAPTION,
                   on_underline=True, label="council_month_rus")
    if data.get("council_year_rus"):
        _draw_text(page, data["council_year_rus"],
                   line_x=(740.0, 766.5), line_y=205.75,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="council_year_rus")

    # ── 4. Дата приказа ─────────────────────────────────────────────────────
    # Каз: (_____ жылғы «___» _____________ № ____ бұйрық)
    if data.get("order_year_kaz"):
        _draw_text(page, data["order_year_kaz"],
                   line_x=(77.4, 102.9), line_y=218.20,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_year_kaz")
    if data.get("order_day"):
        _draw_text(page, data["order_day"],
                   line_x=(142.4, 157.7), line_y=218.20,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_day_kaz")
    if data.get("order_month_kaz"):
        _draw_text(page, data["order_month_kaz"],
                   line_x=(165.2, 234.1), line_y=218.20,
                   size=9.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_month_kaz")
    if data.get("order_number"):
        _draw_text(page, data["order_number"],
                   line_x=(246.8, 267.2), line_y=218.20,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_number_kaz")

    # Англ: (Order № _____ dated «___» ___________ ____ year)
    if data.get("order_number"):
        _draw_text(page, data["order_number"],
                   line_x=(383.0, 408.5), line_y=218.20,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_number_eng")
    if data.get("order_day"):
        _draw_text(page, data["order_day"],
                   line_x=(442.3, 457.6), line_y=218.20,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_day_eng")
    if data.get("order_month_eng"):
        _draw_text(page, data["order_month_eng"],
                   line_x=(465.1, 510.0), line_y=218.20,
                   size=9.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_month_eng")
    if data.get("order_year_eng"):
        _draw_text(page, data["order_year_eng"],
                   line_x=(515.0, 544.1), line_y=218.20,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_year_eng")

    # Рус: (Приказ № _____ от «___» ___________ ____ года)
    if data.get("order_number"):
        _draw_text(page, data["order_number"],
                   line_x=(657.0, 682.5), line_y=218.20,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_number_rus")
    if data.get("order_day"):
        _draw_text(page, data["order_day"],
                   line_x=(701.6, 716.9), line_y=218.20,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_day_rus")
    if data.get("order_month_rus"):
        _draw_text(page, data["order_month_rus"],
                   line_x=(724.4, 780.5), line_y=218.20,
                   size=9.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_month_rus")
    if data.get("order_year_rus"):
        _draw_text(page, data["order_year_rus"],
                   line_x=(782.9, 803.3), line_y=218.20,
                   size=10.0, font_path=FONT_CAPTION,
                   on_underline=True, label="order_year_rus")

    # ── 5. Фамилия (тегі / surname / фамилия) ───────────────────────────────
    if data.get("surname_kaz"):
        _draw_text(page, data["surname_kaz"],
                   line_x=COL_KAZ, line_y=LINE_KAZ_SURNAME,
                   size=11.0, font_path=FONT_BOLD,
                   label="surname_kaz")
    if data.get("surname_eng"):
        _draw_text(page, data["surname_eng"],
                   line_x=COL_ENG, line_y=LINE_ENG_SURNAME,
                   size=11.0, font_path=FONT_BOLD,
                   label="surname_eng")
    if data.get("surname_rus"):
        _draw_text(page, data["surname_rus"],
                   line_x=COL_RUS, line_y=LINE_RUS_SURNAME,
                   size=11.0, font_path=FONT_BOLD,
                   label="surname_rus")

    # ── 6. Имя+отчество ─────────────────────────────────────────────────────
    if data.get("first_name_kaz"):
        _draw_text(page, data["first_name_kaz"],
                   line_x=COL_KAZ, line_y=LINE_KAZ_FIRSTNAME,
                   size=11.0, font_path=FONT_BOLD,
                   label="first_name_kaz")
    if data.get("first_name_eng"):
        _draw_text(page, data["first_name_eng"],
                   line_x=COL_ENG, line_y=LINE_ENG_FIRSTNAME,
                   size=11.0, font_path=FONT_BOLD,
                   label="first_name_eng")
    if data.get("first_name_rus"):
        _draw_text(page, data["first_name_rus"],
                   line_x=COL_RUS, line_y=LINE_RUS_FIRSTNAME,
                   size=11.0, font_path=FONT_BOLD,
                   label="first_name_rus")

    # ── 7. Программа (специальность) ────────────────────────────────────────
    # Каждая колонка имеет 2 линии — для длинного текста переносим на 2 строки.
    # Обратите внимание на ENG: его линии 235.77 и 253.06 ВЫШЕ (наоборот),
    # а KAZ: 272.94 и 289.95, RUS: 312.62 и 329.63.
    if data.get("program_kaz"):
        _draw_text(page, data["program_kaz"],
                   line_x=COL_KAZ, line_y=LINE_KAZ_PROG_1,
                   line2_y=LINE_KAZ_PROG_2,
                   size=9.5, font_path=FONT_CAPTION,
                   wrap=True, label="program_kaz")
    if data.get("program_eng"):
        _draw_text(page, data["program_eng"],
                   line_x=COL_ENG, line_y=LINE_ENG_PROG_1,
                   line2_y=LINE_ENG_PROG_2,
                   size=9.5, font_path=FONT_CAPTION,
                   wrap=True, label="program_eng")
    if data.get("program_rus"):
        _draw_text(page, data["program_rus"],
                   line_x=COL_RUS, line_y=LINE_RUS_PROG_1,
                   line2_y=LINE_RUS_PROG_2,
                   size=9.5, font_path=FONT_CAPTION,
                   wrap=True, label="program_rus")

    # ── 8. Тема диссертации (2 строки в каждой колонке) ─────────────────────
    for lang, col in [("kaz", COL_KAZ), ("eng", COL_ENG), ("rus", COL_RUS)]:
        key = f"dissertation_{lang}"
        if data.get(key):
            _draw_text(page, data[key],
                       line_x=col, line_y=LINE_DISSERT_1,
                       line2_y=LINE_DISSERT_MID,
                       line3_y=LINE_DISSERT_2,
                       size=8.0, font_path=FONT_CAPTION,
                       wrap=True, min_size=6.0, label=key)

    # ── 9. Научные консультанты (до 4 человек, 2 строки × 2 ФИО) ─────────────
    for lang, col in [("kaz", COL_KAZ), ("eng", COL_ENG), ("rus", COL_RUS)]:
        key = f"consultants_{lang}"
        if data.get(key):
            _draw_multi_persons(page, data[key],
                       line_x=col, line_y=LINE_CONSULT_1,
                       line2_y=LINE_CONSULT_MID,
                       line3_y=LINE_CONSULT_2,
                       size=7.0, font_path=FONT_CAPTION,
                       min_size=5.5, label=key)

    # ── 10. Официальные рецензенты (до 4 человек, 2 строки × 2 ФИО) ──────────
    for lang, col in [("kaz", COL_KAZ), ("eng", COL_ENG), ("rus", COL_RUS)]:
        key = f"reviewers_{lang}"
        if data.get(key):
            _draw_multi_persons(page, data[key],
                       line_x=col, line_y=LINE_REVIEW_1,
                       line2_y=LINE_REVIEW_MID,
                       line3_y=LINE_REVIEW_2,
                       size=7.0, font_path=FONT_CAPTION,
                       min_size=5.5, label=key)

    # ── 11. Место защиты (2 строки) ─────────────────────────────────────────
    for lang, col in [("kaz", COL_KAZ), ("eng", COL_ENG), ("rus", COL_RUS)]:
        key = f"place_{lang}"
        if data.get(key):
            _draw_text(page, data[key],
                       line_x=col, line_y=LINE_PLACE_1,
                       line2_y=LINE_PLACE_2,
                       size=9.0, font_path=FONT_CAPTION,
                       wrap=True, min_size=6.0, label=key)

    # ── 12. Дата защиты (1 строка) ──────────────────────────────────────────
    for lang, col in [("kaz", COL_KAZ), ("eng", COL_ENG), ("rus", COL_RUS)]:
        key = f"defense_date_{lang}"
        if data.get(key):
            _draw_text(page, data[key],
                       line_x=col, line_y=LINE_DATE_DEF,
                       size=9.0, font_path=FONT_CAPTION,
                       min_size=6.0, label=key)

    # ── 13. Нижний блок: год / день / месяц выдачи (центральный) ────────────
    if data.get("issue_year"):
        _draw_text(page, data["issue_year"],
                   line_x=(688.95, 722.59), line_y=LINE_OUT_YEAR,
                   size=10.0, font_path=FONT_CAPTION, label="issue_year")
    if data.get("issue_day"):
        _draw_text(page, data["issue_day"],
                   line_x=(758.97, 776.16), line_y=LINE_OUT_DAY,
                   size=10.0, font_path=FONT_CAPTION, label="issue_day")
    if data.get("issue_month_kaz"):
        _draw_text(page, data["issue_month_kaz"],
                   line_x=(783.49, 825.21), line_y=LINE_OUT_MONTH,
                   size=9.0, font_path=FONT_CAPTION, label="issue_month")

    # ── 14. QR ──────────────────────────────────────────────────────────────
    if qr_text and qr_text.strip():
        if not _QR_AVAILABLE:
            print("  ⚠ QR пропущен: модуль qr_diploma не найден")
        else:
            insert_qr_on_page(page, qr_text.strip(), rect=QR_RECT_PHD)
            print(f"  ✓ QR вставлен ({len(qr_text)} симв., в зоне СЛЕВА)")

    doc.save(output_path, garbage=4, deflate=True, deflate_images=True,
             deflate_fonts=True, clean=True)
    print(f"✓ Сохранено → {output_path} (страниц: {len(doc)}, тип: PhD)")


# ── CLI ────────────────────────────────────────────────────────────────────
def ask(prompt, required=True, default=None):
    hint = f" [{default}]" if default else ""
    while True:
        val = input(f"  {prompt}{hint}: ").strip()
        if val: return val
        if default is not None: return default
        if not required: return ""
        print("    (обязательное поле)")


def main():
    print("=" * 60)
    print("  Заполнение диплома PhD КарУ")
    print("=" * 60)

    print("\n── Номер диплома ──")
    phd = ask("PhD номер (11 цифр)")

    print("\n── Дата заседания диссертационного совета ──")
    council_year_kaz = ask("Год каз (4 цифры)")
    council_year_eng = ask("Год eng (4 цифры)", default=council_year_kaz)
    council_year_rus = ask("Год рус (4 цифры)", default=council_year_kaz)
    council_day      = ask("День")
    council_month_kaz= ask("Месяц каз (напр: маусым)")
    council_month_eng= ask("Месяц eng (напр: June)")
    council_month_rus= ask("Месяц рус (напр: июня)")

    print("\n── Дата приказа ──")
    order_year_kaz = ask("Год каз (4 цифры)")
    order_year_eng = ask("Год eng (4 цифры)", default=order_year_kaz)
    order_year_rus = ask("Год рус (4 цифры)", default=order_year_kaz)
    order_day      = ask("День")
    order_month_kaz= ask("Месяц каз")
    order_month_eng= ask("Месяц eng")
    order_month_rus= ask("Месяц рус")
    order_number   = ask("Номер приказа")

    print("\n── Фамилия ──")
    surname_kaz = ask("Фамилия каз")
    surname_rus = ask("Фамилия рус")
    surname_eng = ask("Фамилия eng")

    print("\n── Имя, отчество ──")
    first_name_kaz = ask("Имя+отчество каз")
    first_name_rus = ask("Имя+отчество рус")
    first_name_eng = ask("Имя+отчество eng (без отчества)")

    print("\n── Программа / специальность ──")
    program_kaz = ask("Программа каз")
    program_rus = ask("Программа рус")
    program_eng = ask("Программа eng")

    print("\n── Тема диссертации ──")
    dissertation_kaz = ask("Тема каз")
    dissertation_rus = ask("Тема рус")
    dissertation_eng = ask("Тема eng")

    print("\n── Научные консультанты ──")
    consultants_kaz = ask("Консультанты каз")
    consultants_rus = ask("Консультанты рус")
    consultants_eng = ask("Консультанты eng")

    print("\n── Официальные рецензенты ──")
    reviewers_kaz = ask("Рецензенты каз")
    reviewers_rus = ask("Рецензенты рус")
    reviewers_eng = ask("Рецензенты eng")

    print("\n── Место защиты ──")
    place_kaz = ask("Место каз")
    place_rus = ask("Место рус")
    place_eng = ask("Место eng")

    print("\n── Дата защиты ──")
    defense_date_kaz = ask("Дата каз (напр: 11 маусым 2025)")
    defense_date_rus = ask("Дата рус (напр: 11 июня 2025)")
    defense_date_eng = ask("Дата eng (напр: June 11, 2025)")

    print("\n── Дата выдачи диплома ──")
    issue_year      = ask("Год (4 цифры)", default="2026")
    issue_day       = ask("День")
    issue_month_kaz = ask("Месяц каз (напр: наурыз)")

    print("\n── QR ──")
    qr_text = ask("Текст/URL QR (Enter — пропустить)", required=False)

    data = {
        "phd_number": phd,
        "council_year_kaz": council_year_kaz, "council_year_eng": council_year_eng,
        "council_year_rus": council_year_rus, "council_day": council_day,
        "council_month_kaz": council_month_kaz, "council_month_eng": council_month_eng,
        "council_month_rus": council_month_rus,
        "order_year_kaz": order_year_kaz, "order_year_eng": order_year_eng,
        "order_year_rus": order_year_rus, "order_day": order_day,
        "order_month_kaz": order_month_kaz, "order_month_eng": order_month_eng,
        "order_month_rus": order_month_rus, "order_number": order_number,
        "surname_kaz": surname_kaz, "surname_eng": surname_eng, "surname_rus": surname_rus,
        "first_name_kaz": first_name_kaz, "first_name_eng": first_name_eng, "first_name_rus": first_name_rus,
        "program_kaz": program_kaz, "program_eng": program_eng, "program_rus": program_rus,
        "dissertation_kaz": dissertation_kaz, "dissertation_eng": dissertation_eng, "dissertation_rus": dissertation_rus,
        "consultants_kaz": consultants_kaz, "consultants_eng": consultants_eng, "consultants_rus": consultants_rus,
        "reviewers_kaz": reviewers_kaz, "reviewers_eng": reviewers_eng, "reviewers_rus": reviewers_rus,
        "place_kaz": place_kaz, "place_eng": place_eng, "place_rus": place_rus,
        "defense_date_kaz": defense_date_kaz, "defense_date_eng": defense_date_eng, "defense_date_rus": defense_date_rus,
        "issue_year": issue_year, "issue_day": issue_day, "issue_month_kaz": issue_month_kaz,
    }

    safe = surname_kaz.split()[0] if surname_kaz else "phd"
    output = INPUT_FILE.replace(".pdf", f"_{safe}_{phd}.pdf")
    print()
    fill_diploma_phd(data, output, qr_text=qr_text)


if __name__ == "__main__":
    main()
