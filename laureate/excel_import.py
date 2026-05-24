"""
excel_import.py - Импорт документов из шаблонных XLSX.

Поддерживаемые форматы:
  • parse_bakalavr_import   — бакалавр/магистр
  • parse_phd_import        — диплом PhD (докторант)
  • parse_fdo_import        — сертификат педагогической переподготовки (ФДО)
  • parse_minor_import      — сертификат Minor (к диплому бакалавра)
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET


NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _clean(value):
    text = "" if value is None else str(value)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _clean_multiline(value):
    """Как _clean, но СОХРАНЯЕТ переносы строк (\n).

    Используется для полей где может быть несколько ФИО через перенос
    (научные консультанты, рецензенты).
    """
    text = "" if value is None else str(value)
    text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    # Внутри каждой строки схлопываем пробелы, но \n оставляем
    lines = []
    for ln in text.split("\n"):
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        if ln:
            lines.append(ln)
    return "\n".join(lines)


def _digits(value):
    return "".join(ch for ch in _clean(value) if ch.isdigit())


def _column_index(cell_ref):
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def _cell_value(cell, shared_strings):
    value_node = cell.find(f"{{{NS_MAIN}}}v")
    if value_node is None:
        inline = cell.find(f"{{{NS_MAIN}}}is")
        if inline is None:
            return ""
        return "".join(node.text or "" for node in inline.iter() if node.tag.endswith("}t"))

    raw = value_node.text or ""
    if cell.attrib.get("t") == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return raw
    return raw


def _read_workbook(path):
    sheets = {}
    with ZipFile(path) as archive:
        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            sst = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in sst:
                shared_strings.append(
                    "".join(node.text or "" for node in item.iter() if node.tag.endswith("}t"))
                )

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {
            rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships
        }

        sheets_node = workbook.find(f"{{{NS_MAIN}}}sheets")
        if sheets_node is None:
            return sheets

        for sheet in sheets_node:
            name = sheet.attrib.get("name", "")
            rel_id = sheet.attrib.get(f"{{{NS_REL}}}id")
            target = rel_targets.get(rel_id, "")
            if not target:
                continue
            # Нормализуем target: убираем лидирующий слэш, добавляем "xl/" если нужно
            target = target.lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            root = ET.fromstring(archive.read(target))
            sheet_data = root.find(f"{{{NS_MAIN}}}sheetData")
            rows = []
            if sheet_data is not None:
                for row in sheet_data:
                    row_number = int(row.attrib.get("r", "0") or "0")
                    cells = {}
                    max_idx = -1
                    for cell in row:
                        idx = _column_index(cell.attrib.get("r", "A1"))
                        max_idx = max(max_idx, idx)
                        cells[idx] = _cell_value(cell, shared_strings)
                    if max_idx < 0:
                        continue
                    values = [""] * (max_idx + 1)
                    for idx, value in cells.items():
                        # Сохраняем «сырое» значение с переносами строк
                        # (но нормализуем nbsp и CR/LF). Очистка делается
                        # вызывающими парсерами через _clean / _clean_multiline.
                        raw = "" if value is None else str(value)
                        values[idx] = raw.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
                    rows.append((row_number, values))
            sheets[name] = rows
    return sheets


def _sheet_row_map(rows, key_index):
    mapped = {}
    for row_number, values in rows:
        if row_number < 2:
            continue
        key = _clean(values[key_index] if len(values) > key_index else "")
        if key:
            mapped[key] = values
    return mapped


def _pick(*values):
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return ""


def parse_bakalavr_import(path):
    workbook = _read_workbook(path)
    sheet_lang = workbook.get("Лист1") or workbook.get("Sheet1")
    sheet_meta = workbook.get("Лист2") or workbook.get("Sheet2")
    sheet_fallback = workbook.get("Лист3") or workbook.get("Sheet3")

    if not sheet_lang:
        raise ValueError("Не найден лист с языковыми данными (Лист1).")

    meta_by_iin = _sheet_row_map(sheet_meta or [], 0)
    fallback_by_iin = _sheet_row_map(sheet_fallback or [], 23)

    imported = []
    stats = {"bakalavr": 0, "magistr": 0}

    for row_number, row in sheet_lang:
        if row_number < 3:
            continue
        if not any(_clean(value) for value in row):
            continue

        iin = _clean(row[23] if len(row) > 23 else "")
        if not iin:
            continue

        meta = meta_by_iin.get(iin, [])
        fallback = fallback_by_iin.get(iin, [])

        year_full = _pick(meta[7] if len(meta) > 7 else "", datetime.now().year)
        year_digits = _digits(year_full)
        if len(year_digits) >= 4:
            diploma_year = year_digits[:4]
        else:
            diploma_year = str(datetime.now().year)
        year2 = diploma_year[-2:]

        series = _pick(
            meta[8] if len(meta) > 8 else "",
            fallback[25] if len(fallback) > 25 else "",
        ).upper()
        number = _digits(
            _pick(
                meta[9] if len(meta) > 9 else "",
                fallback[26] if len(fallback) > 26 else "",
            )
        )[:11]
        if not number:
            raise ValueError(f"Строка {row_number}: не найден номер диплома.")

        diploma_type = "magistr" if series.startswith("MD") else "bakalavr"
        stats[diploma_type] += 1

        qr_text = _pick(
            meta[12] if len(meta) > 12 else "",
            fallback[27] if len(fallback) > 27 else "",
        )

        data = {
            "bd_number": number,
            "iin": iin,
            "kaz_fio": _pick(row[3] if len(row) > 3 else ""),
            "rus_fio": _pick(row[16] if len(row) > 16 else ""),
            "eng_fio": _pick(row[7] if len(row) > 7 else ""),
            "kaz_program": _pick(row[4] if len(row) > 4 else ""),
            "rus_program": _pick(row[18] if len(row) > 18 else ""),
            "eng_program": _pick(row[9] if len(row) > 9 else ""),
            "kaz_qualification": _pick(row[5] if len(row) > 5 else ""),
            "rus_qualification": _pick(row[17] if len(row) > 17 else ""),
            "eng_qualification": _pick(row[8] if len(row) > 8 else ""),
            "kaz_form": _pick(row[6] if len(row) > 6 else ""),
            "rus_form": _pick(row[19] if len(row) > 19 else ""),
            "eng_form": _pick(row[10] if len(row) > 10 else ""),
            "kaz_year": year2,
            "rus_year": year2,
            "eng_year": year2,
            "kaz_day": _pick(row[0] if len(row) > 0 else "", row[13] if len(row) > 13 else "", row[11] if len(row) > 11 else ""),
            "rus_day": _pick(row[13] if len(row) > 13 else "", row[0] if len(row) > 0 else ""),
            "eng_day": _pick(row[11] if len(row) > 11 else "", row[0] if len(row) > 0 else ""),
            "kaz_month": _pick(row[1] if len(row) > 1 else ""),
            "rus_month": _pick(row[14] if len(row) > 14 else ""),
            "eng_month": _pick(row[12] if len(row) > 12 else ""),
            "kaz_protocol": _pick(row[2] if len(row) > 2 else ""),
            "rus_protocol": _pick(row[15] if len(row) > 15 else "", row[2] if len(row) > 2 else ""),
            "diploma_year": diploma_year,
            "diploma_day": _pick(row[21] if len(row) > 21 else ""),
            "diploma_month": _pick(row[22] if len(row) > 22 else ""),
            "city": "Қарағанды",
        }

        imported.append(
            {
                "row_number": row_number,
                "iin": iin,
                "series": series,
                "diploma_type": diploma_type,
                "data": data,
                "qr_text": qr_text,
                "recipient_label": _pick(data["kaz_fio"], data["rus_fio"], data["eng_fio"]),
            }
        )

    if not imported:
        raise ValueError("В файле не найдено строк для импорта.")

    return {
        "rows": imported,
        "stats": stats,
    }


# ── Парсер: PhD (докторант) ─────────────────────────────────────────────────
#
# Шаблон: «Шаблон.xlsx», 1 лист, 1-я строка — заголовки.
# Колонки (1-based):
#   A=1  Рег номер
#   B=2  Год Выдачи
#   C=3  День выдачи
#   D=4  Месяц Выдачи     (на русском, например «январь»)
#   E=5  № диплома        (11 цифр)
#   F=6  Год дис Каз
#   G=7  День дис каз
#   H=8  Месяц дис Каз
#   I=9  Год Приказ Каз
#   J=10 День приказ каз
#   K=11 Месяц приказ Каз
#   L=12 Приказ № Каз
#   M=13 Фамилия Каз
#   N=14 ИО Каз
#   O=15 Обр пр Каз       (программа)
#   P=16 Тема Каз
#   Q=17 Научные консультанты Каз
#   R=18 Рецензенты Каз
#   S=19 Место защиты каз
#   T=20 Дата защиты Каз
#   U=21 День дис рус
#   V=22 Месяц дис рус
#   W=23 Год дис рус
#   X=24 Приказ Рус (номер)
#   Y=25 День прик рус
#   Z=26 Месяц прик рус
#   AA=27 Год прик рус
#   AB=28 Фамилия Рус
#   AC=29 ИО Рус
#   AD=30 Обр пр Рус
#   AE=31 Тема Рус
#   AF=32 Научные консультанты Рус
#   AG=33 Рецензенты Рус
#   AH=34 Место защиты рус
#   AI=35 Дата защиты Рус
#   AJ=36 День дис Eng
#   AK=37 Месяц дис Eng
#   AL=38 Год дис Eng
#   AM=39 Приказ Eng (номер)
#   AN=40 День прик Eng
#   AO=41 Месяц прик Eng
#   AP=42 Год прик Eng
#   AQ=43 Фамилия Eng
#   AR=44 ИО Eng
#   AS=45 Обр пр Eng
#   AT=46 Тема Eng
#   AU=47 Научные консультанты Eng
#   AV=48 Рецензенты Eng
#   AW=49 Место защиты англ
#   AX=50 Дата защиты Eng
#   AY=51 ИИН
#   AZ=52 QR

def _v(row, idx, multiline=False):
    """Безопасный доступ к 1-based индексу.

    multiline=True — сохраняет переносы строк (для полей с несколькими ФИО).
    """
    i = idx - 1
    if i < 0 or i >= len(row):
        return ""
    if multiline:
        return _clean_multiline(row[i])
    return _clean(row[i])


def parse_phd_import(path):
    """Парсит шаблон.xlsx с докторантами (PhD).

    Каждая строка после заголовка — отдельный диплом.
    Возвращает {"rows": [...], "stats": {"phd": N}}
    """
    workbook = _read_workbook(path)
    sheet = workbook.get("Лист1") or workbook.get("Sheet1")
    if not sheet:
        # fallback на первый лист
        if workbook:
            first_key = next(iter(workbook))
            sheet = workbook[first_key]
        else:
            raise ValueError("В файле нет ни одного листа.")

    imported = []
    stats = {"phd": 0}

    for row_number, row in sheet:
        if row_number < 2:
            continue
        if not any(_clean(value) for value in row):
            continue

        phd_number = _digits(_v(row, 5))[:11]
        if not phd_number:
            # пропускаем пустые строки
            continue

        iin = _digits(_v(row, 51))
        qr_text = _v(row, 52)

        # Дата выдачи (общая для каз/eng/рус)
        issue_year = _digits(_v(row, 2))[:4]
        issue_day = _v(row, 3)
        issue_month_kaz = _v(row, 4)  # на самом деле русский в шаблоне, но используется в нижнем блоке

        # Дата заседания совета
        council_year_kaz = _digits(_v(row, 6))[:4]
        council_day      = _v(row, 7)   # один день для всех языков
        council_month_kaz= _v(row, 8)
        # русский — другой день/месяц/год может быть, но обычно совпадает
        council_day_rus  = _v(row, 21) or council_day
        council_month_rus= _v(row, 22)
        council_year_rus = _digits(_v(row, 23))[:4] or council_year_kaz
        council_day_eng  = _v(row, 36) or council_day
        council_month_eng= _v(row, 37)
        council_year_eng = _digits(_v(row, 38))[:4] or council_year_kaz

        # Дата приказа
        order_year_kaz   = _digits(_v(row, 9))[:4]
        order_day        = _v(row, 10)
        order_month_kaz  = _v(row, 11)
        order_number     = _v(row, 12)

        order_number_rus = _v(row, 24) or order_number
        order_day_rus    = _v(row, 25) or order_day
        order_month_rus  = _v(row, 26)
        order_year_rus   = _digits(_v(row, 27))[:4] or order_year_kaz

        order_number_eng = _v(row, 39) or order_number
        order_day_eng    = _v(row, 40) or order_day
        order_month_eng  = _v(row, 41)
        order_year_eng   = _digits(_v(row, 42))[:4] or order_year_kaz

        # ФИО
        surname_kaz    = _v(row, 13)
        first_name_kaz = _v(row, 14)
        surname_rus    = _v(row, 28)
        first_name_rus = _v(row, 29)
        surname_eng    = _v(row, 43)
        first_name_eng = _v(row, 44)

        # Программа
        program_kaz = _v(row, 15)
        program_rus = _v(row, 30)
        program_eng = _v(row, 45)

        # Тема диссертации
        dissertation_kaz = _v(row, 16)
        dissertation_rus = _v(row, 31)
        dissertation_eng = _v(row, 46)

        # Научные консультанты (multiline — может быть до 4 человек через \n)
        consultants_kaz = _v(row, 17, multiline=True)
        consultants_rus = _v(row, 32, multiline=True)
        consultants_eng = _v(row, 47, multiline=True)

        # Рецензенты (multiline — может быть до 4 человек)
        reviewers_kaz = _v(row, 18, multiline=True)
        reviewers_rus = _v(row, 33, multiline=True)
        reviewers_eng = _v(row, 48, multiline=True)

        # Место защиты — обычная очистка (это одна организация, не список ФИО)
        place_kaz = _v(row, 19)
        place_rus = _v(row, 34)
        place_eng = _v(row, 49)

        # Дата защиты
        defense_date_kaz = _v(row, 20)
        defense_date_rus = _v(row, 35)
        defense_date_eng = _v(row, 50)

        data = {
            "phd_number": phd_number,
            "iin": iin,
            # Дата заседания совета
            "council_year_kaz": council_year_kaz,
            "council_year_eng": council_year_eng,
            "council_year_rus": council_year_rus,
            "council_day": council_day,
            "council_month_kaz": council_month_kaz,
            "council_month_eng": council_month_eng,
            "council_month_rus": council_month_rus,
            # Дата приказа
            "order_year_kaz": order_year_kaz,
            "order_year_eng": order_year_eng,
            "order_year_rus": order_year_rus,
            "order_day": order_day,
            "order_month_kaz": order_month_kaz,
            "order_month_eng": order_month_eng,
            "order_month_rus": order_month_rus,
            "order_number": order_number,
            # ФИО
            "surname_kaz": surname_kaz,
            "surname_eng": surname_eng,
            "surname_rus": surname_rus,
            "first_name_kaz": first_name_kaz,
            "first_name_eng": first_name_eng,
            "first_name_rus": first_name_rus,
            # Программа
            "program_kaz": program_kaz,
            "program_eng": program_eng,
            "program_rus": program_rus,
            # Тема
            "dissertation_kaz": dissertation_kaz,
            "dissertation_eng": dissertation_eng,
            "dissertation_rus": dissertation_rus,
            # Консультанты
            "consultants_kaz": consultants_kaz,
            "consultants_eng": consultants_eng,
            "consultants_rus": consultants_rus,
            # Рецензенты
            "reviewers_kaz": reviewers_kaz,
            "reviewers_eng": reviewers_eng,
            "reviewers_rus": reviewers_rus,
            # Место защиты
            "place_kaz": place_kaz,
            "place_eng": place_eng,
            "place_rus": place_rus,
            # Дата защиты
            "defense_date_kaz": defense_date_kaz,
            "defense_date_eng": defense_date_eng,
            "defense_date_rus": defense_date_rus,
            # Дата выдачи (общая)
            "issue_year": issue_year,
            "issue_day": issue_day,
            "issue_month_kaz": issue_month_kaz,
        }

        recipient_label = (
            (f"{surname_kaz} {first_name_kaz}".strip()) or
            (f"{surname_rus} {first_name_rus}".strip()) or
            (f"{surname_eng} {first_name_eng}".strip())
        )

        stats["phd"] += 1
        imported.append({
            "row_number": row_number,
            "iin": iin,
            "diploma_type": "phd",
            "data": data,
            "qr_text": qr_text,
            "recipient_label": recipient_label,
        })

    if not imported:
        raise ValueError("В файле не найдено строк PhD для импорта.")

    return {"rows": imported, "stats": stats}


# ── Парсер: ФДО (Сертификат педагогической переподготовки) ───────────────────
#
# Шаблон: «ФДО_шаблон.xlsx», 1 лист, 1-я строка — заголовки (повторяющиеся!).
# Колонки 1-30 — каз/рус/eng блок (по 10 колонок на язык, дублируется ФИО):
#   A=1  День (заседание совета каз)
#   B=2  Месяц (каз)
#   C=3  Протокол № (каз)
#   D=4  ФИО (каз)
#   E=5  День (с) — дата начала обучения каз
#   F=6  Месяц (с) — каз
#   G=7  День (по)
#   H=8  Месяц (по)
#   I=9  Образовательная программа (каз)
#   J=10 Кредит
#   K=11 День (заседание совета рус)
#   L=12 Месяц (рус)
#   M=13 Протокол № (рус)
#   N=14 ФИО (рус)
#   O=15 День (с) — рус
#   P=16 Месяц (с) — рус
#   Q=17 День (по) — рус
#   R=18 Месяц (по) — рус
#   S=19 Образовательная программа (рус)
#   T=20 Кредит (рус)
#   U=21 День (заседание совета eng)
#   V=22 Месяц (eng)
#   W=23 Протокол № (eng)
#   X=24 ФИО (eng)
#   Y=25 День (с) — eng
#   Z=26 Месяц (с) — eng
#   AA=27 День (по) — eng
#   AB=28 Месяц (по) — eng
#   AC=29 Образовательная программа (eng)
#   AD=30 Кредит (eng) [может быть пусто, тогда берём из J]
#   AE=31 Рег.номер
#   AF=32 День выдачи
#   AG=33 Месяц выдачи (каз)
#   AH=34 Серия документа (CPR)
#   AI=35 Номер документа

def parse_fdo_import(path):
    """Парсит ФДО_шаблон.xlsx — Сертификат педагогической переподготовки."""
    workbook = _read_workbook(path)
    sheet = workbook.get("Лист1") or workbook.get("Sheet1")
    if not sheet:
        if workbook:
            first_key = next(iter(workbook))
            sheet = workbook[first_key]
        else:
            raise ValueError("В файле нет ни одного листа.")

    imported = []
    stats = {"fdo": 0}

    for row_number, row in sheet:
        if row_number < 2:
            continue
        if not any(_clean(value) for value in row):
            continue

        cert_number = _digits(_v(row, 35))
        cert_series = _v(row, 34) or "CPR"
        if not cert_number:
            continue
        # Нормализуем номер до 11 цифр
        cert_number_norm = cert_number[:11].rjust(11, "0") if len(cert_number) <= 11 else cert_number[:11]

        reg_number = _v(row, 31)

        # Заседание совета (каз/рус/eng)
        council_day_kaz   = _v(row, 1)
        council_month_kaz = _v(row, 2)
        protocol_kaz      = _v(row, 3)
        fio_kaz           = _v(row, 4)
        # дата с-по (каз)
        from_day_kaz   = _v(row, 5)
        from_month_kaz = _v(row, 6)
        to_day_kaz     = _v(row, 7)
        to_month_kaz   = _v(row, 8)
        program_kaz    = _v(row, 9)
        credits_kaz    = _v(row, 10)

        council_day_rus   = _v(row, 11)
        council_month_rus = _v(row, 12)
        protocol_rus      = _v(row, 13)
        fio_rus           = _v(row, 14)
        from_day_rus   = _v(row, 15)
        from_month_rus = _v(row, 16)
        to_day_rus     = _v(row, 17)
        to_month_rus   = _v(row, 18)
        program_rus    = _v(row, 19)
        credits_rus    = _v(row, 20) or credits_kaz

        council_day_eng   = _v(row, 21)
        council_month_eng = _v(row, 22)
        protocol_eng      = _v(row, 23)
        fio_eng           = _v(row, 24)
        from_day_eng   = _v(row, 25)
        from_month_eng = _v(row, 26)
        to_day_eng     = _v(row, 27)
        to_month_eng   = _v(row, 28)
        program_eng    = _v(row, 29)
        credits_eng    = _v(row, 30) or credits_kaz

        # Дата выдачи
        issue_day       = _v(row, 32)
        issue_month_kaz = _v(row, 33)

        data = {
            "cert_series": cert_series,
            "cert_number": cert_number_norm,
            "reg_number": reg_number,
            # KAZ
            "council_day_kaz": council_day_kaz,
            "council_month_kaz": council_month_kaz,
            "protocol_kaz": protocol_kaz,
            "fio_kaz": fio_kaz,
            "from_day_kaz": from_day_kaz,
            "from_month_kaz": from_month_kaz,
            "to_day_kaz": to_day_kaz,
            "to_month_kaz": to_month_kaz,
            "program_kaz": program_kaz,
            "credits_kaz": credits_kaz,
            # RUS
            "council_day_rus": council_day_rus,
            "council_month_rus": council_month_rus,
            "protocol_rus": protocol_rus,
            "fio_rus": fio_rus,
            "from_day_rus": from_day_rus,
            "from_month_rus": from_month_rus,
            "to_day_rus": to_day_rus,
            "to_month_rus": to_month_rus,
            "program_rus": program_rus,
            "credits_rus": credits_rus,
            # ENG
            "council_day_eng": council_day_eng,
            "council_month_eng": council_month_eng,
            "protocol_eng": protocol_eng,
            "fio_eng": fio_eng,
            "from_day_eng": from_day_eng,
            "from_month_eng": from_month_eng,
            "to_day_eng": to_day_eng,
            "to_month_eng": to_month_eng,
            "program_eng": program_eng,
            "credits_eng": credits_eng,
            # ВЫДАЧА
            "issue_day": issue_day,
            "issue_month_kaz": issue_month_kaz,
            # Год выдачи: год от даты приказа (вторая часть). Берём из year по умолчанию = текущий
            "issue_year": str(datetime.now().year),
        }

        recipient_label = fio_kaz or fio_rus or fio_eng

        stats["fdo"] += 1
        imported.append({
            "row_number": row_number,
            "iin": "",
            "diploma_type": "fdo",
            "data": data,
            "qr_text": "",
            "recipient_label": recipient_label,
            "series": cert_series,
        })

    if not imported:
        raise ValueError("В файле не найдено строк ФДО для импорта.")

    return {"rows": imported, "stats": stats}


# ── Парсер: Минор (Сертификат к диплому бакалавра) ────────────────────────────
#
# Шаблон: «Шаблон для печати сертификатов.xlsx», 1 лист, 1-я строка — заголовки.
# Колонки:
#   A=1  № диплома (каз)
#   B=2  CodeKaz (программа каз)
#   C=3  FioKaz (фио каз)
#   D=4  год — год начала (каз)
#   E=5  день — день начала (каз)
#   F=6  месяц — месяц начала (каз)
#   G=7  год — год конца (каз)
#   H=8  день — день конца (каз)
#   I=9  месяц — месяц конца (каз)
#   J=10 Minor KZ — название Minor каз
#   K=11 № диплома (англ)
#   L=12 FioEng
#   M=13 CodeEng
#   N=14 Minor ENG
#   O=15 day (начало eng)
#   P=16 month (начало eng)
#   Q=17 year (начало eng)
#   R=18 day (конец eng)
#   S=19 month (конец eng)
#   T=20 year (конец eng)
#   U=21 № диплома (рус)
#   V=22 FioRus
#   W=23 CodeRus
#   X=24 Minor RUS
#   Y=25 день (начало рус)
#   Z=26 месяц (начало рус)
#   AA=27 год (начало рус)
#   AB=28 день (конец рус)
#   AC=29 месяц (конец рус)
#   AD=30 год (конец рус)
#   AE=31 ИИН выпускника
#   AF=32 Ссылка (QR)

def parse_minor_import(path):
    """Парсит «Шаблон для печати сертификатов.xlsx» — Минор."""
    workbook = _read_workbook(path)
    sheet = workbook.get("Лист1") or workbook.get("Sheet1")
    if not sheet:
        if workbook:
            first_key = next(iter(workbook))
            sheet = workbook[first_key]
        else:
            raise ValueError("В файле нет ни одного листа.")

    imported = []
    stats = {"minor": 0}

    for row_number, row in sheet:
        if row_number < 2:
            continue
        if not any(_clean(value) for value in row):
            continue

        bd_number = _digits(_v(row, 1))[:11]
        if not bd_number:
            continue

        iin = _digits(_v(row, 31))
        qr_text = _v(row, 32)

        # KAZ
        program_kaz = _v(row, 2)
        fio_kaz = _v(row, 3)
        from_year_kaz  = _v(row, 4)
        from_day_kaz   = _v(row, 5)
        from_month_kaz = _v(row, 6)
        to_year_kaz    = _v(row, 7)
        to_day_kaz     = _v(row, 8)
        to_month_kaz   = _v(row, 9)
        minor_kaz      = _v(row, 10)

        # ENG
        fio_eng     = _v(row, 12)
        program_eng = _v(row, 13)
        minor_eng   = _v(row, 14)
        from_day_eng   = _v(row, 15)
        from_month_eng = _v(row, 16)
        from_year_eng  = _v(row, 17)
        to_day_eng     = _v(row, 18)
        to_month_eng   = _v(row, 19)
        to_year_eng    = _v(row, 20)

        # RUS
        fio_rus     = _v(row, 22)
        program_rus = _v(row, 23)
        minor_rus   = _v(row, 24)
        from_day_rus   = _v(row, 25)
        from_month_rus = _v(row, 26)
        from_year_rus  = _v(row, 27)
        to_day_rus     = _v(row, 28)
        to_month_rus   = _v(row, 29)
        to_year_rus    = _v(row, 30)

        data = {
            "bd_number": bd_number,
            "iin": iin,
            # KAZ
            "program_kaz": program_kaz,
            "fio_kaz": fio_kaz,
            "minor_kaz": minor_kaz,
            "from_day_kaz": from_day_kaz,
            "from_month_kaz": from_month_kaz,
            "from_year_kaz": from_year_kaz,
            "to_day_kaz": to_day_kaz,
            "to_month_kaz": to_month_kaz,
            "to_year_kaz": to_year_kaz,
            # ENG
            "program_eng": program_eng,
            "fio_eng": fio_eng,
            "minor_eng": minor_eng,
            "from_day_eng": from_day_eng,
            "from_month_eng": from_month_eng,
            "from_year_eng": from_year_eng,
            "to_day_eng": to_day_eng,
            "to_month_eng": to_month_eng,
            "to_year_eng": to_year_eng,
            # RUS
            "program_rus": program_rus,
            "fio_rus": fio_rus,
            "minor_rus": minor_rus,
            "from_day_rus": from_day_rus,
            "from_month_rus": from_month_rus,
            "from_year_rus": from_year_rus,
            "to_day_rus": to_day_rus,
            "to_month_rus": to_month_rus,
            "to_year_rus": to_year_rus,
            # дата выдачи (Тіркеу нөмірі) — берём дату текущая
            "issue_year": str(datetime.now().year),
            "issue_day": "",
            "issue_month_kaz": "",
            "reg_number": "",
        }

        recipient_label = fio_kaz or fio_rus or fio_eng

        stats["minor"] += 1
        imported.append({
            "row_number": row_number,
            "iin": iin,
            "diploma_type": "minor",
            "data": data,
            "qr_text": qr_text,
            "recipient_label": recipient_label,
        })

    if not imported:
        raise ValueError("В файле не найдено строк Минор для импорта.")

    return {"rows": imported, "stats": stats}
