# Лауреат

Веб-сервис для заполнения дипломов Карагандинского университета им. Е.А. Букетова.

## Возможности

**4 типа дипломов:**
- Бакалавр (обычный)
- Бакалавр с отличием (ҮЗДІК)
- Магистр
- Доктор PhD (3 параллельные колонки каз/eng/рус, 50+ полей)

**Авторизация и роли:**
- **admin** — единственный супер-юзер (создаётся при первом запуске: `admin/admin`).
  Управляет учётными записями редакторов и печатников, видит все документы.
- **editor** — заполняет данные диплома, сохраняет как черновик, редактирует,
  отправляет в печать, может отозвать обратно в черновик.
- **printer** — видит очередь готовых к печати документов с комментариями
  редактора, скачивает PDF, отмечает как «напечатано».

**Workflow документа:** `draft → ready_for_print → printed`.

## Установка

```bash
cd laureate/
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py    # http://127.0.0.1:5000
```

При первом запуске создаётся `laureate.db` (SQLite) и пользователь `admin/admin`.
**Сразу смените пароль через UI** (`/admin/users` → новый пароль для admin).

## Структура

```
laureate/
├── app.py              Flask: маршруты + auth + workflow
├── db.py               SQLite (stdlib, без ORM): users, documents
├── templates.py        HTML-шаблоны со встроенным CSS (без фреймворков)
├── fill_diploma.py     Бакалавр / с отличием / магистр
├── fill_diploma_phd.py PhD (3-колоночная структура)
├── qr_diploma.py       Универсальный модуль QR
├── fonts/              PT Serif Caption + PT Serif Bold
├── diplomas/           4 PDF-шаблона
├── outputs/            Сгенерированные PDF
├── laureate.db         SQLite (создаётся автоматически)
├── requirements.txt
└── README.md
```

## Маршруты

**Публичные:**
- `GET /login`, `POST /login`, `GET /logout`
- `GET /healthz` — `{"status": "ok"}`

**Editor + admin:**
- `GET /` — список документов (admin видит все)
- `GET /new` — выбор типа диплома
- `GET|POST /new/bakalavr` — форма для бакалавра/магистра
- `GET|POST /new/phd` — форма для PhD
- `GET|POST /doc/<id>/edit` — редактирование (только если не printed)
- `GET /doc/<id>/preview` — открыть PDF в браузере
- `GET /doc/<id>/download` — скачать PDF
- `POST /doc/<id>/send` — отправить в печать
- `POST /doc/<id>/recall` — вернуть из печати в черновик
- `POST /doc/<id>/delete` — удалить (если не printed)

**Printer + admin:**
- `GET /print` — очередь готовых + история печати
- `POST /print/<id>/done` — пометить как напечатано

**Admin:**
- `GET|POST /admin/users` — список + форма создания
- `POST /admin/users/<id>/delete`
- `POST /admin/users/<id>/pwd` — сменить пароль

## Цветовая схема UI

- Фон: `#f7f7f5` (тёплый светлый)
- Текст: `#1a1d24`
- КарУ-синий: `#1f3a8a`
- КарУ-бордовый: `#7c1c2c`

## Системные шрифты

- **PT Serif Caption + Bold** — основной (в `fonts/`)
- **DejaVu Sans ExtraLight** — для номеров бакалавра/магистра (`fonts-dejavu`)
- **Carlito Regular** — для номера PhD (`fonts-crosextra-carlito`, open-source аналог Calibri)

На Linux пакеты ставятся: `apt install fonts-dejavu fonts-crosextra-carlito`.

## Деплой в продакшен

Flask dev-сервер (`app.run`) для прода не годится. Через gunicorn:

```bash
pip install gunicorn
LAUREATE_SECRET=$(openssl rand -hex 32) gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

За nginx с https. SQLite файл `laureate.db` положите в защищённую директорию.
