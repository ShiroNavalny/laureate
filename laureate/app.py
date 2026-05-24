"""
Лауреат — веб-сервис для заполнения дипломов КарУ.

Архитектура:
  • SQLite (db.py) для хранения пользователей и документов
  • Flask + Flask-Login для аутентификации
  • 3 роли: admin / editor / printer
  • Workflow документа: draft → ready_for_print → printed

Маршруты см. README.md
"""

import os
import platform
import secrets
import shutil
import threading
import time
import uuid
from io import BytesIO
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import fitz
from flask import (Flask, request, redirect, url_for, send_file, abort,
                   render_template_string, flash, send_from_directory, session,
                   jsonify)
from flask_login import (LoginManager, login_user, logout_user, current_user,
                         login_required, UserMixin)

import db
import excel_import
import fill_diploma as fd
import fill_diploma_phd as fd_phd
import fill_diploma_fdo as fd_fdo
import fill_diploma_minor as fd_minor
from templates import (LAYOUT, SOFT_NAV_HTML, LOGIN_HTML, INDEX_HTML, NEW_TYPE_HTML,
                       FORM_BAKALAVR_HTML, FORM_PHD_HTML, IMPORT_BAKALAVR_HTML,
                       IMPORT_PHD_HTML, IMPORT_FDO_HTML, IMPORT_MINOR_HTML,
                       FORM_FDO_HTML, FORM_MINOR_HTML,
                       ARCHIVE_HTML,
                       PRINT_QUEUE_HTML, ADMIN_USERS_HTML, ADMIN_SYSTEM_HTML,
                       ADMIN_LOGS_HTML,
                       ERROR_HTML)


app = Flask(__name__)
APP_DIR = os.path.dirname(__file__)
DEFAULT_SECRET = "dev-secret-please-change"
CSRF_SESSION_KEY = "csrf_token"

app.secret_key = os.environ.get("LAUREATE_SECRET", DEFAULT_SECRET)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("LAUREATE_SECURE_COOKIES") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,
)

OUTPUT_DIR = os.path.join(APP_DIR, "outputs")
ADMIN_FILE_ROOT = OUTPUT_DIR
os.makedirs(OUTPUT_DIR, exist_ok=True)

db.init_db()
db.purge_expired_printed_files()

IMPORT_JOB_TTL_SECONDS = 60 * 60 * 6
IMPORT_JOBS = {}
IMPORT_JOBS_LOCK = threading.Lock()


# ── Auth ────────────────────────────────────────────────────────────────────

class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.role = row["role"]

    @property
    def is_admin(self):   return self.role == "admin"
    @property
    def is_editor(self):  return self.role in ("admin", "editor")
    @property
    def is_printer(self): return self.role in ("admin", "printer")


login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Войдите для доступа."


@login_manager.user_loader
def load_user(uid):
    row = db.get_user_by_id(int(uid))
    return User(row) if row else None


def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        @login_required
        def wrapper(*a, **kw):
            if current_user.role not in roles and not current_user.is_admin:
                return render(ERROR_HTML, msg="Доступ запрещён."), 403
            return fn(*a, **kw)
        return wrapper
    return deco


def format_bytes(num_bytes):
    size = float(num_bytes or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024


def format_percent(value):
    return f"{value:.1f}%"


def format_seconds(seconds):
    total = int(seconds or 0)
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days} д {hours} ч"
    if hours:
        return f"{hours} ч {minutes} мин"
    return f"{minutes} мин"


def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(24)
        session[CSRF_SESSION_KEY] = token
    return token


def get_csrf_input():
    token = get_csrf_token()
    return f'<input type="hidden" name="csrf_token" value="{token}">'


def is_autosave_request():
    return request.form.get("action") == "autosave"


def is_soft_navigation_request():
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        and request.headers.get("X-Soft-Navigation") == "1"
    )


def autosave_error(message, status=400):
    return jsonify({"ok": False, "error": message}), status


def autosave_success(*, doc_id, message):
    doc = db.get_document(doc_id)
    payload = {
        "ok": True,
        "doc_id": doc_id,
        "message": message,
        "edit_url": url_for("edit_doc", doc_id=doc_id),
        "preview_url": url_for("doc_preview", doc_id=doc_id) if doc and doc.get("file_path") else None,
        "preview_image_url": url_for("doc_preview_image", doc_id=doc_id) if doc and doc.get("file_path") else None,
        "download_url": url_for("doc_download", doc_id=doc_id) if doc and doc.get("file_path") else None,
        "saved_at": datetime.now().strftime("%H:%M:%S"),
    }
    return jsonify(payload)


def render(body, **ctx):
    """Рендерит body_html внутри LAYOUT.

    Двухэтапный рендер: сначала body со всеми контекстными переменными,
    потом результат подставляется в LAYOUT как готовый HTML. Без этого
    Jinja2 не обработает {% %} конструкции в body, потому что |safe
    препятствует повторной интерпретации.
    """
    ctx.setdefault("print_retention_days", db.get_print_retention_days())
    ctx.setdefault("csrf_token", get_csrf_token())
    ctx.setdefault("csrf_input", get_csrf_input())
    body_rendered = render_template_string(body, **ctx)
    if is_soft_navigation_request() and current_user.is_authenticated:
        partial_html = render_template_string(SOFT_NAV_HTML, body_html=body_rendered, **ctx)
        response = app.response_class(partial_html, mimetype="text/html")
        response.headers["X-App-Shell"] = "partial"
        return response
    return render_template_string(LAYOUT, body_html=body_rendered, **ctx)


def prepare_document(doc, retention_days=None):
    if not doc:
        return None
    prepared = dict(doc)
    prepared["has_print_issue"] = bool((prepared.get("print_issue_note") or "").strip())
    expires_at = db.get_print_file_expires_at(prepared, retention_days=retention_days)
    prepared["expires_at"] = expires_at.strftime("%Y-%m-%d %H:%M") if expires_at else None
    prepared["hidden_by_retention"] = db.is_printed_document_hidden(
        prepared, retention_days=retention_days
    )
    prepared["file_available"] = bool(prepared.get("file_path"))
    return prepared


def prepare_documents(rows, *, include_hidden=False):
    retention_days = db.get_print_retention_days()
    docs = [prepare_document(dict(row), retention_days=retention_days) for row in rows]
    if include_hidden:
        return docs
    return [doc for doc in docs if not doc["hidden_by_retention"]]


def _read_proc_kb_value(path, key):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(key):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _read_proc_uptime_seconds():
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as f:
            return float(f.read().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def collect_output_stats():
    file_count = 0
    total_size = 0
    for root, _, files in os.walk(OUTPUT_DIR):
        for filename in files:
            file_count += 1
            path = os.path.join(root, filename)
            try:
                total_size += os.path.getsize(path)
            except OSError:
                continue
    return {"count": file_count, "size_bytes": total_size, "size_text": format_bytes(total_size)}


def collect_system_stats():
    cpu_count = os.cpu_count() or 1
    load1, load5, load15 = os.getloadavg()
    load_pct = min((load1 / cpu_count) * 100, 999.0)

    mem_total = _read_proc_kb_value("/proc/meminfo", "MemTotal:")
    mem_avail = _read_proc_kb_value("/proc/meminfo", "MemAvailable:")
    memory = None
    if mem_total and mem_avail is not None:
        used = max(mem_total - mem_avail, 0)
        pct = (used / mem_total) * 100 if mem_total else 0
        memory = {
            "used_bytes": used,
            "total_bytes": mem_total,
            "free_bytes": mem_avail,
            "used_text": format_bytes(used),
            "total_text": format_bytes(mem_total),
            "free_text": format_bytes(mem_avail),
            "pct": pct,
            "pct_text": format_percent(pct),
        }

    disk_total, disk_used, disk_free = shutil.disk_usage(APP_DIR)
    disk_pct = (disk_used / disk_total) * 100 if disk_total else 0

    process_rss = _read_proc_kb_value("/proc/self/status", "VmRSS:")
    uptime_seconds = _read_proc_uptime_seconds()
    output_stats = collect_output_stats()
    db_size = os.path.getsize(db.DB_PATH) if os.path.exists(db.DB_PATH) else 0
    doc_counts = db.count_documents_by_status()
    user_counts = db.count_users_by_role()

    security_flags = [
        {
            "label": "CSRF на POST",
            "value": "Включено",
            "state": "ok",
        },
        {
            "label": "Cookie Secure",
            "value": "Да" if app.config["SESSION_COOKIE_SECURE"] else "Нет",
            "state": "ok" if app.config["SESSION_COOKIE_SECURE"] else "warn",
        },
        {
            "label": "Секрет приложения",
            "value": "Надёжный" if app.secret_key != DEFAULT_SECRET else "Дефолтный",
            "state": "ok" if app.secret_key != DEFAULT_SECRET else "danger",
        },
    ]

    return {
        "host": platform.node() or "localhost",
        "platform": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "cpu_count": cpu_count,
        "load": {
            "one": f"{load1:.2f}",
            "five": f"{load5:.2f}",
            "fifteen": f"{load15:.2f}",
            "pct": load_pct,
            "pct_text": format_percent(load_pct),
        },
        "memory": memory,
        "disk": {
            "used_bytes": disk_used,
            "total_bytes": disk_total,
            "free_bytes": disk_free,
            "used_text": format_bytes(disk_used),
            "total_text": format_bytes(disk_total),
            "free_text": format_bytes(disk_free),
            "pct": disk_pct,
            "pct_text": format_percent(disk_pct),
        },
        "process": {
            "rss_bytes": process_rss or 0,
            "rss_text": format_bytes(process_rss or 0),
            "uptime_text": format_seconds(uptime_seconds) if uptime_seconds is not None else "—",
        },
        "storage": {
            "db_text": format_bytes(db_size),
            "db_bytes": db_size,
            "outputs_count": output_stats["count"],
            "outputs_text": output_stats["size_text"],
        },
        "documents": doc_counts,
        "users": user_counts,
        "security_flags": security_flags,
    }


def resolve_admin_path(raw_rel_path=""):
    cleaned = (raw_rel_path or "").strip().replace("\\", "/").lstrip("/")
    candidate = os.path.realpath(os.path.join(ADMIN_FILE_ROOT, cleaned))
    root_real = os.path.realpath(ADMIN_FILE_ROOT)
    if os.path.commonpath([root_real, candidate]) != root_real:
        abort(403)
    rel_path = os.path.relpath(candidate, root_real)
    rel_path = "" if rel_path == "." else rel_path.replace(os.sep, "/")
    return candidate, rel_path


def build_breadcrumbs(rel_path):
    crumbs = [{"label": "PDF", "rel_path": ""}]
    if not rel_path:
        return crumbs
    parts = rel_path.split("/")
    acc = []
    for part in parts:
        acc.append(part)
        crumbs.append({"label": part, "rel_path": "/".join(acc)})
    return crumbs


def build_file_browser(rel_path):
    target_dir, normalized_rel = resolve_admin_path(rel_path)
    if not os.path.isdir(target_dir):
        abort(404)

    entries = []
    try:
        with os.scandir(target_dir) as iterator:
            for entry in iterator:
                if entry.is_symlink():
                    continue
                try:
                    stat = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                is_dir = entry.is_dir(follow_symlinks=False)
                ext = os.path.splitext(entry.name)[1].lower()
                child_rel = "/".join(filter(None, [normalized_rel, entry.name]))
                entries.append({
                    "name": entry.name,
                    "rel_path": child_rel,
                    "is_dir": is_dir,
                    "is_pdf": (not is_dir) and ext == ".pdf",
                    "type_label": "Папка" if is_dir else (os.path.splitext(entry.name)[1].lstrip(".") or "файл"),
                    "size_text": "—" if is_dir else format_bytes(stat.st_size),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
    except OSError:
        abort(404)

    entries.sort(key=lambda item: (not item["is_dir"], item["name"].lower()))
    parent_rel = ""
    if normalized_rel:
        parent_rel = normalized_rel.rsplit("/", 1)[0] if "/" in normalized_rel else ""

    file_count = sum(1 for item in entries if not item["is_dir"])
    dir_count = sum(1 for item in entries if item["is_dir"])

    return {
        "current_rel": normalized_rel,
        "current_label": "/" if not normalized_rel else f"/{normalized_rel}",
        "parent_rel": parent_rel,
        "breadcrumbs": build_breadcrumbs(normalized_rel),
        "entries": entries,
        "file_count": file_count,
        "dir_count": dir_count,
    }


@app.before_request
def cleanup_expired_printed_files():
    db.purge_expired_printed_files()


@app.before_request
def enforce_csrf_for_post():
    if request.method != "POST":
        return None
    expected = session.get(CSRF_SESSION_KEY)
    provided = request.form.get("csrf_token", "")
    if expected and secrets.compare_digest(provided, expected):
        return None
    return render(
        ERROR_HTML,
        msg="Защитный токен формы устарел. Обновите страницу и повторите действие.",
    ), 400


@app.after_request
def apply_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self'; "
        "frame-ancestors 'none'",
    )
    if response.mimetype == "text/html":
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.route("/assets/<path:filename>")
def asset_file(filename):
    allowed = {"LaureatLogo.png", "LaureatMain.png", "favicon.ico"}
    if filename not in allowed:
        abort(404)
    return send_from_directory(os.path.dirname(__file__), filename)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.dirname(__file__),
        "favicon.ico",
        mimetype="image/x-icon",
    )


def can_access_document(doc):
    if not doc:
        return False
    if current_user.is_admin:
        return True
    if db.is_printed_document_hidden(doc):
        return False
    return bool(current_user.is_authenticated)


def sanitize_storage_name(value, fallback="batch"):
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in str(value or ""))
    cleaned = cleaned.strip("._")
    return cleaned[:80] or fallback


def build_source_meta(*, kind="", label="", filename="", folder="", row_number=None):
    return {
        "source_kind": kind or "",
        "source_label": label or "",
        "source_filename": filename or "",
        "source_folder": folder or "",
        "source_row_number": row_number,
    }


def source_meta_from_doc(doc):
    if not doc:
        return build_source_meta()
    return build_source_meta(
        kind=doc.get("source_kind", ""),
        label=doc.get("source_label", ""),
        filename=doc.get("source_filename", ""),
        folder=doc.get("source_folder", ""),
        row_number=doc.get("source_row_number"),
    )


def normalize_document_series(value):
    normalized = "".join(ch for ch in str(value or "").upper().strip() if ch.isalnum())
    return normalized[:32]


def extract_document_series_label(doc):
    if not doc:
        return ""
    raw = str(doc.get("document_series", "") or "").strip()
    if raw:
        return raw
    data = doc.get("data") or {}
    if isinstance(data, dict):
        raw = str(data.get("series", "") or "").strip()
        if raw:
            return raw
    raw = str(doc.get("source_label", "") or "").strip()
    if raw:
        return raw
    return ""


def get_document_series(doc):
    return normalize_document_series(extract_document_series_label(doc))


def get_series_label(series):
    return str(series or "").strip() or "Без серии"


def build_document_groups(docs):
    groups = []
    buckets = {}
    for doc in docs:
        series_key = get_document_series(doc)
        series_label = extract_document_series_label(doc)
        key = series_key or "__no_series__"
        group = buckets.get(key)
        if group is None:
            group = {
                "key": key,
                "series": series_key,
                "label": get_series_label(series_label),
                "docs": [],
                "total": 0,
                "draft_count": 0,
                "ready_count": 0,
                "printed_count": 0,
                "issue_count": 0,
            }
            buckets[key] = group
            groups.append(group)
        group["docs"].append(doc)
        group["total"] += 1
        if doc.get("status") == "draft":
            group["draft_count"] += 1
        elif doc.get("status") == "ready_for_print":
            group["ready_count"] += 1
        elif doc.get("status") == "printed":
            group["printed_count"] += 1
        if doc.get("has_print_issue"):
            group["issue_count"] += 1

    groups.sort(
        key=lambda item: (
            item["series"] == "",
            item["label"].casefold(),
            -(item["docs"][0].get("id") or 0),
        )
    )
    for group in groups:
        group["default_open"] = False
    return groups


def prune_import_jobs(now_ts=None):
    now_ts = now_ts or time.time()
    with IMPORT_JOBS_LOCK:
        expired = [
            job_id
            for job_id, job in IMPORT_JOBS.items()
            if now_ts - job.get("updated_ts", now_ts) > IMPORT_JOB_TTL_SECONDS
        ]
        for job_id in expired:
            IMPORT_JOBS.pop(job_id, None)


def create_import_job(*, user_id, batch_label, original_filename):
    prune_import_jobs()
    job_id = uuid.uuid4().hex
    now_ts = time.time()
    job = {
        "job_id": job_id,
        "user_id": user_id,
        "batch_label": batch_label,
        "original_filename": original_filename,
        "state": "queued",
        "stage": "Подготовка",
        "message": "Файл принят, подготавливаю импорт.",
        "total": 0,
        "processed": 0,
        "created": 0,
        "stats": {"bakalavr": 0, "magistr": 0},
        "error": "",
        "updated_ts": now_ts,
        "created_ts": now_ts,
        "redirect_url": url_for("index"),
    }
    with IMPORT_JOBS_LOCK:
        IMPORT_JOBS[job_id] = job
    return job_id


def update_import_job(job_id, **changes):
    with IMPORT_JOBS_LOCK:
        job = IMPORT_JOBS.get(job_id)
        if not job:
            return
        job.update(changes)
        job["updated_ts"] = time.time()


def get_import_job(job_id):
    prune_import_jobs()
    with IMPORT_JOBS_LOCK:
        job = IMPORT_JOBS.get(job_id)
        if not job:
            return None
        return dict(job)


def create_import_batch_dir(label):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{stamp}_{sanitize_storage_name(label)}_{uuid.uuid4().hex[:6]}"
    rel_dir = os.path.join("imports", folder_name)
    abs_dir = os.path.join(OUTPUT_DIR, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    return abs_dir, rel_dir.replace(os.sep, "/")


def resolve_source_output_dir(doc):
    folder = (doc or {}).get("source_folder", "")
    normalized = str(folder or "").strip().replace("/", os.sep)
    if not normalized:
        return None
    root = os.path.abspath(OUTPUT_DIR)
    target = os.path.abspath(os.path.join(root, normalized))
    try:
        if os.path.commonpath([root, target]) != root:
            return None
    except ValueError:
        return None
    os.makedirs(target, exist_ok=True)
    return target


def run_bakalavr_import_job(job_id, *, user_id, batch_label, original_filename, source_path, batch_dir, batch_rel):
    created_ids = []
    try:
        update_import_job(
            job_id,
            state="running",
            stage="Чтение Excel",
            message="Читаю и разбираю файл Excel.",
        )
        parsed = excel_import.parse_bakalavr_import(source_path)
        if os.path.exists(source_path):
            try:
                os.remove(source_path)
            except OSError:
                pass
        rows = parsed["rows"]
        stats = parsed["stats"]
        total = len(rows)
        update_import_job(
            job_id,
            total=total,
            stats=stats,
            stage="Генерация PDF",
            message=f"Найдено {total} записей. Начинаю генерацию PDF.",
        )

        for index, item in enumerate(rows, start=1):
            pdf_path = _generate_pdf(
                item["diploma_type"],
                item["data"],
                item["qr_text"],
                None,
                output_dir=batch_dir,
            )
            series_label = (batch_label or item.get("series") or "").strip()
            payload = dict(item["data"])
            payload["diploma_type"] = item["diploma_type"]
            payload["series"] = series_label
            doc_id = db.create_document(
                diploma_type=item["diploma_type"],
                data=payload,
                qr_text=item["qr_text"],
                file_path=pdf_path,
                recipient_label=item["recipient_label"],
                created_by=user_id,
                comment="",
                status="draft",
                person_iin=item["iin"],
                diploma_number=payload.get("bd_number", ""),
                document_series=series_label,
                **build_source_meta(
                    kind="excel",
                    label=batch_label,
                    filename=original_filename,
                    folder=batch_rel,
                    row_number=item["row_number"],
                ),
            )
            created_ids.append(doc_id)
            update_import_job(
                job_id,
                processed=index,
                created=index,
                message=f"Создано {index} из {total}: {item['recipient_label'] or 'документ'}",
            )

        parts = [f"{len(created_ids)} файлов"]
        if stats.get("bakalavr"):
            parts.append(f"бакалавр: {stats['bakalavr']}")
        if stats.get("magistr"):
            parts.append(f"магистр: {stats['magistr']}")
        update_import_job(
            job_id,
            state="succeeded",
            stage="Готово",
            processed=total,
            created=len(created_ids),
            message=f"Импорт завершён: {', '.join(parts)}.",
        )
    except Exception as exc:
        for doc_id in created_ids:
            file_path = db.delete_document(doc_id)
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        shutil.rmtree(batch_dir, ignore_errors=True)
        update_import_job(
            job_id,
            state="failed",
            stage="Ошибка",
            error=str(exc),
            message=str(exc),
        )


def run_generic_import_job(job_id, *, kind, parser, user_id, batch_label,
                           original_filename, source_path, batch_dir, batch_rel):
    """Универсальный воркер импорта PhD / ФДО / Минор из XLSX.

    `kind` — короткое имя типа документа (для статистики и логов).
    `parser` — функция, парсящая файл и возвращающая
              {"rows": [...], "stats": {...}}.
    """
    created_ids = []
    try:
        update_import_job(
            job_id,
            state="running",
            stage="Чтение Excel",
            message="Читаю и разбираю файл Excel.",
        )
        parsed = parser(source_path)
        if os.path.exists(source_path):
            try:
                os.remove(source_path)
            except OSError:
                pass
        rows = parsed["rows"]
        stats = parsed.get("stats", {})
        total = len(rows)
        update_import_job(
            job_id,
            total=total,
            stats=stats,
            stage="Генерация PDF",
            message=f"Найдено {total} записей. Начинаю генерацию PDF.",
        )

        for index, item in enumerate(rows, start=1):
            pdf_path = _generate_pdf(
                item["diploma_type"],
                item["data"],
                item.get("qr_text", ""),
                None,
                output_dir=batch_dir,
            )
            series_label = (batch_label or item.get("series") or "").strip()
            payload = dict(item["data"])
            payload["diploma_type"] = item["diploma_type"]
            payload["series"] = series_label

            # Номер диплома зависит от типа
            if item["diploma_type"] == "phd":
                diploma_number = payload.get("phd_number", "")
            elif item["diploma_type"] == "fdo":
                diploma_number = payload.get("cert_number", "")
            elif item["diploma_type"] == "minor":
                diploma_number = payload.get("bd_number", "")
            else:
                diploma_number = payload.get("bd_number", "")

            doc_id = db.create_document(
                diploma_type=item["diploma_type"],
                data=payload,
                qr_text=item.get("qr_text", ""),
                file_path=pdf_path,
                recipient_label=item.get("recipient_label", ""),
                created_by=user_id,
                comment="",
                status="draft",
                person_iin=item.get("iin", ""),
                diploma_number=diploma_number,
                document_series=series_label,
                **build_source_meta(
                    kind="excel",
                    label=batch_label,
                    filename=original_filename,
                    folder=batch_rel,
                    row_number=item["row_number"],
                ),
            )
            created_ids.append(doc_id)
            update_import_job(
                job_id,
                processed=index,
                created=index,
                message=f"Создано {index} из {total}: {item.get('recipient_label') or 'документ'}",
            )

        parts = [f"{len(created_ids)} файлов"]
        for stat_key, stat_value in stats.items():
            if stat_value:
                parts.append(f"{stat_key}: {stat_value}")
        update_import_job(
            job_id,
            state="succeeded",
            stage="Готово",
            processed=total,
            created=len(created_ids),
            message=f"Импорт завершён: {', '.join(parts)}.",
        )
    except Exception as exc:
        for doc_id in created_ids:
            file_path = db.delete_document(doc_id)
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        shutil.rmtree(batch_dir, ignore_errors=True)
        update_import_job(
            job_id,
            state="failed",
            stage="Ошибка",
            error=str(exc),
            message=str(exc),
        )


def list_series_documents_for_user(series, *, status=None):
    normalized_series = normalize_document_series(series)
    docs = prepare_documents(
        db.list_documents(
            status=status,
            created_by=None if current_user.is_admin else current_user.id,
            limit=5000,
            order_field="created_at",
        ),
        include_hidden=True,
    )
    return [doc for doc in docs if get_document_series(doc) == normalized_series]


def parse_selected_doc_ids(values):
    raw_values = values if isinstance(values, list) else [values]
    doc_ids = []
    seen = set()
    for raw_value in raw_values:
        for part in str(raw_value or "").replace(";", ",").split(","):
            part = part.strip()
            if not part:
                continue
            try:
                doc_id = int(part)
            except ValueError:
                continue
            if doc_id <= 0 or doc_id in seen:
                continue
            seen.add(doc_id)
            doc_ids.append(doc_id)
    return doc_ids


def build_bulk_zip_response(docs, *, archive_prefix):
    archive_buffer = BytesIO()
    used_names = set()
    with ZipFile(archive_buffer, "w", compression=ZIP_DEFLATED) as archive:
        for doc in docs:
            file_path = doc.get("file_path")
            if not file_path or not os.path.exists(file_path):
                continue
            label = doc.get("recipient_label") or f"document_{doc['id']}"
            safe_label = "".join(ch if ch.isalnum() else "_" for ch in label)[:50] or "document"
            base_name = f"{doc.get('diploma_type', 'doc')}_{safe_label}_{doc['id']}.pdf"
            entry_name = base_name
            suffix = 1
            while entry_name in used_names:
                stem = os.path.splitext(base_name)[0]
                entry_name = f"{stem}_{suffix}.pdf"
                suffix += 1
            used_names.add(entry_name)
            archive.write(file_path, arcname=entry_name)

    archive_buffer.seek(0)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        archive_buffer,
        as_attachment=True,
        download_name=f"{archive_prefix}_{stamp}.zip",
        mimetype="application/zip",
    )


def get_selected_editor_documents(doc_ids):
    docs = []
    for doc_id in doc_ids:
        doc = db.get_document(doc_id)
        if not doc:
            continue
        if not current_user.is_admin and doc["created_by"] != current_user.id:
            continue
        docs.append(prepare_document(doc))
    return docs


def get_selected_printer_documents(doc_ids):
    docs = []
    for doc_id in doc_ids:
        doc = db.get_document(doc_id)
        if not doc or doc.get("status") != "ready_for_print":
            continue
        docs.append(prepare_document(doc))
    return docs


def build_phd_recipient_label(data):
    labels = [
        " ".join(
            part for part in [data.get("surname_kaz", "").strip(), data.get("first_name_kaz", "").strip()]
            if part
        ).strip(),
        " ".join(
            part for part in [data.get("surname_rus", "").strip(), data.get("first_name_rus", "").strip()]
            if part
        ).strip(),
        " ".join(
            part for part in [data.get("surname_eng", "").strip(), data.get("first_name_eng", "").strip()]
            if part
        ).strip(),
    ]
    return next((label for label in labels if label), "")


BAKALAVR_PROGRESS_FIELDS = (
    ("bd_number",),
    ("kaz_fio",),
    ("rus_fio",),
    ("eng_fio",),
    ("kaz_program",),
    ("rus_program",),
    ("eng_program",),
    ("kaz_form",),
    ("rus_form",),
    ("eng_form",),
    ("kaz_year", "year2"),
    ("kaz_day", "day"),
    ("kaz_protocol", "protocol"),
    ("kaz_month", "month_kaz"),
    ("rus_month", "month_rus"),
    ("eng_month", "month_eng"),
)

PHD_PROGRESS_FIELDS = (
    ("phd_number",),
    ("council_year_kaz",),
    ("council_year_eng",),
    ("council_year_rus",),
    ("council_day",),
    ("council_month_kaz",),
    ("council_month_eng",),
    ("council_month_rus",),
    ("order_year_kaz",),
    ("order_year_eng",),
    ("order_year_rus",),
    ("order_day",),
    ("order_number",),
    ("order_month_kaz",),
    ("order_month_eng",),
    ("order_month_rus",),
    ("surname_kaz",),
    ("surname_eng",),
    ("surname_rus",),
    ("first_name_kaz",),
    ("first_name_eng",),
    ("first_name_rus",),
    ("program_kaz",),
    ("program_eng",),
    ("program_rus",),
    ("dissertation_kaz",),
    ("dissertation_eng",),
    ("dissertation_rus",),
)


def build_form_progress(field_groups, data):
    values = data or {}
    filled = 0
    for aliases in field_groups:
        if isinstance(aliases, str):
            aliases = (aliases,)
        if any(str(values.get(key, "")).strip() for key in aliases):
            filled += 1
    total = len(field_groups)
    percent = round((filled / total) * 100) if total else 100
    return {"filled": filled, "total": total, "percent": percent}


MONTH_OPTIONS = [
    ("1", "Январь"),
    ("2", "Февраль"),
    ("3", "Март"),
    ("4", "Апрель"),
    ("5", "Май"),
    ("6", "Июнь"),
    ("7", "Июль"),
    ("8", "Август"),
    ("9", "Сентябрь"),
    ("10", "Октябрь"),
    ("11", "Ноябрь"),
    ("12", "Декабрь"),
]


def _parse_date_input(raw_value):
    if not raw_value:
        return None
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d").date()
    except ValueError:
        return None


def build_date_filters(args):
    today = date.today()
    period = (args.get("period") or "all").strip().lower()
    if period not in {"all", "today", "7d", "30d", "month", "year", "custom"}:
        period = "all"

    year = today.year
    month = today.month
    try:
        year = int((args.get("year") or "").strip() or today.year)
    except ValueError:
        year = today.year
    if year < 2000 or year > 2100:
        year = today.year

    try:
        month = int((args.get("month") or "").strip() or today.month)
    except ValueError:
        month = today.month
    if month < 1 or month > 12:
        month = today.month

    date_from_value = (args.get("date_from") or "").strip()
    date_to_value = (args.get("date_to") or "").strip()
    start = end = None

    if period == "today":
        start = end = today
    elif period == "7d":
        start = today - timedelta(days=6)
        end = today
    elif period == "30d":
        start = today - timedelta(days=29)
        end = today
    elif period == "month":
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
    elif period == "year":
        start = date(year, 1, 1)
        end = date(year, 12, 31)
    elif period == "custom":
        start = _parse_date_input(date_from_value)
        end = _parse_date_input(date_to_value)
        if start and end and start > end:
            start, end = end, start

    if period != "custom":
        date_from_value = start.isoformat() if start else ""
        date_to_value = end.isoformat() if end else ""

    year_options = [str(y) for y in range(today.year + 1, today.year - 6, -1)]
    selected_month = str(month)

    return {
        "period": period,
        "year": str(year),
        "month": selected_month,
        "date_from": date_from_value,
        "date_to": date_to_value,
        "query_from": start.isoformat() if start else None,
        "query_to": end.isoformat() if end else None,
        "year_options": year_options,
        "month_options": MONTH_OPTIONS,
    }


# ── Login / Logout ──────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        row = db.verify_password(username, password)
        if row:
            login_user(User(row))
            return redirect(url_for("index"))
        error = "Неверный логин или пароль"
    return render(LOGIN_HTML, error=error, page_title="Вход")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))


# ── Editor: списки и создание документов ───────────────────────────────────

@app.route("/")
@login_required
def index():
    if current_user.is_printer and not current_user.is_editor:
        return redirect(url_for("print_queue"))
    doc_filters = build_date_filters(request.args)
    if current_user.is_admin:
        docs = db.list_documents(
            date_field="created_at",
            date_from=doc_filters["query_from"],
            date_to=doc_filters["query_to"],
            order_field="created_at",
        )
    else:
        docs = db.list_documents(
            created_by=current_user.id,
            date_field="created_at",
            date_from=doc_filters["query_from"],
            date_to=doc_filters["query_to"],
            order_field="created_at",
        )
    prepared_docs = prepare_documents(docs)
    return render(
        INDEX_HTML,
        docs=prepared_docs,
        doc_groups=build_document_groups(prepared_docs),
        doc_filters=doc_filters,
        page_title="Мои документы",
        diploma_types=fd.DIPLOMA_TYPES,
    )


@app.route("/archive")
@login_required
def archive():
    archive_filters = build_date_filters(request.args)
    archive_query = (request.args.get("q") or "").strip()
    archive_status = (request.args.get("status") or "").strip()
    if archive_status not in db.STATUSES:
        archive_status = ""
    docs = prepare_documents(
        db.list_documents(
            status=archive_status or None,
            limit=2000,
            date_field="created_at",
            date_from=archive_filters["query_from"],
            date_to=archive_filters["query_to"],
            order_field="created_at",
            search=archive_query,
        ),
        include_hidden=True,
    )
    return render(
        ARCHIVE_HTML,
        docs=docs,
        archive_filters=archive_filters,
        archive_query=archive_query,
        archive_status=archive_status,
        page_title="Архив",
    )


@app.route("/new")
@role_required("editor")
def new_type():
    return render(NEW_TYPE_HTML, page_title="Новый диплом")


@app.route("/new/bakalavr", methods=["GET", "POST"])
@role_required("editor")
def new_bakalavr():
    if request.method == "POST":
        return _handle_bakalavr_save(doc_id=None)
    return render(FORM_BAKALAVR_HTML, doc=None, data={},
                  form_progress=build_form_progress(BAKALAVR_PROGRESS_FIELDS, {}),
                  diploma_types=fd.DIPLOMA_TYPES,
                  page_title="Новый диплом (бакалавр/магистр)")


@app.route("/new/phd", methods=["GET", "POST"])
@role_required("editor")
def new_phd():
    if request.method == "POST":
        return _handle_phd_save(doc_id=None)
    return render(FORM_PHD_HTML, doc=None, data={},
                  form_progress=build_form_progress(PHD_PROGRESS_FIELDS, {}),
                  page_title="Новый диплом (PhD)")


@app.route("/new/bakalavr/import", methods=["GET", "POST"])
@role_required("editor")
def import_bakalavr():
    form_data = {"batch_label": ""}
    is_xhr = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if request.method == "GET":
        return render(IMPORT_BAKALAVR_HTML, error=None, form_data=form_data,
                      import_job_id="",
                      page_title="Импорт Excel")

    batch_label = (request.form.get("batch_label") or "").strip()
    form_data["batch_label"] = batch_label
    uploaded = request.files.get("xlsx_file")
    if not uploaded or not (uploaded.filename or "").strip():
        if is_xhr:
            return jsonify({"ok": False, "error": "Файл не выбран."}), 400
        return render(IMPORT_BAKALAVR_HTML, error="Файл не выбран.",
                      form_data=form_data, import_job_id="", page_title="Импорт Excel"), 400

    original_filename = Path(uploaded.filename).name
    ext = Path(original_filename).suffix.lower()
    if ext != ".xlsx":
        if is_xhr:
            return jsonify({"ok": False, "error": "Поддерживается только .xlsx."}), 400
        return render(IMPORT_BAKALAVR_HTML, error="Поддерживается только .xlsx.",
                      form_data=form_data, import_job_id="", page_title="Импорт Excel"), 400

    batch_label = batch_label or Path(original_filename).stem
    batch_dir, batch_rel = create_import_batch_dir(batch_label)
    stored_name = f"{sanitize_storage_name(Path(original_filename).stem, 'source')}{ext}"
    source_path = os.path.join(batch_dir, stored_name)

    try:
        uploaded.save(source_path)
    except Exception as exc:
        shutil.rmtree(batch_dir, ignore_errors=True)
        if is_xhr:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return render(IMPORT_BAKALAVR_HTML, error=str(exc),
                      form_data=form_data, import_job_id="", page_title="Импорт Excel"), 400

    job_id = create_import_job(
        user_id=current_user.id,
        batch_label=batch_label,
        original_filename=original_filename,
    )
    worker = threading.Thread(
        target=run_bakalavr_import_job,
        kwargs={
            "job_id": job_id,
            "user_id": current_user.id,
            "batch_label": batch_label,
            "original_filename": original_filename,
            "source_path": source_path,
            "batch_dir": batch_dir,
            "batch_rel": batch_rel,
        },
        daemon=True,
    )
    worker.start()

    if is_xhr:
        return jsonify(
            {
                "ok": True,
                "job_id": job_id,
                "status_url": url_for("import_bakalavr_status", job_id=job_id),
                "redirect_url": url_for("index"),
            }
        )

    flash("Импорт запущен. Страница покажет прогресс автоматически.", "info")
    return render(
        IMPORT_BAKALAVR_HTML,
        error=None,
        form_data=form_data,
        import_job_id=job_id,
        page_title="Импорт Excel",
    )


@app.route("/new/phd/import", methods=["GET", "POST"])
@role_required("editor")
def import_phd():
    return _generic_import(
        kind="phd",
        parser=excel_import.parse_phd_import,
        template=IMPORT_PHD_HTML,
        page_title="Импорт PhD (Excel)",
        diploma_label="phd",
    )


@app.route("/new/fdo", methods=["GET", "POST"])
@role_required("editor")
def new_fdo():
    if request.method == "POST":
        return _handle_fdo_save(doc_id=None)
    return render(FORM_FDO_HTML, doc=None, data={},
                  page_title="Новый сертификат ФДО")


@app.route("/new/fdo/import", methods=["GET", "POST"])
@role_required("editor")
def import_fdo():
    return _generic_import(
        kind="fdo",
        parser=excel_import.parse_fdo_import,
        template=IMPORT_FDO_HTML,
        page_title="Импорт ФДО (Excel)",
        diploma_label="fdo",
    )


@app.route("/new/minor", methods=["GET", "POST"])
@role_required("editor")
def new_minor():
    if request.method == "POST":
        return _handle_minor_save(doc_id=None)
    return render(FORM_MINOR_HTML, doc=None, data={},
                  page_title="Новый сертификат Минор")


@app.route("/new/minor/import", methods=["GET", "POST"])
@role_required("editor")
def import_minor():
    return _generic_import(
        kind="minor",
        parser=excel_import.parse_minor_import,
        template=IMPORT_MINOR_HTML,
        page_title="Импорт Минор (Excel)",
        diploma_label="minor",
    )


def _generic_import(*, kind, parser, template, page_title, diploma_label):
    """Универсальный handler для импорта PhD/ФДО/Минор. Аналогичен import_bakalavr."""
    form_data = {"batch_label": ""}
    is_xhr = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if request.method == "GET":
        return render(template, error=None, form_data=form_data,
                      import_job_id="", page_title=page_title)

    batch_label = (request.form.get("batch_label") or "").strip()
    form_data["batch_label"] = batch_label
    uploaded = request.files.get("xlsx_file")
    if not uploaded or not (uploaded.filename or "").strip():
        if is_xhr:
            return jsonify({"ok": False, "error": "Файл не выбран."}), 400
        return render(template, error="Файл не выбран.",
                      form_data=form_data, import_job_id="", page_title=page_title), 400

    original_filename = Path(uploaded.filename).name
    ext = Path(original_filename).suffix.lower()
    if ext != ".xlsx":
        if is_xhr:
            return jsonify({"ok": False, "error": "Поддерживается только .xlsx."}), 400
        return render(template, error="Поддерживается только .xlsx.",
                      form_data=form_data, import_job_id="", page_title=page_title), 400

    batch_label = batch_label or Path(original_filename).stem
    batch_dir, batch_rel = create_import_batch_dir(batch_label)
    stored_name = f"{sanitize_storage_name(Path(original_filename).stem, 'source')}{ext}"
    source_path = os.path.join(batch_dir, stored_name)

    try:
        uploaded.save(source_path)
    except Exception as exc:
        shutil.rmtree(batch_dir, ignore_errors=True)
        if is_xhr:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return render(template, error=str(exc),
                      form_data=form_data, import_job_id="", page_title=page_title), 400

    job_id = create_import_job(
        user_id=current_user.id,
        batch_label=batch_label,
        original_filename=original_filename,
    )
    worker = threading.Thread(
        target=run_generic_import_job,
        kwargs={
            "job_id": job_id,
            "kind": kind,
            "parser": parser,
            "user_id": current_user.id,
            "batch_label": batch_label,
            "original_filename": original_filename,
            "source_path": source_path,
            "batch_dir": batch_dir,
            "batch_rel": batch_rel,
        },
        daemon=True,
    )
    worker.start()

    if is_xhr:
        return jsonify(
            {
                "ok": True,
                "job_id": job_id,
                "status_url": url_for("import_bakalavr_status", job_id=job_id),
                "redirect_url": url_for("index"),
            }
        )

    flash("Импорт запущен. Страница покажет прогресс автоматически.", "info")
    return render(
        template,
        error=None,
        form_data=form_data,
        import_job_id=job_id,
        page_title=page_title,
    )


@app.route("/imports/<job_id>/status")
@role_required("editor")
def import_bakalavr_status(job_id):
    job = get_import_job(job_id)
    if not job or job.get("user_id") != current_user.id:
        return jsonify({"ok": False, "error": "Задание импорта не найдено."}), 404
    return jsonify(
        {
            "ok": True,
            "job_id": job["job_id"],
            "state": job["state"],
            "stage": job["stage"],
            "message": job["message"],
            "error": job.get("error", ""),
            "total": job.get("total", 0),
            "processed": job.get("processed", 0),
            "created": job.get("created", 0),
            "stats": job.get("stats", {}),
            "redirect_url": job.get("redirect_url") or url_for("index"),
        }
    )


@app.route("/doc/<int:doc_id>/edit", methods=["GET", "POST"])
@role_required("editor")
def edit_doc(doc_id):
    doc = db.get_document(doc_id)
    if not doc: abort(404)
    if not current_user.is_admin and doc["created_by"] != current_user.id:
        return render(ERROR_HTML, msg="Чужой документ."), 403
    if doc["status"] == "printed":
        return render(ERROR_HTML, msg="Напечатанный документ нельзя редактировать."), 400

    if request.method == "POST":
        if doc["diploma_type"] == "phd":
            return _handle_phd_save(doc_id=doc_id)
        elif doc["diploma_type"] == "fdo":
            return _handle_fdo_save(doc_id=doc_id)
        elif doc["diploma_type"] == "minor":
            return _handle_minor_save(doc_id=doc_id)
        else:
            return _handle_bakalavr_save(doc_id=doc_id)

    if doc["diploma_type"] == "phd":
        return render(FORM_PHD_HTML, doc=doc, data=doc["data"],
                      form_progress=build_form_progress(PHD_PROGRESS_FIELDS, doc["data"]),
                      page_title=f"Редактирование #{doc_id}")
    elif doc["diploma_type"] == "fdo":
        return render(FORM_FDO_HTML, doc=doc, data=doc["data"],
                      page_title=f"Редактирование #{doc_id}")
    elif doc["diploma_type"] == "minor":
        return render(FORM_MINOR_HTML, doc=doc, data=doc["data"],
                      page_title=f"Редактирование #{doc_id}")
    else:
        return render(FORM_BAKALAVR_HTML, doc=doc, data=doc["data"],
                      form_progress=build_form_progress(BAKALAVR_PROGRESS_FIELDS, doc["data"]),
                      diploma_types=fd.DIPLOMA_TYPES,
                      page_title=f"Редактирование #{doc_id}")


def _generate_pdf(diploma_type, data, qr_text, doc_id_hint, *, output_dir=None):
    token = uuid.uuid4().hex[:8]
    if diploma_type == "phd":
        prefix = "phd"
        safe = (data.get("surname_kaz", "").split() or ["phd"])[0]
    elif diploma_type == "fdo":
        prefix = "fdo"
        safe = (data.get("fio_kaz", "").split() or data.get("fio_rus", "").split() or ["fdo"])[0]
    elif diploma_type == "minor":
        prefix = "minor"
        safe = (data.get("fio_kaz", "").split() or data.get("fio_rus", "").split() or ["minor"])[0]
    else:
        prefix = diploma_type
        safe = (data.get("kaz_fio", "").split() or ["diploma"])[0]
    safe = "".join(c if c.isalnum() else "_" for c in safe)[:30]
    target_dir = output_dir or OUTPUT_DIR
    os.makedirs(target_dir, exist_ok=True)
    out_name = f"{prefix}_{safe}_{doc_id_hint or 'new'}_{token}.pdf"
    out_path = os.path.join(target_dir, out_name)

    if diploma_type == "phd":
        fd_phd.fill_diploma_phd(data, out_path, qr_text=qr_text)
    elif diploma_type == "fdo":
        fd_fdo.fill_diploma_fdo(data, out_path, qr_text=qr_text)
    elif diploma_type == "minor":
        fd_minor.fill_diploma_minor(data, out_path, qr_text=qr_text)
    else:
        fd.fill_diploma(data, out_path, diploma_type, qr_text=qr_text)
    return out_path


def _handle_bakalavr_save(doc_id):
    f = request.form
    autosave_mode = is_autosave_request()
    diploma_type = f.get("diploma_type", "bakalavr")
    if diploma_type not in fd.DIPLOMA_TYPES:
        if autosave_mode:
            return autosave_error(f"Неверный тип: {diploma_type}")
        return render(ERROR_HTML, msg=f"Неверный тип: {diploma_type}"), 400

    data = {k: f.get(k, "").strip() for k in [
        "bd_number",
        "iin",
        "kaz_fio", "rus_fio", "eng_fio",
        "kaz_program", "rus_program", "eng_program",
        "kaz_qualification", "rus_qualification", "eng_qualification",
        "kaz_form", "rus_form", "eng_form",
        "diploma_year", "diploma_day", "diploma_month", "city",
    ]}
    year2     = f.get("year2", "").strip()
    day       = f.get("day", "").strip()
    protocol  = f.get("protocol", "").strip()
    data.update({
        "kaz_year": year2, "rus_year": year2, "eng_year": year2,
        "kaz_day": day, "rus_day": day, "eng_day": day,
        "kaz_month": f.get("month_kaz", "").strip(),
        "rus_month": f.get("month_rus", "").strip(),
        "eng_month": f.get("month_eng", "").strip(),
        "kaz_protocol": protocol, "rus_protocol": protocol,
    })
    qr_text = f.get("qr_text", "").strip()
    comment = f.get("comment", "").strip()
    recipient_label = (data.get("kaz_fio") or data.get("rus_fio") or "").strip()
    person_iin = data.get("iin", "").strip()
    diploma_number = data.get("bd_number", "").strip()
    old = db.get_document(doc_id) if doc_id else None
    document_series = normalize_document_series((old or {}).get("document_series", ""))
    source_meta = source_meta_from_doc(old)
    output_dir = resolve_source_output_dir(old)

    try:
        pdf_path = _generate_pdf(diploma_type, data, qr_text, doc_id, output_dir=output_dir)
    except Exception as e:
        if autosave_mode:
            return autosave_error(f"Ошибка генерации: {type(e).__name__}: {e}", 500)
        return render(ERROR_HTML, msg=f"Ошибка генерации: {type(e).__name__}: {e}"), 500

    d2 = dict(data); d2["diploma_type"] = diploma_type
    if doc_id:
        if old and old["file_path"] and os.path.exists(old["file_path"]):
            try: os.remove(old["file_path"])
            except OSError: pass
        db.update_document(doc_id, data=d2, qr_text=qr_text, comment=comment,
                           recipient_label=recipient_label, file_path=pdf_path,
                           person_iin=person_iin, diploma_number=diploma_number,
                           document_series=document_series,
                           **source_meta)
        conn = db.get_conn()
        conn.execute("UPDATE documents SET diploma_type=? WHERE id=?", (diploma_type, doc_id))
        conn.commit(); conn.close()
    else:
        doc_id = db.create_document(
            diploma_type=diploma_type, data=d2, qr_text=qr_text,
            file_path=pdf_path, recipient_label=recipient_label,
            created_by=current_user.id, comment=comment, status="draft",
            person_iin=person_iin, diploma_number=diploma_number,
            document_series=document_series,
            **build_source_meta(),
        )

    if autosave_mode:
        return autosave_success(doc_id=doc_id, message="Черновик обновлён.")

    if f.get("action") == "send":
        db.set_doc_status(doc_id, "ready_for_print")
        flash("Документ отправлен в печать.", "success")
    else:
        flash("Документ сохранён как черновик.", "success")
    return redirect(url_for("index"))


def _handle_phd_save(doc_id):
    f = request.form
    autosave_mode = is_autosave_request()
    keys = [
        "phd_number",
        "iin",
        "council_year_kaz", "council_year_eng", "council_year_rus",
        "council_day", "council_month_kaz", "council_month_eng", "council_month_rus",
        "order_year_kaz", "order_year_eng", "order_year_rus",
        "order_day", "order_month_kaz", "order_month_eng", "order_month_rus",
        "order_number",
        "surname_kaz", "surname_eng", "surname_rus",
        "first_name_kaz", "first_name_eng", "first_name_rus",
        "program_kaz", "program_eng", "program_rus",
        "dissertation_kaz", "dissertation_eng", "dissertation_rus",
        "consultants_kaz", "consultants_eng", "consultants_rus",
        "reviewers_kaz", "reviewers_eng", "reviewers_rus",
        "place_kaz", "place_eng", "place_rus",
        "defense_date_kaz", "defense_date_eng", "defense_date_rus",
        "issue_year", "issue_day", "issue_month_kaz",
    ]
    data = {k: f.get(k, "").strip() for k in keys}
    qr_text = f.get("qr_text", "").strip()
    comment = f.get("comment", "").strip()
    recipient_label = build_phd_recipient_label(data)
    person_iin = data.get("iin", "").strip()
    diploma_number = data.get("phd_number", "").strip()
    old = db.get_document(doc_id) if doc_id else None
    document_series = normalize_document_series((old or {}).get("document_series", ""))
    source_meta = source_meta_from_doc(old)
    output_dir = resolve_source_output_dir(old)

    try:
        pdf_path = _generate_pdf("phd", data, qr_text, doc_id, output_dir=output_dir)
    except Exception as e:
        if autosave_mode:
            return autosave_error(f"Ошибка генерации: {type(e).__name__}: {e}", 500)
        return render(ERROR_HTML, msg=f"Ошибка генерации: {type(e).__name__}: {e}"), 500

    d2 = dict(data); d2["diploma_type"] = "phd"
    if doc_id:
        if old and old["file_path"] and os.path.exists(old["file_path"]):
            try: os.remove(old["file_path"])
            except OSError: pass
        db.update_document(doc_id, data=d2, qr_text=qr_text, comment=comment,
                           recipient_label=recipient_label, file_path=pdf_path,
                           person_iin=person_iin, diploma_number=diploma_number,
                           document_series=document_series,
                           **source_meta)
    else:
        doc_id = db.create_document(
            diploma_type="phd", data=d2, qr_text=qr_text,
            file_path=pdf_path, recipient_label=recipient_label,
            created_by=current_user.id, comment=comment, status="draft",
            person_iin=person_iin, diploma_number=diploma_number,
            document_series=document_series,
            **build_source_meta(),
        )

    if autosave_mode:
        return autosave_success(doc_id=doc_id, message="Черновик обновлён.")

    if f.get("action") == "send":
        db.set_doc_status(doc_id, "ready_for_print")
        flash("Документ отправлен в печать.", "success")
    else:
        flash("Документ сохранён как черновик.", "success")
    return redirect(url_for("index"))


def build_fdo_recipient_label(data):
    """ФИО получателя сертификата ФДО — берём первый непустой из каз/рус/eng."""
    return (data.get("fio_kaz") or data.get("fio_rus") or data.get("fio_eng") or "").strip()


def build_minor_recipient_label(data):
    return (data.get("fio_kaz") or data.get("fio_rus") or data.get("fio_eng") or "").strip()


def _handle_fdo_save(doc_id):
    f = request.form
    autosave_mode = is_autosave_request()
    keys = [
        "cert_series", "cert_number", "reg_number",
        # KAZ
        "council_day_kaz", "council_month_kaz", "council_year_kaz",
        "protocol_kaz", "fio_kaz",
        "from_day_kaz", "from_month_kaz", "to_day_kaz", "to_month_kaz",
        "program_kaz", "credits_kaz",
        # RUS
        "council_day_rus", "council_month_rus", "council_year_rus",
        "protocol_rus", "fio_rus",
        "from_day_rus", "from_month_rus", "to_day_rus", "to_month_rus",
        "program_rus", "credits_rus",
        # ENG
        "council_day_eng", "council_month_eng", "council_year_eng",
        "fio_eng",
        "from_day_eng", "from_month_eng", "to_day_eng", "to_month_eng",
        "program_eng", "credits_eng",
        # ВЫДАЧА
        "issue_year", "issue_day", "issue_month_kaz",
        "from_year_kaz", "to_year_kaz",
        "from_year_rus", "to_year_rus",
        "from_year_eng", "to_year_eng",
    ]
    data = {k: f.get(k, "").strip() for k in keys}
    if not data.get("cert_series"):
        data["cert_series"] = "CPR"
    qr_text = f.get("qr_text", "").strip()
    comment = f.get("comment", "").strip()
    recipient_label = build_fdo_recipient_label(data)
    diploma_number = data.get("cert_number", "").strip()
    old = db.get_document(doc_id) if doc_id else None
    document_series = normalize_document_series((old or {}).get("document_series", ""))
    source_meta = source_meta_from_doc(old)
    output_dir = resolve_source_output_dir(old)

    try:
        pdf_path = _generate_pdf("fdo", data, qr_text, doc_id, output_dir=output_dir)
    except Exception as e:
        if autosave_mode:
            return autosave_error(f"Ошибка генерации: {type(e).__name__}: {e}", 500)
        return render(ERROR_HTML, msg=f"Ошибка генерации: {type(e).__name__}: {e}"), 500

    d2 = dict(data); d2["diploma_type"] = "fdo"
    if doc_id:
        if old and old["file_path"] and os.path.exists(old["file_path"]):
            try: os.remove(old["file_path"])
            except OSError: pass
        db.update_document(doc_id, data=d2, qr_text=qr_text, comment=comment,
                           recipient_label=recipient_label, file_path=pdf_path,
                           person_iin="", diploma_number=diploma_number,
                           document_series=document_series,
                           **source_meta)
    else:
        doc_id = db.create_document(
            diploma_type="fdo", data=d2, qr_text=qr_text,
            file_path=pdf_path, recipient_label=recipient_label,
            created_by=current_user.id, comment=comment, status="draft",
            person_iin="", diploma_number=diploma_number,
            document_series=document_series,
            **build_source_meta(),
        )

    if autosave_mode:
        return autosave_success(doc_id=doc_id, message="Черновик обновлён.")

    if f.get("action") == "send":
        db.set_doc_status(doc_id, "ready_for_print")
        flash("Документ отправлен в печать.", "success")
    else:
        flash("Документ сохранён как черновик.", "success")
    return redirect(url_for("index"))


def _handle_minor_save(doc_id):
    f = request.form
    autosave_mode = is_autosave_request()
    keys = [
        "bd_number", "iin",
        # KAZ
        "program_kaz", "fio_kaz", "minor_kaz",
        "from_day_kaz", "from_month_kaz", "from_year_kaz",
        "to_day_kaz", "to_month_kaz", "to_year_kaz",
        # ENG
        "program_eng", "fio_eng", "minor_eng",
        "from_day_eng", "from_month_eng", "from_year_eng",
        "to_day_eng", "to_month_eng", "to_year_eng",
        # RUS
        "program_rus", "fio_rus", "minor_rus",
        "from_day_rus", "from_month_rus", "from_year_rus",
        "to_day_rus", "to_month_rus", "to_year_rus",
        # ВЫДАЧА
        "issue_year", "issue_day", "issue_month_kaz", "reg_number",
    ]
    data = {k: f.get(k, "").strip() for k in keys}
    qr_text = f.get("qr_text", "").strip()
    comment = f.get("comment", "").strip()
    recipient_label = build_minor_recipient_label(data)
    person_iin = data.get("iin", "").strip()
    diploma_number = data.get("bd_number", "").strip()
    old = db.get_document(doc_id) if doc_id else None
    document_series = normalize_document_series((old or {}).get("document_series", ""))
    source_meta = source_meta_from_doc(old)
    output_dir = resolve_source_output_dir(old)

    try:
        pdf_path = _generate_pdf("minor", data, qr_text, doc_id, output_dir=output_dir)
    except Exception as e:
        if autosave_mode:
            return autosave_error(f"Ошибка генерации: {type(e).__name__}: {e}", 500)
        return render(ERROR_HTML, msg=f"Ошибка генерации: {type(e).__name__}: {e}"), 500

    d2 = dict(data); d2["diploma_type"] = "minor"
    if doc_id:
        if old and old["file_path"] and os.path.exists(old["file_path"]):
            try: os.remove(old["file_path"])
            except OSError: pass
        db.update_document(doc_id, data=d2, qr_text=qr_text, comment=comment,
                           recipient_label=recipient_label, file_path=pdf_path,
                           person_iin=person_iin, diploma_number=diploma_number,
                           document_series=document_series,
                           **source_meta)
    else:
        doc_id = db.create_document(
            diploma_type="minor", data=d2, qr_text=qr_text,
            file_path=pdf_path, recipient_label=recipient_label,
            created_by=current_user.id, comment=comment, status="draft",
            person_iin=person_iin, diploma_number=diploma_number,
            document_series=document_series,
            **build_source_meta(),
        )

    if autosave_mode:
        return autosave_success(doc_id=doc_id, message="Черновик обновлён.")

    if f.get("action") == "send":
        db.set_doc_status(doc_id, "ready_for_print")
        flash("Документ отправлен в печать.", "success")
    else:
        flash("Документ сохранён как черновик.", "success")
    return redirect(url_for("index"))


@app.route("/doc/<int:doc_id>/preview")
@login_required
def doc_preview(doc_id):
    doc = db.get_document(doc_id)
    if not doc: abort(404)
    if not can_access_document(doc):
        return render(ERROR_HTML, msg="Доступ запрещён."), 403
    if not doc["file_path"] or not os.path.exists(doc["file_path"]):
        return render(ERROR_HTML, msg="PDF-файл недоступен."), 404
    response = send_file(doc["file_path"], mimetype="application/pdf",
                         as_attachment=False)
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'self'; "
        "frame-ancestors 'self'"
    )
    return response


@app.route("/doc/<int:doc_id>/preview-image")
@login_required
def doc_preview_image(doc_id):
    doc = db.get_document(doc_id)
    if not doc:
        abort(404)
    if not can_access_document(doc):
        return render(ERROR_HTML, msg="Доступ запрещён."), 403
    if not doc["file_path"] or not os.path.exists(doc["file_path"]):
        return render(ERROR_HTML, msg="PDF-файл недоступен."), 404

    pdf = None
    try:
        pdf = fitz.open(doc["file_path"])
        if len(pdf) == 0:
            abort(404)
        page = pdf[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.55, 1.55), alpha=False)
        response = send_file(BytesIO(pix.tobytes("png")), mimetype="image/png")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response
    finally:
        if pdf is not None:
            pdf.close()


@app.route("/doc/<int:doc_id>/download")
@login_required
def doc_download(doc_id):
    doc = db.get_document(doc_id)
    if not doc: abort(404)
    if not can_access_document(doc):
        return render(ERROR_HTML, msg="Доступ запрещён."), 403
    if not doc["file_path"] or not os.path.exists(doc["file_path"]):
        return render(ERROR_HTML, msg="PDF-файл недоступен."), 404
    label = doc["recipient_label"] or f"diploma_{doc_id}"
    safe = "".join(c if c.isalnum() else "_" for c in label)[:50]
    name = f"{doc['diploma_type']}_{safe}_{doc_id}.pdf"
    return send_file(doc["file_path"], as_attachment=True,
                     download_name=name, mimetype="application/pdf")


@app.route("/doc/<int:doc_id>/send", methods=["POST"])
@role_required("editor")
def doc_send(doc_id):
    doc = db.get_document(doc_id)
    if not doc: abort(404)
    if not current_user.is_admin and doc["created_by"] != current_user.id:
        return render(ERROR_HTML, msg="Чужой документ."), 403
    if doc["status"] == "printed":
        flash("Документ уже напечатан.", "error")
        return redirect(url_for("index"))
    db.set_doc_status(doc_id, "ready_for_print")
    flash(f"Документ #{doc_id} отправлен в печать.", "success")
    return redirect(url_for("index"))


@app.route("/docs/bulk/download", methods=["POST"])
@role_required("editor")
def docs_bulk_download():
    doc_ids = parse_selected_doc_ids(request.form.getlist("doc_ids"))
    selected_docs = [doc for doc in get_selected_editor_documents(doc_ids) if doc.get("file_available")]
    if not selected_docs:
        flash("Не выбраны документы с доступным PDF.", "error")
        return redirect(url_for("index"))
    return build_bulk_zip_response(selected_docs, archive_prefix="documents")


@app.route("/docs/bulk/send", methods=["POST"])
@role_required("editor")
def docs_bulk_send():
    doc_ids = parse_selected_doc_ids(request.form.getlist("doc_ids"))
    selected_docs = [doc for doc in get_selected_editor_documents(doc_ids) if doc.get("status") == "draft"]
    if not selected_docs:
        flash("Не выбраны черновики для отправки в печать.", "error")
        return redirect(url_for("index"))
    for doc in selected_docs:
        db.set_doc_status(doc["id"], "ready_for_print")
    flash(f"Отправлено в печать: {len(selected_docs)} документов.", "success")
    return redirect(url_for("index"))


@app.route("/docs/bulk/recall", methods=["POST"])
@role_required("editor")
def docs_bulk_recall():
    doc_ids = parse_selected_doc_ids(request.form.getlist("doc_ids"))
    selected_docs = [doc for doc in get_selected_editor_documents(doc_ids) if doc.get("status") == "ready_for_print"]
    if not selected_docs:
        flash("Не выбраны документы в статусе печати.", "error")
        return redirect(url_for("index"))
    for doc in selected_docs:
        db.set_doc_status(doc["id"], "draft")
    flash(f"Возвращено в черновики: {len(selected_docs)} документов.", "success")
    return redirect(url_for("index"))


@app.route("/docs/bulk/delete", methods=["POST"])
@role_required("admin")
def docs_bulk_delete():
    doc_ids = parse_selected_doc_ids(request.form.getlist("doc_ids"))
    if not doc_ids:
        flash("Не выбраны документы для удаления.", "error")
        return redirect(url_for("index"))

    deleted = 0
    for doc_id in doc_ids:
        doc = db.get_document(doc_id)
        if not doc:
            continue
        file_path = db.delete_document(doc_id)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        deleted += 1

    if not deleted:
        flash("Не удалось удалить выбранные документы.", "error")
        return redirect(url_for("index"))

    flash(f"Удалено документов: {deleted}.", "success")
    return redirect(url_for("index"))


@app.route("/docs/series/send", methods=["POST"])
@role_required("editor")
def docs_series_send():
    series = request.form.get("series", "")
    series_docs = [
        doc for doc in list_series_documents_for_user(series)
        if doc.get("status") == "draft"
    ]
    if not series_docs:
        flash("В выбранной серии нет черновиков для отправки.", "error")
        return redirect(url_for("index"))

    for doc in series_docs:
        db.set_doc_status(doc["id"], "ready_for_print")
    flash(
        f"Серия {get_series_label(normalize_document_series(series))}: отправлено в печать {len(series_docs)} шт.",
        "success",
    )
    return redirect(url_for("index"))


@app.route("/doc/<int:doc_id>/recall", methods=["POST"])
@role_required("editor")
def doc_recall(doc_id):
    doc = db.get_document(doc_id)
    if not doc: abort(404)
    if not current_user.is_admin and doc["created_by"] != current_user.id:
        return render(ERROR_HTML, msg="Чужой документ."), 403
    if doc["status"] == "ready_for_print":
        db.set_doc_status(doc_id, "draft")
        flash(f"Документ #{doc_id} возвращён в черновики.", "success")
    return redirect(url_for("index"))


@app.route("/docs/series/recall", methods=["POST"])
@role_required("editor")
def docs_series_recall():
    series = request.form.get("series", "")
    series_docs = [
        doc for doc in list_series_documents_for_user(series)
        if doc.get("status") == "ready_for_print"
    ]
    if not series_docs:
        flash("В выбранной серии нет документов в печати.", "error")
        return redirect(url_for("index"))

    for doc in series_docs:
        db.set_doc_status(doc["id"], "draft")
    flash(
        f"Серия {get_series_label(normalize_document_series(series))}: возвращено в черновики {len(series_docs)} шт.",
        "success",
    )
    return redirect(url_for("index"))


@app.route("/doc/<int:doc_id>/delete", methods=["POST"])
@role_required("admin")
def doc_delete(doc_id):
    doc = db.get_document(doc_id)
    if not doc: abort(404)
    file_path = db.delete_document(doc_id)
    if file_path and os.path.exists(file_path):
        try: os.remove(file_path)
        except OSError: pass
    flash(f"Документ #{doc_id} удалён.", "success")
    return redirect(url_for("index"))


# ── Printer: очередь печати ─────────────────────────────────────────────────

@app.route("/print")
@role_required("printer")
def print_queue():
    ready_docs = prepare_documents(db.list_documents(status="ready_for_print"))
    ready = [doc for doc in ready_docs if not doc["has_print_issue"]]
    issues = [doc for doc in ready_docs if doc["has_print_issue"]]
    printed = prepare_documents(db.list_documents(status="printed", limit=50))
    return render(PRINT_QUEUE_HTML, ready=ready, ready_groups=build_document_groups(ready), issues=issues, printed=printed,
                  page_title="Очередь печати")


@app.route("/print/<int:doc_id>/done", methods=["POST"])
@role_required("printer")
def print_done(doc_id):
    doc = db.get_document(doc_id)
    if not doc: abort(404)
    if doc["status"] != "ready_for_print":
        flash("Документ не в очереди печати.", "error")
        return redirect(url_for("print_queue"))
    db.set_doc_status(doc_id, "printed", user_id=current_user.id)
    flash(f"Документ #{doc_id} отмечен как напечатанный.", "success")
    return redirect(url_for("print_queue"))


@app.route("/print/bulk/download", methods=["POST"])
@role_required("printer")
def print_bulk_download():
    doc_ids = parse_selected_doc_ids(request.form.getlist("doc_ids"))
    selected_docs = [doc for doc in get_selected_printer_documents(doc_ids) if doc.get("file_available")]
    if not selected_docs:
        flash("Не выбраны документы с доступным PDF.", "error")
        return redirect(url_for("print_queue"))
    return build_bulk_zip_response(selected_docs, archive_prefix="print_queue")


@app.route("/print/bulk/done", methods=["POST"])
@role_required("printer")
def print_bulk_done():
    doc_ids = parse_selected_doc_ids(request.form.getlist("doc_ids"))
    selected_docs = [
        doc for doc in get_selected_printer_documents(doc_ids)
        if not doc.get("has_print_issue")
    ]
    if not selected_docs:
        flash("Не выбраны документы для отметки как напечатанные.", "error")
        return redirect(url_for("print_queue"))
    for doc in selected_docs:
        db.set_doc_status(doc["id"], "printed", user_id=current_user.id)
    flash(f"Отмечено как напечатанные: {len(selected_docs)} документов.", "success")
    return redirect(url_for("print_queue"))


@app.route("/print/series/done", methods=["POST"])
@role_required("printer")
def print_series_done():
    series = request.form.get("series", "")
    series_docs = [
        doc for doc in prepare_documents(
            db.list_documents(status="ready_for_print", limit=5000),
            include_hidden=True,
        )
        if get_document_series(doc) == normalize_document_series(series) and not doc.get("has_print_issue")
    ]
    if not series_docs:
        flash("В выбранной серии нет доступных документов для отметки.", "error")
        return redirect(url_for("print_queue"))

    for doc in series_docs:
        db.set_doc_status(doc["id"], "printed", user_id=current_user.id)
    flash(
        f"Серия {get_series_label(normalize_document_series(series))}: отмечено как напечатанные {len(series_docs)} шт.",
        "success",
    )
    return redirect(url_for("print_queue"))


@app.route("/print/problem", methods=["POST"])
@app.route("/print/<int:doc_id>/problem", methods=["POST"])
@role_required("printer")
def print_problem(doc_id=None):
    if doc_id is None:
        try:
            doc_id = int((request.form.get("doc_id") or "").strip())
        except ValueError:
            flash("Не удалось определить документ для отметки проблемы.", "error")
            return redirect(url_for("print_queue"))
    doc = db.get_document(doc_id)
    if not doc:
        abort(404)
    if doc["status"] != "ready_for_print":
        flash("Проблему можно отметить только у документа в очереди печати.", "error")
        return redirect(url_for("print_queue"))

    note = request.form.get("problem_note", "").strip()
    if not note:
        note = "Возникла проблема при печати."

    db.mark_print_issue(doc_id, note, user_id=current_user.id)
    flash(f"Документ #{doc_id} помечен как проблемный.", "error")
    return redirect(url_for("print_queue"))


# ── Admin: пользователи ─────────────────────────────────────────────────────

@app.route("/admin/users", methods=["GET", "POST"])
@role_required("admin")
def admin_users():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role     = request.form.get("role", "editor")
        if not username or not password:
            error = "Логин и пароль обязательны"
        elif role not in db.ROLES:
            error = f"Недопустимая роль: {role}"
        elif role == "admin":
            error = "Создавать новых админов через эту форму нельзя."
        else:
            try:
                db.create_user(username, password, role, current_user.id)
                flash(f"Пользователь {username} ({role}) создан.", "success")
                return redirect(url_for("admin_users"))
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
    users = db.list_users()
    return render(ADMIN_USERS_HTML, users=users, error=error,
                  page_title="Пользователи")


@app.route("/admin/settings/retention", methods=["POST"])
@role_required("admin")
def admin_retention():
    try:
        days = db.set_print_retention_days(request.form.get("retention_days", "").strip())
        flash(
            f"Срок хранения PDF напечатанных документов обновлён: {days} дн.",
            "success",
        )
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_users"))


@app.route("/admin/logs")
@role_required("admin")
def admin_logs():
    log_filters = build_date_filters(request.args)
    printed = prepare_documents(
        db.list_documents(
            status="printed",
            limit=1000,
            date_field="printed_at",
            date_from=log_filters["query_from"],
            date_to=log_filters["query_to"],
            order_field="printed_at",
        ),
        include_hidden=True,
    )
    return render(
        ADMIN_LOGS_HTML,
        printed=printed,
        log_filters=log_filters,
        page_title="Все логи",
    )


@app.route("/admin/system")
@role_required("admin")
def admin_system():
    rel_path = (request.args.get("path") or "").strip()
    return render(
        ADMIN_SYSTEM_HTML,
        system_stats=collect_system_stats(),
        file_browser=build_file_browser(rel_path),
        page_title="Система",
    )


@app.route("/admin/files/open")
@role_required("admin")
def admin_file_open():
    target, rel_path = resolve_admin_path(request.args.get("path", ""))
    if not os.path.isfile(target):
        abort(404)
    return send_file(target, as_attachment=False, download_name=os.path.basename(rel_path))


@app.route("/admin/files/delete", methods=["POST"])
@role_required("admin")
def admin_file_delete():
    target, rel_path = resolve_admin_path(request.form.get("path", ""))
    if not os.path.isfile(target):
        flash("Удалять можно только файлы.", "error")
        return redirect(url_for("admin_system", path=os.path.dirname(rel_path)))

    parent_rel = os.path.dirname(rel_path).replace("\\", "/")
    try:
        os.remove(target)
        flash(f"Файл удалён: {rel_path}", "success")
    except OSError as e:
        flash(f"Не удалось удалить файл: {e}", "error")
    return redirect(url_for("admin_system", path=parent_rel))


@app.route("/admin/users/<int:uid>/delete", methods=["POST"])
@role_required("admin")
def admin_user_delete(uid):
    if uid == current_user.id:
        flash("Себя удалять нельзя.", "error")
        return redirect(url_for("admin_users"))
    try:
        db.delete_user(uid)
        flash("Пользователь удалён.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:uid>/pwd", methods=["POST"])
@role_required("admin")
def admin_user_pwd(uid):
    new_pw = request.form.get("password", "").strip()
    if len(new_pw) < 4:
        flash("Пароль слишком короткий.", "error")
    else:
        db.update_user_password(uid, new_pw)
        flash("Пароль обновлён.", "success")
    return redirect(url_for("admin_users"))


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    print()
    print("  ┌─── Лауреат ────────────────────────────────")
    print("  │  http://127.0.0.1:5000")
    print("  │  По умолчанию: admin / admin (СМЕНИТЕ!)")
    print("  └────────────────────────────────────────────")
    print()
    app.run(host="0.0.0.0", port=5000, debug=False)
