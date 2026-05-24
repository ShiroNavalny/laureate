"""
Шаблоны Лауреата: строгий минималистичный UI без фреймворков.

Цветовая схема:
  • Фон:           #f7f7f5 (тёплый светлый)
  • Текст:         #1a1d24
  • Акцент (КарУ): #1f3a8a (тёмно-синий) и #7c1c2c (бордовый)
  • Граница:       #dcdcd6
"""

# ── LAYOUT: общая обёртка для всех страниц ──────────────────────────────────

LAYOUT = r"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ page_title or 'Лауреат' }} — Лауреат</title>
  <link rel="icon" href="{{ url_for('favicon') }}" sizes="any">
  <style>
    :root {
      --header-offset: 0px;
    }
    *, *::before, *::after { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                   'Helvetica Neue', Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(31,58,138,0.08), transparent 34%),
        linear-gradient(180deg, #f9fafb 0%, #f7f7f5 38%, #f4f2ee 100%);
      color: #1a1d24;
      font-size: 14px;
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      transition: background 0.25s ease;
    }
    body.app-has-header { padding-top: var(--header-offset); }
    a { color: #1f3a8a; text-decoration: none; }
    a:hover { text-decoration: underline; }
    strong { font-weight: 600; }

    /* Шапка */
    header {
      position: fixed;
      inset: 0 0 auto 0;
      background: linear-gradient(135deg, #1f3a8a 0%, #28469d 55%, #233576 100%);
      color: #fff;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      gap: 24px;
      flex-wrap: wrap;
      box-shadow: 0 14px 34px rgba(31,58,138,0.18);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid rgba(255,255,255,0.14);
      z-index: 80;
    }
    header .brand-lockup {
      display: flex;
      align-items: center;
      gap: 14px;
      flex-shrink: 0;
    }
    header .brand-logo {
      height: 72px;
      width: auto;
      object-fit: contain;
      display: block;
    }
    header .brand {
      font-weight: 700;
      font-size: 18px;
      letter-spacing: 0.3px;
      color: #fff;
    }
    header .brand:hover { text-decoration: none; }
    header nav { display: flex; gap: 18px; flex: 1; }
    header nav a {
      color: rgba(255,255,255,0.85);
      font-size: 14px;
      padding: 8px 12px;
      border-radius: 999px;
      transition: background 0.18s ease, color 0.18s ease, transform 0.18s ease;
    }
    header nav a:hover { color: #fff; text-decoration: none; background: rgba(255,255,255,0.08); }
    header nav a.is-active {
      color: #fff;
      background: rgba(255,255,255,0.16);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.12);
    }
    header .user {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 13px;
      color: rgba(255,255,255,0.85);
    }
    header .user .role {
      background: rgba(255,255,255,0.15);
      padding: 2px 8px;
      border-radius: 3px;
      text-transform: uppercase;
      font-size: 11px;
      letter-spacing: 0.5px;
    }
    header .user a {
      color: rgba(255,255,255,0.85);
      border: 1px solid rgba(255,255,255,0.3);
      padding: 4px 10px;
      border-radius: 3px;
    }
    header .user a:hover { background: rgba(255,255,255,0.1); text-decoration: none; }
    .nav-inline-form { display: inline; margin: 0; }
    .nav-link-button {
      color: rgba(255,255,255,0.85);
      border: 1px solid rgba(255,255,255,0.3);
      background: transparent;
      padding: 4px 10px;
      border-radius: 3px;
      font: inherit;
      cursor: pointer;
    }
    .nav-link-button:hover { background: rgba(255,255,255,0.1); color: #fff; }
    .header-progress {
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: 3px;
      background: rgba(255,255,255,0.08);
      overflow: hidden;
      opacity: 0;
      transition: opacity 0.18s ease;
    }
    .header-progress.is-visible { opacity: 1; }
    .header-progress > span {
      display: block;
      width: 38%;
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, rgba(255,255,255,0.1), #f8fafc, rgba(255,255,255,0.1));
      transform: translateX(-120%);
      animation: nav-progress 1s linear infinite;
    }

    /* Контейнер */
    main {
      flex: 1;
      max-width: 1280px;
      width: 100%;
      margin: 0 auto;
      padding: 28px 24px 32px;
      min-height: calc(100vh - var(--header-offset, 0px));
      will-change: opacity, transform;
      transition: opacity 0.22s ease, transform 0.22s ease, filter 0.22s ease;
    }
    main.is-transitioning-out {
      opacity: 0;
      transform: translateY(18px);
      filter: blur(6px);
    }
    main.is-transitioning-in {
      animation: content-in 0.3s ease both;
    }
    body.is-navigating main {
      pointer-events: none;
    }

    h1 { font-size: 24px; margin: 0 0 16px 0; font-weight: 600; }
    h2 { font-size: 18px; margin: 24px 0 12px 0; font-weight: 600; color: #1f3a8a; }
    h3 { font-size: 15px; margin: 16px 0 8px 0; font-weight: 600; }

    /* Flash сообщения */
    .flash {
      padding: 12px 16px;
      border-radius: 4px;
      margin-bottom: 16px;
      font-size: 14px;
      border-left: 3px solid;
    }
    .flash.success { background: #ecfdf5; border-color: #059669; color: #064e3b; }
    .flash.error   { background: #fef2f2; border-color: #dc2626; color: #7f1d1d; }
    .flash.info    { background: #eff6ff; border-color: #1f3a8a; color: #1e3a8a; }

    /* Карточка */
    .card {
      background: #fff;
      border: 1px solid #dcdcd6;
      border-radius: 16px;
      padding: 20px 24px;
      box-shadow: 0 20px 44px rgba(26,29,36,0.05);
      transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    }
    .card + .card { margin-top: 16px; }
    .card:hover {
      border-color: #cfd7ef;
      transform: translateY(-1px);
      box-shadow: 0 24px 48px rgba(26,29,36,0.07);
    }

    /* Кнопки */
    .btn {
      display: inline-block;
      padding: 8px 14px;
      border: 1px solid #1f3a8a;
      background: #1f3a8a;
      color: #fff;
      font-size: 13px;
      font-family: inherit;
      cursor: pointer;
      border-radius: 3px;
      text-decoration: none;
      line-height: 1.4;
      transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease,
                  border-color 0.15s ease, color 0.15s ease;
    }
    .btn:hover {
      background: #163073;
      text-decoration: none;
      transform: translateY(-1px);
      box-shadow: 0 10px 22px rgba(31,58,138,0.16);
    }
    .btn.secondary {
      background: #fff; color: #1f3a8a;
    }
    .btn.secondary:hover { background: #eef1f8; }
    .btn.danger {
      background: #7c1c2c; border-color: #7c1c2c;
    }
    .btn.danger:hover { background: #5d1521; }
    .btn.ghost {
      background: transparent; color: #555; border-color: #c8c8c0;
    }
    .btn.ghost:hover { background: #f0f0e8; color: #1a1d24; }
    .btn.small { padding: 4px 10px; font-size: 12px; }
    .btn[disabled], .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    /* Формы */
    .form-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px 16px;
      margin-bottom: 12px;
    }
    .field {
      display: flex;
      flex-direction: column;
      gap: 4px;
      position: relative;
    }
    .field.field-wide { grid-column: span 2; }
    .field label {
      font-size: 12px;
      color: #555;
      font-weight: 500;
    }
    .field .hint { font-size: 11px; color: #888; margin-top: 2px; }
    input[type=text], input[type=password], input[type=url], input[type=number], input[type=date],
    select, textarea {
      width: 100%;
      padding: 7px 10px;
      border: 1px solid #c8c8c0;
      border-radius: 3px;
      font-size: 13px;
      font-family: inherit;
      background: #fff;
      color: #1a1d24;
    }
    input:focus, select:focus, textarea:focus {
      outline: none;
      border-color: #1f3a8a;
      box-shadow: 0 0 0 2px rgba(31,58,138,0.15);
    }
    textarea { resize: vertical; min-height: 60px; }
    .field.invalid label { color: #991b1b; }
    .field.invalid input,
    .field.invalid select,
    .field.invalid textarea {
      border-color: #dc2626;
      background: #fff7f7;
      box-shadow: 0 0 0 2px rgba(220,38,38,0.12);
    }
    .field-error {
      min-height: 15px;
      font-size: 11px;
      color: #991b1b;
      line-height: 1.3;
    }

    /* Fieldset группа полей */
    fieldset {
      border: 1px solid #dcdcd6;
      border-radius: 14px;
      padding: 14px 18px 16px;
      margin: 0 0 14px 0;
      background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(249,250,251,0.98));
      transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    }
    fieldset:hover {
      border-color: #cfd7ef;
      transform: translateY(-1px);
      box-shadow: 0 16px 34px rgba(31,58,138,0.07);
    }
    legend {
      font-weight: 600;
      font-size: 13px;
      padding: 0 8px;
      color: #1f3a8a;
    }

    /* Радио-кнопки в ряд */
    .radio-group { display: flex; gap: 18px; flex-wrap: wrap; }
    .radio-group label {
      display: flex; align-items: center; gap: 6px;
      cursor: pointer; font-size: 13px; color: #1a1d24;
    }
    .radio-group input[type=radio] { margin: 0; }

    /* Таблица документов */
    table.docs {
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border: 1px solid #dcdcd6;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 18px 40px rgba(26,29,36,0.05);
    }
    table.docs th, table.docs td {
      padding: 10px 14px;
      text-align: left;
      border-bottom: 1px solid #ececec;
      font-size: 13px;
      vertical-align: middle;
    }
    table.docs th {
      background: #f0f0e8;
      font-weight: 600;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      color: #555;
    }
    table.docs tbody tr:hover { background: #fafaf6; }
    table.docs tbody tr:last-child td { border-bottom: none; }
    table.docs td.actions {
      white-space: nowrap;
      text-align: right;
    }
    table.docs td.actions form { display: inline-block; margin: 0 0 0 4px; }
    .doc-person {
      display: grid;
      gap: 4px;
      min-width: 220px;
    }
    .doc-person strong {
      font-size: 13px;
      color: #111827;
    }
    .doc-meta-lines {
      display: grid;
      gap: 2px;
    }
    .source-details { margin-top: 4px; }
    .source-details > summary {
      list-style: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      cursor: pointer;
    }
    .source-details > summary::-webkit-details-marker { display: none; }
    .source-details[open] > summary { margin-bottom: 8px; }
    .source-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 3px 8px;
      border-radius: 999px;
      background: #eef2ff;
      border: 1px solid rgba(31,58,138,0.12);
      color: #1e3a8a;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }
    .source-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 8px;
      padding: 10px 12px;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      background: #f8fafc;
    }
    .source-item {
      display: grid;
      gap: 3px;
    }
    .source-label {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #6b7280;
    }
    .source-value {
      font-size: 12px;
      color: #111827;
      word-break: break-word;
    }

    /* Статус-чип */
    .chip {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 3px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.4px;
      text-transform: uppercase;
    }
    .chip.draft        { background: #f0f0e8; color: #555; }
    .chip.ready_for_print { background: #fef3c7; color: #78350f; }
    .chip.printed      { background: #d1fae5; color: #064e3b; }
    .chip.issue        { background: #fee2e2; color: #991b1b; }
    .chip.type         { background: #e0e7ff; color: #1e3a8a; }

    /* Карточки выбора (на странице "новый диплом") */
    .choice-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      margin-top: 8px;
    }
    .choice-card {
      display: block;
      background: #fff;
      border: 1px solid #dcdcd6;
      border-radius: 18px;
      padding: 24px;
      color: inherit;
      transition: border-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
    }
    .choice-card:hover {
      border-color: #1f3a8a;
      box-shadow: 0 18px 34px rgba(31,58,138,0.12);
      transform: translateY(-2px);
      text-decoration: none;
    }
    .choice-card.is-disabled { border-style: dashed; }
    .choice-card h3 { margin: 0 0 8px 0; color: #1f3a8a; font-size: 16px; }
    .choice-card p { margin: 0; color: #555; font-size: 13px; }
    .choice-tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      margin-bottom: 14px;
      border-radius: 999px;
      background: #eff6ff;
      color: #1e3a8a;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    .choice-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 16px;
    }

    /* Login */
    .login-wrap {
      min-height: calc(100vh - 100px);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .login-card {
      width: 100%;
      max-width: 380px;
      background: #fff;
      border: 1px solid #dcdcd6;
      border-radius: 18px;
      padding: 32px 28px;
      box-shadow: 0 26px 48px rgba(31,58,138,0.12);
    }
    .login-logo {
      display: block;
      width: 260px;
      max-width: 100%;
      margin: 0 auto 18px;
      object-fit: contain;
    }
    .login-card h1 {
      margin: 0 0 24px 0;
      text-align: center;
      color: #1f3a8a;
    }
    .login-card .field { margin-bottom: 14px; }

    /* Утилиты */
    .empty {
      text-align: center;
      padding: 48px 24px;
      color: #888;
      background: #fff;
      border: 1px dashed #dcdcd6;
      border-radius: 4px;
    }
    .empty p { margin: 0 0 12px 0; }
    .toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;
    }
    .muted { color: #888; font-size: 12px; }
    .actions-bar {
      display: flex;
      gap: 8px;
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid #ececec;
      flex-wrap: wrap;
    }
    .actions-bar.right { justify-content: flex-end; }
    .actions-bar.sticky {
      position: sticky;
      bottom: 14px;
      padding: 12px;
      margin-top: 22px;
      border: 1px solid rgba(31,58,138,0.14);
      border-radius: 14px;
      background: rgba(255,255,255,0.94);
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 38px rgba(31,58,138,0.12);
      z-index: 5;
    }
    .filters-card {
      margin-bottom: 16px;
      padding-top: 16px;
      padding-bottom: 16px;
    }
    .filters-card .form-row { margin-bottom: 0; }
    .filters-actions {
      display: flex;
      gap: 8px;
      align-items: flex-end;
      flex-wrap: wrap;
    }
    .section-intro {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 16px;
    }
    .section-intro p { margin: 6px 0 0 0; max-width: 760px; }
    .pill-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      background: #eef2ff;
      color: #1e3a8a;
      font-size: 12px;
      font-weight: 600;
      border: 1px solid rgba(31,58,138,0.12);
    }
    .pill.warn {
      background: #fff7ed;
      color: #9a3412;
      border-color: rgba(154,52,18,0.12);
    }
    .series-groups {
      display: grid;
      gap: 14px;
    }
    .series-card {
      border: 1px solid #d7dcef;
      border-radius: 16px;
      background: #fff;
      box-shadow: 0 14px 30px rgba(26,29,36,0.05);
      overflow: hidden;
    }
    .series-card[open] {
      border-color: #9db0e8;
      box-shadow: 0 18px 36px rgba(31,58,138,0.10);
    }
    .series-summary {
      list-style: none;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      padding: 16px 18px;
      background: linear-gradient(180deg, #eef3ff, #f7f9ff);
      border-bottom: 1px solid transparent;
    }
    .series-summary::-webkit-details-marker { display: none; }
    .series-card[open] .series-summary {
      border-bottom-color: #dde4f7;
    }
    .series-summary-main {
      display: flex;
      align-items: center;
      gap: 14px;
      min-width: 0;
      flex: 1;
    }
    .series-folder-icon {
      position: relative;
      width: 22px;
      height: 16px;
      border-radius: 4px 4px 5px 5px;
      background: linear-gradient(180deg, #f6d77d, #eebc4f);
      border: 1px solid #d9a53b;
      flex: 0 0 auto;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
    }
    .series-folder-icon::before {
      content: "";
      position: absolute;
      left: 2px;
      top: -5px;
      width: 10px;
      height: 6px;
      border-radius: 4px 4px 0 0;
      background: #f4cf70;
      border: 1px solid #d9a53b;
      border-bottom: none;
    }
    .series-chevron {
      width: 10px;
      height: 10px;
      border-right: 2px solid #5f6f99;
      border-bottom: 2px solid #5f6f99;
      transform: rotate(-45deg);
      transition: transform 0.16s ease;
      flex: 0 0 auto;
      margin-left: 4px;
    }
    .series-card[open] .series-chevron {
      transform: rotate(45deg);
    }
    .series-title {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }
    .series-name {
      font-size: 16px;
      font-weight: 700;
      color: #243b7d;
      letter-spacing: 0.02em;
    }
    .series-subtitle {
      margin-top: 4px;
      color: #6b7280;
      font-size: 12px;
    }
    .series-meta {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
      align-items: center;
    }
    .series-body {
      padding: 16px 18px 18px;
      display: grid;
      gap: 14px;
      background: linear-gradient(180deg, #ffffff, #fbfcff);
    }
    .series-toolbar {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    .series-select-tools {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }
    .series-select-toggle {
      display: inline-flex;
      gap: 8px;
      align-items: center;
      font-size: 12px;
      color: #475569;
    }
    .series-select-toggle input {
      width: 15px;
      height: 15px;
      margin: 0;
    }
    .series-toolbar-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    .series-grid {
      display: grid;
      gap: 12px;
    }
    .series-doc {
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 12px 14px;
      background: #fff;
      display: grid;
      gap: 10px;
    }
    .series-doc.is-selected {
      border-color: #8ea4e6;
      box-shadow: 0 0 0 3px rgba(31,58,138,0.08);
      background: #fdfefe;
    }
    .series-doc-topline {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    .series-doc-check {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: #475569;
    }
    .series-doc-check input {
      width: 16px;
      height: 16px;
      margin: 0;
    }
    .series-doc-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      flex-wrap: wrap;
    }
    .series-doc-meta {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    .series-doc-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }
    .import-progress-shell {
      display: grid;
      gap: 16px;
      margin-top: 16px;
    }
    .import-progress-card {
      border: 1px solid rgba(31,58,138,0.12);
      border-radius: 18px;
      padding: 18px 20px;
      background: linear-gradient(180deg, #ffffff, #f7faff);
      box-shadow: 0 18px 36px rgba(31,58,138,0.08);
    }
    .import-progress-card[hidden] { display: none; }
    .import-progress-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }
    .import-progress-title {
      margin: 0 0 6px 0;
      font-size: 16px;
      color: #1f3a8a;
    }
    .import-progress-bar {
      height: 14px;
      border-radius: 999px;
      background: #e5e7eb;
      overflow: hidden;
      margin-bottom: 10px;
    }
    .import-progress-bar > span {
      display: block;
      height: 100%;
      width: 0%;
      border-radius: inherit;
      background: linear-gradient(90deg, #1f3a8a, #2563eb, #60a5fa);
      transition: width 0.35s ease;
    }
    .import-progress-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
    }
    .import-progress-note {
      font-size: 12px;
      color: #6b7280;
    }
    .form-shell {
      display: grid;
      gap: 16px;
    }
    .form-hero {
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
      gap: 18px;
      align-items: start;
    }
    .form-hero h1 { margin-bottom: 8px; }
    .form-hero p { margin: 0; }
    .form-meta {
      display: grid;
      gap: 10px;
    }
    .mini-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 10px;
    }
    .mini-stat {
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 10px 12px;
      background: #fcfcfd;
    }
    .mini-stat strong {
      display: block;
      font-size: 18px;
      line-height: 1.1;
      color: #1f3a8a;
      margin-bottom: 4px;
    }
    .mini-stat span {
      font-size: 12px;
      color: #6b7280;
    }
    .autosave-panel {
      border: 1px solid rgba(31,58,138,0.12);
      border-radius: 14px;
      padding: 12px 14px;
      background: linear-gradient(180deg, #ffffff, #f8fbff);
      box-shadow: 0 14px 30px rgba(31,58,138,0.07);
    }
    .autosave-status {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
      color: #334155;
      margin-bottom: 6px;
    }
    .autosave-dot {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: #94a3b8;
      flex: 0 0 auto;
      transition: background 0.2s ease, transform 0.2s ease;
    }
    .autosave-panel[data-state="dirty"] .autosave-dot { background: #f59e0b; }
    .autosave-panel[data-state="saving"] .autosave-dot {
      background: #2563eb;
      transform: scale(1.15);
    }
    .autosave-panel[data-state="saved"] .autosave-dot { background: #16a34a; }
    .autosave-panel[data-state="error"] .autosave-dot { background: #dc2626; }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 14px;
    }
    .metric-card {
      background: linear-gradient(180deg, #ffffff, #f8fafc);
      border: 1px solid #dcdcd6;
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 18px 34px rgba(15,23,42,0.05);
      animation: rise-in 0.35s ease both;
    }
    .metric-card h3 {
      margin: 0 0 10px 0;
      color: #1a1d24;
      font-size: 14px;
    }
    .metric-main {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: baseline;
      margin-bottom: 10px;
    }
    .metric-value {
      font-size: 26px;
      font-weight: 700;
      color: #1f3a8a;
      line-height: 1;
    }
    .metric-note {
      font-size: 12px;
      color: #6b7280;
    }
    .meter {
      height: 10px;
      background: #e5e7eb;
      border-radius: 999px;
      overflow: hidden;
      margin-bottom: 8px;
    }
    .meter > span {
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #1f3a8a, #3b82f6);
      transition: width 0.4s ease;
    }
    .meter.warn > span { background: linear-gradient(90deg, #d97706, #f59e0b); }
    .meter.danger > span { background: linear-gradient(90deg, #b91c1c, #ef4444); }
    .security-flags {
      display: grid;
      gap: 10px;
    }
    .security-item {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 12px 14px;
      border-radius: 12px;
      border: 1px solid #e5e7eb;
      background: #fff;
    }
    .security-item.ok { border-color: #bbf7d0; background: #f0fdf4; }
    .security-item.warn { border-color: #fed7aa; background: #fff7ed; }
    .security-item.danger { border-color: #fecaca; background: #fef2f2; }
    .file-browser-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }
    .breadcrumbs {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
      font-size: 13px;
    }
    .breadcrumbs .sep { color: #9ca3af; }
    .table-scroll { overflow-x: auto; }
    .file-type {
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-size: 11px;
      font-weight: 700;
    }
    .danger-zone {
      border-color: rgba(124,28,44,0.18);
      background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(252,245,246,0.98));
    }
    .page-note {
      margin: 0 0 16px 0;
      color: #6b7280;
      max-width: 840px;
    }
    .modal-backdrop {
      border: none;
      padding: 0;
      border-radius: 18px;
      width: min(520px, calc(100vw - 24px));
      box-shadow: 0 30px 80px rgba(15,23,42,0.28);
    }
    .modal-backdrop::backdrop {
      background: rgba(15,23,42,0.45);
      backdrop-filter: blur(2px);
    }
    .modal-card {
      padding: 22px 24px;
      background: #fff;
      border-radius: 18px;
    }
    .modal-card h3 { margin-top: 0; margin-bottom: 8px; }
    .modal-card p { margin-top: 0; }
    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 14px;
    }
    .toast-stack {
      position: fixed;
      top: 18px;
      right: 18px;
      width: min(380px, calc(100vw - 24px));
      display: grid;
      gap: 10px;
      z-index: 90;
      pointer-events: none;
    }
    .toast {
      pointer-events: auto;
      border-radius: 16px;
      padding: 14px 16px;
      border: 1px solid rgba(15,23,42,0.08);
      background: rgba(255,255,255,0.96);
      backdrop-filter: blur(10px);
      box-shadow: 0 24px 50px rgba(15,23,42,0.18);
      display: grid;
      gap: 6px;
      transform: translateY(-6px);
      opacity: 0;
      animation: toast-in 0.22s ease forwards;
    }
    .toast.success { border-color: rgba(22,163,74,0.22); }
    .toast.error { border-color: rgba(220,38,38,0.22); }
    .toast.info { border-color: rgba(37,99,235,0.22); }
    .toast.warn { border-color: rgba(245,158,11,0.22); }
    .toast-head {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-start;
    }
    .toast-title {
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: #334155;
    }
    .toast-message {
      font-size: 13px;
      color: #0f172a;
      line-height: 1.45;
    }
    .toast-close {
      border: none;
      background: transparent;
      color: #64748b;
      cursor: pointer;
      font-size: 16px;
      line-height: 1;
      padding: 0;
    }
    .toast[data-leaving="true"] {
      animation: toast-out 0.18s ease forwards;
    }
    .form-workspace {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 380px;
      gap: 18px;
      align-items: start;
    }
    .form-sidebar {
      position: sticky;
      top: 18px;
      display: grid;
      gap: 16px;
    }
    .preview-card {
      padding: 0;
      overflow: hidden;
    }
    .preview-card .card-head {
      padding: 16px 18px 12px;
      border-bottom: 1px solid #e5e7eb;
    }
    .preview-frame-wrap {
      padding: 14px;
      background: linear-gradient(180deg, #eef2ff, #f8fafc);
    }
    .preview-stage {
      display: block;
      border: 1px solid #dbe4ff;
      border-radius: 16px;
      overflow: hidden;
      background: #fff;
      box-shadow: 0 16px 34px rgba(31,58,138,0.08);
    }
    .preview-stage:hover {
      text-decoration: none;
      transform: translateY(-1px);
      box-shadow: 0 20px 40px rgba(31,58,138,0.12);
    }
    .preview-image {
      width: 100%;
      height: auto;
      display: block;
      background: #fff;
    }
    .preview-empty {
      min-height: 320px;
      padding: 30px 20px;
      text-align: center;
      color: #64748b;
      background: linear-gradient(180deg, #f8fafc, #ffffff);
      display: grid;
      place-items: center;
    }
    .progress-card {
      display: grid;
      gap: 12px;
    }
    .progress-head {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: baseline;
    }
    .progress-value {
      font-size: 24px;
      font-weight: 700;
      color: #1f3a8a;
    }
    .progress-meta {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .progress-meta .mini-stat { background: #fff; }
    .restore-banner {
      display: none;
      border: 1px dashed rgba(217,119,6,0.38);
      background: #fff8eb;
      border-radius: 14px;
      padding: 14px 16px;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
    }
    .restore-banner.active { display: flex; }
    .restore-banner .restore-copy { max-width: 460px; }
    .restore-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .modal-shell {
      display: grid;
      gap: 14px;
    }
    .modal-copy {
      color: #64748b;
      margin: 0;
    }
    .modal-form {
      display: grid;
      gap: 12px;
    }
    .flash, .card, table.docs, .choice-card, .login-card, fieldset {
      animation: rise-in 0.35s ease both;
    }
    @keyframes rise-in {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes toast-in {
      from { opacity: 0; transform: translateY(-8px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes toast-out {
      from { opacity: 1; transform: translateY(0) scale(1); }
      to { opacity: 0; transform: translateY(-6px) scale(0.98); }
    }
    @keyframes content-in {
      from { opacity: 0; transform: translateY(16px); filter: blur(6px); }
      to { opacity: 1; transform: translateY(0); filter: blur(0); }
    }
    @keyframes nav-progress {
      from { transform: translateX(-120%); }
      to { transform: translateX(340%); }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { animation: none !important; transition: none !important; }
    }

    @media (max-width: 1080px) {
      .form-workspace {
        grid-template-columns: 1fr;
      }
      .form-sidebar {
        position: static;
      }
    }

    @media (max-width: 860px) {
      header { gap: 14px; }
      header nav { order: 3; width: 100%; }
      header .user { margin-left: auto; }
      header .brand-logo { height: 56px; }
      .login-logo { width: 220px; }
      main { padding: 20px 18px 28px; }
      .form-hero { grid-template-columns: 1fr; }
      .field.field-wide { grid-column: auto; }
      .metric-grid { grid-template-columns: 1fr; }
      .section-intro { flex-direction: column; }
      .actions-bar.sticky { bottom: 8px; }
      .series-summary,
      .series-toolbar,
      .series-doc-head {
        flex-direction: column;
      }
      .series-meta {
        justify-content: flex-start;
      }
      .toast-stack {
        left: 12px;
        right: 12px;
        width: auto;
      }
    }
  </style>
</head>
<body class="{% if current_user and current_user.is_authenticated %}app-has-header{% endif %}">
{% if current_user and current_user.is_authenticated %}
<header id="app-header">
  <div class="brand-lockup">
    <img class="brand-logo"
         src="{{ url_for('asset_file', filename='LaureatMain.png') }}"
         alt="Laureat Main">
    <a class="brand" href="{{ url_for('index') }}" data-nav-scope="docs">Лауреат</a>
  </div>
  <nav>
    {% if current_user.is_editor %}
      <a href="{{ url_for('index') }}" data-nav-scope="docs">Документы</a>
      <a href="{{ url_for('new_type') }}" data-nav-scope="new">Создать</a>
    {% endif %}
    <a href="{{ url_for('archive') }}" data-nav-scope="archive">Архив</a>
    {% if current_user.is_printer %}
      <a href="{{ url_for('print_queue') }}" data-nav-scope="print">Очередь печати</a>
    {% endif %}
    {% if current_user.is_admin %}
      <a href="{{ url_for('admin_users') }}" data-nav-scope="admin-users">Пользователи</a>
      <a href="{{ url_for('admin_system') }}" data-nav-scope="admin-system">Система</a>
      <a href="{{ url_for('admin_logs') }}" data-nav-scope="admin-logs">Все логи</a>
    {% endif %}
  </nav>
  <div class="user">
    <span>{{ current_user.username }}</span>
    <span class="role">{{ current_user.role }}</span>
    <form method="POST" action="{{ url_for('logout') }}" class="nav-inline-form">
      {{ csrf_input|safe }}
      <button type="submit" class="nav-link-button">Выйти</button>
    </form>
  </div>
  <div class="header-progress" id="header-progress" aria-hidden="true"><span></span></div>
</header>
{% endif %}

<div class="toast-stack" id="toast-stack">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="toast {{ cat }}" data-toast>
        <div class="toast-head">
          <div class="toast-title">{% if cat == 'error' %}Ошибка{% elif cat == 'success' %}Готово{% elif cat == 'warn' %}Внимание{% else %}Сообщение{% endif %}</div>
          <button type="button" class="toast-close" data-toast-close>&times;</button>
        </div>
        <div class="toast-message">{{ msg }}</div>
      </div>
    {% endfor %}
  {% endwith %}
</div>

<main id="app-main">
  {{ body_html|safe }}
</main>
  <script id="layout-runtime-script">
  (function () {
    var toastStack = document.getElementById('toast-stack');

    function toArray(list) {
      return Array.prototype.slice.call(list || []);
    }

    function forEachNode(list, callback) {
      toArray(list).forEach(callback);
    }

    function dismissToast(node) {
      if (!node) return;
      node.dataset.leaving = 'true';
      window.setTimeout(function () { node.remove(); }, 180);
    }

    function wireToast(node) {
      if (!node || node.dataset.wired === '1') return;
      node.dataset.wired = '1';
      var close = node.querySelector('[data-toast-close]');
      if (close) close.addEventListener('click', function () { dismissToast(node); });
      window.setTimeout(function () { dismissToast(node); }, 4200);
    }

    function showToast(message, kind, title) {
      if (!toastStack) return;
      var toast = document.createElement('div');
      toast.className = 'toast ' + (kind || 'info');
      toast.setAttribute('data-toast', '');
      toast.innerHTML =
        '<div class="toast-head">' +
        '<div class="toast-title"></div>' +
        '<button type="button" class="toast-close" data-toast-close>&times;</button>' +
        '</div>' +
        '<div class="toast-message"></div>';
      toast.querySelector('.toast-title').textContent = title || (kind === 'error' ? 'Ошибка' : kind === 'success' ? 'Готово' : kind === 'warn' ? 'Внимание' : 'Сообщение');
      toast.querySelector('.toast-message').textContent = message;
      toastStack.appendChild(toast);
      wireToast(toast);
    }

    window.appToast = { show: showToast };
    forEachNode(toastStack && toastStack.querySelectorAll('[data-toast]'), wireToast);
  })();

  (function () {
    var modal = document.getElementById('print-problem-modal');
    if (!modal) return;

    var form = document.getElementById('print-problem-modal-form');
    var docLabel = document.getElementById('print-problem-doc-label');
    var hiddenId = document.getElementById('print-problem-doc-id');
    var textarea = document.getElementById('print-problem-note');
    var cancelBtn = document.getElementById('print-problem-cancel');

    Array.prototype.slice.call(document.querySelectorAll('.js-open-problem-modal')).forEach(function (button) {
      button.addEventListener('click', function () {
        hiddenId.value = button.getAttribute('data-doc-id') || '';
        docLabel.textContent = '#' + (button.getAttribute('data-doc-id') || '');
        textarea.value = button.getAttribute('data-default-note') || '';
        if (typeof modal.showModal === 'function') modal.showModal();
        else modal.setAttribute('open', 'open');
        window.setTimeout(function () { textarea.focus(); }, 30);
      });
    });

    cancelBtn && cancelBtn.addEventListener('click', function () {
      if (typeof modal.close === 'function') modal.close();
      else modal.removeAttribute('open');
    });

    modal.addEventListener('click', function (event) {
      if (event.target === modal && typeof modal.close === 'function') modal.close();
    });

    form && form.addEventListener('submit', function () {
      if (!textarea.value.trim()) textarea.value = 'Возникла проблема при печати.';
    });
  })();

  (function () {
    function getFieldWrap(field) {
      return field.closest('.field');
    }

    function ensureErrorNode(field) {
      var wrap = getFieldWrap(field);
      if (!wrap) return null;
      var node = wrap.querySelector('.field-error');
      if (!node) {
        node = document.createElement('div');
        node.className = 'field-error';
        wrap.appendChild(node);
      }
      return node;
    }

    function shouldValidateField(field) {
      if (!field || field.disabled) return false;
      var type = (field.type || '').toLowerCase();
      return ['hidden', 'submit', 'button', 'reset'].indexOf(type) === -1;
    }

    function validateField(field, force) {
      if (!shouldValidateField(field)) return true;
      var wrap = getFieldWrap(field);
      if (!wrap) return true;
      var errorNode = ensureErrorNode(field);
      var touched = force || field.dataset.touched === '1';
      var valid = field.checkValidity();
      wrap.classList.toggle('invalid', touched && !valid);
      if (errorNode) errorNode.textContent = touched && !valid ? field.validationMessage : '';
      return valid;
    }

    function validateForm(form, force) {
      var fields = Array.prototype.slice.call(form.querySelectorAll('input, select, textarea'));
      var invalidField = null;
      fields.forEach(function (field) {
        var valid = validateField(field, force);
        if (!valid && !invalidField) invalidField = field;
      });
      return invalidField;
    }

    function setAutosaveState(panel, state, text) {
      if (!panel) return;
      panel.dataset.state = state;
      var statusText = panel.querySelector('.js-autosave-text');
      if (statusText) statusText.textContent = text;
    }

    function wireManagedForm(form) {
      if (!form || form.dataset.enhanced === '1') return;
      form.dataset.enhanced = '1';

      var shell = form.closest('.form-shell');
      var panel = shell && shell.querySelector('.js-autosave-panel');
      var restoreBanner = shell && shell.querySelector('.js-restore-banner');
      var restoreApplyBtn = restoreBanner && restoreBanner.querySelector('.js-restore-apply');
      var restoreDiscardBtn = restoreBanner && restoreBanner.querySelector('.js-restore-discard');
      var restoreTime = restoreBanner && restoreBanner.querySelector('.js-restore-time');
      var progressBar = shell && shell.querySelector('.js-progress-bar');
      var progressValue = shell && shell.querySelector('.js-progress-value');
      var progressFilled = shell && shell.querySelector('.js-progress-filled');
      var progressTotal = shell && shell.querySelector('.js-progress-total');
      var previewStage = shell && shell.querySelector('.js-preview-stage');
      var previewImage = shell && shell.querySelector('.js-preview-image');
      var previewEmpty = shell && shell.querySelector('.js-preview-empty');
      var previewLink = shell && shell.querySelector('.js-preview-link');
      var downloadLink = shell && shell.querySelector('.js-download-link');
      var docIdNodes = shell ? shell.querySelectorAll('[data-doc-id-live]') : [];
      var dirty = false;
      var inflight = false;
      var timer = null;
      var submitting = false;
      var persistTimer = null;
      var draftKey = form.dataset.draftKey || '';
      var initialSnapshot = '';
      var restoreSnapshot = null;
      var hasSuccessfulAutosave = false;

      function currentDataObject() {
        if (!form.isConnected) return {};
        var data = {};
        var elements = form.elements || [];
        for (var i = 0; i < elements.length; i += 1) {
          var field = elements[i];
          if (!field || !field.name || field.disabled) continue;
          if (field.name === 'csrf_token' || field.name === 'action') continue;
          var type = (field.type || '').toLowerCase();
          if (type === 'submit' || type === 'button' || type === 'reset' || type === 'file') continue;
          if ((type === 'radio' || type === 'checkbox') && !field.checked) continue;
          data[field.name] = field.value;
        }
        return data;
      }

      function snapshotString() {
        return JSON.stringify(currentDataObject());
      }

      function updateProgress() {
        var requiredFields = Array.prototype.slice.call(form.querySelectorAll('[required]')).filter(shouldValidateField);
        var seenRadio = {};
        var totalCount = 0;
        var filled = 0;
        requiredFields.forEach(function (field) {
          if (field.type === 'radio') {
            if (seenRadio[field.name]) return;
            seenRadio[field.name] = true;
            totalCount += 1;
            if (form.querySelector('[name="' + field.name + '"]:checked')) filled += 1;
            return;
          }
          totalCount += 1;
          if (String(field.value || '').trim()) filled += 1;
        });
        var percent = totalCount ? Math.round((filled / totalCount) * 100) : 100;
        if (progressBar) progressBar.style.width = percent + '%';
        if (progressValue) progressValue.textContent = percent + '%';
        if (progressFilled) progressFilled.textContent = String(filled);
        if (progressTotal) progressTotal.textContent = String(totalCount);
      }

      function persistLocalDraft() {
        if (!draftKey || !form.isConnected) return;
        window.clearTimeout(persistTimer);
        persistTimer = window.setTimeout(function () {
          try {
            window.localStorage.setItem('laureate:draft:' + draftKey, JSON.stringify({
              savedAt: new Date().toISOString(),
              data: currentDataObject()
            }));
          } catch (error) {
          }
        }, 400);
      }

      function maybeShowRestoreBanner() {
        if (!draftKey || !restoreBanner || !form.isConnected) return;
        try {
          var raw = window.localStorage.getItem('laureate:draft:' + draftKey);
          if (!raw) return;
          var parsed = JSON.parse(raw);
          if (!parsed || !parsed.data) return;
          if (JSON.stringify(parsed.data) === initialSnapshot) return;
          restoreSnapshot = parsed;
          restoreBanner.classList.add('active');
          if (restoreTime) {
            restoreTime.textContent = parsed.savedAt ? new Date(parsed.savedAt).toLocaleString('ru-RU') : 'недавно';
          }
        } catch (error) {
        }
      }

      function applyRestoredDraft(data) {
        Object.keys(data).forEach(function (name) {
          var fields = form.querySelectorAll('[name="' + name + '"]');
          if (!fields.length) return;
          Array.prototype.slice.call(fields).forEach(function (field) {
            if (field.type === 'radio') field.checked = field.value === data[name];
            else if (field.type !== 'hidden') field.value = data[name];
            field.dataset.touched = '1';
            validateField(field, false);
          });
        });
        markDirty();
        updateProgress();
        persistLocalDraft();
        scheduleAutosave(1200);
      }

      function syncEditUrl(data) {
        if (!data || !data.edit_url) return;
        if (window.location.pathname !== data.edit_url) {
          window.history.replaceState({}, '', data.edit_url);
        }
        form.setAttribute('action', data.edit_url);
      }

      function syncDocId(data) {
        if (!data || !data.doc_id) return;
        Array.prototype.slice.call(docIdNodes).forEach(function (node) {
          node.textContent = String(data.doc_id);
        });
        if (draftKey && draftKey.endsWith(':new')) {
          var nextKey = draftKey.replace(/:new$/, ':' + String(data.doc_id));
          try {
            var raw = window.localStorage.getItem('laureate:draft:' + draftKey);
            if (raw) {
              window.localStorage.setItem('laureate:draft:' + nextKey, raw);
              window.localStorage.removeItem('laureate:draft:' + draftKey);
            }
          } catch (error) {
          }
          draftKey = nextKey;
          form.dataset.draftKey = nextKey;
        }
      }

      function updatePreview(data) {
        if (!previewEmpty || !data || !data.preview_url || !data.preview_image_url) return;
        if (previewImage) {
          previewImage.src = data.preview_image_url + '?ts=' + Date.now();
        }
        if (previewStage) {
          previewStage.href = data.preview_url;
          previewStage.hidden = false;
        }
        previewEmpty.hidden = true;
        if (previewLink) {
          previewLink.href = data.preview_url;
          previewLink.hidden = false;
        }
        if (downloadLink && data.download_url) {
          downloadLink.href = data.download_url;
          downloadLink.hidden = false;
        }
      }

      function markDirty() {
        dirty = true;
        if (!inflight) setAutosaveState(panel, 'dirty', 'Есть изменения.');
      }

      function scheduleAutosave(delay) {
        if (!dirty || submitting) return;
        window.clearTimeout(timer);
        timer = window.setTimeout(runAutosave, delay || 1800);
      }

      function runAutosave() {
        if (!form.isConnected || !dirty || inflight || submitting) return;
        window.clearTimeout(timer);
        inflight = true;
        setAutosaveState(panel, 'saving', 'Сохранение...');
        var payload = new FormData(form);
        payload.set('action', 'autosave');
        var xhr = new XMLHttpRequest();
        xhr.open('POST', form.getAttribute('action'), true);
        xhr.withCredentials = true;
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.onreadystatechange = function () {
          if (xhr.readyState !== 4) return;
          inflight = false;
          var result = null;
          try {
            result = JSON.parse(xhr.responseText || '{}');
          } catch (error) {
            result = { ok: false, error: 'Некорректный ответ сервера.' };
          }
          if (xhr.status >= 200 && xhr.status < 300 && result && result.ok) {
            dirty = false;
            syncEditUrl(result);
            syncDocId(result);
            updatePreview(result);
            initialSnapshot = snapshotString();
            persistLocalDraft();
            setAutosaveState(panel, 'saved', 'Сохранено: ' + result.saved_at + '.');
            if (!hasSuccessfulAutosave) {
              hasSuccessfulAutosave = true;
              window.appToast && window.appToast.show('Сохранено.', 'success');
            }
            return;
          }
          var message = result && result.error ? result.error : 'Ошибка сохранения.';
          setAutosaveState(panel, 'error', message);
          window.appToast && window.appToast.show(message, 'error');
        };
        xhr.onerror = function () {
          inflight = false;
          setAutosaveState(panel, 'error', 'Ошибка сети.');
          window.appToast && window.appToast.show('Ошибка сети.', 'error');
        };
        xhr.send(payload);
      }

      Array.prototype.slice.call(form.querySelectorAll('input, select, textarea')).forEach(function (field) {
        if (!shouldValidateField(field)) return;
        ensureErrorNode(field);

        field.addEventListener('input', function () {
          if (!form.isConnected) return;
          field.dataset.touched = '1';
          validateField(field, false);
          markDirty();
          updateProgress();
          persistLocalDraft();
          scheduleAutosave(1800);
        });

        field.addEventListener('change', function () {
          if (!form.isConnected) return;
          field.dataset.touched = '1';
          validateField(field, true);
          markDirty();
          updateProgress();
          persistLocalDraft();
          scheduleAutosave(900);
        });

        field.addEventListener('blur', function () {
          if (!form.isConnected) return;
          field.dataset.touched = '1';
          validateField(field, true);
          if (dirty && field.dataset.autosavePriority === '1') runAutosave();
        });
      });

      form.addEventListener('submit', function (event) {
        if (!form.isConnected) return;
        submitting = true;
        var invalidField = validateForm(form, true);
        if (invalidField) {
          event.preventDefault();
          submitting = false;
          setAutosaveState(panel, 'error', 'Проверьте поля.');
          window.appToast && window.appToast.show('Проверьте поля.', 'warn');
          invalidField.focus();
          invalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
          return;
        }
        setAutosaveState(panel, 'saving', 'Сохраняю документ...');
      });

      document.addEventListener('visibilitychange', function () {
        if (!form.isConnected) return;
        if (document.hidden && dirty && !submitting) runAutosave();
      });

      window.addEventListener('beforeunload', function (event) {
        if (!form.isConnected) return;
        if (dirty && !submitting) {
          persistLocalDraft();
          event.preventDefault();
          event.returnValue = '';
        }
      });

      if (restoreApplyBtn) {
        restoreApplyBtn.addEventListener('click', function () {
          if (!restoreSnapshot || !restoreSnapshot.data) return;
          applyRestoredDraft(restoreSnapshot.data);
          restoreBanner.classList.remove('active');
          window.appToast && window.appToast.show('Черновик восстановлен.', 'success');
        });
      }

      if (restoreDiscardBtn) {
        restoreDiscardBtn.addEventListener('click', function () {
          restoreBanner.classList.remove('active');
          if (draftKey) window.localStorage.removeItem('laureate:draft:' + draftKey);
          window.appToast && window.appToast.show('Черновик удалён.', 'info');
        });
      }

      initialSnapshot = snapshotString();
      hasSuccessfulAutosave = !!(previewStage && !previewStage.hidden);
      updateProgress();
      maybeShowRestoreBanner();
    }

    Array.prototype.slice.call(document.querySelectorAll('[data-autosave-form="true"]')).forEach(wireManagedForm);
  })();

  (function () {
    function wireImportJobForm(form) {
      if (!form || form.dataset.enhancedImport === '1') return;
      form.dataset.enhancedImport = '1';

      var submitButton = form.querySelector('.js-import-submit');
      var progressCard = document.querySelector('.js-import-progress-card');
      if (!progressCard) return;

      var stageNode = progressCard.querySelector('.js-import-stage');
      var countNode = progressCard.querySelector('.js-import-count');
      var createdNode = progressCard.querySelector('.js-import-created');
      var messageNode = progressCard.querySelector('.js-import-message');
      var percentNode = progressCard.querySelector('.js-import-percent');
      var bakalavrNode = progressCard.querySelector('.js-import-bakalavr');
      var magistrNode = progressCard.querySelector('.js-import-magistr');
      var stateNode = progressCard.querySelector('.js-import-state');
      var barNode = progressCard.querySelector('.js-import-progress-bar');
      var finishLink = progressCard.querySelector('.js-import-finish-link');

      var activeJobId = form.dataset.activeJobId || '';
      var statusUrl = progressCard.dataset.statusUrl || '';
      var pollTimer = null;
      var currentState = '';

      function setSubmitting(isSubmitting) {
        if (!submitButton) return;
        submitButton.disabled = !!isSubmitting;
        submitButton.textContent = isSubmitting ? 'Запуск...' : 'Импорт';
      }

      function renderStatus(payload) {
        if (!payload) return;
        currentState = payload.state || '';
        progressCard.hidden = false;
        var total = Number(payload.total || 0);
        var processed = Number(payload.processed || 0);
        var created = Number(payload.created || 0);
        var percent = total > 0 ? Math.round((processed / total) * 100) : (currentState === 'succeeded' ? 100 : currentState === 'failed' ? 0 : 5);
        if (stageNode) stageNode.textContent = payload.stage || 'Обработка';
        if (countNode) countNode.textContent = processed + ' / ' + total;
        if (createdNode) createdNode.textContent = 'Создано: ' + created;
        if (messageNode) messageNode.textContent = payload.message || 'Идёт обработка...';
        if (percentNode) percentNode.textContent = percent + '%';
        if (bakalavrNode) bakalavrNode.textContent = String((payload.stats && payload.stats.bakalavr) || 0);
        if (magistrNode) magistrNode.textContent = String((payload.stats && payload.stats.magistr) || 0);
        if (stateNode) {
          stateNode.textContent =
            currentState === 'queued' ? 'в очереди' :
            currentState === 'running' ? 'в работе' :
            currentState === 'succeeded' ? 'завершён' :
            currentState === 'failed' ? 'ошибка' : 'ожидание';
        }
        if (barNode) barNode.style.width = percent + '%';
        if (finishLink && payload.redirect_url) finishLink.href = payload.redirect_url;

        if (currentState === 'succeeded') {
          setSubmitting(false);
          if (finishLink) finishLink.hidden = false;
          if (progressCard.dataset.doneToast !== '1') {
            progressCard.dataset.doneToast = '1';
            window.appToast && window.appToast.show(payload.message || 'Импорт завершён.', 'success');
          }
        } else if (currentState === 'failed') {
          setSubmitting(false);
          if (progressCard.dataset.errorToast !== '1') {
            progressCard.dataset.errorToast = '1';
            window.appToast && window.appToast.show(payload.error || payload.message || 'Ошибка импорта.', 'error');
          }
        }
      }

      function stopPolling() {
        if (pollTimer) {
          window.clearTimeout(pollTimer);
          pollTimer = null;
        }
      }

      function schedulePoll(delay) {
        stopPolling();
        pollTimer = window.setTimeout(fetchStatus, delay || 1200);
      }

      function fetchStatus() {
        if (!statusUrl) return;
        fetch(statusUrl, {
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin'
        })
          .then(function (response) { return response.json().then(function (data) { return { ok: response.ok, data: data }; }); })
          .then(function (result) {
            if (!result.ok || !result.data || !result.data.ok) {
              throw new Error((result.data && result.data.error) || 'Не удалось получить статус импорта.');
            }
            renderStatus(result.data);
            if (currentState === 'queued' || currentState === 'running') schedulePoll(1200);
          })
          .catch(function (error) {
            if (messageNode) messageNode.textContent = error.message || 'Ошибка получения статуса импорта.';
            if (currentState === 'queued' || currentState === 'running') schedulePoll(2000);
          });
      }

      form.addEventListener('submit', function (event) {
        event.preventDefault();
        if (typeof form.reportValidity === 'function' && !form.reportValidity()) return;

        stopPolling();
        progressCard.dataset.doneToast = '';
        progressCard.dataset.errorToast = '';
        if (finishLink) finishLink.hidden = true;
        progressCard.hidden = false;
        setSubmitting(true);
        renderStatus({
          state: 'queued',
          stage: 'Подготовка',
          total: 0,
          processed: 0,
          created: 0,
          stats: { bakalavr: 0, magistr: 0 },
          message: 'Загружаю файл и запускаю импорт...'
        });

        fetch(form.getAttribute('action'), {
          method: 'POST',
          body: new FormData(form),
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin'
        })
          .then(function (response) { return response.json().then(function (data) { return { ok: response.ok, data: data }; }); })
          .then(function (result) {
            if (!result.ok || !result.data || !result.data.ok) {
              throw new Error((result.data && result.data.error) || 'Не удалось запустить импорт.');
            }
            activeJobId = result.data.job_id || '';
            form.dataset.activeJobId = activeJobId;
            statusUrl = result.data.status_url || '';
            progressCard.dataset.statusUrl = statusUrl;
            fetchStatus();
          })
          .catch(function (error) {
            setSubmitting(false);
            if (messageNode) messageNode.textContent = error.message || 'Ошибка запуска импорта.';
            if (stateNode) stateNode.textContent = 'ошибка';
            window.appToast && window.appToast.show(error.message || 'Ошибка запуска импорта.', 'error');
          });
      });

      if (activeJobId && statusUrl) fetchStatus();
    }

    Array.prototype.slice.call(document.querySelectorAll('.js-import-job-form')).forEach(wireImportJobForm);
  })();

  (function () {
    function wireSeriesBulk(card) {
      if (!card || card.dataset.seriesBulk === '1') return;
      card.dataset.seriesBulk = '1';

      var selectAll = card.querySelector('.js-series-select-all');
      var countNode = card.querySelector('.js-series-selected-count');
      var checkboxes = Array.prototype.slice.call(card.querySelectorAll('.js-series-doc-checkbox'));
      var forms = Array.prototype.slice.call(card.querySelectorAll('.js-series-bulk-form'));

      function selectedIds() {
        return checkboxes.filter(function (checkbox) { return checkbox.checked; }).map(function (checkbox) {
          return checkbox.value;
        });
      }

      function applySelection(ids) {
        if (countNode) countNode.textContent = 'Выбрано: ' + ids.length;
        if (selectAll) {
          var allChecked = checkboxes.length > 0 && ids.length === checkboxes.length;
          selectAll.checked = allChecked;
          selectAll.indeterminate = ids.length > 0 && ids.length < checkboxes.length;
        }
        checkboxes.forEach(function (checkbox) {
          var cardNode = checkbox.closest('.series-doc');
          if (cardNode) cardNode.classList.toggle('is-selected', checkbox.checked);
        });
        forms.forEach(function (form) {
          var hidden = form.querySelector('input[name="doc_ids"]');
          var button = form.querySelector('button[type="submit"]');
          if (hidden) hidden.value = ids.join(',');
          if (button) button.disabled = ids.length === 0;
        });
      }

      function refreshState() {
        applySelection(selectedIds());
      }

      if (selectAll) {
        selectAll.addEventListener('click', function (event) {
          event.stopPropagation();
        });
        selectAll.addEventListener('change', function () {
          checkboxes.forEach(function (checkbox) {
            checkbox.checked = selectAll.checked;
          });
          window.setTimeout(refreshState, 0);
        });
      }

      checkboxes.forEach(function (checkbox) {
        checkbox.addEventListener('click', function (event) {
          event.stopPropagation();
        });
        checkbox.addEventListener('change', refreshState);
      });

      forms.forEach(function (form) {
        form.addEventListener('submit', function (event) {
          var ids = selectedIds();
          applySelection(ids);
          if (!ids.length) {
            event.preventDefault();
            window.appToast && window.appToast.show('Сначала выберите документы.', 'warn');
          }
        });
      });

      refreshState();
    }

    Array.prototype.slice.call(document.querySelectorAll('.series-card')).forEach(wireSeriesBulk);
  })();

  (function () {
    function bindDialogTriggers(selector, modalId, onOpen) {
      var modal = document.getElementById(modalId);
      if (!modal) return;
      var cancel = modal.querySelector('[data-modal-cancel]');
      Array.prototype.slice.call(document.querySelectorAll(selector)).forEach(function (button) {
        button.addEventListener('click', function () {
          if (onOpen) onOpen(modal, button);
          if (typeof modal.showModal === 'function') modal.showModal();
          else modal.setAttribute('open', 'open');
        });
      });
      cancel && cancel.addEventListener('click', function () {
        if (typeof modal.close === 'function') modal.close();
      });
      modal.addEventListener('click', function (event) {
        if (event.target === modal && typeof modal.close === 'function') modal.close();
      });
    }

    bindDialogTriggers('.js-open-delete-doc', 'delete-doc-modal', function (modal, button) {
      modal.querySelector('form').action = button.dataset.action || '';
      modal.querySelector('[data-modal-text]').textContent = button.dataset.message || '';
    });

    bindDialogTriggers('.js-open-delete-user', 'delete-user-modal', function (modal, button) {
      modal.querySelector('form').action = button.dataset.action || '';
      modal.querySelector('[data-modal-text]').textContent = button.dataset.message || '';
    });

    bindDialogTriggers('.js-open-delete-file', 'delete-file-modal', function (modal, button) {
      modal.querySelector('form').action = button.dataset.action || '';
      modal.querySelector('input[name="path"]').value = button.dataset.path || '';
      modal.querySelector('[data-modal-text]').textContent = button.dataset.message || '';
    });

    bindDialogTriggers('.js-open-password-modal', 'change-password-modal', function (modal, button) {
      modal.querySelector('form').action = button.dataset.action || '';
      modal.querySelector('[data-password-username]').textContent = button.dataset.username || '';
      var input = modal.querySelector('input[name="password"]');
      if (input) input.value = '';
      window.setTimeout(function () { input && input.focus(); }, 40);
    });
  })();
</script>
<script>
  (function () {
    var main = document.getElementById('app-main');
    var runtimeScript = document.getElementById('layout-runtime-script');
    var header = document.getElementById('app-header');
    var progress = document.getElementById('header-progress');
    var navAbort = null;
    var navSequence = 0;
    var cacheTtlMs = 12000;
    var maxCacheEntries = 10;
    var pageCache = new Map();
    var prefetching = new Set();
    var hoverPrefetchTimer = null;

    function forEachNode(list, callback) {
      Array.prototype.slice.call(list || []).forEach(callback);
    }

    function updateHeaderOffset() {
      if (!header) return;
      document.documentElement.style.setProperty('--header-offset', header.offsetHeight + 'px');
    }

    function resolveNavScope(pathname) {
      if (pathname.startsWith('/new')) return 'new';
      if (pathname.startsWith('/archive')) return 'archive';
      if (pathname.startsWith('/print')) return 'print';
      if (pathname.startsWith('/admin/users')) return 'admin-users';
      if (pathname.startsWith('/admin/system') || pathname.startsWith('/admin/files')) return 'admin-system';
      if (pathname.startsWith('/admin/logs')) return 'admin-logs';
      if (pathname.startsWith('/doc/')) return 'docs';
      if (pathname === '/') return 'docs';
      return '';
    }

    function refreshNavState(pathname) {
      var scope = resolveNavScope(pathname || window.location.pathname);
      forEachNode(document.querySelectorAll('header nav a[data-nav-scope], header .brand[data-nav-scope]'), function (link) {
        link.classList.toggle('is-active', !!scope && link.dataset.navScope === scope);
      });
    }

    function closeOpenDialogs() {
      forEachNode(document.querySelectorAll('dialog[open]'), function (dialog) {
        if (typeof dialog.close === 'function') dialog.close();
        else dialog.removeAttribute('open');
      });
    }

    function normalizeUrl(url) {
      var parsed = new URL(url, window.location.origin);
      parsed.hash = '';
      return parsed.toString();
    }

    function showProgress() {
      if (progress) progress.classList.add('is-visible');
    }

    function hideProgress() {
      if (progress) progress.classList.remove('is-visible');
    }

    function shouldSoftNavigate(link, event) {
      if (!link) return false;
      if (event && (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)) return false;
      if (link.target && link.target !== '_self') return false;
      if (link.hasAttribute('download')) return false;
      if ((link.getAttribute('href') || '').startsWith('#')) return false;
      if (link.dataset.softNav === 'off') return false;

      var url = new URL(link.href, window.location.origin);
      if (url.origin !== window.location.origin) return false;
      if (url.pathname.startsWith('/assets/')) return false;
      if (url.pathname.endsWith('.pdf')) return false;
      if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash === window.location.hash) return false;
      return true;
    }

    function executeRuntime() {
      if (!runtimeScript) return;
      try {
        new Function(runtimeScript.textContent)();
      } catch (error) {
        console.error('runtime reinit failed', error);
      }
    }

    function rememberPage(url, payload) {
      var key = normalizeUrl(url);
      pageCache.set(key, {
        html: payload.html,
        finalUrl: payload.finalUrl || key,
        shellMode: payload.shellMode || '',
        cachedAt: Date.now()
      });
      if (pageCache.size <= maxCacheEntries) return;
      var oldestKey = null;
      var oldestAt = Infinity;
      pageCache.forEach(function (entry, entryKey) {
        if (entry.cachedAt < oldestAt) {
          oldestAt = entry.cachedAt;
          oldestKey = entryKey;
        }
      });
      if (oldestKey) pageCache.delete(oldestKey);
    }

    function getCachedPage(url) {
      var key = normalizeUrl(url);
      var entry = pageCache.get(key);
      if (!entry) return null;
      if ((Date.now() - entry.cachedAt) > cacheTtlMs) {
        pageCache.delete(key);
        return null;
      }
      return entry;
    }

    async function fetchPage(url, signal) {
      var response = await fetch(url, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-Soft-Navigation': '1'
        },
        credentials: 'same-origin',
        signal: signal
      });
      var contentType = response.headers.get('content-type') || '';
      if (!response.ok || contentType.indexOf('text/html') === -1) {
        return { fallbackUrl: response.url || url };
      }
      var payload = {
        html: await response.text(),
        finalUrl: response.url || url,
        shellMode: (response.headers.get('X-App-Shell') || '').toLowerCase()
      };
      rememberPage(url, payload);
      rememberPage(payload.finalUrl || url, payload);
      return payload;
    }

    function applyPayload(payload, options) {
      var parsed = new DOMParser().parseFromString(payload.html, 'text/html');
      var nextMain = parsed.getElementById('app-main');
      var nextHeader = parsed.getElementById('app-header');
      var nextToastStack = parsed.getElementById('toast-stack');
      var isPartialShell = payload.shellMode === 'partial' || (parsed.body && parsed.body.dataset.softShell === '1');
      var targetUrl = payload.finalUrl || (options && options.url) || window.location.href;

      if (!nextMain) {
        window.location.href = targetUrl;
        return false;
      }
      if (!isPartialShell && (!!header) !== (!!nextHeader)) {
        window.location.href = targetUrl;
        return false;
      }

      main.innerHTML = nextMain.innerHTML;
      main.setAttribute('aria-busy', 'true');
      document.title = parsed.title || document.title;

      if (nextToastStack) {
        var currentToastStack = document.getElementById('toast-stack');
        if (currentToastStack) currentToastStack.innerHTML = nextToastStack.innerHTML;
      }

      if (options && options.replace) history.replaceState({ url: targetUrl }, '', targetUrl);
      else history.pushState({ url: targetUrl }, '', targetUrl);

      window.scrollTo({ top: 0, behavior: 'auto' });
      executeRuntime();
      updateHeaderOffset();
      refreshNavState(new URL(targetUrl, window.location.origin).pathname);
      main.classList.remove('is-transitioning-out');
      main.classList.add('is-transitioning-in');
      window.setTimeout(function () {
        main.classList.remove('is-transitioning-in');
        main.removeAttribute('aria-busy');
      }, 320);
      return true;
    }

    async function prefetchUrl(url) {
      var key = normalizeUrl(url);
      if (getCachedPage(key) || prefetching.has(key) || key === normalizeUrl(window.location.href)) return;
      prefetching.add(key);
      try {
        await fetchPage(key);
      } catch (error) {
      } finally {
        prefetching.delete(key);
      }
    }

    function warmNavigationLinks() {
      forEachNode(document.querySelectorAll('header nav a[href], header .brand[href]'), function (link) {
        if (shouldSoftNavigate(link)) prefetchUrl(link.href);
      });
    }

    async function navigateTo(url, options) {
      options = options || {};
      if (!main) {
        window.location.href = url;
        return;
      }

      var navId = ++navSequence;
      var targetUrl = normalizeUrl(url);
      if (navAbort) navAbort.abort();
      navAbort = new AbortController();
      document.body.classList.add('is-navigating');
      showProgress();
      closeOpenDialogs();
      main.classList.remove('is-transitioning-in');
      main.classList.add('is-transitioning-out');

      try {
        var payload = getCachedPage(targetUrl);
        if (!payload) {
          payload = await fetchPage(targetUrl, navAbort.signal);
        }
        if (navId !== navSequence) return;
        if (!payload || payload.fallbackUrl) {
          window.location.href = payload && payload.fallbackUrl ? payload.fallbackUrl : targetUrl;
          return;
        }
        applyPayload(payload, { url: targetUrl, replace: !!options.replace });
      } catch (error) {
        if (error && error.name === 'AbortError') return;
        window.location.href = targetUrl;
      } finally {
        if (navId !== navSequence) return;
        hideProgress();
        document.body.classList.remove('is-navigating');
      }
    }

    document.addEventListener('click', function (event) {
      var link = event.target.closest('a[href]');
      if (!shouldSoftNavigate(link, event)) return;
      event.preventDefault();
      navigateTo(link.href);
    });

    document.addEventListener('mouseover', function (event) {
      var link = event.target.closest('a[href]');
      if (!shouldSoftNavigate(link)) return;
      window.clearTimeout(hoverPrefetchTimer);
      hoverPrefetchTimer = window.setTimeout(function () {
        prefetchUrl(link.href);
      }, 80);
    });

    document.addEventListener('focusin', function (event) {
      var link = event.target.closest('a[href]');
      if (!shouldSoftNavigate(link)) return;
      prefetchUrl(link.href);
    });

    document.addEventListener('touchstart', function (event) {
      var link = event.target.closest('a[href]');
      if (!shouldSoftNavigate(link)) return;
      prefetchUrl(link.href);
    }, { passive: true });

    window.addEventListener('popstate', function () {
      navigateTo(window.location.href, { replace: true });
    });

    window.addEventListener('resize', updateHeaderOffset);
    window.addEventListener('load', function () {
      updateHeaderOffset();
      warmNavigationLinks();
    });
    updateHeaderOffset();
    refreshNavState(window.location.pathname);
    window.setTimeout(warmNavigationLinks, 180);
    if (!history.state) {
      history.replaceState({ url: window.location.href }, '', window.location.href);
    }
  })();
</script>
</body>
</html>
"""


SOFT_NAV_HTML = r"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>{{ page_title or 'Лауреат' }} — Лауреат</title>
</head>
<body data-soft-shell="1">
<div class="toast-stack" id="toast-stack">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}
      <div class="toast {{ cat }}" data-toast>
        <div class="toast-head">
          <div class="toast-title">{% if cat == 'error' %}Ошибка{% elif cat == 'success' %}Готово{% elif cat == 'warn' %}Внимание{% else %}Сообщение{% endif %}</div>
          <button type="button" class="toast-close" data-toast-close>&times;</button>
        </div>
        <div class="toast-message">{{ msg }}</div>
      </div>
    {% endfor %}
  {% endwith %}
</div>

<main id="app-main">
  {{ body_html|safe }}
</main>
</body>
</html>
"""


# ── LOGIN ───────────────────────────────────────────────────────────────────

LOGIN_HTML = r"""
<div class="login-wrap">
  <form method="POST" action="{{ url_for('login') }}" class="login-card">
    {{ csrf_input|safe }}
    <img class="login-logo"
         src="{{ url_for('asset_file', filename='LaureatLogo.png') }}"
         alt="Laureat Logo">
    <h1>Лауреат</h1>
    {% if error %}<div class="flash error">{{ error }}</div>{% endif %}
    <div class="field">
      <label for="username">Логин</label>
      <input id="username" name="username" type="text" autofocus required>
    </div>
    <div class="field">
      <label for="password">Пароль</label>
      <input id="password" name="password" type="password" required>
    </div>
    <button type="submit" class="btn" style="width:100%; margin-top:8px;">Войти</button>
  </form>
</div>
"""


# ── INDEX (мои документы) ──────────────────────────────────────────────────

INDEX_HTML = r"""
<div class="toolbar">
  <h1>{% if current_user.is_admin %}Все документы{% else %}Мои документы{% endif %}</h1>
  {% if current_user.is_editor %}
    <a class="btn" href="{{ url_for('new_type') }}">+ Новый диплом</a>
  {% endif %}
</div>

<div class="card filters-card">
  <form method="GET" action="{{ url_for('index') }}">
    <div class="form-row">
      <div class="field">
        <label>Период</label>
        <select name="period">
          <option value="all" {% if doc_filters.period == 'all' %}selected{% endif %}>Все даты</option>
          <option value="today" {% if doc_filters.period == 'today' %}selected{% endif %}>Сегодня</option>
          <option value="7d" {% if doc_filters.period == '7d' %}selected{% endif %}>Последние 7 дней</option>
          <option value="30d" {% if doc_filters.period == '30d' %}selected{% endif %}>Последние 30 дней</option>
          <option value="month" {% if doc_filters.period == 'month' %}selected{% endif %}>Месяц</option>
          <option value="year" {% if doc_filters.period == 'year' %}selected{% endif %}>Год</option>
          <option value="custom" {% if doc_filters.period == 'custom' %}selected{% endif %}>Свой диапазон</option>
        </select>
      </div>
      <div class="field">
        <label>Год</label>
        <select name="year">
          {% for year in doc_filters.year_options %}
            <option value="{{ year }}" {% if doc_filters.year == year %}selected{% endif %}>{{ year }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="field">
        <label>Месяц</label>
        <select name="month">
          {% for month_value, month_label in doc_filters.month_options %}
            <option value="{{ month_value }}" {% if doc_filters.month == month_value %}selected{% endif %}>{{ month_label }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="field">
        <label>С даты</label>
        <input type="date" name="date_from" value="{{ doc_filters.date_from }}">
      </div>
      <div class="field">
        <label>По дату</label>
        <input type="date" name="date_to" value="{{ doc_filters.date_to }}">
      </div>
      <div class="filters-actions">
        <button class="btn" type="submit">Показать</button>
        <a class="btn ghost" href="{{ url_for('index') }}">Сбросить</a>
      </div>
    </div>
  </form>
</div>

{% if not docs %}
  <div class="empty">
    <p>Документов пока нет.</p>
    {% if current_user.is_editor %}
      <a class="btn" href="{{ url_for('new_type') }}">Создать первый диплом</a>
    {% endif %}
  </div>
{% else %}
<div class="pill-row" style="margin-bottom:14px;">
  <span class="pill">{{ docs|length }} документов</span>
  <span class="pill">{{ doc_groups|length }} серий</span>
</div>
<div class="series-groups">
  {% for group in doc_groups %}
    <details class="series-card" {% if group.default_open %}open{% endif %}>
      <summary class="series-summary">
        <div class="series-summary-main">
          <span class="series-folder-icon" aria-hidden="true"></span>
          <div>
            <div class="series-title">
              <span class="series-name">Серия {{ group.label }}</span>
              <span class="pill">Папка</span>
              <span class="pill">{{ group.total }} документов</span>
            {% if group.issue_count %}
              <span class="chip issue">Проблемы: {{ group.issue_count }}</span>
            {% endif %}
            </div>
            <div class="series-subtitle">Нажмите на серию, чтобы раскрыть документы внутри.</div>
          </div>
        </div>
        <div class="series-meta">
          <span class="pill">Черновики: {{ group.draft_count }}</span>
          <span class="pill">В печати: {{ group.ready_count }}</span>
          <span class="pill">Готово: {{ group.printed_count }}</span>
          <span class="series-chevron" aria-hidden="true"></span>
        </div>
      </summary>
      <div class="series-body">
        <div class="series-toolbar">
          <div class="series-select-tools">
            <label class="series-select-toggle">
              <input type="checkbox" class="js-series-select-all">
              <span>Выбрать все</span>
            </label>
            <span class="pill js-series-selected-count">Выбрано: 0</span>
            <div class="muted">Серия {{ group.label }} сгруппирована для массовой работы.</div>
          </div>
          <div class="series-toolbar-actions">
            <form method="POST" action="{{ url_for('docs_bulk_download') }}" class="js-series-bulk-form">
              {{ csrf_input|safe }}
              <input type="hidden" name="doc_ids" value="">
              <button class="btn secondary" type="submit" disabled>Скачать выбранные</button>
            </form>
            <form method="POST" action="{{ url_for('docs_bulk_send') }}" class="js-series-bulk-form">
              {{ csrf_input|safe }}
              <input type="hidden" name="doc_ids" value="">
              <button class="btn" type="submit" disabled>В печать выбранные</button>
            </form>
            <form method="POST" action="{{ url_for('docs_bulk_recall') }}" class="js-series-bulk-form">
              {{ csrf_input|safe }}
              <input type="hidden" name="doc_ids" value="">
              <button class="btn ghost" type="submit" disabled>Отозвать выбранные</button>
            </form>
            {% if current_user.is_admin %}
              <form method="POST" action="{{ url_for('docs_bulk_delete') }}" class="js-series-bulk-form">
                {{ csrf_input|safe }}
                <input type="hidden" name="doc_ids" value="">
                <button class="btn danger" type="submit" disabled>Удалить выбранные</button>
              </form>
            {% endif %}
            {% if group.draft_count %}
              <form method="POST" action="{{ url_for('docs_series_send') }}">
                {{ csrf_input|safe }}
                <input type="hidden" name="series" value="{{ group.series }}">
                <button class="btn" type="submit">В печать всю серию</button>
              </form>
            {% endif %}
            {% if group.ready_count %}
              <form method="POST" action="{{ url_for('docs_series_recall') }}">
                {{ csrf_input|safe }}
                <input type="hidden" name="series" value="{{ group.series }}">
                <button class="btn ghost" type="submit">Отозвать серию</button>
              </form>
            {% endif %}
          </div>
        </div>
        <div class="series-grid">
          {% for d in group.docs %}
            <article class="series-doc" data-doc-id="{{ d.id }}">
              <div class="series-doc-topline">
                <label class="series-doc-check">
                  <input type="checkbox" class="js-series-doc-checkbox" value="{{ d.id }}">
                  <span>Выбрать документ</span>
                </label>
              </div>
              <div class="series-doc-head">
                <div class="doc-person">
                  <strong>#{{ d.id }} · {{ d.recipient_label or '—' }}</strong>
                  <div class="doc-meta-lines">
                    <div class="muted">ИИН: {{ d.person_iin or '—' }}</div>
                    <div class="muted">№ диплома: {{ d.diploma_number or '—' }}</div>
                    <div class="muted">Создан: {{ d.created_at[:16] }}{% if current_user.is_admin %} · {{ d.creator_name or '—' }}{% endif %}</div>
                  </div>
                </div>
                <div class="series-doc-meta">
                  <span class="chip type">{% if d.diploma_type=='phd' %}PhD{% elif d.diploma_type=='magistr' %}Магистр{% elif d.diploma_type=='bakalavr_honors' %}Бакалавр (отл.){% else %}Бакалавр{% endif %}</span>
                  {% if d.has_print_issue %}
                    <span class="chip issue">Проблема печати</span>
                  {% else %}
                    <span class="chip {{ d.status }}">{% if d.status=='draft' %}Черновик{% elif d.status=='ready_for_print' %}В печать{% else %}Напечатан{% endif %}</span>
                  {% endif %}
                </div>
              </div>
              {% if d.has_print_issue %}
                <div class="muted">{{ d.print_issue_note }}</div>
              {% elif d.expires_at %}
                <div class="muted">PDF хранится до {{ d.expires_at }}</div>
              {% endif %}
              {% if d.source_kind == 'excel' %}
                <details class="source-details">
                  <summary><span class="source-chip">Excel</span></summary>
                  <div class="source-grid">
                    <div class="source-item"><span class="source-label">Серия</span><span class="source-value">{{ d.source_label or '—' }}</span></div>
                    <div class="source-item"><span class="source-label">Файл</span><span class="source-value">{{ d.source_filename or '—' }}</span></div>
                    <div class="source-item"><span class="source-label">Папка</span><span class="source-value">{{ d.source_folder or '—' }}</span></div>
                    <div class="source-item"><span class="source-label">Строка</span><span class="source-value">{{ d.source_row_number or '—' }}</span></div>
                  </div>
                </details>
              {% endif %}
              <div class="series-doc-actions">
                {% if d.file_available %}
                  <a class="btn small ghost" href="{{ url_for('doc_preview', doc_id=d.id) }}" target="_blank">PDF</a>
                {% else %}
                  <span class="muted">PDF удалён</span>
                {% endif %}
                {% if d.status != 'printed' %}
                  <a class="btn small secondary" href="{{ url_for('edit_doc', doc_id=d.id) }}">Изменить</a>
                {% endif %}
                {% if d.status == 'draft' %}
                  <form method="POST" action="{{ url_for('doc_send', doc_id=d.id) }}">
                    {{ csrf_input|safe }}
                    <button class="btn small" type="submit">В печать</button>
                  </form>
                {% elif d.status == 'ready_for_print' %}
                  <form method="POST" action="{{ url_for('doc_recall', doc_id=d.id) }}">
                    {{ csrf_input|safe }}
                    <button class="btn small ghost" type="submit">Отозвать</button>
                  </form>
                {% endif %}
                {% if current_user.is_admin %}
                  <button class="btn small danger js-open-delete-doc"
                          type="button"
                          data-action="{{ url_for('doc_delete', doc_id=d.id) }}"
                          data-message="Документ #{{ d.id }} будет удалён вместе с PDF-файлом. Это действие нельзя отменить.">Удалить</button>
                {% endif %}
              </div>
            </article>
          {% endfor %}
        </div>
      </div>
    </details>
  {% endfor %}
</div>
{% endif %}

<dialog id="delete-doc-modal" class="modal-backdrop">
  <div class="modal-card modal-shell">
    <h3 style="margin:0;">Удалить документ</h3>
    <p class="modal-copy" data-modal-text>Документ будет удалён без возможности восстановления.</p>
    <form method="POST" action="" class="modal-form">
      {{ csrf_input|safe }}
      <div class="modal-actions">
        <button type="button" class="btn ghost" data-modal-cancel>Отмена</button>
        <button type="submit" class="btn danger">Удалить</button>
      </div>
    </form>
  </div>
</dialog>
"""


# ── ARCHIVE ─────────────────────────────────────────────────────────────────

ARCHIVE_HTML = r"""
<div class="toolbar">
  <h1>Архив</h1>
  <div class="pill-row">
    <span class="pill">{{ docs|length }} записей</span>
  </div>
</div>

<div class="card filters-card">
  <form method="GET" action="{{ url_for('archive') }}">
    <div class="form-row">
      <div class="field field-wide">
        <label>Поиск</label>
        <input type="text" name="q" value="{{ archive_query }}" placeholder="ФИО, ИИН, номер, серия, файл">
      </div>
      <div class="field">
        <label>Статус</label>
        <select name="status">
          <option value="" {% if not archive_status %}selected{% endif %}>Все</option>
          <option value="draft" {% if archive_status == 'draft' %}selected{% endif %}>Черновик</option>
          <option value="ready_for_print" {% if archive_status == 'ready_for_print' %}selected{% endif %}>В печать</option>
          <option value="printed" {% if archive_status == 'printed' %}selected{% endif %}>Напечатан</option>
        </select>
      </div>
      <div class="field">
        <label>Период</label>
        <select name="period">
          <option value="all" {% if archive_filters.period == 'all' %}selected{% endif %}>Все даты</option>
          <option value="today" {% if archive_filters.period == 'today' %}selected{% endif %}>Сегодня</option>
          <option value="7d" {% if archive_filters.period == '7d' %}selected{% endif %}>Последние 7 дней</option>
          <option value="30d" {% if archive_filters.period == '30d' %}selected{% endif %}>Последние 30 дней</option>
          <option value="month" {% if archive_filters.period == 'month' %}selected{% endif %}>Месяц</option>
          <option value="year" {% if archive_filters.period == 'year' %}selected{% endif %}>Год</option>
          <option value="custom" {% if archive_filters.period == 'custom' %}selected{% endif %}>Свой диапазон</option>
        </select>
      </div>
      <div class="field">
        <label>Год</label>
        <select name="year">
          {% for year in archive_filters.year_options %}
            <option value="{{ year }}" {% if archive_filters.year == year %}selected{% endif %}>{{ year }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="field">
        <label>Месяц</label>
        <select name="month">
          {% for month_value, month_label in archive_filters.month_options %}
            <option value="{{ month_value }}" {% if archive_filters.month == month_value %}selected{% endif %}>{{ month_label }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="field">
        <label>С даты</label>
        <input type="date" name="date_from" value="{{ archive_filters.date_from }}">
      </div>
      <div class="field">
        <label>По дату</label>
        <input type="date" name="date_to" value="{{ archive_filters.date_to }}">
      </div>
      <div class="filters-actions">
        <button class="btn" type="submit">Найти</button>
        <a class="btn ghost" href="{{ url_for('archive') }}">Сбросить</a>
      </div>
    </div>
  </form>
</div>

{% if not docs %}
  <div class="empty"><p>Совпадений нет.</p></div>
{% else %}
<div class="table-scroll">
  <table class="docs">
    <thead>
      <tr>
        <th>#</th>
        <th>Тип</th>
        <th>Получатель</th>
        <th>Статус</th>
        <th>Автор</th>
        <th>Создан</th>
        <th>Печать</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {% for d in docs %}
      <tr>
        <td>{{ d.id }}</td>
        <td><span class="chip type">{% if d.diploma_type=='phd' %}PhD{% elif d.diploma_type=='magistr' %}Магистр{% elif d.diploma_type=='bakalavr_honors' %}Бакалавр (отл.){% else %}Бакалавр{% endif %}</span></td>
        <td>
          <div class="doc-person">
            <strong>{{ d.recipient_label or '—' }}</strong>
            <div class="doc-meta-lines">
              <div class="muted">ИИН: {{ d.person_iin or '—' }}</div>
              <div class="muted">№ диплома: {{ d.diploma_number or '—' }}</div>
            </div>
            {% if d.source_kind == 'excel' %}
              <details class="source-details">
                <summary><span class="source-chip">Excel</span></summary>
                <div class="source-grid">
                  <div class="source-item"><span class="source-label">Серия</span><span class="source-value">{{ d.source_label or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Файл</span><span class="source-value">{{ d.source_filename or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Папка</span><span class="source-value">{{ d.source_folder or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Строка</span><span class="source-value">{{ d.source_row_number or '—' }}</span></div>
                </div>
              </details>
            {% endif %}
          </div>
        </td>
        <td>
          {% if d.has_print_issue %}
            <span class="chip issue">Проблема</span>
            <div class="muted">{{ d.print_issue_note }}</div>
          {% else %}
            <span class="chip {{ d.status }}">{% if d.status=='draft' %}Черновик{% elif d.status=='ready_for_print' %}В печать{% else %}Напечатан{% endif %}</span>
          {% endif %}
        </td>
        <td class="muted">{{ d.creator_name or '—' }}</td>
        <td class="muted">{{ d.created_at[:16] }}</td>
        <td>
          {% if d.printed_at %}
            <div class="muted">{{ d.printed_at[:16] }}</div>
            <div class="muted">{{ d.printer_name or '—' }}</div>
          {% elif d.sent_to_print_at %}
            <div class="muted">{{ d.sent_to_print_at[:16] }}</div>
            <div class="muted">в очереди</div>
          {% else %}
            <span class="muted">—</span>
          {% endif %}
        </td>
        <td class="actions">
          {% if d.file_available %}
            <a class="btn small ghost" href="{{ url_for('doc_preview', doc_id=d.id) }}" target="_blank">PDF</a>
            <a class="btn small secondary" href="{{ url_for('doc_download', doc_id=d.id) }}">Скачать</a>
          {% else %}
            <span class="muted">PDF удалён</span>
          {% endif %}
          {% if current_user.is_editor and d.status != 'printed' and (current_user.is_admin or d.created_by == current_user.id) %}
            <a class="btn small secondary" href="{{ url_for('edit_doc', doc_id=d.id) }}">Изменить</a>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}
"""


# ── NEW TYPE: выбор бакалавр/PhD ───────────────────────────────────────────

NEW_TYPE_HTML = r"""
<h1>Новый диплом</h1>

<div class="choice-grid">
  <div class="choice-card">
    <div class="choice-tag">Бакалавр / Магистр</div>
    <h3>Создание</h3>
    <p>Форма или Excel.</p>
    <div class="choice-actions">
      <a class="btn" href="{{ url_for('new_bakalavr') }}">Форма</a>
      <a class="btn secondary" href="{{ url_for('import_bakalavr') }}">Excel</a>
    </div>
  </div>
  <div class="choice-card">
    <div class="choice-tag">PhD</div>
    <h3>Создание</h3>
    <p>Форма или Excel.</p>
    <div class="choice-actions">
      <a class="btn" href="{{ url_for('new_phd') }}">Форма</a>
      <a class="btn secondary" href="{{ url_for('import_phd') }}">Excel</a>
    </div>
  </div>
  <div class="choice-card">
    <div class="choice-tag">Сертификат ФДО</div>
    <h3>Создание</h3>
    <p>Педагогическая переподготовка.</p>
    <div class="choice-actions">
      <a class="btn" href="{{ url_for('new_fdo') }}">Форма</a>
      <a class="btn secondary" href="{{ url_for('import_fdo') }}">Excel</a>
    </div>
  </div>
  <div class="choice-card">
    <div class="choice-tag">Сертификат Минор</div>
    <h3>Создание</h3>
    <p>К диплому бакалавра.</p>
    <div class="choice-actions">
      <a class="btn" href="{{ url_for('new_minor') }}">Форма</a>
      <a class="btn secondary" href="{{ url_for('import_minor') }}">Excel</a>
    </div>
  </div>
</div>
"""


# ── IMPORT BAKALAVR / MAGISTR ──────────────────────────────────────────────

IMPORT_BAKALAVR_HTML = r"""
<div class="section-intro">
  <div>
    <h1>Импорт Excel</h1>
    <p class="page-note">Бакалавр / магистр.</p>
  </div>
</div>

<div class="card">
  {% if error %}<div class="flash error">{{ error }}</div>{% endif %}
  <form method="POST"
        action="{{ url_for('import_bakalavr') }}"
        enctype="multipart/form-data"
        class="js-import-job-form"
        data-active-job-id="{{ import_job_id or '' }}">
    {{ csrf_input|safe }}
    <div class="form-row">
      <div class="field">
        <label>Серия</label>
        <input type="text" name="batch_label" value="{{ form_data.batch_label }}" placeholder="ФИЯ_2026">
      </div>
      <div class="field">
        <label>.xlsx</label>
        <input type="file" name="xlsx_file" accept=".xlsx" required>
      </div>
    </div>
    <div class="actions-bar">
      <a class="btn ghost" href="{{ url_for('new_type') }}">Назад</a>
      <button class="btn js-import-submit" type="submit">Импорт</button>
    </div>
  </form>
</div>

<div class="import-progress-shell">
  <div class="import-progress-card js-import-progress-card"
       data-status-url="{% if import_job_id %}{{ url_for('import_bakalavr_status', job_id=import_job_id) }}{% endif %}"
       {% if not import_job_id %}hidden{% endif %}>
    <div class="import-progress-head">
      <div>
        <h3 class="import-progress-title">Импорт на сервере</h3>
        <div class="muted js-import-stage">Ожидание запуска</div>
      </div>
      <div class="pill-row">
        <span class="pill js-import-count">0 / 0</span>
        <span class="pill js-import-created">Создано: 0</span>
      </div>
    </div>
    <div class="import-progress-bar"><span class="js-import-progress-bar"></span></div>
    <div class="import-progress-note js-import-message">Здесь появится текущий статус обработки.</div>
    <div class="import-progress-stats" style="margin-top:14px;">
      <div class="mini-stat"><strong class="js-import-percent">0%</strong><span>готово</span></div>
      <div class="mini-stat"><strong class="js-import-bakalavr">0</strong><span>бакалавр</span></div>
      <div class="mini-stat"><strong class="js-import-magistr">0</strong><span>магистр</span></div>
      <div class="mini-stat"><strong class="js-import-state">ожидание</strong><span>состояние</span></div>
    </div>
    <div class="actions-bar">
      <a class="btn secondary js-import-finish-link" href="{{ url_for('index') }}" hidden>К документам</a>
    </div>
  </div>
</div>
"""


# ── FORM BAKALAVR ─────────────────────────────────────────────────────────

FORM_BAKALAVR_HTML = r"""
<div class="form-shell">
  <div class="card form-hero">
    <div>
      <h1>{{ 'Редактирование диплома' if doc else 'Новый диплом (бакалавр / магистр)' }}</h1>
      {% if doc and doc.print_issue_note %}
        <div class="flash error" style="margin-bottom:0;">
          <strong>Возникла проблема на печати.</strong><br>
          {{ doc.print_issue_note }}
          <div class="muted" style="margin-top:6px; color:inherit;">
            {% if doc.issue_reporter_name %}Отметил: {{ doc.issue_reporter_name }}{% endif %}
            {% if doc.print_issue_at %}{% if doc.issue_reporter_name %} · {% endif %}{{ doc.print_issue_at[:16] }}{% endif %}
          </div>
        </div>
      {% endif %}
    </div>
    <div class="form-meta">
      <div class="autosave-panel js-autosave-panel" data-state="saved">
        <div class="autosave-status"><span class="autosave-dot"></span><span class="js-autosave-text">Автосохранение включено.</span></div>
      </div>
      <div class="mini-stats">
        <div class="mini-stat"><strong data-doc-id-live>{{ doc.id if doc else 'new' }}</strong><span>ID документа</span></div>
      </div>
    </div>
  </div>

  <div class="restore-banner js-restore-banner">
    <div class="restore-copy">
      <strong>Локальный черновик</strong>
      <div class="muted"><span class="js-restore-time">недавно</span></div>
    </div>
    <div class="restore-actions">
      <button type="button" class="btn secondary js-restore-apply">Применить</button>
      <button type="button" class="btn ghost js-restore-discard">Удалить</button>
    </div>
  </div>

  <div class="form-workspace">
  <form method="POST"
        action="{{ url_for('edit_doc', doc_id=doc.id) if doc else url_for('new_bakalavr') }}"
        data-autosave-form="true"
        data-draft-key="bakalavr:{{ doc.id if doc else 'new' }}"
        novalidate>
  {{ csrf_input|safe }}

  <fieldset>
    <legend>Тип</legend>
    <div class="radio-group">
      {% for key, dt in diploma_types.items() %}
        <label>
          <input type="radio" name="diploma_type" value="{{ key }}"
            {% if (data.get('diploma_type') == key) or (not data.get('diploma_type') and loop.first) %}checked{% endif %}>
          {{ dt.title }}
        </label>
      {% endfor %}
    </div>
  </fieldset>

  <fieldset>
    <legend>Номер диплома</legend>
    <div class="form-row">
      <div class="field">
        <label>BD / MD номер (11 цифр)</label>
        <input type="text" name="bd_number" required maxlength="11" pattern="\d{11}" data-autosave-priority="1"
               value="{{ data.get('bd_number','') }}" placeholder="00021884825">
      </div>
      <div class="field">
        <label>ИИН</label>
        <input type="text" name="iin" maxlength="12" pattern="\d{12}"
               value="{{ data.get('iin','') }}" placeholder="123456789012">
      </div>
    </div>
  </fieldset>

  <fieldset>
    <legend>ФИО получателя</legend>
    <div class="form-row">
      <div class="field"><label>Казахский</label>
        <input type="text" name="kaz_fio" required data-autosave-priority="1" value="{{ data.get('kaz_fio','') }}"
          placeholder="Жанымгереева Күндыз Саматқызына"></div>
      <div class="field"><label>Русский</label>
        <input type="text" name="rus_fio" required data-autosave-priority="1" value="{{ data.get('rus_fio','') }}"></div>
      <div class="field"><label>Английский</label>
        <input type="text" name="eng_fio" required data-autosave-priority="1" value="{{ data.get('eng_fio','') }}"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Образовательная программа</legend>
    <div class="form-row">
      <div class="field"><label>Казахский</label>
        <input type="text" name="kaz_program" required value="{{ data.get('kaz_program','') }}"></div>
      <div class="field"><label>Русский</label>
        <input type="text" name="rus_program" required value="{{ data.get('rus_program','') }}"></div>
      <div class="field"><label>Английский</label>
        <input type="text" name="eng_program" required value="{{ data.get('eng_program','') }}"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Квалификация (по желанию)</legend>
    <div class="form-row">
      <div class="field"><label>Казахский</label>
        <input type="text" name="kaz_qualification" value="{{ data.get('kaz_qualification','') }}"
          placeholder="техника және технология"></div>
      <div class="field"><label>Русский</label>
        <input type="text" name="rus_qualification" value="{{ data.get('rus_qualification','') }}"
          placeholder="техники и технологий"></div>
      <div class="field"><label>Английский</label>
        <input type="text" name="eng_qualification" value="{{ data.get('eng_qualification','') }}"
          placeholder="Engineering and Technology"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Форма обучения / направление</legend>
    <div class="form-row">
      <div class="field"><label>Каз</label>
        <input type="text" name="kaz_form" required value="{{ data.get('kaz_form','') }}"
          placeholder="күндізгі / ғылыми-педагогикалық"></div>
      <div class="field"><label>Рус</label>
        <input type="text" name="rus_form" required value="{{ data.get('rus_form','') }}"
          placeholder="очное / научно-педагогическое"></div>
      <div class="field"><label>Англ</label>
        <input type="text" name="eng_form" required value="{{ data.get('eng_form','') }}"
          placeholder="full-time / scientific-pedagogical"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Дата решения комиссии</legend>
    <div class="form-row">
      <div class="field"><label>Год (2 цифры)</label>
        <input type="text" name="year2" required maxlength="2" pattern="\d{2}"
          value="{{ data.get('kaz_year') or data.get('year2','') }}" placeholder="25"></div>
      <div class="field"><label>День</label>
        <input type="text" name="day" required maxlength="2"
          value="{{ data.get('kaz_day') or data.get('day','') }}" placeholder="11"></div>
      <div class="field"><label>Протокол №</label>
        <input type="text" name="protocol" required
          value="{{ data.get('kaz_protocol') or data.get('protocol','') }}" placeholder="68"></div>
    </div>
    <div class="form-row">
      <div class="field"><label>Месяц каз</label>
        <input type="text" name="month_kaz" required value="{{ data.get('kaz_month','') }}"
          placeholder="маусымдағы"></div>
      <div class="field"><label>Месяц рус</label>
        <input type="text" name="month_rus" required value="{{ data.get('rus_month','') }}"
          placeholder="июня"></div>
      <div class="field"><label>Месяц eng</label>
        <input type="text" name="month_eng" required value="{{ data.get('eng_month','') }}"
          placeholder="June"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Дата выдачи (нижняя строка)</legend>
    <div class="form-row">
      <div class="field"><label>Год (4 цифры)</label>
        <input type="text" name="diploma_year" maxlength="4" pattern="\d{4}"
          value="{{ data.get('diploma_year','') }}" placeholder="2026"></div>
      <div class="field"><label>День</label>
        <input type="text" name="diploma_day" maxlength="2"
          value="{{ data.get('diploma_day','') }}" placeholder="12"></div>
      <div class="field"><label>Месяц (каз, словом)</label>
        <input type="text" name="diploma_month" value="{{ data.get('diploma_month','') }}"
          placeholder="наурыз"></div>
      <div class="field"><label>Город</label>
        <input type="text" name="city" value="{{ data.get('city','Қарағанды') }}"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>QR-код (опционально)</legend>
    <div class="form-row">
      <div class="field"><label>Текст или URL для QR</label>
        <input type="text" name="qr_text" value="{{ doc.qr_text if doc else '' }}"
          placeholder="https://buketov.edu.kz/diploma/verify/00021884825"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Комментарий для печатника</legend>
    <textarea name="comment" rows="2">{{ doc.comment if doc else '' }}</textarea>
  </fieldset>

  <div class="actions-bar sticky">
    <a class="btn ghost" href="{{ url_for('index') }}">Отмена</a>
    <button class="btn secondary" type="submit" name="action" value="save">Черновик</button>
    <button class="btn" type="submit" name="action" value="send">В печать</button>
  </div>
</form>

  <aside class="form-sidebar">
    <div class="card progress-card">
      <div class="progress-head">
        <div>
          <h3 style="margin:0 0 4px 0;">Готовность формы</h3>
        </div>
        <div class="progress-value js-progress-value">{{ form_progress.percent }}%</div>
      </div>
      <div class="meter"><span class="js-progress-bar" style="width:{{ form_progress.percent }}%;"></span></div>
      <div class="progress-meta">
        <div class="mini-stat"><strong class="js-progress-filled">{{ form_progress.filled }}</strong><span>заполнено</span></div>
        <div class="mini-stat"><strong class="js-progress-total">{{ form_progress.total }}</strong><span>обязательно</span></div>
      </div>
    </div>

    <div class="card preview-card">
      <div class="card-head">
        <h3 style="margin:0 0 6px 0;">PDF</h3>
        <div class="pill-row">
          <a class="btn small ghost js-preview-link" href="{{ url_for('doc_preview', doc_id=doc.id) if doc and doc.file_path else '#' }}" {% if not doc or not doc.file_path %}hidden{% endif %} target="_blank">Открыть</a>
          <a class="btn small secondary js-download-link" href="{{ url_for('doc_download', doc_id=doc.id) if doc and doc.file_path else '#' }}" {% if not doc or not doc.file_path %}hidden{% endif %}>Скачать</a>
        </div>
      </div>
      <div class="preview-frame-wrap">
        <div class="preview-empty js-preview-empty" {% if doc and doc.file_path %}hidden{% endif %}>
          Нет PDF.
        </div>
        <a class="preview-stage js-preview-stage"
           href="{{ url_for('doc_preview', doc_id=doc.id) if doc and doc.file_path else '#' }}"
           {% if not doc or not doc.file_path %}hidden{% endif %}
           target="_blank">
          <img class="preview-image js-preview-image"
               src="{{ url_for('doc_preview_image', doc_id=doc.id) if doc and doc.file_path else '' }}"
               alt="Превью первой страницы PDF"
               loading="lazy">
        </a>
      </div>
    </div>
  </aside>
  </div>
</div>
"""


# ── FORM PHD ────────────────────────────────────────────────────────────────

FORM_PHD_HTML = r"""
<div class="form-shell">
  <div class="card form-hero">
    <div>
      <h1>{{ 'Редактирование диплома PhD' if doc else 'Новый диплом (PhD)' }}</h1>
      {% if doc and doc.print_issue_note %}
        <div class="flash error" style="margin-bottom:0;">
          <strong>Возникла проблема на печати.</strong><br>
          {{ doc.print_issue_note }}
          <div class="muted" style="margin-top:6px; color:inherit;">
            {% if doc.issue_reporter_name %}Отметил: {{ doc.issue_reporter_name }}{% endif %}
            {% if doc.print_issue_at %}{% if doc.issue_reporter_name %} · {% endif %}{{ doc.print_issue_at[:16] }}{% endif %}
          </div>
        </div>
      {% endif %}
    </div>
    <div class="form-meta">
      <div class="autosave-panel js-autosave-panel" data-state="saved">
        <div class="autosave-status"><span class="autosave-dot"></span><span class="js-autosave-text">Автосохранение включено.</span></div>
      </div>
      <div class="mini-stats">
        <div class="mini-stat"><strong data-doc-id-live>{{ doc.id if doc else 'new' }}</strong><span>ID документа</span></div>
      </div>
    </div>
  </div>

  <div class="restore-banner js-restore-banner">
    <div class="restore-copy">
      <strong>Локальный черновик</strong>
      <div class="muted"><span class="js-restore-time">недавно</span></div>
    </div>
    <div class="restore-actions">
      <button type="button" class="btn secondary js-restore-apply">Применить</button>
      <button type="button" class="btn ghost js-restore-discard">Удалить</button>
    </div>
  </div>

  <div class="form-workspace">
  <form method="POST"
        action="{{ url_for('edit_doc', doc_id=doc.id) if doc else url_for('new_phd') }}"
        data-autosave-form="true"
        data-draft-key="phd:{{ doc.id if doc else 'new' }}"
        novalidate>
  {{ csrf_input|safe }}

  <fieldset>
    <legend>Номер диплома</legend>
    <div class="form-row">
      <div class="field"><label>PhD номер (11 цифр)</label>
        <input type="text" name="phd_number" required maxlength="11" pattern="\d{11}" data-autosave-priority="1"
          value="{{ data.get('phd_number','') }}" placeholder="00001234567"></div>
      <div class="field"><label>ИИН</label>
        <input type="text" name="iin" maxlength="12" pattern="\d{12}"
          value="{{ data.get('iin','') }}" placeholder="123456789012"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Дата заседания диссертационного совета</legend>
    <div class="form-row">
      <div class="field"><label>Год каз</label>
        <input type="text" name="council_year_kaz" required maxlength="4" pattern="\d{4}"
          value="{{ data.get('council_year_kaz','') }}"></div>
      <div class="field"><label>Год eng</label>
        <input type="text" name="council_year_eng" required maxlength="4" pattern="\d{4}"
          value="{{ data.get('council_year_eng','') }}"></div>
      <div class="field"><label>Год рус</label>
        <input type="text" name="council_year_rus" required maxlength="4" pattern="\d{4}"
          value="{{ data.get('council_year_rus','') }}"></div>
      <div class="field"><label>День</label>
        <input type="text" name="council_day" required maxlength="2"
          value="{{ data.get('council_day','') }}"></div>
    </div>
    <div class="form-row">
      <div class="field"><label>Месяц каз</label>
        <input type="text" name="council_month_kaz" required value="{{ data.get('council_month_kaz','') }}" placeholder="мамыр"></div>
      <div class="field"><label>Месяц eng</label>
        <input type="text" name="council_month_eng" required value="{{ data.get('council_month_eng','') }}" placeholder="May"></div>
      <div class="field"><label>Месяц рус</label>
        <input type="text" name="council_month_rus" required value="{{ data.get('council_month_rus','') }}" placeholder="мая"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Дата приказа</legend>
    <div class="form-row">
      <div class="field"><label>Год каз</label>
        <input type="text" name="order_year_kaz" required maxlength="4" pattern="\d{4}"
          value="{{ data.get('order_year_kaz','') }}"></div>
      <div class="field"><label>Год eng</label>
        <input type="text" name="order_year_eng" required maxlength="4" pattern="\d{4}"
          value="{{ data.get('order_year_eng','') }}"></div>
      <div class="field"><label>Год рус</label>
        <input type="text" name="order_year_rus" required maxlength="4" pattern="\d{4}"
          value="{{ data.get('order_year_rus','') }}"></div>
      <div class="field"><label>День</label>
        <input type="text" name="order_day" required maxlength="2"
          value="{{ data.get('order_day','') }}"></div>
      <div class="field"><label>№ приказа</label>
        <input type="text" name="order_number" required value="{{ data.get('order_number','') }}"></div>
    </div>
    <div class="form-row">
      <div class="field"><label>Месяц каз</label>
        <input type="text" name="order_month_kaz" required value="{{ data.get('order_month_kaz','') }}"></div>
      <div class="field"><label>Месяц eng</label>
        <input type="text" name="order_month_eng" required value="{{ data.get('order_month_eng','') }}"></div>
      <div class="field"><label>Месяц рус</label>
        <input type="text" name="order_month_rus" required value="{{ data.get('order_month_rus','') }}"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Фамилия и имя</legend>
    <div class="form-row">
      <div class="field"><label>Фамилия каз</label>
        <input type="text" name="surname_kaz" required data-autosave-priority="1" value="{{ data.get('surname_kaz','') }}"></div>
      <div class="field"><label>Фамилия eng</label>
        <input type="text" name="surname_eng" required data-autosave-priority="1" value="{{ data.get('surname_eng','') }}"></div>
      <div class="field"><label>Фамилия рус</label>
        <input type="text" name="surname_rus" required data-autosave-priority="1" value="{{ data.get('surname_rus','') }}"></div>
    </div>
    <div class="form-row">
      <div class="field"><label>Имя+отчество каз</label>
        <input type="text" name="first_name_kaz" required data-autosave-priority="1" value="{{ data.get('first_name_kaz','') }}"></div>
      <div class="field"><label>Имя eng</label>
        <input type="text" name="first_name_eng" required data-autosave-priority="1" value="{{ data.get('first_name_eng','') }}"></div>
      <div class="field"><label>Имя+отчество рус</label>
        <input type="text" name="first_name_rus" required data-autosave-priority="1" value="{{ data.get('first_name_rus','') }}"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Программа / специальность</legend>
    <div class="form-row">
      <div class="field"><label>Каз</label>
        <input type="text" name="program_kaz" required value="{{ data.get('program_kaz','') }}"></div>
      <div class="field"><label>Eng</label>
        <input type="text" name="program_eng" required value="{{ data.get('program_eng','') }}"></div>
      <div class="field"><label>Рус</label>
        <input type="text" name="program_rus" required value="{{ data.get('program_rus','') }}"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Тема диссертации</legend>
    <div class="form-row">
      <div class="field"><label>Каз</label>
        <input type="text" name="dissertation_kaz" required value="{{ data.get('dissertation_kaz','') }}"></div>
      <div class="field"><label>Eng</label>
        <input type="text" name="dissertation_eng" required value="{{ data.get('dissertation_eng','') }}"></div>
      <div class="field"><label>Рус</label>
        <input type="text" name="dissertation_rus" required value="{{ data.get('dissertation_rus','') }}"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Научные консультанты</legend>
    <div class="form-row">
      <div class="field"><label>Каз</label>
        <input type="text" name="consultants_kaz" value="{{ data.get('consultants_kaz','') }}"></div>
      <div class="field"><label>Eng</label>
        <input type="text" name="consultants_eng" value="{{ data.get('consultants_eng','') }}"></div>
      <div class="field"><label>Рус</label>
        <input type="text" name="consultants_rus" value="{{ data.get('consultants_rus','') }}"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Официальные рецензенты</legend>
    <div class="form-row">
      <div class="field"><label>Каз</label>
        <input type="text" name="reviewers_kaz" value="{{ data.get('reviewers_kaz','') }}"></div>
      <div class="field"><label>Eng</label>
        <input type="text" name="reviewers_eng" value="{{ data.get('reviewers_eng','') }}"></div>
      <div class="field"><label>Рус</label>
        <input type="text" name="reviewers_rus" value="{{ data.get('reviewers_rus','') }}"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Место защиты</legend>
    <div class="form-row">
      <div class="field"><label>Каз</label>
        <input type="text" name="place_kaz" value="{{ data.get('place_kaz','') }}"
          placeholder="Қарағанды, КарУ им. Е.А. Бөкетов"></div>
      <div class="field"><label>Eng</label>
        <input type="text" name="place_eng" value="{{ data.get('place_eng','') }}"></div>
      <div class="field"><label>Рус</label>
        <input type="text" name="place_rus" value="{{ data.get('place_rus','') }}"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Дата защиты</legend>
    <div class="form-row">
      <div class="field"><label>Каз</label>
        <input type="text" name="defense_date_kaz" value="{{ data.get('defense_date_kaz','') }}"
          placeholder="11 мамыр 2025"></div>
      <div class="field"><label>Eng</label>
        <input type="text" name="defense_date_eng" value="{{ data.get('defense_date_eng','') }}"
          placeholder="May 11, 2025"></div>
      <div class="field"><label>Рус</label>
        <input type="text" name="defense_date_rus" value="{{ data.get('defense_date_rus','') }}"
          placeholder="11 мая 2025"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Дата выдачи диплома</legend>
    <div class="form-row">
      <div class="field"><label>Год (4 цифры)</label>
        <input type="text" name="issue_year" maxlength="4" pattern="\d{4}"
          value="{{ data.get('issue_year','') }}" placeholder="2026"></div>
      <div class="field"><label>День</label>
        <input type="text" name="issue_day" maxlength="2"
          value="{{ data.get('issue_day','') }}" placeholder="12"></div>
      <div class="field"><label>Месяц каз</label>
        <input type="text" name="issue_month_kaz" value="{{ data.get('issue_month_kaz','') }}"
          placeholder="наурыз"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>QR-код (опционально)</legend>
    <div class="form-row">
      <div class="field"><label>Текст или URL</label>
        <input type="text" name="qr_text" value="{{ doc.qr_text if doc else '' }}"
          placeholder="https://buketov.edu.kz/diploma/verify/00001234567"></div>
    </div>
  </fieldset>

  <fieldset>
    <legend>Комментарий для печатника</legend>
    <textarea name="comment" rows="2">{{ doc.comment if doc else '' }}</textarea>
  </fieldset>

  <div class="actions-bar sticky">
    <a class="btn ghost" href="{{ url_for('index') }}">Отмена</a>
    <button class="btn secondary" type="submit" name="action" value="save">Черновик</button>
    <button class="btn" type="submit" name="action" value="send">В печать</button>
  </div>
</form>

  <aside class="form-sidebar">
    <div class="card progress-card">
      <div class="progress-head">
        <div>
          <h3 style="margin:0 0 4px 0;">Готовность формы</h3>
        </div>
        <div class="progress-value js-progress-value">{{ form_progress.percent }}%</div>
      </div>
      <div class="meter"><span class="js-progress-bar" style="width:{{ form_progress.percent }}%;"></span></div>
      <div class="progress-meta">
        <div class="mini-stat"><strong class="js-progress-filled">{{ form_progress.filled }}</strong><span>заполнено</span></div>
        <div class="mini-stat"><strong class="js-progress-total">{{ form_progress.total }}</strong><span>обязательно</span></div>
      </div>
    </div>

    <div class="card preview-card">
      <div class="card-head">
        <h3 style="margin:0 0 6px 0;">PDF</h3>
        <div class="pill-row">
          <a class="btn small ghost js-preview-link" href="{{ url_for('doc_preview', doc_id=doc.id) if doc and doc.file_path else '#' }}" {% if not doc or not doc.file_path %}hidden{% endif %} target="_blank">Открыть</a>
          <a class="btn small secondary js-download-link" href="{{ url_for('doc_download', doc_id=doc.id) if doc and doc.file_path else '#' }}" {% if not doc or not doc.file_path %}hidden{% endif %}>Скачать</a>
        </div>
      </div>
      <div class="preview-frame-wrap">
        <div class="preview-empty js-preview-empty" {% if doc and doc.file_path %}hidden{% endif %}>
          Нет PDF.
        </div>
        <a class="preview-stage js-preview-stage"
           href="{{ url_for('doc_preview', doc_id=doc.id) if doc and doc.file_path else '#' }}"
           {% if not doc or not doc.file_path %}hidden{% endif %}
           target="_blank">
          <img class="preview-image js-preview-image"
               src="{{ url_for('doc_preview_image', doc_id=doc.id) if doc and doc.file_path else '' }}"
               alt="Превью первой страницы PDF"
               loading="lazy">
        </a>
      </div>
    </div>
  </aside>
  </div>
</div>
"""


# ── PRINT QUEUE ────────────────────────────────────────────────────────────

PRINT_QUEUE_HTML = r"""
<h1>Очередь печати</h1>

<h2>В очереди <span class="muted">({{ ready|length }})</span></h2>
{% if not ready %}
  <div class="empty"><p>Нет документов.</p></div>
{% else %}
<div class="series-groups">
  {% for group in ready_groups %}
    <details class="series-card" {% if group.default_open %}open{% endif %}>
      <summary class="series-summary">
        <div class="series-summary-main">
          <span class="series-folder-icon" aria-hidden="true"></span>
          <div>
            <div class="series-title">
              <span class="series-name">Серия {{ group.label }}</span>
              <span class="pill">Папка</span>
              <span class="pill">{{ group.total }} документов</span>
              <span class="chip ready_for_print">В очереди</span>
            </div>
            <div class="series-subtitle">Нажмите на серию, чтобы раскрыть документы на печать.</div>
          </div>
        </div>
        <div class="series-meta">
          <span class="pill">Отправлено: {{ group.ready_count }}</span>
          <span class="series-chevron" aria-hidden="true"></span>
        </div>
      </summary>
      <div class="series-body">
        <div class="series-toolbar">
          <div class="series-select-tools">
            <label class="series-select-toggle">
              <input type="checkbox" class="js-series-select-all">
              <span>Выбрать все</span>
            </label>
            <span class="pill js-series-selected-count">Выбрано: 0</span>
            <div class="muted">Серия подготовлена к печати.</div>
          </div>
          <div class="series-toolbar-actions">
            <form method="POST" action="{{ url_for('print_bulk_download') }}" class="js-series-bulk-form">
              {{ csrf_input|safe }}
              <input type="hidden" name="doc_ids" value="">
              <button class="btn secondary" type="submit" disabled>Скачать выбранные</button>
            </form>
            <form method="POST" action="{{ url_for('print_bulk_done') }}" class="js-series-bulk-form">
              {{ csrf_input|safe }}
              <input type="hidden" name="doc_ids" value="">
              <button class="btn" type="submit" disabled>Пометить выбранные</button>
            </form>
            <form method="POST" action="{{ url_for('print_series_done') }}">
              {{ csrf_input|safe }}
              <input type="hidden" name="series" value="{{ group.series }}">
              <button class="btn" type="submit">Напечатать всю серию</button>
            </form>
          </div>
        </div>
        <div class="series-grid">
          {% for d in group.docs %}
            <article class="series-doc" data-doc-id="{{ d.id }}">
              <div class="series-doc-topline">
                <label class="series-doc-check">
                  <input type="checkbox" class="js-series-doc-checkbox" value="{{ d.id }}">
                  <span>Выбрать документ</span>
                </label>
              </div>
              <div class="series-doc-head">
                <div class="doc-person">
                  <strong>#{{ d.id }} · {{ d.recipient_label or '—' }}</strong>
                  <div class="doc-meta-lines">
                    <div class="muted">ИИН: {{ d.person_iin or '—' }}</div>
                    <div class="muted">№ диплома: {{ d.diploma_number or '—' }}</div>
                    <div class="muted">Отправил: {{ d.creator_name or '—' }} · {{ (d.sent_to_print_at or d.updated_at)[:16] }}</div>
                  </div>
                </div>
                <div class="series-doc-meta">
                  <span class="chip type">{% if d.diploma_type=='phd' %}PhD{% elif d.diploma_type=='magistr' %}Магистр{% elif d.diploma_type=='bakalavr_honors' %}Бакалавр (отл.){% else %}Бакалавр{% endif %}</span>
                </div>
              </div>
              <div class="muted">{{ d.comment or 'Без комментария' }}</div>
              {% if d.source_kind == 'excel' %}
                <details class="source-details">
                  <summary><span class="source-chip">Excel</span></summary>
                  <div class="source-grid">
                    <div class="source-item"><span class="source-label">Серия</span><span class="source-value">{{ d.source_label or '—' }}</span></div>
                    <div class="source-item"><span class="source-label">Файл</span><span class="source-value">{{ d.source_filename or '—' }}</span></div>
                    <div class="source-item"><span class="source-label">Папка</span><span class="source-value">{{ d.source_folder or '—' }}</span></div>
                    <div class="source-item"><span class="source-label">Строка</span><span class="source-value">{{ d.source_row_number or '—' }}</span></div>
                  </div>
                </details>
              {% endif %}
              <div class="series-doc-actions">
                {% if d.file_available %}
                  <a class="btn small ghost" href="{{ url_for('doc_preview', doc_id=d.id) }}" target="_blank">Просмотр</a>
                  <a class="btn small secondary" href="{{ url_for('doc_download', doc_id=d.id) }}">Скачать PDF</a>
                {% else %}
                  <span class="muted">PDF удалён</span>
                {% endif %}
                <button class="btn small danger js-open-problem-modal"
                        type="button"
                        data-doc-id="{{ d.id }}"
                        data-default-note="">Проблема</button>
                <form method="POST" action="{{ url_for('print_done', doc_id=d.id) }}">
                  {{ csrf_input|safe }}
                  <button class="btn small" type="submit">Напечатано</button>
                </form>
              </div>
            </article>
          {% endfor %}
        </div>
      </div>
    </details>
  {% endfor %}
</div>
{% endif %}

<h2 style="margin-top:32px;">Проблемы <span class="muted">({{ issues|length }})</span></h2>
{% if not issues %}
  <div class="empty"><p>Нет записей.</p></div>
{% else %}
<div class="table-scroll">
  <table class="docs">
    <thead>
      <tr>
        <th>#</th><th>Тип</th><th>Получатель</th><th>Проблема</th><th>Кто отметил</th><th>Когда</th><th></th>
      </tr>
    </thead>
    <tbody>
      {% for d in issues %}
      <tr>
        <td>{{ d.id }}</td>
        <td><span class="chip type">{% if d.diploma_type=='phd' %}PhD{% elif d.diploma_type=='magistr' %}Магистр{% elif d.diploma_type=='bakalavr_honors' %}Бакалавр (отл.){% else %}Бакалавр{% endif %}</span></td>
        <td>
          <div class="doc-person">
            <strong>{{ d.recipient_label or '—' }}</strong>
            <div class="doc-meta-lines">
              <div class="muted">ИИН: {{ d.person_iin or '—' }}</div>
              <div class="muted">№ диплома: {{ d.diploma_number or '—' }}</div>
            </div>
            {% if d.source_kind == 'excel' %}
              <details class="source-details">
                <summary><span class="source-chip">Excel</span></summary>
                <div class="source-grid">
                  <div class="source-item"><span class="source-label">Серия</span><span class="source-value">{{ d.source_label or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Файл</span><span class="source-value">{{ d.source_filename or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Папка</span><span class="source-value">{{ d.source_folder or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Строка</span><span class="source-value">{{ d.source_row_number or '—' }}</span></div>
                </div>
              </details>
            {% endif %}
          </div>
        </td>
        <td>{{ d.print_issue_note }}</td>
        <td class="muted">{{ d.issue_reporter_name or '—' }}</td>
        <td class="muted">{{ (d.print_issue_at or '')[:16] }}</td>
        <td class="actions">
          {% if d.file_available %}
            <a class="btn small ghost" href="{{ url_for('doc_preview', doc_id=d.id) }}" target="_blank">Просмотр</a>
            <a class="btn small secondary" href="{{ url_for('doc_download', doc_id=d.id) }}">Скачать PDF</a>
          {% else %}
            <span class="muted">PDF удалён</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}

<dialog id="print-problem-modal" class="modal-backdrop">
  <div class="modal-card">
    <h3>Проблема при печати <span id="print-problem-doc-label"></span></h3>
    <form id="print-problem-modal-form" method="POST" action="{{ url_for('print_problem') }}">
      {{ csrf_input|safe }}
      <input id="print-problem-doc-id" type="hidden" name="doc_id" value="">
      <div class="field">
        <label for="print-problem-note">Описание проблемы</label>
        <textarea id="print-problem-note" name="problem_note" rows="4"
                  placeholder="Описание"></textarea>
      </div>
      <div class="modal-actions">
        <button id="print-problem-cancel" type="button" class="btn ghost">Отмена</button>
        <button type="submit" class="btn danger">Сохранить</button>
      </div>
    </form>
  </div>
</dialog>

<h2 style="margin-top:32px;">История <span class="muted">(последние 50)</span></h2>
{% if not printed %}
  <div class="empty"><p>Нет записей.</p></div>
{% else %}
<div class="table-scroll">
  <table class="docs">
    <thead>
      <tr><th>#</th><th>Тип</th><th>Получатель</th><th>Кто печатал</th><th>Когда</th><th>Автоудаление</th><th></th></tr>
    </thead>
    <tbody>
      {% for d in printed %}
      <tr>
        <td>{{ d.id }}</td>
        <td><span class="chip type">{% if d.diploma_type=='phd' %}PhD{% elif d.diploma_type=='magistr' %}Магистр{% elif d.diploma_type=='bakalavr_honors' %}Бакалавр (отл.){% else %}Бакалавр{% endif %}</span></td>
        <td>
          <div class="doc-person">
            <strong>{{ d.recipient_label or '—' }}</strong>
            <div class="doc-meta-lines">
              <div class="muted">ИИН: {{ d.person_iin or '—' }}</div>
              <div class="muted">№ диплома: {{ d.diploma_number or '—' }}</div>
            </div>
            {% if d.source_kind == 'excel' %}
              <details class="source-details">
                <summary><span class="source-chip">Excel</span></summary>
                <div class="source-grid">
                  <div class="source-item"><span class="source-label">Серия</span><span class="source-value">{{ d.source_label or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Файл</span><span class="source-value">{{ d.source_filename or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Папка</span><span class="source-value">{{ d.source_folder or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Строка</span><span class="source-value">{{ d.source_row_number or '—' }}</span></div>
                </div>
              </details>
            {% endif %}
          </div>
        </td>
        <td class="muted">{{ d.printer_name or '—' }}</td>
        <td class="muted">{{ (d.printed_at or '')[:16] }}</td>
        <td class="muted">{{ d.expires_at or '—' }}</td>
        <td class="actions">
          {% if d.file_available %}
            <a class="btn small ghost" href="{{ url_for('doc_download', doc_id=d.id) }}">Скачать</a>
          {% else %}
            <span class="muted">PDF удалён</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}
"""


# ── ADMIN USERS ────────────────────────────────────────────────────────────

ADMIN_USERS_HTML = r"""
<h1>Пользователи</h1>

<div class="card">
  <h3 style="margin-top:0">Хранение напечатанных документов</h3>
  <p class="muted" style="margin-top:0;">
    По истечении срока PDF удаляется. Запись остаётся в логах.
  </p>
  <form method="POST" action="{{ url_for('admin_retention') }}">
    {{ csrf_input|safe }}
    <div class="form-row">
      <div class="field">
        <label>Срок хранения PDF (дней)</label>
        <input type="number" name="retention_days" min="1" max="3650"
               value="{{ print_retention_days }}" required>
      </div>
    </div>
    <div class="actions-bar right" style="border:none; padding:0; margin-top:12px;">
      <button class="btn" type="submit">Сохранить срок</button>
    </div>
  </form>
</div>

<div class="card">
  <h3 style="margin-top:0">Новый пользователь</h3>
  {% if error %}<div class="flash error">{{ error }}</div>{% endif %}
  <form method="POST" action="{{ url_for('admin_users') }}">
    {{ csrf_input|safe }}
    <div class="form-row">
      <div class="field"><label>Логин</label>
        <input type="text" name="username" required></div>
      <div class="field"><label>Пароль</label>
        <input type="password" name="password" required></div>
      <div class="field"><label>Роль</label>
        <select name="role" required>
          <option value="editor">Редактор</option>
          <option value="printer">Печатник</option>
        </select></div>
    </div>
    <div class="actions-bar right" style="border:none; padding:0; margin-top:12px;">
      <button class="btn" type="submit">Создать</button>
    </div>
  </form>
</div>

<h2 style="margin-top:32px;">Все пользователи ({{ users|length }})</h2>
<table class="docs">
  <thead>
    <tr><th>#</th><th>Логин</th><th>Роль</th><th>Создан</th><th>Кем создан</th><th></th></tr>
  </thead>
  <tbody>
  {% for u in users %}
    <tr>
      <td>{{ u.id }}</td>
      <td><strong>{{ u.username }}</strong>{% if u.id == current_user.id %} <span class="muted">(вы)</span>{% endif %}</td>
      <td>
        <span class="chip {% if u.role=='admin' %}printed{% elif u.role=='editor' %}ready_for_print{% else %}draft{% endif %}">
          {{ u.role }}
        </span>
      </td>
      <td class="muted">{{ u.created_at[:16] }}</td>
      <td class="muted">{{ u.creator_name or 'system' }}</td>
      <td class="actions">
        <button class="btn small ghost js-open-password-modal"
                type="button"
                data-action="{{ url_for('admin_user_pwd', uid=u.id) }}"
                data-username="{{ u.username }}">Пароль</button>
        {% if u.id != current_user.id and u.role != 'admin' %}
        <button class="btn small danger js-open-delete-user"
                type="button"
                data-action="{{ url_for('admin_user_delete', uid=u.id) }}"
                data-message="Пользователь {{ u.username }} будет удалён. Это действие нельзя отменить.">×</button>
        {% endif %}
      </td>
    </tr>
  {% endfor %}
  </tbody>
</table>

<dialog id="change-password-modal" class="modal-backdrop">
  <div class="modal-card modal-shell">
    <h3 style="margin:0;">Сменить пароль</h3>
    <p class="modal-copy"><strong data-password-username></strong></p>
    <form method="POST" action="" class="modal-form">
      {{ csrf_input|safe }}
      <div class="field">
        <label>Новый пароль</label>
        <input type="password" name="password" required minlength="4">
      </div>
      <div class="modal-actions">
        <button type="button" class="btn ghost" data-modal-cancel>Отмена</button>
        <button type="submit" class="btn">Сохранить пароль</button>
      </div>
    </form>
  </div>
</dialog>

<dialog id="delete-user-modal" class="modal-backdrop">
  <div class="modal-card modal-shell">
    <h3 style="margin:0;">Удалить пользователя</h3>
    <p class="modal-copy" data-modal-text>Пользователь будет удалён без возможности восстановления.</p>
    <form method="POST" action="" class="modal-form">
      {{ csrf_input|safe }}
      <div class="modal-actions">
        <button type="button" class="btn ghost" data-modal-cancel>Отмена</button>
        <button type="submit" class="btn danger">Удалить</button>
      </div>
    </form>
  </div>
</dialog>
"""


# ── ADMIN SYSTEM ────────────────────────────────────────────────────────────

ADMIN_SYSTEM_HTML = r"""
<div class="section-intro">
  <div>
    <h1>Система</h1>
  </div>
  <div class="pill-row">
    <span class="pill">{{ system_stats.host }}</span>
    <span class="pill">{{ system_stats.platform }}</span>
    <span class="pill warn">Python {{ system_stats.python }}</span>
  </div>
</div>

<div class="metric-grid" style="margin-bottom:16px;">
  <div class="metric-card">
    <h3>CPU / Load</h3>
    <div class="metric-main">
      <div class="metric-value">{{ system_stats.load.pct_text }}</div>
      <div class="metric-note">{{ system_stats.cpu_count }} ядер</div>
    </div>
    <div class="meter {% if system_stats.load.pct >= 85 %}danger{% elif system_stats.load.pct >= 60 %}warn{% endif %}">
      <span style="width: {{ [system_stats.load.pct, 100]|min }}%;"></span>
    </div>
    <div class="muted">1м: {{ system_stats.load.one }} · 5м: {{ system_stats.load.five }} · 15м: {{ system_stats.load.fifteen }}</div>
  </div>

  <div class="metric-card">
    <h3>Память</h3>
    {% if system_stats.memory %}
      <div class="metric-main">
        <div class="metric-value">{{ system_stats.memory.pct_text }}</div>
        <div class="metric-note">{{ system_stats.memory.used_text }} / {{ system_stats.memory.total_text }}</div>
      </div>
      <div class="meter {% if system_stats.memory.pct >= 90 %}danger{% elif system_stats.memory.pct >= 70 %}warn{% endif %}">
        <span style="width: {{ [system_stats.memory.pct, 100]|min }}%;"></span>
      </div>
      <div class="muted">Свободно: {{ system_stats.memory.free_text }}</div>
    {% else %}
      <div class="metric-main">
        <div class="metric-value">—</div>
        <div class="metric-note">/proc/meminfo недоступен</div>
      </div>
    {% endif %}
  </div>

  <div class="metric-card">
    <h3>Диск</h3>
    <div class="metric-main">
      <div class="metric-value">{{ system_stats.disk.pct_text }}</div>
      <div class="metric-note">{{ system_stats.disk.used_text }} / {{ system_stats.disk.total_text }}</div>
    </div>
    <div class="meter {% if system_stats.disk.pct >= 90 %}danger{% elif system_stats.disk.pct >= 75 %}warn{% endif %}">
      <span style="width: {{ [system_stats.disk.pct, 100]|min }}%;"></span>
    </div>
    <div class="muted">Свободно на разделе: {{ system_stats.disk.free_text }}</div>
  </div>

  <div class="metric-card">
    <h3>Процесс</h3>
    <div class="metric-main">
      <div class="metric-value">{{ system_stats.process.rss_text }}</div>
      <div class="metric-note">RAM</div>
    </div>
    <div class="muted">Аптайм: {{ system_stats.process.uptime_text }}</div>
    <div class="muted">outputs/: {{ system_stats.storage.outputs_count }} · {{ system_stats.storage.outputs_text }}</div>
    <div class="muted">БД: {{ system_stats.storage.db_text }}</div>
  </div>
  </div>

<div class="metric-grid" style="margin-bottom:16px;">
  <div class="metric-card">
    <h3>Документы</h3>
    <div class="mini-stats">
      <div class="mini-stat"><strong>{{ system_stats.documents.total }}</strong><span>всего</span></div>
      <div class="mini-stat"><strong>{{ system_stats.documents.draft }}</strong><span>черновики</span></div>
      <div class="mini-stat"><strong>{{ system_stats.documents.ready_for_print }}</strong><span>в печати</span></div>
      <div class="mini-stat"><strong>{{ system_stats.documents.printed }}</strong><span>напечатаны</span></div>
    </div>
  </div>

  <div class="metric-card">
    <h3>Пользователи</h3>
    <div class="mini-stats">
      <div class="mini-stat"><strong>{{ system_stats.users.total }}</strong><span>всего</span></div>
      <div class="mini-stat"><strong>{{ system_stats.users.admin }}</strong><span>админы</span></div>
      <div class="mini-stat"><strong>{{ system_stats.users.editor }}</strong><span>редакторы</span></div>
      <div class="mini-stat"><strong>{{ system_stats.users.printer }}</strong><span>печатники</span></div>
    </div>
  </div>
</div>

<div class="card danger-zone">
  <div class="file-browser-head">
    <div>
      <h3 style="margin-top:0; margin-bottom:6px;">Файлы</h3>
      <div class="breadcrumbs">
        {% for crumb in file_browser.breadcrumbs %}
          {% if not loop.first %}<span class="sep">/</span>{% endif %}
          <a href="{{ url_for('admin_system', path=crumb.rel_path) }}">{{ crumb.label }}</a>
        {% endfor %}
      </div>
    </div>
    <div class="pill-row">
      <span class="pill">{{ file_browser.dir_count }} папок</span>
      <span class="pill">{{ file_browser.file_count }} файлов</span>
      <a class="btn ghost" href="{{ url_for('admin_system', path=file_browser.current_rel) }}">Обновить</a>
      {% if file_browser.current_rel %}
        <a class="btn secondary" href="{{ url_for('admin_system', path=file_browser.parent_rel) }}">Вверх</a>
      {% endif %}
    </div>
  </div>

  {% if not file_browser.entries %}
    <div class="empty"><p>Нет файлов.</p></div>
  {% else %}
    <div class="table-scroll">
      <table class="docs">
        <thead>
          <tr><th>Имя</th><th>Тип</th><th>Размер</th><th>Изменён</th><th></th></tr>
        </thead>
        <tbody>
          {% for entry in file_browser.entries %}
          <tr>
            <td>
              {% if entry.is_dir %}
                <a href="{{ url_for('admin_system', path=entry.rel_path) }}"><strong>{{ entry.name }}</strong></a>
              {% else %}
                <strong>{{ entry.name }}</strong>
              {% endif %}
              <div class="muted">{{ entry.rel_path }}</div>
            </td>
            <td><span class="file-type">{{ entry.type_label }}</span></td>
            <td class="muted">{{ entry.size_text }}</td>
            <td class="muted">{{ entry.modified_at }}</td>
            <td class="actions">
              {% if entry.is_dir %}
                <a class="btn small ghost" href="{{ url_for('admin_system', path=entry.rel_path) }}">Открыть</a>
              {% else %}
                <a class="btn small secondary" href="{{ url_for('admin_file_open', path=entry.rel_path) }}" target="_blank">Открыть</a>
                <button class="btn small danger js-open-delete-file"
                        type="button"
                        data-action="{{ url_for('admin_file_delete') }}"
                        data-path="{{ entry.rel_path }}"
                        data-message="Файл {{ entry.rel_path }} будет удалён.">Удалить</button>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  {% endif %}
</div>

<dialog id="delete-file-modal" class="modal-backdrop">
  <div class="modal-card modal-shell">
    <h3 style="margin:0;">Удалить файл</h3>
    <p class="modal-copy" data-modal-text>Файл будет удалён.</p>
    <form method="POST" action="" class="modal-form">
      {{ csrf_input|safe }}
      <input type="hidden" name="path" value="">
      <div class="modal-actions">
        <button type="button" class="btn ghost" data-modal-cancel>Отмена</button>
        <button type="submit" class="btn danger">Удалить</button>
      </div>
    </form>
  </div>
</dialog>
"""


# ── ADMIN LOGS ─────────────────────────────────────────────────────────────

ADMIN_LOGS_HTML = r"""
<h1>Все логи</h1>

<div class="card filters-card">
  <form method="GET" action="{{ url_for('admin_logs') }}">
    <div class="form-row">
      <div class="field">
        <label>Период печати</label>
        <select name="period">
          <option value="all" {% if log_filters.period == 'all' %}selected{% endif %}>Все даты</option>
          <option value="today" {% if log_filters.period == 'today' %}selected{% endif %}>Сегодня</option>
          <option value="7d" {% if log_filters.period == '7d' %}selected{% endif %}>Последние 7 дней</option>
          <option value="30d" {% if log_filters.period == '30d' %}selected{% endif %}>Последние 30 дней</option>
          <option value="month" {% if log_filters.period == 'month' %}selected{% endif %}>Месяц</option>
          <option value="year" {% if log_filters.period == 'year' %}selected{% endif %}>Год</option>
          <option value="custom" {% if log_filters.period == 'custom' %}selected{% endif %}>Свой диапазон</option>
        </select>
      </div>
      <div class="field">
        <label>Год</label>
        <select name="year">
          {% for year in log_filters.year_options %}
            <option value="{{ year }}" {% if log_filters.year == year %}selected{% endif %}>{{ year }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="field">
        <label>Месяц</label>
        <select name="month">
          {% for month_value, month_label in log_filters.month_options %}
            <option value="{{ month_value }}" {% if log_filters.month == month_value %}selected{% endif %}>{{ month_label }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="field">
        <label>С даты</label>
        <input type="date" name="date_from" value="{{ log_filters.date_from }}">
      </div>
      <div class="field">
        <label>По дату</label>
        <input type="date" name="date_to" value="{{ log_filters.date_to }}">
      </div>
      <div class="filters-actions">
        <button class="btn" type="submit">Показать</button>
        <a class="btn ghost" href="{{ url_for('admin_logs') }}">Сбросить</a>
      </div>
    </div>
  </form>
</div>

{% if not printed %}
  <div class="empty"><p>Нет записей.</p></div>
{% else %}
<div class="table-scroll">
  <table class="docs">
    <thead>
      <tr>
        <th>#</th><th>Тип</th><th>Получатель</th><th>Автор</th>
        <th>Напечатан</th><th>Хранить до</th><th>Файл</th><th></th>
      </tr>
    </thead>
    <tbody>
      {% for d in printed %}
      <tr>
        <td>{{ d.id }}</td>
        <td><span class="chip type">{% if d.diploma_type=='phd' %}PhD{% elif d.diploma_type=='magistr' %}Магистр{% elif d.diploma_type=='bakalavr_honors' %}Бакалавр (отл.){% else %}Бакалавр{% endif %}</span></td>
        <td>
          <div class="doc-person">
            <strong>{{ d.recipient_label or '—' }}</strong>
            <div class="doc-meta-lines">
              <div class="muted">ИИН: {{ d.person_iin or '—' }}</div>
              <div class="muted">№ диплома: {{ d.diploma_number or '—' }}</div>
            </div>
            {% if d.source_kind == 'excel' %}
              <details class="source-details">
                <summary><span class="source-chip">Excel</span></summary>
                <div class="source-grid">
                  <div class="source-item"><span class="source-label">Серия</span><span class="source-value">{{ d.source_label or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Файл</span><span class="source-value">{{ d.source_filename or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Папка</span><span class="source-value">{{ d.source_folder or '—' }}</span></div>
                  <div class="source-item"><span class="source-label">Строка</span><span class="source-value">{{ d.source_row_number or '—' }}</span></div>
                </div>
              </details>
            {% endif %}
          </div>
        </td>
        <td class="muted">{{ d.creator_name or '—' }}</td>
        <td class="muted">{{ (d.printed_at or '')[:16] }}</td>
        <td class="muted">{{ d.expires_at or '—' }}</td>
        <td>
          {% if d.file_available %}
            <span class="chip printed">Есть PDF</span>
          {% else %}
            <span class="chip ready_for_print">Удалён</span>
          {% endif %}
        </td>
        <td class="actions">
          {% if d.file_available %}
            <a class="btn small ghost" href="{{ url_for('doc_preview', doc_id=d.id) }}" target="_blank">PDF</a>
            <a class="btn small secondary" href="{{ url_for('doc_download', doc_id=d.id) }}">Скачать</a>
          {% else %}
            <span class="muted">Удалён</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endif %}
"""


# ── ERROR ──────────────────────────────────────────────────────────────────

ERROR_HTML = r"""
<div class="card" style="max-width:600px; margin:32px auto;">
  <h2 style="color:#7c1c2c; margin-top:0;">Ошибка</h2>
  <p>{{ msg }}</p>
  <p><a class="btn secondary" href="{{ url_for('index') }}">На главную</a></p>
</div>
"""


# ── IMPORT PHD (Excel) ────────────────────────────────────────────────────

IMPORT_PHD_HTML = r"""
<div class="section-intro">
  <div>
    <h1>Импорт Excel — PhD</h1>
    <p class="page-note">Докторанты. Один файл = до 4 строк за раз (или больше).</p>
  </div>
</div>

<div class="card">
  {% if error %}<div class="flash error">{{ error }}</div>{% endif %}
  <p class="muted" style="margin-top:0;">
    Шаблон: «Шаблон.xlsx». 1-я строка — заголовки;
    с 2-й — данные (рег.номер, год выдачи, № диплома, ФИО каз/рус/eng, программа,
    тема, консультанты, рецензенты, место и дата защиты, ИИН, QR).
  </p>
  <form method="POST"
        action="{{ url_for('import_phd') }}"
        enctype="multipart/form-data"
        class="js-import-job-form"
        data-active-job-id="{{ import_job_id or '' }}">
    {{ csrf_input|safe }}
    <div class="form-row">
      <div class="field">
        <label>Серия / название батча</label>
        <input type="text" name="batch_label" value="{{ form_data.batch_label }}" placeholder="PhD_2026">
      </div>
      <div class="field">
        <label>.xlsx</label>
        <input type="file" name="xlsx_file" accept=".xlsx" required>
      </div>
    </div>
    <div class="actions-bar">
      <a class="btn ghost" href="{{ url_for('new_type') }}">Назад</a>
      <button class="btn js-import-submit" type="submit">Импорт</button>
    </div>
  </form>
</div>

<div class="import-progress-shell">
  <div class="import-progress-card js-import-progress-card"
       data-status-url="{% if import_job_id %}{{ url_for('import_bakalavr_status', job_id=import_job_id) }}{% endif %}"
       {% if not import_job_id %}hidden{% endif %}>
    <div class="import-progress-head">
      <div>
        <h3 class="import-progress-title">Импорт на сервере</h3>
        <div class="muted js-import-stage">Ожидание запуска</div>
      </div>
      <div class="pill-row">
        <span class="pill js-import-count">0 / 0</span>
        <span class="pill js-import-created">Создано: 0</span>
      </div>
    </div>
    <div class="import-progress-bar"><span class="js-import-progress-bar"></span></div>
    <div class="import-progress-note js-import-message">Здесь появится текущий статус обработки.</div>
    <div class="import-progress-stats" style="margin-top:14px;">
      <div class="mini-stat"><strong class="js-import-percent">0%</strong><span>готово</span></div>
      <div class="mini-stat"><strong class="js-import-state">ожидание</strong><span>состояние</span></div>
    </div>
    <div class="actions-bar">
      <a class="btn secondary js-import-finish-link" href="{{ url_for('index') }}" hidden>К документам</a>
    </div>
  </div>
</div>
"""


# ── IMPORT FDO (Excel) ────────────────────────────────────────────────────

IMPORT_FDO_HTML = r"""
<div class="section-intro">
  <div>
    <h1>Импорт Excel — Сертификат ФДО</h1>
    <p class="page-note">Педагогическая переподготовка. Используйте «ФДО_шаблон.xlsx».</p>
  </div>
</div>

<div class="card">
  {% if error %}<div class="flash error">{{ error }}</div>{% endif %}
  <p class="muted" style="margin-top:0;">
    Шаблон: «ФДО_шаблон.xlsx». Колонки A–AI (день/месяц/протокол совета,
    ФИО, период «с-по», программа, кредиты на 3 языках; рег.номер, серия CPR, номер).
  </p>
  <form method="POST"
        action="{{ url_for('import_fdo') }}"
        enctype="multipart/form-data"
        class="js-import-job-form"
        data-active-job-id="{{ import_job_id or '' }}">
    {{ csrf_input|safe }}
    <div class="form-row">
      <div class="field">
        <label>Серия / название батча</label>
        <input type="text" name="batch_label" value="{{ form_data.batch_label }}" placeholder="ФДО_2026">
      </div>
      <div class="field">
        <label>.xlsx</label>
        <input type="file" name="xlsx_file" accept=".xlsx" required>
      </div>
    </div>
    <div class="actions-bar">
      <a class="btn ghost" href="{{ url_for('new_type') }}">Назад</a>
      <button class="btn js-import-submit" type="submit">Импорт</button>
    </div>
  </form>
</div>

<div class="import-progress-shell">
  <div class="import-progress-card js-import-progress-card"
       data-status-url="{% if import_job_id %}{{ url_for('import_bakalavr_status', job_id=import_job_id) }}{% endif %}"
       {% if not import_job_id %}hidden{% endif %}>
    <div class="import-progress-head">
      <div>
        <h3 class="import-progress-title">Импорт на сервере</h3>
        <div class="muted js-import-stage">Ожидание запуска</div>
      </div>
      <div class="pill-row">
        <span class="pill js-import-count">0 / 0</span>
        <span class="pill js-import-created">Создано: 0</span>
      </div>
    </div>
    <div class="import-progress-bar"><span class="js-import-progress-bar"></span></div>
    <div class="import-progress-note js-import-message">Здесь появится текущий статус обработки.</div>
    <div class="import-progress-stats" style="margin-top:14px;">
      <div class="mini-stat"><strong class="js-import-percent">0%</strong><span>готово</span></div>
      <div class="mini-stat"><strong class="js-import-state">ожидание</strong><span>состояние</span></div>
    </div>
    <div class="actions-bar">
      <a class="btn secondary js-import-finish-link" href="{{ url_for('index') }}" hidden>К документам</a>
    </div>
  </div>
</div>
"""


# ── IMPORT MINOR (Excel) ──────────────────────────────────────────────────

IMPORT_MINOR_HTML = r"""
<div class="section-intro">
  <div>
    <h1>Импорт Excel — Сертификат Минор</h1>
    <p class="page-note">К диплому бакалавра. «Шаблон для печати сертификатов.xlsx».</p>
  </div>
</div>

<div class="card">
  {% if error %}<div class="flash error">{{ error }}</div>{% endif %}
  <p class="muted" style="margin-top:0;">
    Шаблон: «Шаблон для печати сертификатов.xlsx». № диплома, программа,
    ФИО и Minor на 3-х языках, период «с-по», ИИН, QR.
  </p>
  <form method="POST"
        action="{{ url_for('import_minor') }}"
        enctype="multipart/form-data"
        class="js-import-job-form"
        data-active-job-id="{{ import_job_id or '' }}">
    {{ csrf_input|safe }}
    <div class="form-row">
      <div class="field">
        <label>Серия / название батча</label>
        <input type="text" name="batch_label" value="{{ form_data.batch_label }}" placeholder="Минор_2026">
      </div>
      <div class="field">
        <label>.xlsx</label>
        <input type="file" name="xlsx_file" accept=".xlsx" required>
      </div>
    </div>
    <div class="actions-bar">
      <a class="btn ghost" href="{{ url_for('new_type') }}">Назад</a>
      <button class="btn js-import-submit" type="submit">Импорт</button>
    </div>
  </form>
</div>

<div class="import-progress-shell">
  <div class="import-progress-card js-import-progress-card"
       data-status-url="{% if import_job_id %}{{ url_for('import_bakalavr_status', job_id=import_job_id) }}{% endif %}"
       {% if not import_job_id %}hidden{% endif %}>
    <div class="import-progress-head">
      <div>
        <h3 class="import-progress-title">Импорт на сервере</h3>
        <div class="muted js-import-stage">Ожидание запуска</div>
      </div>
      <div class="pill-row">
        <span class="pill js-import-count">0 / 0</span>
        <span class="pill js-import-created">Создано: 0</span>
      </div>
    </div>
    <div class="import-progress-bar"><span class="js-import-progress-bar"></span></div>
    <div class="import-progress-note js-import-message">Здесь появится текущий статус обработки.</div>
    <div class="import-progress-stats" style="margin-top:14px;">
      <div class="mini-stat"><strong class="js-import-percent">0%</strong><span>готово</span></div>
      <div class="mini-stat"><strong class="js-import-state">ожидание</strong><span>состояние</span></div>
    </div>
    <div class="actions-bar">
      <a class="btn secondary js-import-finish-link" href="{{ url_for('index') }}" hidden>К документам</a>
    </div>
  </div>
</div>
"""


# ── FORM FDO (ручное заполнение) ──────────────────────────────────────────

FORM_FDO_HTML = r"""
<div class="form-shell">
  <div class="card form-hero">
    <h1>{{ doc and ('Редактирование сертификата ФДО #' ~ doc.id) or 'Новый сертификат ФДО' }}</h1>
    <p class="muted">Педагогическая переподготовка. Заполните три языковых блока (каз / рус / англ).</p>
  </div>

  <form method="POST" action="{{ doc and url_for('edit_doc', doc_id=doc.id) or url_for('new_fdo') }}" class="card form-card">
    {{ csrf_input|safe }}

    <fieldset>
      <legend>Серия и номер</legend>
      <div class="form-row">
        <div class="field">
          <label>Серия</label>
          <input type="text" name="cert_series" value="{{ data.get('cert_series','CPR') }}" placeholder="CPR">
        </div>
        <div class="field">
          <label>Номер сертификата (11 цифр)</label>
          <input type="text" name="cert_number" value="{{ data.get('cert_number','') }}" placeholder="00000000000">
        </div>
        <div class="field">
          <label>Рег. номер</label>
          <input type="text" name="reg_number" value="{{ data.get('reg_number','') }}" placeholder="0001">
        </div>
      </div>
    </fieldset>

    <fieldset>
      <legend>Казахский блок</legend>
      <div class="form-row">
        <div class="field"><label>День совета</label>
          <input type="text" name="council_day_kaz" value="{{ data.get('council_day_kaz','') }}"></div>
        <div class="field"><label>Месяц совета (каз)</label>
          <input type="text" name="council_month_kaz" value="{{ data.get('council_month_kaz','') }}" placeholder="маусымдағы"></div>
        <div class="field"><label>Год совета (каз)</label>
          <input type="text" name="council_year_kaz" value="{{ data.get('council_year_kaz','') }}" placeholder="2025"></div>
        <div class="field"><label>Протокол №</label>
          <input type="text" name="protocol_kaz" value="{{ data.get('protocol_kaz','') }}"></div>
      </div>
      <div class="field"><label>ФИО (каз)</label>
        <input type="text" name="fio_kaz" value="{{ data.get('fio_kaz','') }}" placeholder="Юлдашева София Малкайдаровна"></div>
      <div class="form-row">
        <div class="field"><label>Начало: день</label>
          <input type="text" name="from_day_kaz" value="{{ data.get('from_day_kaz','') }}"></div>
        <div class="field"><label>Начало: месяц (каз)</label>
          <input type="text" name="from_month_kaz" value="{{ data.get('from_month_kaz','') }}" placeholder="қаңтар"></div>
        <div class="field"><label>Конец: день</label>
          <input type="text" name="to_day_kaz" value="{{ data.get('to_day_kaz','') }}"></div>
        <div class="field"><label>Конец: месяц (каз)</label>
          <input type="text" name="to_month_kaz" value="{{ data.get('to_month_kaz','') }}" placeholder="маусым"></div>
      </div>
      <div class="field"><label>Программа (каз)</label>
        <input type="text" name="program_kaz" value="{{ data.get('program_kaz','') }}"></div>
      <div class="field"><label>Кредиты</label>
        <input type="text" name="credits_kaz" value="{{ data.get('credits_kaz','') }}" placeholder="40"></div>
    </fieldset>

    <fieldset>
      <legend>Русский блок</legend>
      <div class="form-row">
        <div class="field"><label>День совета</label>
          <input type="text" name="council_day_rus" value="{{ data.get('council_day_rus','') }}"></div>
        <div class="field"><label>Месяц совета</label>
          <input type="text" name="council_month_rus" value="{{ data.get('council_month_rus','') }}" placeholder="июня"></div>
        <div class="field"><label>Год совета</label>
          <input type="text" name="council_year_rus" value="{{ data.get('council_year_rus','') }}"></div>
        <div class="field"><label>Протокол №</label>
          <input type="text" name="protocol_rus" value="{{ data.get('protocol_rus','') }}"></div>
      </div>
      <div class="field"><label>ФИО (рус)</label>
        <input type="text" name="fio_rus" value="{{ data.get('fio_rus','') }}"></div>
      <div class="form-row">
        <div class="field"><label>Начало: день</label>
          <input type="text" name="from_day_rus" value="{{ data.get('from_day_rus','') }}"></div>
        <div class="field"><label>Начало: месяц</label>
          <input type="text" name="from_month_rus" value="{{ data.get('from_month_rus','') }}" placeholder="января"></div>
        <div class="field"><label>Конец: день</label>
          <input type="text" name="to_day_rus" value="{{ data.get('to_day_rus','') }}"></div>
        <div class="field"><label>Конец: месяц</label>
          <input type="text" name="to_month_rus" value="{{ data.get('to_month_rus','') }}" placeholder="июня"></div>
      </div>
      <div class="field"><label>Программа (рус)</label>
        <input type="text" name="program_rus" value="{{ data.get('program_rus','') }}"></div>
      <div class="field"><label>Кредиты</label>
        <input type="text" name="credits_rus" value="{{ data.get('credits_rus','') }}"></div>
    </fieldset>

    <fieldset>
      <legend>Английский блок</legend>
      <div class="form-row">
        <div class="field"><label>День совета</label>
          <input type="text" name="council_day_eng" value="{{ data.get('council_day_eng','') }}"></div>
        <div class="field"><label>Месяц совета (eng)</label>
          <input type="text" name="council_month_eng" value="{{ data.get('council_month_eng','') }}" placeholder="June"></div>
        <div class="field"><label>Год совета</label>
          <input type="text" name="council_year_eng" value="{{ data.get('council_year_eng','') }}"></div>
      </div>
      <div class="field"><label>ФИО (eng)</label>
        <input type="text" name="fio_eng" value="{{ data.get('fio_eng','') }}"></div>
      <div class="form-row">
        <div class="field"><label>From: day</label>
          <input type="text" name="from_day_eng" value="{{ data.get('from_day_eng','') }}"></div>
        <div class="field"><label>From: month</label>
          <input type="text" name="from_month_eng" value="{{ data.get('from_month_eng','') }}" placeholder="January"></div>
        <div class="field"><label>To: day</label>
          <input type="text" name="to_day_eng" value="{{ data.get('to_day_eng','') }}"></div>
        <div class="field"><label>To: month</label>
          <input type="text" name="to_month_eng" value="{{ data.get('to_month_eng','') }}" placeholder="June"></div>
      </div>
      <div class="field"><label>Программа (eng)</label>
        <input type="text" name="program_eng" value="{{ data.get('program_eng','') }}"></div>
      <div class="field"><label>Кредиты</label>
        <input type="text" name="credits_eng" value="{{ data.get('credits_eng','') }}"></div>
    </fieldset>

    <fieldset>
      <legend>Дата выдачи (Тіркеу нөмірі, нижний блок)</legend>
      <div class="form-row">
        <div class="field"><label>Год выдачи</label>
          <input type="text" name="issue_year" value="{{ data.get('issue_year','') }}" placeholder="2025"></div>
        <div class="field"><label>День выдачи</label>
          <input type="text" name="issue_day" value="{{ data.get('issue_day','') }}"></div>
        <div class="field"><label>Месяц выдачи (каз)</label>
          <input type="text" name="issue_month_kaz" value="{{ data.get('issue_month_kaz','') }}" placeholder="маусым"></div>
      </div>
    </fieldset>

    <fieldset>
      <legend>Дополнительно</legend>
      <div class="field"><label>QR-код / ссылка верификации (опционально)</label>
        <input type="text" name="qr_text" value="{{ doc and doc.qr_text or '' }}"></div>
      <div class="field"><label>Комментарий (для печатника)</label>
        <textarea name="comment" rows="2">{{ doc and doc.comment or '' }}</textarea></div>
    </fieldset>

    <div class="actions-bar">
      <a class="btn ghost" href="{{ url_for('index') }}">Отмена</a>
      <button class="btn secondary" type="submit" name="action" value="save">Сохранить черновик</button>
      <button class="btn" type="submit" name="action" value="send">Сохранить и в печать</button>
    </div>
  </form>
</div>
"""


# ── FORM MINOR (ручное заполнение) ────────────────────────────────────────

FORM_MINOR_HTML = r"""
<div class="form-shell">
  <div class="card form-hero">
    <h1>{{ doc and ('Редактирование сертификата Минор #' ~ doc.id) or 'Новый сертификат Минор' }}</h1>
    <p class="muted">К диплому бакалавра. Заполните три языковых блока (каз / англ / рус).</p>
  </div>

  <form method="POST" action="{{ doc and url_for('edit_doc', doc_id=doc.id) or url_for('new_minor') }}" class="card form-card">
    {{ csrf_input|safe }}

    <fieldset>
      <legend>Номер диплома</legend>
      <div class="form-row">
        <div class="field">
          <label>BD № (11 цифр)</label>
          <input type="text" name="bd_number" value="{{ data.get('bd_number','') }}" placeholder="00002707224">
        </div>
        <div class="field">
          <label>ИИН выпускника</label>
          <input type="text" name="iin" value="{{ data.get('iin','') }}"></div>
        <div class="field">
          <label>Рег. номер</label>
          <input type="text" name="reg_number" value="{{ data.get('reg_number','') }}"></div>
      </div>
    </fieldset>

    <fieldset>
      <legend>Казахский блок</legend>
      <div class="field"><label>Программа (каз)</label>
        <input type="text" name="program_kaz" value="{{ data.get('program_kaz','') }}"
               placeholder="6B07105 - Көлік, көліктік техника және технологиялар"></div>
      <div class="field"><label>ФИО (каз)</label>
        <input type="text" name="fio_kaz" value="{{ data.get('fio_kaz','') }}" placeholder="Байтөре Алмат Сейткеримұлына"></div>
      <div class="field"><label>Minor (каз)</label>
        <input type="text" name="minor_kaz" value="{{ data.get('minor_kaz','') }}"
               placeholder="Автомобильдерді техникалық пайдалану"></div>
      <div class="form-row">
        <div class="field"><label>Начало: день</label>
          <input type="text" name="from_day_kaz" value="{{ data.get('from_day_kaz','') }}"></div>
        <div class="field"><label>Начало: месяц (каз)</label>
          <input type="text" name="from_month_kaz" value="{{ data.get('from_month_kaz','') }}" placeholder="тамызы"></div>
        <div class="field"><label>Начало: год</label>
          <input type="text" name="from_year_kaz" value="{{ data.get('from_year_kaz','') }}" placeholder="20"></div>
        <div class="field"><label>Конец: день</label>
          <input type="text" name="to_day_kaz" value="{{ data.get('to_day_kaz','') }}"></div>
        <div class="field"><label>Конец: месяц (каз)</label>
          <input type="text" name="to_month_kaz" value="{{ data.get('to_month_kaz','') }}" placeholder="маусымы"></div>
        <div class="field"><label>Конец: год</label>
          <input type="text" name="to_year_kaz" value="{{ data.get('to_year_kaz','') }}" placeholder="24"></div>
      </div>
    </fieldset>

    <fieldset>
      <legend>Английский блок</legend>
      <div class="field"><label>Программа (eng)</label>
        <input type="text" name="program_eng" value="{{ data.get('program_eng','') }}"></div>
      <div class="field"><label>ФИО (eng)</label>
        <input type="text" name="fio_eng" value="{{ data.get('fio_eng','') }}" placeholder="Baitore Almat"></div>
      <div class="field"><label>Minor (eng)</label>
        <input type="text" name="minor_eng" value="{{ data.get('minor_eng','') }}"></div>
      <div class="form-row">
        <div class="field"><label>From: day</label>
          <input type="text" name="from_day_eng" value="{{ data.get('from_day_eng','') }}"></div>
        <div class="field"><label>From: month</label>
          <input type="text" name="from_month_eng" value="{{ data.get('from_month_eng','') }}" placeholder="August"></div>
        <div class="field"><label>From: year</label>
          <input type="text" name="from_year_eng" value="{{ data.get('from_year_eng','') }}"></div>
        <div class="field"><label>To: day</label>
          <input type="text" name="to_day_eng" value="{{ data.get('to_day_eng','') }}"></div>
        <div class="field"><label>To: month</label>
          <input type="text" name="to_month_eng" value="{{ data.get('to_month_eng','') }}" placeholder="June"></div>
        <div class="field"><label>To: year</label>
          <input type="text" name="to_year_eng" value="{{ data.get('to_year_eng','') }}"></div>
      </div>
    </fieldset>

    <fieldset>
      <legend>Русский блок</legend>
      <div class="field"><label>Программа (рус)</label>
        <input type="text" name="program_rus" value="{{ data.get('program_rus','') }}"></div>
      <div class="field"><label>ФИО (рус)</label>
        <input type="text" name="fio_rus" value="{{ data.get('fio_rus','') }}"></div>
      <div class="field"><label>Minor (рус)</label>
        <input type="text" name="minor_rus" value="{{ data.get('minor_rus','') }}"></div>
      <div class="form-row">
        <div class="field"><label>Начало: день</label>
          <input type="text" name="from_day_rus" value="{{ data.get('from_day_rus','') }}"></div>
        <div class="field"><label>Начало: месяц</label>
          <input type="text" name="from_month_rus" value="{{ data.get('from_month_rus','') }}" placeholder="августа"></div>
        <div class="field"><label>Начало: год</label>
          <input type="text" name="from_year_rus" value="{{ data.get('from_year_rus','') }}"></div>
        <div class="field"><label>Конец: день</label>
          <input type="text" name="to_day_rus" value="{{ data.get('to_day_rus','') }}"></div>
        <div class="field"><label>Конец: месяц</label>
          <input type="text" name="to_month_rus" value="{{ data.get('to_month_rus','') }}" placeholder="июня"></div>
        <div class="field"><label>Конец: год</label>
          <input type="text" name="to_year_rus" value="{{ data.get('to_year_rus','') }}"></div>
      </div>
    </fieldset>

    <fieldset>
      <legend>Тіркеу нөмірі (нижняя строка казахского)</legend>
      <div class="form-row">
        <div class="field"><label>Год выдачи (4 цифры)</label>
          <input type="text" name="issue_year" value="{{ data.get('issue_year','') }}" placeholder="2026"></div>
        <div class="field"><label>День выдачи</label>
          <input type="text" name="issue_day" value="{{ data.get('issue_day','') }}"></div>
        <div class="field"><label>Месяц выдачи (каз)</label>
          <input type="text" name="issue_month_kaz" value="{{ data.get('issue_month_kaz','') }}" placeholder="маусым"></div>
      </div>
    </fieldset>

    <fieldset>
      <legend>Дополнительно</legend>
      <div class="field"><label>QR-код / ссылка верификации (опционально)</label>
        <input type="text" name="qr_text" value="{{ doc and doc.qr_text or '' }}"></div>
      <div class="field"><label>Комментарий (для печатника)</label>
        <textarea name="comment" rows="2">{{ doc and doc.comment or '' }}</textarea></div>
    </fieldset>

    <div class="actions-bar">
      <a class="btn ghost" href="{{ url_for('index') }}">Отмена</a>
      <button class="btn secondary" type="submit" name="action" value="save">Сохранить черновик</button>
      <button class="btn" type="submit" name="action" value="send">Сохранить и в печать</button>
    </div>
  </form>
</div>
"""
