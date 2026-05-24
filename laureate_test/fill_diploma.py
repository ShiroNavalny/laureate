"""
fill_diploma.py — Заполнение всех полей PDF-диплома КарУ (v8)

Изменения v8 относительно v7:
  • Введена константа CENTER_X = 453.5 — визуальная ось симметрии бланка
    (по ней отцентрированы шапки, подсказки «(фамилия, имя, отчество)»,
    «(graduate’s full name)», «(тегі, аты, әкесінің аты)» и др.).
  • Добавлен опциональный параметр поля `x_anchor`. Если задан, КОРОТКИЙ
    текст центрируется относительно него, а не относительно геометрической
    середины линии подчёркивания. Это нужно для полей, у которых линия
    несимметрична относительно бланка (слева — длинный лейбл вроде
    «Форма обучения», справа — QR-код). Anchor применяется только если
    текст занимает не более 60% ширины линии — на длинных текстах
    (заполняющих линию) поведение сохраняется как в v7 (геометрический
    центр линии). Это требование пользователя: «на больших работает,
    на маленьких неровно — поправь только маленькие».
  • `x_anchor=CENTER_X` добавлен пяти проблемным полям:
        rus_qualification, kaz_form, eng_form, kaz_program, eng_program.
    На длинных текстах (как было раньше) ничего не меняется, на коротких
    («очная», «техник-программист») текст теперь становится ровно
    под подсказкой, а не съезжает влево/вправо.
  • Поправлен спецрежим 2-строчной русской программы: при ней
    раньше квалификация ставилась впритык (а на PT Serif Caption даже
    пересекалась с «присвоена степень БАКАЛАВР» на 0.66pt). Теперь
    квалификация опущена с baseline=485 на 487, размер программы и
    квалификации уменьшен с 8pt до 7.5pt — это даёт зазор сверху
    +1.85pt и зазор снизу до программы +1.0pt. Английский блок
    не тронут — там зазор сверху и так был +1.6pt.

Изменения v7 относительно v6:
  • 2-строчная программа теперь работает ВМЕСТЕ с квалификацией.
    Стратегия: erase_bbox у квалификации сужается ровно до ширины
    её текста (clip_erase=True) — тогда стирание не задевает боковые
    части верхней строки 2-строчной программы. Квалификация рисуется
    ПОСЛЕ программы и ложится поверх центральной части программы,
    точно как на фото реального диплома.
  • Добавлена нижняя строка диплома (дата выдачи дубликата + город):
      diploma_year  — год (напр. 2026) под линией 378.42–412.06
      diploma_day   — день (напр. 12) под линией 448.44–465.63
      diploma_month — месяц словом (напр. наурыз) под 472.96–528.63
      city          — город (напр. Қарағанды) под 584.81–679.80
    Регистрационный номер (Тіркеу нөмірі) по-прежнему НЕ заполняется.

Изменения v6: QR-код (модуль qr_diploma.py) в зону 110.55 × 110.55 pt.
Изменения v5: 3 типа дипломов, перенос программы на 2 строки,
BASELINE_OFFSET=-0.5, обе страницы сохраняются.

Зависимости: pip install pymupdf qrcode pillow
Шрифты:
  ./fonts/PTSerifCaption-Regular.ttf
  ./fonts/PTSerif-Bold.ttf
  /usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf  (для BD/MD №)
"""

import fitz
import os
import sys

# QR-код (модуль лежит рядом)
try:
    from qr_diploma import insert_qr_on_page
    _QR_AVAILABLE = True
except ImportError:
    _QR_AVAILABLE = False

# ── Пути к шрифтам ──────────────────────────────────────────────────────────
# ── Шрифты: приоритет 1 — папка fonts/, 2 — системные paratype ──────────
def _resolve_font(local_name, system_path):
    _dir = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(_dir, "fonts", local_name)
    return local if os.path.exists(local) else system_path

FONT_CAPTION = _resolve_font("PTSerifCaption-Regular.ttf",
                              "/usr/share/fonts/truetype/paratype/PTZ55F.ttf")
FONT_BOLD    = _resolve_font("PTSerif-Bold.ttf",
                              "/usr/share/fonts/truetype/paratype/PTF75F.ttf")
def _first_existing(paths, fallback):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return fallback


FONT_BD = _first_existing([
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
], FONT_BOLD)

# ── Цвета ───────────────────────────────────────────────────────────────────
COLOR_DARK = (0.106, 0.106, 0.102)   # rgb(27,27,26) — основной текст
COLOR_GREY = (0.427, 0.431, 0.439)   # rgb(109,110,112) — для BD/MD №

# ── Визуальная ось симметрии бланка ─────────────────────────────────────────
# По ней отцентрированы все шапки и подсказки в скобках:
#   «(тегі, аты, әкесінің аты, бар болса)»          cx ≈ 453.53
#   «(фамилия, имя, отчество, при наличии)»          cx ≈ 453.55
#   «(graduate’s full name)»                         cx ≈ 453.53
#   «(күндізгі немесе ... оқытуға ауыстыра отырып)»  cx ≈ 453.53
#   «(full-time or with transfer to distance ...)»   cx ≈ 453.59
#   «(білім беру бағдарламасының коды, ...)»         cx ≈ 453.24
#   «(code and name of the educational program, ...)» cx ≈ 453.59
#   «Академик Е.А. Бөкетов атындағы ...»             cx ≈ 453.46
# Используется как `x_anchor` для коротких текстов в полях,
# у которых линия подчёркивания несимметрична (слева длинный лейбл
# или справа QR-код).
CENTER_X = 453.5

# ── Координаты линий подчёркивания ──────────────────────────────────────────
# Совпадают у всех трёх новых шаблонов (bakalavr / honors / magistr).
LINE_KAZ_DATE = 204.56   # год / день / месяц / протокол — одна y
LINE_KAZ_FIO  = 220.63
LINE_KAZ_PROG = 234.52
LINE_KAZ_QUAL = 248.69
LINE_KAZ_FORM = 272.22
LINE_ENG_FIO  = 325.96
LINE_ENG_QUAL = 355.72
LINE_ENG_PROG = 371.73
LINE_ENG_FORM = 385.77
LINE_ENG_DATE = 404.86
LINE_RUS_DATE = 443.51
LINE_RUS_FIO  = 459.57
LINE_RUS_QUAL = 489.19
LINE_RUS_PROG = 505.20
LINE_RUS_FORM = 519.24

# Нижняя строка — дата выдачи дубликата + город (все линии на одной y).
LINE_BOTTOM   = 587.39

# Baseline относительно линии подчёркивания. Отрицательное = приподнят над.
# По просьбе пользователя: чуть-чуть выше линии, а не впритык на неё.
BASELINE_OFFSET = -0.5

def bl(line_y: float) -> float:
    return line_y + BASELINE_OFFSET


# ── Типы диплома ────────────────────────────────────────────────────────────
#
# У магистра линии формы-обучения/направления начинаются левее,
# потому что лейблы «бағыты» / «Направление» / «Type of program» короче
# чем «оқыту нысаны» / «Форма обучения» / «Form of training».
DIPLOMA_TYPES = {
    "bakalavr": {
        "title":       "Обычный бакалавр",
        "input_file":  "diplomas/ДИПЛОМ_бакалавра_2025.pdf",
        "bd_prefix":   "ВD № ",
        "kaz_form_x":  (196.09, 764.02),   # после «оқыту нысаны»
        "rus_form_x":  (282.66, 701.73),   # после «Форма обучения»
    },
    "bakalavr_honors": {
        "title":       "Бакалавр с отличием",
        "input_file":  "diplomas/ДИПЛОМ_бакалавра_с_отличием_2025.pdf",
        "bd_prefix":   "ВD № ",
        "kaz_form_x":  (196.09, 764.02),
        "rus_form_x":  (282.66, 701.73),
    },
    "magistr": {
        "title":       "Магистр",
        "input_file":  "diplomas/ДИПЛОМ_Магистра_2025.pdf",
        "bd_prefix":   "MD № ",
        "kaz_form_x":  (169.35, 764.02),   # после «бағыты» (короче)
        "rus_form_x":  (264.00, 701.73),   # после «Направление» (короче)
    },
}


# ── Описание всех полей ─────────────────────────────────────────────────────
def build_fields(diploma_type: str) -> dict:
    """
    Возвращает словарь полей FIELDS для данного типа диплома.
    У магистра шире линии форма/направление — остальные поля одинаковы.
    """
    dt = DIPLOMA_TYPES[diploma_type]

    FIELDS = {

        # ── Номер BD/MD ──────────────────────────────────────────────────
        "bd_number": {
            "label": "Номер диплома (11 цифр)",
            "x": 378.4, "y": 172.2,
            "size": 18.0,
            "font": FONT_BD,
            "color": COLOR_GREY,
            "prefix": dt["bd_prefix"],
            "erase_bbox": (378.4, 158.2, 528.0, 177.5),
        },

        # ── Казахский блок ──────────────────────────────────────────────

        "kaz_fio": {
            "label": "ФИО (казахский)",
            "y": bl(LINE_KAZ_FIO),
            "x_center": (143.84, 764.02),
            "size": 13.0, "min_size": 10.0,
            "font": FONT_BOLD,
            "color": COLOR_DARK,
            "erase_bbox": (143.8, 208.4, 764.0, 220.5),
        },
        "kaz_program": {
            "label": "Программа (казахский)",
            "y": bl(LINE_KAZ_PROG),
            "x_center": (143.84, 648.55),
            "x_anchor": CENTER_X,        # короткий текст — по визуальной оси
            "size": 9.5, "min_size": 7.5,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "allow_wrap": True,
            "erase_bbox": (143.8, 228.0, 648.5, 234.3),
        },
        "kaz_qualification": {
            "label": "Квалификация (казахский)",
            "y": bl(LINE_KAZ_QUAL),
            "x_center": (143.84, 764.02),
            "size": 10.0, "min_size": 8.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "clip_erase": True,
            "erase_bbox": (143.8, 241.0, 764.0, 248.5),
        },
        "kaz_form": {
            "label": "Форма / направление (казахский)",
            "y": bl(LINE_KAZ_FORM),
            "x_center": dt["kaz_form_x"],
            "x_anchor": CENTER_X,        # короткое «очная» — по визуальной оси
            "size": 9.0, "min_size": 7.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (dt["kaz_form_x"][0] - 0.1, 263.5,
                           dt["kaz_form_x"][1],        272.0),
        },
        "kaz_year": {
            "label": "Год (казахский)",
            "y": bl(LINE_KAZ_DATE),
            "x_center": (373.16, 390.26),
            "size": 11.0, "min_size": 9.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (373.41, 195.7, 390.01, 206.3),
        },
        "kaz_day": {
            "label": "День (казахский)",
            "y": bl(LINE_KAZ_DATE),
            "x_center": (426.45, 450.90),
            "size": 11.0, "min_size": 9.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (426.7, 196.0, 450.65, 205.5),
        },
        "kaz_month": {
            "label": "Месяц (казахский)",
            "y": bl(LINE_KAZ_DATE),
            "x_center": (456.21, 547.42),
            "size": 9.0, "min_size": 7.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (456.46, 196.0, 547.17, 205.5),
        },
        "kaz_protocol": {
            "label": "Протокол (казахский)",
            "y": bl(LINE_KAZ_DATE),
            "x_center": (608.44, 622.20),
            "size": 11.0, "min_size": 9.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (608.69, 196.0, 621.95, 205.5),
        },

        # ── Английский блок ─────────────────────────────────────────────

        "eng_fio": {
            "label": "ФИО (английский)",
            "y": bl(LINE_ENG_FIO),
            "x_center": (143.84, 764.02),
            "size": 13.0, "min_size": 10.0,
            "font": FONT_BOLD,
            "color": COLOR_DARK,
            "erase_bbox": (143.8, 311.0, 764.0, 325.8),
        },
        "eng_qualification": {
            "label": "Квалификация (английский)",
            "y": bl(LINE_ENG_QUAL),
            "x_center": (143.84, 764.02),
            "size": 10.0, "min_size": 8.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (143.8, 344.5, 764.0, 355.5),
        },
        "eng_program": {
            "label": "Программа (английский)",
            "y": bl(LINE_ENG_PROG),
            "x_center": (244.90, 764.02),
            "x_anchor": CENTER_X,        # короткий текст — по визуальной оси
            "size": 9.5, "min_size": 7.5,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "allow_wrap": True,
            "erase_bbox": (244.9, 357.5, 764.0, 371.5),
        },
        "eng_form": {
            "label": "Форма / Type of program (английский)",
            "y": bl(LINE_ENG_FORM),
            "x_center": (201.50, 764.02),
            "x_anchor": CENTER_X,        # короткое «full-time» — по визуальной оси
            "size": 9.0, "min_size": 7.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (201.0, 378.7, 764.0, 385.5),
        },
        "eng_year": {
            "label": "Год (английский)",
            "y": bl(LINE_ENG_DATE),
            "x_center": (509.30, 522.84),
            "size": 11.0, "min_size": 9.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (509.55, 393.5, 522.59, 407.0),
        },
        "eng_day": {
            "label": "День (английский)",
            "y": bl(LINE_ENG_DATE),
            "x_center": (407.19, 425.39),
            "size": 11.0, "min_size": 9.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (407.44, 393.5, 425.14, 407.0),
        },
        "eng_month": {
            "label": "Месяц (английский)",
            "y": bl(LINE_ENG_DATE),
            "x_center": (431.61, 496.17),
            "size": 9.0, "min_size": 7.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (431.86, 393.5, 495.92, 407.0),
        },

        # ── Русский блок ────────────────────────────────────────────────

        "rus_fio": {
            "label": "ФИО (русский)",
            "y": bl(LINE_RUS_FIO),
            "x_center": (143.84, 764.02),
            "size": 13.0, "min_size": 10.0,
            "font": FONT_BOLD,
            "color": COLOR_DARK,
            "erase_bbox": (143.8, 447.5, 764.0, 459.5),
        },
        "rus_qualification": {
            "label": "Квалификация (русский)",
            "y": bl(LINE_RUS_QUAL),
            "x_center": (143.84, 701.73),
            "x_anchor": CENTER_X,        # справа QR-код, линия несимметрична
            "size": 10.0, "min_size": 8.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (143.8, 478.0, 701.8, 489.0),
        },
        "rus_program": {
            "label": "Программа (русский)",
            "y": bl(LINE_RUS_PROG),
            "x_center": (345.31, 701.73),
            "size": 9.5, "min_size": 7.5,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "allow_wrap": True,
            "erase_bbox": (345.3, 494.0, 701.7, 505.0),
        },
        "rus_form": {
            "label": "Форма / направление (русский)",
            "y": bl(LINE_RUS_FORM),
            "x_center": dt["rus_form_x"],
            "size": 9.0, "min_size": 7.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (dt["rus_form_x"][0] - 0.1, 512.2,
                           dt["rus_form_x"][1],        519.0),
        },
        "rus_year": {
            "label": "Год (русский)",
            "y": bl(LINE_RUS_DATE),
            "x_center": (455.86, 469.54),
            "size": 11.0, "min_size": 9.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (456.11, 434.4, 469.29, 445.2),
        },
        "rus_day": {
            "label": "День (русский)",
            "y": bl(LINE_RUS_DATE),
            "x_center": (358.16, 376.44),
            "size": 11.0, "min_size": 9.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (358.41, 434.4, 376.19, 444.7),
        },
        "rus_month": {
            "label": "Месяц (русский)",
            "y": bl(LINE_RUS_DATE),
            "x_center": (381.12, 445.73),
            "size": 9.0, "min_size": 7.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (381.37, 434.4, 445.48, 444.7),
        },
        "rus_protocol": {
            "label": "Протокол (русский)",
            "y": bl(LINE_RUS_DATE),
            "x_center": (544.96, 562.02),
            "size": 11.0, "min_size": 9.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (545.21, 434.4, 561.77, 444.7),
        },

        # ── Нижняя строка (дата выдачи дубликата + город) ────────────────
        # Регистрационный номер (Тіркеу нөмірі) НЕ заполняется — его
        # вписывает ректорат от руки. Линия под ним x=270.73–341.19.

        "diploma_year": {
            "label": "Год выдачи (нижняя строка)",
            "y": bl(LINE_BOTTOM),
            "x_center": (378.42, 412.06),
            "size": 11.0, "min_size": 9.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (378.67, 578.0, 411.81, 588.0),
        },
        "diploma_day": {
            "label": "День выдачи (нижняя строка)",
            "y": bl(LINE_BOTTOM),
            "x_center": (448.44, 465.63),
            "size": 11.0, "min_size": 9.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (448.69, 578.0, 465.38, 588.0),
        },
        "diploma_month": {
            "label": "Месяц выдачи (нижняя строка, словом)",
            "y": bl(LINE_BOTTOM),
            "x_center": (472.96, 528.63),
            "size": 9.0, "min_size": 7.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (473.21, 578.0, 528.38, 588.0),
        },
        "city": {
            "label": "Город выдачи",
            "y": bl(LINE_BOTTOM),
            "x_center": (584.81, 679.80),
            "size": 11.0, "min_size": 9.0,
            "font": FONT_CAPTION,
            "color": COLOR_DARK,
            "erase_bbox": (585.06, 578.0, 679.55, 588.0),
        },
    }
    return FIELDS


# ── Порядок отрисовки ───────────────────────────────────────────────────────
# Даты рисуются первыми в каждом блоке: их erase_bbox соседствуют с зонами
# ФИО/программы. Квалификация — после программы, чтобы erase_bbox программы
# не задел только что нарисованную квалификацию.
DRAW_ORDER = [
    "bd_number",
    "kaz_year", "kaz_day", "kaz_month", "kaz_protocol",
    "kaz_fio", "kaz_program", "kaz_qualification", "kaz_form",
    "eng_year", "eng_day", "eng_month",
    "eng_fio", "eng_program", "eng_qualification", "eng_form",
    "rus_year", "rus_day", "rus_month", "rus_protocol",
    "rus_fio", "rus_program", "rus_qualification", "rus_form",
    # Нижняя строка (Тіркеу нөмірі оставляем пустым).
    "diploma_year", "diploma_day", "diploma_month", "city",
]


# ── Кэш шрифтов ─────────────────────────────────────────────────────────────
_FONT_CACHE = {}

def _font_buf(path):
    if path not in _FONT_CACHE:
        with open(path, "rb") as f:
            _FONT_CACHE[path] = f.read()
    return _FONT_CACHE[path]


# ── Разбивка текста на 2 строки ─────────────────────────────────────────────
def _try_wrap_2(text: str, font, size: float, max_width: float):
    """
    Пытается разбить текст на ровно 2 строки, каждая ≤ max_width.

    Стратегия:
      1) Если есть запятая — пробуем разбить по каждой запятой и выбираем
         самый сбалансированный (min(max(left, right))) вариант из тех,
         где обе половинки влезают.
      2) Если запятые не помогли — пробуем разбить по пробелу
         (аналогично, ищем лучший split).
      3) Если ни одна разбивка не вмещается — возвращаем None.
    """
    def fits(s):
        return font.text_length(s, fontsize=size) <= max_width

    candidates = []

    # (1) Разбиение по запятым.
    if "," in text:
        parts = text.split(",")
        for i in range(1, len(parts)):
            left  = ",".join(parts[:i]).rstrip() + ","
            right = ",".join(parts[i:]).lstrip()
            if left and right and fits(left) and fits(right):
                score = max(font.text_length(left, fontsize=size),
                            font.text_length(right, fontsize=size))
                candidates.append((score, left, right))

    # (2) Разбиение по пробелам.
    words = text.split(" ")
    if len(words) > 1:
        for i in range(1, len(words)):
            left  = " ".join(words[:i])
            right = " ".join(words[i:])
            if fits(left) and fits(right):
                score = max(font.text_length(left, fontsize=size),
                            font.text_length(right, fontsize=size))
                candidates.append((score, left, right))

    if not candidates:
        return None
    # Выбираем самый сбалансированный = минимальная длина максимальной строки.
    candidates.sort(key=lambda c: c[0])
    _, left, right = candidates[0]
    return [left, right]


def _layout_text(text: str, font, base_size: float,
                 max_width: float, min_size: float,
                 allow_wrap: bool, field_label: str = ""):
    """
    Возвращает (lines, size).

    Логика:
      1) 1 строка при base_size — если влезает, ок.
      2) Если allow_wrap — 2 строки при base_size, если влезают, ок.
      3) Адаптивно уменьшаем размер для 1 строки (с 2% запасом).
         Если результат ≥ min_size — ок.
      4) Если allow_wrap и 1 строка < min_size — 2 строки при min_size.
      5) Крайний случай (warning): 1 строка с сильно уменьшенным размером.
    """
    # (1) 1 строка на базовом размере
    if font.text_length(text, fontsize=base_size) <= max_width:
        return [text], base_size

    # (2) 2 строки на базовом размере
    if allow_wrap:
        lines = _try_wrap_2(text, font, base_size, max_width)
        if lines:
            return lines, base_size

    # (3) Адаптивное уменьшение одной строки
    w = font.text_length(text, fontsize=base_size)
    scaled = base_size * (max_width / w) * 0.98
    if scaled >= min_size:
        return [text], scaled

    # (4) 2 строки на min_size
    if allow_wrap:
        lines = _try_wrap_2(text, font, min_size, max_width)
        if lines:
            return lines, min_size

    # (5) Сильно уменьшаем 1 строку — с предупреждением
    preview = text if len(text) <= 40 else text[:37] + "..."
    print(f"  ⚠ {field_label}: текст слишком длинный, ужат до "
          f"{scaled:.1f}pt (желательный минимум {min_size}pt) — «{preview}»")
    return [text], scaled


# ── Отрисовка одного поля ───────────────────────────────────────────────────
def draw_field(page, value, field):
    if not str(value).strip():
        return

    buf  = _font_buf(field["font"])
    font = fitz.Font(fontbuffer=buf)

    text = field.get("prefix", "") + str(value)
    base_size = float(field["size"])

    # Рассчитываем позицию X и layout
    if field.get("x_center") is not None:
        x0, x1 = field["x_center"]
        max_width = x1 - x0
        min_size = float(field.get("min_size", base_size * 0.75))
        allow_wrap = bool(field.get("allow_wrap", False))

        lines, size = _layout_text(text, font, base_size, max_width,
                                   min_size, allow_wrap,
                                   field.get("label", ""))
    else:
        lines, size = [text], base_size

    # Стираем область под нашим полем.
    eb = list(field["erase_bbox"])

    # clip_erase: сужаем erase_bbox до реальной ширины текста (+ запас).
    # Нужно для квалификации, чтобы её erase не задел боковые края
    # верхней строки 2-строчной программы (квалификация узкая в центре,
    # а программа широкая).
    if field.get("clip_erase") and field.get("x_center") is not None:
        x0, x1 = field["x_center"]
        # Если задан x_anchor — сужаем вокруг него (туда же сместится текст);
        # иначе — вокруг геометрической середины линии.
        cx = field.get("x_anchor", (x0 + x1) / 2)
        max_w = max(font.text_length(ln, fontsize=size) for ln in lines)
        half = max_w / 2 + 2.0
        eb[0] = max(x0, cx - half)
        eb[2] = min(x1, cx + half)

    # Многострочный текст: erase расширяется вверх на (N-1)*1.1*size.
    # ВАЖНО: max_y_extension ограничивает, насколько erase может уйти вверх.
    # Для программы при наличии квалификации это нужно, чтобы erase верхней
    # строки не стёр текст квалификации (она нарисована раньше — см. DRAW_ORDER).
    if len(lines) > 1:
        extra = (len(lines) - 1) * size * 1.1
        eb[1] = eb[1] - extra
        if "max_y_top" in field:
            eb[1] = max(eb[1], field["max_y_top"])

    page.add_redact_annot(fitz.Rect(*eb), fill=None)
    page.apply_redactions(graphics=0)

    # Рисуем (одну или несколько) строк.
    tw = fitz.TextWriter(page.rect)
    y_last = field["y"]
    # Порог применения x_anchor по ширине текста относительно ширины линии.
    # Короткие тексты (≤ 60% линии) выравниваем по визуальной оси (anchor),
    # длинные (> 60%) — по геометрической середине линии, как раньше.
    # Это сохраняет старое поведение для текстов, заполняющих почти всю
    # линию (там симметрия относительно линии важнее визуальной оси).
    ANCHOR_MAX_RATIO = 0.60
    for i, line in enumerate(lines):
        y = y_last - (len(lines) - 1 - i) * size * 1.1
        if field.get("x_center") is not None:
            x0, x1 = field["x_center"]
            line_w = x1 - x0
            w = font.text_length(line, fontsize=size)
            anchor = field.get("x_anchor")
            # anchor применим, если он задан, текст достаточно короткий,
            # и при центрировании по anchor он полностью помещается в линию.
            use_anchor = (
                anchor is not None
                and w <= line_w * ANCHOR_MAX_RATIO
                and (anchor - w / 2) >= x0
                and (anchor + w / 2) <= x1
            )
            if use_anchor:
                x = anchor - w / 2
            else:
                # Стандартное геометрическое центрирование между x0 и x1.
                x = x0 + (x1 - x0 - w) / 2
                x = max(x, x0)
        else:
            x = field["x"]
        tw.append((x, y), line, font=font, fontsize=size)
    tw.write_text(page, color=field["color"])


# ── Главная функция ─────────────────────────────────────────────────────────
def fill_diploma(data: dict, output_path: str, diploma_type: str = "bakalavr",
                 qr_text: str = ""):
    if diploma_type not in DIPLOMA_TYPES:
        raise ValueError(
            f"Неизвестный тип диплома: {diploma_type}. "
            f"Допустимые: {', '.join(DIPLOMA_TYPES)}"
        )

    dt = DIPLOMA_TYPES[diploma_type]
    input_file = dt["input_file"]
    if not os.path.exists(input_file):
        # Пробуем resolve относительно директории скрипта и соседнего laureate/
        _dir = os.path.dirname(os.path.abspath(__file__))
        for base in (_dir, os.path.join(_dir, "..", "laureate")):
            candidate = os.path.join(base, input_file)
            if os.path.exists(candidate):
                input_file = os.path.abspath(candidate)
                break
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Файл шаблона не найден: {input_file}")
    for p in (FONT_CAPTION, FONT_BOLD, FONT_BD):
        if not os.path.exists(p):
            raise FileNotFoundError(f"Шрифт не найден: {p}")

    fields = build_fields(diploma_type)

    # Спецрежим: если программа потребует 2 строк (длинный текст) И задана
    # квалификация — обе строки физически не помещаются в стандартных
    # размерах. Уменьшаем программу и квалификацию (РУССКИЙ блок до 7.5pt,
    # АНГЛИЙСКИЙ до 8pt — там зазор сверху от BACHELOR изначально больше),
    # и опускаем baseline квалификации.
    #
    # Расчёт для русского (PT Serif Caption: ascender = 8.31×size/10,
    # descender = 2.29×size/10):
    #   Квалификация 7.5pt baseline=487 → span y=479.2..489.2.
    #   Программа 7.5pt: межстрочный 8.25, верхняя baseline=496.45,
    #   span y=490.2..498.0. Зазор квал↔программа = +1.0 pt (ОК).
    #   Над квалификацией: «присвоена степень БАКАЛАВР» y_bot=477.35.
    #   Зазор сверху = 479.2 - 477.35 = +1.85 pt (комфортно).
    #
    # Расчёт для английского при 8pt не менялся:
    #   Квалификация 8pt baseline=350 → span y=343.4..352.3.
    #   «BACHELOR» y_bot=343.83 → зазор +1.6 pt (приемлемо в v7,
    #   не трогаем).
    def _rus_check_wraps(text, base_size=9.5, max_w=701.73 - 345.31):
        """Проверяю, потребуется ли wrap (приближённо — без построения шрифта)."""
        if not text:
            return False
        # PT Serif Caption ~= 0.55 * size на символ кириллицы. Проверяю грубо:
        return len(text) * 0.55 * base_size > max_w

    def _eng_check_wraps(text, base_size=9.5, max_w=764.02 - 244.90):
        if not text:
            return False
        return len(text) * 0.50 * base_size > max_w

    if data.get("rus_program") and data.get("rus_qualification"):
        if _rus_check_wraps(data["rus_program"]):
            fields["rus_program"] = dict(fields["rus_program"])
            # 7.5pt вместо 8.0pt — даёт +0.7pt зазор сверху от квалификации
            fields["rus_program"]["size"] = 7.5
            fields["rus_program"]["min_size"] = 6.0
            fields["rus_qualification"] = dict(fields["rus_qualification"])
            fields["rus_qualification"]["size"] = 10.0
            fields["rus_qualification"]["min_size"] = 8.0
            fields["rus_qualification"]["clip_erase"] = True
            # baseline 487 (вместо v7=485): на 2pt ниже — больше зазор
            # сверху от «присвоена степень БАКАЛАВР».
            fields["rus_qualification"]["y"] = 487.0
            fields["rus_qualification"]["erase_bbox"] = (143.8, 479.0, 701.8, 489.5)
            # У программы max_y_top = 489.7 (нижняя граница квалификации с зазором)
            fields["rus_program"]["max_y_top"] = 489.7
        else:
            # Программа влезает в 1 строку — стандарт
            fields["rus_program"] = dict(fields["rus_program"])
            fields["rus_program"]["max_y_top"] = 492.0

    if data.get("eng_program") and data.get("eng_qualification"):
        if _eng_check_wraps(data["eng_program"]):
            fields["eng_program"] = dict(fields["eng_program"])
            fields["eng_program"]["size"] = 8.0
            fields["eng_program"]["min_size"] = 6.5
            fields["eng_qualification"] = dict(fields["eng_qualification"])
            fields["eng_qualification"]["size"] = 8.0
            fields["eng_qualification"]["min_size"] = 6.5
            # English: «the Degree of BACHELOR of» y=333-344, линия eng_qual y=355.72.
            # Поднимаем квалификацию выше: baseline=350 (между BACHELOR и линией)
            fields["eng_qualification"]["y"] = 350.0
            fields["eng_qualification"]["erase_bbox"] = (143.8, 344.5, 764.0, 352.0)
            fields["eng_program"]["max_y_top"] = 352.5
        else:
            fields["eng_program"] = dict(fields["eng_program"])
            fields["eng_program"]["max_y_top"] = 358.5

    if data.get("kaz_program") and data.get("kaz_qualification"):
        # У казаха зона между FIO (220.63) и PROG (234.52) = 14pt — 2 строки
        # 9.5pt не влезают. Принудительно 1 строка с адаптивом.
        fields["kaz_program"] = dict(fields["kaz_program"])
        fields["kaz_program"]["allow_wrap"] = False
        fields["kaz_program"]["min_size"] = 6.0

    doc  = fitz.open(input_file)
    page = doc[0]  # заполняем первую страницу; вторая (обратная) — как есть

    for key in DRAW_ORDER:
        if key not in data:
            continue
        value = data[key]
        if not value:
            continue
        field = fields[key]
        if key == "bd_number":
            digits = "".join(c for c in str(value) if c.isdigit())[:11]
            value  = digits.zfill(11)
        draw_field(page, value, field)

    # Предупреждение о неизвестных полях
    known = set(DRAW_ORDER)
    for key in data:
        if key not in known and key in fields:
            print(f"  ⚠ Поле не в DRAW_ORDER, пропущено: {key}")

    # ── QR ──
    if qr_text and qr_text.strip():
        if not _QR_AVAILABLE:
            print("  ⚠ QR пропущен: модуль qr_diploma не найден")
        else:
            insert_qr_on_page(page, qr_text.strip())
            print(f"  ✓ QR вставлен ({len(qr_text)} симв.)")

    doc.save(output_path, garbage=4, deflate=True, deflate_images=True,
             deflate_fonts=True, clean=True)
    print(f"✓ Сохранено → {output_path} (страниц: {len(doc)}, тип: {dt['title']})")


# ── Интерактивный ввод ──────────────────────────────────────────────────────
def ask(prompt, required=True, default=None):
    hint = f" [{default}]" if default else ""
    while True:
        val = input(f"  {prompt}{hint}: ").strip()
        if val:
            return val
        if default is not None:
            return default
        if not required:
            return ""
        print("    (обязательное поле)")


def choose_type():
    print("\nВыберите тип диплома:")
    keys = list(DIPLOMA_TYPES)
    for i, k in enumerate(keys, 1):
        print(f"  {i}. {DIPLOMA_TYPES[k]['title']:25s} ({k})")
    while True:
        val = input("  Номер: ").strip()
        if val.isdigit() and 1 <= int(val) <= len(keys):
            return keys[int(val) - 1]
        if val in keys:
            return val


def main():
    print("=" * 60)
    print("  Заполнение диплома КарУ")
    print("=" * 60)

    diploma_type = choose_type()
    dt = DIPLOMA_TYPES[diploma_type]
    is_magistr = (diploma_type == "magistr")

    print(f"\n── Тип: {dt['title']} ──")
    bd_label = "MD номер" if is_magistr else "BD номер"
    bd = ask(f"{bd_label} (11 цифр)")

    print("\n── ФИО ──")
    fio_kaz = ask("ФИО казахский")
    fio_rus = ask("ФИО русский")
    fio_eng = ask("ФИО английский")

    print("\n── Образовательная программа ──")
    prog_kaz = ask("Программа каз")
    prog_rus = ask("Программа рус")
    prog_eng = ask("Программа eng")

    print("\n── Квалификация ──")
    qual_kaz = ask("Квалификация каз", required=False)
    qual_rus = ask("Квалификация рус", required=False)
    qual_eng = ask("Квалификация eng", required=False)

    if is_magistr:
        print("\n── Направление ──")
        form_kaz = ask("Бағыты (каз, напр: ғылыми-педагогикалық)")
        form_rus = ask("Направление (рус, напр: научно-педагогическое)")
        form_eng = ask("Type of program (eng, напр: scientific-pedagogical)")
    else:
        print("\n── Форма обучения ──")
        form_kaz = ask("Форма каз (напр: күндізгі)")
        form_rus = ask("Форма рус (напр: очное)")
        form_eng = ask("Форма eng (напр: full-time)")

    print("\n── Дата решения ──")
    year2     = ask("Год 2 цифры (напр: 25)")
    day       = ask("День (напр: 11)")
    month_kaz = ask("Месяц каз (напр: маусымдағы)")
    month_rus = ask("Месяц рус (напр: июня)")
    month_eng = ask("Месяц eng (напр: June)")
    protocol  = ask("Протокол № (напр: 68)")

    print("\n── Дата выдачи дубликата (нижняя строка) ──")
    diploma_year  = ask("Год выдачи 4 цифры (напр: 2026)")
    diploma_day   = ask("День выдачи (напр: 12)")
    diploma_month = ask("Месяц выдачи словом каз (напр: наурыз)")
    city          = ask("Город (напр: Қарағанды)", default="Қарағанды")

    print("\n── QR-код ──")
    qr_text = ask("Текст/URL для QR (Enter — пропустить)", required=False)

    data = {
        "bd_number": bd,
        "kaz_fio": fio_kaz, "kaz_program": prog_kaz,
        "kaz_qualification": qual_kaz, "kaz_form": form_kaz,
        "kaz_year": year2, "kaz_day": day,
        "kaz_month": month_kaz, "kaz_protocol": protocol,
        "eng_fio": fio_eng, "eng_program": prog_eng,
        "eng_qualification": qual_eng, "eng_form": form_eng,
        "eng_year": year2, "eng_day": day, "eng_month": month_eng,
        "rus_fio": fio_rus, "rus_program": prog_rus,
        "rus_qualification": qual_rus, "rus_form": form_rus,
        "rus_year": year2, "rus_day": day,
        "rus_month": month_rus, "rus_protocol": protocol,
        "diploma_year": diploma_year, "diploma_day": diploma_day,
        "diploma_month": diploma_month, "city": city,
    }

    safe = fio_kaz.split()[0] if fio_kaz else "diploma"
    output = dt["input_file"].replace(".pdf", f"_{safe}_{bd}.pdf")
    print()
    fill_diploma(data, output, diploma_type, qr_text=qr_text)


if __name__ == "__main__":
    main()
