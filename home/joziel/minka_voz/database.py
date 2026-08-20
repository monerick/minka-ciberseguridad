#!/usr/bin/env python3
"""
database.py — MINKA VOZ
Base de datos principal + soporte multi-usuario con encriptación
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/minka/minka.db")

_user_db_path = None
_master_password = None

def _ensure_db_dir():
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

def conectar():
    _ensure_db_dir()
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con

def inicializar_db():
    con = conectar()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dictionary (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            kogui     TEXT NOT NULL,
            spanish   TEXT NOT NULL,
            categoria TEXT DEFAULT 'general',
            notas     TEXT DEFAULT '',
            fecha     TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user            TEXT DEFAULT 'minka_voz',
            message         TEXT DEFAULT '',
            texto_traducido TEXT DEFAULT '',
            direccion       TEXT DEFAULT 'k2e',
            fuente          TEXT DEFAULT 'api',
            fecha           TEXT DEFAULT ''
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_dict_kogui ON dictionary(LOWER(kogui))")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_dict_spanish ON dictionary(LOWER(spanish))")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_fecha ON conversations(fecha)")

    con.commit()
    con.close()

# ── Palabras ────────────────────────────────────────────────────────────────────

def agregar_palabra(kogui, espanol, categoria="general", notas=""):
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT id FROM dictionary WHERE LOWER(kogui) = LOWER(?)", (kogui,))
    if cur.fetchone():
        con.close()
        return False, "ya existe"
    cur.execute("""
        INSERT INTO dictionary (kogui, spanish, categoria, notas, fecha)
        VALUES (?, ?, ?, ?, ?)
    """, (kogui.strip(), espanol.strip(), categoria.strip(), notas.strip(),
          datetime.now().strftime("%Y-%m-%d %H:%M")))
    con.commit()
    con.close()
    return True, "agregada"

def buscar_en_diccionario(texto, direccion="k2e"):
    con = conectar()
    cur = con.cursor()
    palabras = texto.strip().split()
    encontradas = {}
    for palabra in palabras:
        p = palabra.strip(".,!?;:")
        if direccion == "k2e":
            cur.execute("SELECT spanish FROM dictionary WHERE LOWER(kogui) = LOWER(?)", (p,))
        else:
            cur.execute("SELECT kogui FROM dictionary WHERE LOWER(spanish) = LOWER(?)", (p,))
        resultado = cur.fetchone()
        if resultado:
            encontradas[palabra] = resultado[0]
    con.close()
    return encontradas

def obtener_todas_palabras():
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT id, kogui, spanish, categoria, notas, fecha FROM dictionary ORDER BY spanish ASC")
    palabras = cur.fetchall()
    con.close()
    return palabras

def buscar_palabra(termino):
    con = conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT id, kogui, spanish, categoria, notas, fecha
        FROM dictionary
        WHERE LOWER(kogui) LIKE LOWER(?) OR LOWER(spanish) LIKE LOWER(?)
        ORDER BY kogui
    """, (f"%{termino}%", f"%{termino}%"))
    palabras = cur.fetchall()
    con.close()
    return palabras

def eliminar_palabra(palabra_id):
    con = conectar()
    cur = con.cursor()
    cur.execute("DELETE FROM dictionary WHERE id = ?", (palabra_id,))
    eliminada = cur.rowcount > 0
    con.commit()
    con.close()
    return eliminada

# ── Historial ───────────────────────────────────────────────────────────────────

def guardar_conversacion(original, traducido, direccion, fuente="api", user="minka_voz"):
    con = conectar()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO conversations (user, message, texto_traducido, direccion, fuente, fecha)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user, original, traducido, direccion, fuente,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    con.commit()
    con.close()

def obtener_historial(limite=20, user="minka_voz"):
    con = conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT id, message, texto_traducido, direccion, fuente, fecha
        FROM conversations WHERE user = ?
        ORDER BY fecha DESC LIMIT ?
    """, (user, limite))
    historial = cur.fetchall()
    con.close()
    return historial

def buscar_historial(termino, user="minka_voz"):
    con = conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT id, message, texto_traducido, direccion, fuente, fecha
        FROM conversations
        WHERE user = ? AND (LOWER(message) LIKE LOWER(?) OR LOWER(texto_traducido) LIKE LOWER(?))
        ORDER BY fecha DESC
    """, (user, f"%{termino}%", f"%{termino}%"))
    resultados = cur.fetchall()
    con.close()
    return resultados

def estadisticas(user=None):
    con = conectar()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM dictionary")
    total_palabras = cur.fetchone()[0]

    where = "WHERE user = ?" if user else "WHERE 1=1"
    params = (user,) if user else ()

    cur.execute(f"SELECT COUNT(*) FROM conversations {where}", params)
    total_conv = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) FROM conversations {where} AND direccion = 'k2e'", params)
    kogui_a_esp = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) FROM conversations {where} AND direccion = 'e2k'", params)
    esp_a_kogui = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) FROM conversations {where} AND fuente = 'diccionario'", params)
    desde_dic = cur.fetchone()[0]

    con.close()
    return {
        "palabras": total_palabras,
        "conversaciones": total_conv,
        "kogui_a_esp": kogui_a_esp,
        "esp_a_kogui": esp_a_kogui,
        "desde_diccionario": desde_dic
    }

def estadisticas_globales():
    con = conectar()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM dictionary")
    total_palabras = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM conversations")
    total_conv = cur.fetchone()[0]

    cur.execute("SELECT user, COUNT(*) as cnt FROM conversations GROUP BY user ORDER BY cnt DESC")
    por_usuario = cur.fetchall()

    cur.execute("""
        SELECT DATE(fecha) as dia, COUNT(*) as cnt
        FROM conversations WHERE fecha != ''
        GROUP BY dia ORDER BY dia DESC LIMIT 30
    """)
    por_dia = cur.fetchall()

    cur.execute("SELECT COUNT(DISTINCT user) FROM conversations")
    total_users = cur.fetchone()[0]

    con.close()
    return {
        "palabras": total_palabras,
        "conversaciones": total_conv,
        "usuarios_activos": total_users,
        "por_usuario": por_usuario,
        "por_dia": por_dia
    }

# ── Base de datos de usuario ────────────────────────────────────────────────────

def set_user_db(db_path, master_password=None):
    global _user_db_path, _master_password
    _user_db_path = db_path
    _master_password = master_password

def _conectar_user():
    if not _user_db_path:
        return None
    con = sqlite3.connect(_user_db_path)
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_user_db():
    con = _conectar_user()
    if not con:
        return
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER,
            added_at TEXT DEFAULT ''
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE,
            setting_value TEXT DEFAULT ''
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fav_word ON user_favorites(word_id)")
    con.commit()
    con.close()

def save_user_setting(key, value):
    con = _conectar_user()
    if not con:
        return
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO user_settings (setting_key, setting_value) VALUES (?, ?)", (key, value))
    con.commit()
    con.close()

def get_user_setting(key, default=""):
    con = _conectar_user()
    if not con:
        return default
    cur = con.cursor()
    cur.execute("SELECT setting_value FROM user_settings WHERE setting_key = ?", (key,))
    result = cur.fetchone()
    con.close()
    return result[0] if result else default

def add_favorite(word_id):
    con = _conectar_user()
    if not con:
        return
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO user_favorites (word_id, added_at) VALUES (?, ?)",
                (word_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    con.commit()
    con.close()

def remove_favorite(word_id):
    con = _conectar_user()
    if not con:
        return
    cur = con.cursor()
    cur.execute("DELETE FROM user_favorites WHERE word_id = ?", (word_id,))
    con.commit()
    con.close()

def is_favorite(word_id):
    con = _conectar_user()
    if not con:
        return False
    cur = con.cursor()
    cur.execute("SELECT id FROM user_favorites WHERE word_id = ?", (word_id,))
    result = cur.fetchone()
    con.close()
    return result is not None

def get_favorites():
    con = _conectar_user()
    if not con:
        return []
    cur = con.cursor()
    cur.execute("""
        SELECT word_id, added_at FROM user_favorites ORDER BY added_at DESC
    """)
    favs = cur.fetchall()
    con.close()

    con2 = conectar()
    cur2 = con2.cursor()
    resultados = []
    for word_id, added_at in favs:
        cur2.execute("SELECT id, kogui, spanish, categoria FROM dictionary WHERE id = ?", (word_id,))
        row = cur2.fetchone()
        if row:
            resultados.append((row[0], row[1], row[2], row[3], added_at))
    con2.close()
    return resultados

def save_user_note(word_id, note):
    con = _conectar_user()
    if not con:
        return
    cur = con.cursor()
    cur.execute("INSERT INTO user_notes (word_id, note, created_at) VALUES (?, ?, ?)",
                (word_id, note, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    con.commit()
    con.close()

def get_user_notes(word_id=None):
    con = _conectar_user()
    if not con:
        return []
    cur = con.cursor()
    if word_id:
        cur.execute("SELECT id, word_id, note, created_at FROM user_notes WHERE word_id = ?", (word_id,))
    else:
        cur.execute("SELECT id, word_id, note, created_at FROM user_notes ORDER BY created_at DESC")
    notes = cur.fetchall()
    con.close()
    return notes

def delete_user_note(note_id):
    con = _conectar_user()
    if not con:
        return
    cur = con.cursor()
    cur.execute("DELETE FROM user_notes WHERE id = ?", (note_id,))
    con.commit()
    con.close()
