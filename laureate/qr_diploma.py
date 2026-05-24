"""
qr_diploma.py — Генерация QR-кода для диплома.

QR-зона в шаблонах диплома КарУ — это квадрат 110.55 × 110.55 pt
в позиции (707.01, 442.52) – (817.56, 553.07). Одинаковый во всех трёх
шаблонах (bakalavr / bakalavr_honors / magistr).

Функции:
  • generate_qr_image(text, ...) — сгенерировать PIL.Image нужного размера.
  • insert_qr_on_page(page, text, ...) — вставить QR на страницу PDF
    точно в зону 110.55 × 110.55 pt.

QR генерируется с высоким разрешением (по умолчанию 600 px) чтобы при
печати не было рваных краёв, а потом вписывается в целевую зону
PDF-рендером через page.insert_image.
"""

import io
import fitz
import qrcode
from qrcode.constants import ERROR_CORRECT_M


# Координаты QR-зоны в шаблоне (одинаковы для всех трёх типов дипломов).
# Проверены через page.get_drawings() — это реальная рамка в PDF.
QR_RECT = fitz.Rect(707.0119, 442.5211, 817.5631, 553.0723)   # 110.55 × 110.55 pt


def generate_qr_image(
    text: str,
    pixel_size: int = 600,
    border: int = 1,
    error_correction=ERROR_CORRECT_M,
) -> bytes:
    """
    Генерирует QR-код заданного текста и возвращает PNG-байты.

    • pixel_size — желаемая сторона QR в пикселях (600 = высокое разрешение
      для чёткой печати; при 110 pt = ~38.9 мм это даёт ~392 dpi, что
      с запасом хватает типографии).
    • border — ширина тихой зоны вокруг QR в модулях (по стандарту ≥4,
      но т.к. фон светлый и QR маленький, 1-2 обычно достаточно;
      если нужна максимальная совместимость сканеров — ставьте 4).
    • error_correction — уровень избыточности (M = 15%, допустимо
      повреждение части кода; если QR будет печататься на большой
      площади или вероятны загрязнения — лучше H = 30%).
    """
    qr = qrcode.QRCode(
        version=None,                    # автоподбор минимальной версии
        error_correction=error_correction,
        border=border,
        box_size=10,                     # временное, ниже ресайзим до pixel_size
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img = img.convert("RGB")

    # Приводим точно к нужному размеру (без интерполяции — nearest, чтобы
    # чёрные модули оставались чёткими).
    from PIL import Image
    if img.size != (pixel_size, pixel_size):
        img = img.resize((pixel_size, pixel_size), Image.NEAREST)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def insert_qr_on_page(
    page: "fitz.Page",
    text: str,
    rect: fitz.Rect = None,
    pixel_size: int = 600,
    border: int = 1,
    error_correction=ERROR_CORRECT_M,
    remove_placeholder: bool = True,
):
    """
    Вставляет QR-код в заданный прямоугольник на странице PDF.

    • text  — содержимое QR.
    • rect  — зона в PDF-координатах (по умолчанию QR_RECT = правый
      нижний квадрат диплома 110.55 × 110.55 pt).
    • remove_placeholder=True — стирает шаблонный текст «QR» под зоной
      перед вставкой изображения.
    """
    if rect is None:
        rect = QR_RECT

    if remove_placeholder:
        # Стираем текст «QR» (~24pt, цвет rgb(109,110,112)) под зоной.
        # graphics=0 сохраняет рамку прямоугольника.
        page.add_redact_annot(rect, fill=None)
        page.apply_redactions(graphics=0)

    png_bytes = generate_qr_image(text, pixel_size=pixel_size, border=border,
                                  error_correction=error_correction)
    page.insert_image(rect, stream=png_bytes, keep_proportion=True, overlay=True)


# ── Быстрая проверка из командной строки ────────────────────────────────────
if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "https://example.kz/diploma/00021884825"
    png = generate_qr_image(text)
    with open("qr_preview.png", "wb") as f:
        f.write(png)
    print(f"✓ qr_preview.png ({len(png)} байт) — текст: {text}")
    print(f"  Целевой размер в PDF: {QR_RECT.width:.2f} × {QR_RECT.height:.2f} pt "
          f"(~{QR_RECT.width * 0.352778:.2f} × {QR_RECT.height * 0.352778:.2f} мм)")
