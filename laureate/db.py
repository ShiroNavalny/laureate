"""
db.py — модель данных для Лауреата.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "laureate.db")

ROLES = ("admin", "editor", "printer")
STATUSES = ("draft", "ready_for_print", "printed")
DEFAULT_PRINT_RETENTION_DAYS = 30
MAX_PRINT_RETENTION_DAYS = 3650


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Создаёт таблицы и админа по умолчанию (один раз)."""
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','editor','printer')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diploma_type TEXT NOT NULL,
            data_json TEXT NOT NULL,
            qr_text TEXT,
            status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','ready_for_print','printed')),
            file_path TEXT,
            comment TEXT,
            recipient_label TEXT,
            person_iin TEXT,
            diploma_number TEXT,
            document_series TEXT,
            source_kind TEXT,
            source_label TEXT,
            source_filename TEXT,
            source_folder TEXT,
            source_row_number INTEGER,
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            sent_to_print_at TEXT,
            printed_by INTEGER REFERENCES users(id),
            printed_at TEXT,
            print_issue_note TEXT,
            print_issue_by INTEGER REFERENCES users(id),
            print_issue_at TEXT,
            file_purged_at TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_docs_status ON documents(status);
        CREATE INDEX IF NOT EXISTS idx_docs_creator ON documents(created_by);
    """)

    c.execute(
        """INSERT OR IGNORE INTO settings (key, value)
           VALUES ('print_retention_days', ?)""",
        (str(DEFAULT_PRINT_RETENTION_DAYS),),
    )

    doc_columns = {
        row["name"] for row in c.execute("PRAGMA table_info(documents)").fetchall()
    }
    if "print_issue_note" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN print_issue_note TEXT")
    if "print_issue_by" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN print_issue_by INTEGER REFERENCES users(id)")
    if "print_issue_at" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN print_issue_at TEXT")
    if "file_purged_at" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN file_purged_at TEXT")
    if "source_kind" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN source_kind TEXT")
    if "person_iin" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN person_iin TEXT")
    if "diploma_number" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN diploma_number TEXT")
    if "document_series" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN document_series TEXT")
    if "source_label" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN source_label TEXT")
    if "source_filename" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN source_filename TEXT")
    if "source_folder" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN source_folder TEXT")
    if "source_row_number" not in doc_columns:
        c.execute("ALTER TABLE documents ADD COLUMN source_row_number INTEGER")

    # Индексы на колонки, которые могли быть добавлены через ALTER TABLE — создаём после них
    c.executescript("""
        CREATE INDEX IF NOT EXISTS idx_docs_person_iin ON documents(person_iin);
        CREATE INDEX IF NOT EXISTS idx_docs_diploma_number ON documents(diploma_number);
        CREATE INDEX IF NOT EXISTS idx_docs_document_series ON documents(document_series);
        CREATE INDEX IF NOT EXISTS idx_docs_recipient_label ON documents(recipient_label);
    """)

    # Создаём admin'а если его нет
    c.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
            ("admin", generate_password_hash("admin")),
        )
        print("  ▸ Создан admin/admin (СМЕНИТЕ ПАРОЛЬ!)")
    conn.commit()
    conn.close()


# ── Пользователи ────────────────────────────────────────────────────────────

def get_user_by_username(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return row


def get_user_by_id(uid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return row


def list_users():
    conn = get_conn()
    rows = conn.execute(
        "SELECT u.*, c.username AS creator_name FROM users u "
        "LEFT JOIN users c ON c.id = u.created_by "
        "ORDER BY u.created_at DESC"
    ).fetchall()
    conn.close()
    return rows


def count_users_by_role():
    conn = get_conn()
    rows = conn.execute(
        "SELECT role, COUNT(*) AS total FROM users GROUP BY role"
    ).fetchall()
    conn.close()
    counts = {role: 0 for role in ROLES}
    for row in rows:
        counts[row["role"]] = row["total"]
    counts["total"] = sum(counts.values())
    return counts


def create_user(username, password, role, created_by):
    if role not in ROLES:
        raise ValueError(f"Недопустимая роль: {role}")
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, created_by) VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), role, created_by),
        )
        conn.commit()
    finally:
        conn.close()


def update_user_password(uid, new_password):
    conn = get_conn()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                 (generate_password_hash(new_password), uid))
    conn.commit()
    conn.close()


def delete_user(uid):
    conn = get_conn()
    row = conn.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
    if row and row["role"] == "admin":
        n = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
        if n <= 1:
            conn.close()
            raise ValueError("Нельзя удалить последнего администратора.")
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()


def verify_password(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


# ── Системные настройки ────────────────────────────────────────────────────

def get_setting(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_conn()
    conn.execute(
        """INSERT INTO settings (key, value, updated_at)
           VALUES (?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(key) DO UPDATE SET
             value=excluded.value,
             updated_at=CURRENT_TIMESTAMP""",
        (key, str(value)),
    )
    conn.commit()
    conn.close()


def get_print_retention_days():
    raw = get_setting("print_retention_days", str(DEFAULT_PRINT_RETENTION_DAYS))
    try:
        days = int(raw)
    except (TypeError, ValueError):
        days = DEFAULT_PRINT_RETENTION_DAYS
    return min(max(days, 1), MAX_PRINT_RETENTION_DAYS)


def set_print_retention_days(days):
    try:
        normalized = int(days)
    except (TypeError, ValueError):
        raise ValueError("Срок хранения должен быть целым числом дней.")
    if normalized < 1 or normalized > MAX_PRINT_RETENTION_DAYS:
        raise ValueError(
            f"Срок хранения должен быть от 1 до {MAX_PRINT_RETENTION_DAYS} дней."
        )
    set_setting("print_retention_days", normalized)
    return normalized


# ── Документы ───────────────────────────────────────────────────────────────

def create_document(*, diploma_type, data, qr_text, file_path,
                    recipient_label, created_by, comment="", status="draft",
                    person_iin="", diploma_number="", document_series="",
                    source_kind="", source_label="", source_filename="",
                    source_folder="", source_row_number=None):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO documents
           (diploma_type, data_json, qr_text, status, file_path,
            comment, recipient_label, person_iin, diploma_number, document_series,
            source_kind, source_label, source_filename, source_folder,
            source_row_number, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (diploma_type, json.dumps(data, ensure_ascii=False),
         qr_text or "", status, file_path,
         comment or "", recipient_label or "",
         person_iin or "", diploma_number or "", document_series or "",
         source_kind or "", source_label or "", source_filename or "",
         source_folder or "", source_row_number, created_by),
    )
    doc_id = cur.lastrowid
    conn.commit()
    conn.close()
    return doc_id


def update_document(doc_id, *, data, qr_text, comment, recipient_label, file_path,
                    person_iin="", diploma_number="", document_series="",
                    source_kind="", source_label="", source_filename="",
                    source_folder="", source_row_number=None):
    conn = get_conn()
    conn.execute(
        """UPDATE documents SET
              data_json=?, qr_text=?, comment=?, recipient_label=?,
              person_iin=?, diploma_number=?, document_series=?,
              source_kind=?, source_label=?, source_filename=?,
              source_folder=?, source_row_number=?,
              file_path=?, file_purged_at=NULL,
              print_issue_note=NULL, print_issue_by=NULL, print_issue_at=NULL,
              updated_at=CURRENT_TIMESTAMP
           WHERE id=?""",
        (json.dumps(data, ensure_ascii=False), qr_text or "",
         comment or "", recipient_label or "",
         person_iin or "", diploma_number or "", document_series or "",
         source_kind or "", source_label or "", source_filename or "",
         source_folder or "", source_row_number,
         file_path, doc_id),
    )
    conn.commit()
    conn.close()


def mark_print_issue(doc_id, note, *, user_id):
    conn = get_conn()
    conn.execute(
        """UPDATE documents SET
              print_issue_note=?, print_issue_by=?, print_issue_at=CURRENT_TIMESTAMP,
              updated_at=CURRENT_TIMESTAMP
           WHERE id=?""",
        (note or "", user_id, doc_id),
    )
    conn.commit()
    conn.close()


def set_doc_status(doc_id, status, *, user_id=None):
    if status not in STATUSES:
        raise ValueError(f"Недопустимый статус: {status}")
    conn = get_conn()
    if status == "ready_for_print":
        conn.execute(
            "UPDATE documents SET status=?, sent_to_print_at=CURRENT_TIMESTAMP, "
            "print_issue_note=NULL, print_issue_by=NULL, print_issue_at=NULL, "
            "updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, doc_id))
    elif status == "printed":
        conn.execute(
            "UPDATE documents SET status=?, printed_by=?, printed_at=CURRENT_TIMESTAMP, "
            "print_issue_note=NULL, print_issue_by=NULL, print_issue_at=NULL, "
            "updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, user_id, doc_id))
    else:
        conn.execute(
            "UPDATE documents SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, doc_id))
    conn.commit()
    conn.close()


def get_document(doc_id):
    conn = get_conn()
    row = conn.execute(
        """SELECT d.*, uc.username AS creator_name, up.username AS printer_name,
                  ui.username AS issue_reporter_name
           FROM documents d
           LEFT JOIN users uc ON uc.id = d.created_by
           LEFT JOIN users up ON up.id = d.printed_by
           LEFT JOIN users ui ON ui.id = d.print_issue_by
           WHERE d.id=?""", (doc_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["data"] = json.loads(d["data_json"])
        return d
    return None


def list_documents(*, status=None, created_by=None, limit=200,
                   date_field=None, date_from=None, date_to=None,
                   order_field=None, search=None):
    allowed_fields = {"created_at", "updated_at", "printed_at", "sent_to_print_at"}
    if date_field and date_field not in allowed_fields:
        raise ValueError(f"Недопустимое поле даты: {date_field}")
    if order_field and order_field not in allowed_fields:
        raise ValueError(f"Недопустимое поле сортировки: {order_field}")

    conn = get_conn()
    effective_limit = limit
    if search and limit:
        effective_limit = max(int(limit), 5000)
    q = """SELECT d.*, uc.username AS creator_name, up.username AS printer_name,
                  ui.username AS issue_reporter_name
           FROM documents d
           LEFT JOIN users uc ON uc.id = d.created_by
           LEFT JOIN users up ON up.id = d.printed_by
           LEFT JOIN users ui ON ui.id = d.print_issue_by
           WHERE 1=1"""
    params = []
    if status:
        q += " AND d.status=?"
        params.append(status)
    if created_by:
        q += " AND d.created_by=?"
        params.append(created_by)
    if date_field and date_from:
        q += f" AND date(d.{date_field}) >= date(?)"
        params.append(date_from)
    if date_field and date_to:
        q += f" AND date(d.{date_field}) <= date(?)"
        params.append(date_to)
    q += f" ORDER BY d.{order_field or 'updated_at'} DESC, d.id DESC"
    if effective_limit:
        q += " LIMIT ?"
        params.append(effective_limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    if search:
        needle = str(search or "").strip().casefold()
        if needle:
            rows = [row for row in rows if _document_matches_search(row, needle)]
            if limit:
                rows = rows[:limit]
    return rows


def _document_matches_search(row, needle):
    return needle in _document_search_text(row)


def _document_search_text(row):
    values = [
        row["recipient_label"],
        row["person_iin"],
        row["diploma_number"],
        row["document_series"],
        row["comment"],
        row["qr_text"],
        row["source_kind"],
        row["source_label"],
        row["source_filename"],
        row["source_folder"],
        row["creator_name"],
        row["printer_name"],
        row["issue_reporter_name"],
        row["diploma_type"],
    ]
    try:
        payload = json.loads(row["data_json"] or "{}")
    except (TypeError, ValueError):
        payload = {}
    if isinstance(payload, dict):
        values.extend(payload.values())
    elif payload:
        values.append(payload)
    return " ".join(str(value or "") for value in values).casefold()


def count_documents_by_status():
    conn = get_conn()
    rows = conn.execute(
        "SELECT status, COUNT(*) AS total FROM documents GROUP BY status"
    ).fetchall()
    conn.close()
    counts = {status: 0 for status in STATUSES}
    for row in rows:
        counts[row["status"]] = row["total"]
    counts["total"] = sum(counts.values())
    return counts


def delete_document(doc_id):
    conn = get_conn()
    row = conn.execute("SELECT file_path FROM documents WHERE id=?", (doc_id,)).fetchone()
    conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()
    return row["file_path"] if row else None


def parse_db_datetime(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def get_print_file_expires_at(doc, retention_days=None):
    if not doc:
        return None
    if doc.get("status") and doc.get("status") != "printed":
        return None
    printed_at = parse_db_datetime(doc.get("printed_at"))
    if not printed_at:
        return None
    days = retention_days if retention_days is not None else get_print_retention_days()
    return printed_at + timedelta(days=days)


def is_printed_document_hidden(doc, retention_days=None, now=None):
    expires_at = get_print_file_expires_at(doc, retention_days=retention_days)
    if not expires_at:
        return False
    current = now or datetime.utcnow()
    return expires_at <= current


def purge_expired_printed_files(retention_days=None):
    days = retention_days if retention_days is not None else get_print_retention_days()
    now = datetime.utcnow()

    conn = get_conn()
    rows = conn.execute(
        """SELECT id, status, file_path, printed_at, file_purged_at
           FROM documents
           WHERE status='printed' AND printed_at IS NOT NULL AND file_purged_at IS NULL"""
    ).fetchall()

    purged_ids = []
    for row in rows:
        doc = dict(row)
        if not is_printed_document_hidden(doc, retention_days=days, now=now):
            continue

        file_path = doc.get("file_path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                continue

        purged_ids.append(doc["id"])

    if purged_ids:
        conn.executemany(
            """UPDATE documents
               SET file_path=NULL, file_purged_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            [(doc_id,) for doc_id in purged_ids],
        )
        conn.commit()

    conn.close()
    return len(purged_ids)
