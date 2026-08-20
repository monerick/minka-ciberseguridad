#!/usr/bin/env python3
"""
MINKA VOZ — Android App
Traductor Kogui <-> Español con seguridad
"""

import os
import sys
import time
import json
import sqlite3
import threading
import tempfile
from datetime import datetime, timedelta

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform

# ── Configuración de rutas ──────────────────────────────────────────────────────

if platform == 'android':
    from android.storage import app_storage_path
    APP_DIR = app_storage_path()
    DB_DIR = os.path.join(APP_DIR, 'data')
else:
    APP_DIR = os.path.expanduser("~/.minka_voz")
    DB_DIR = os.path.join(APP_DIR, 'data')

os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "minka.db")
USERS_DB = os.path.join(DB_DIR, "users.db")
SALT_FILE = os.path.join(DB_DIR, ".salt")

# ── Colores Kivy ───────────────────────────────────────────────────────────────

COLORS = {
    'bg': (0.08, 0.12, 0.08, 1),
    'bg_card': (0.12, 0.18, 0.12, 1),
    'green': (0.2, 0.8, 0.2, 1),
    'blue': (0.2, 0.5, 0.9, 1),
    'yellow': (0.9, 0.8, 0.2, 1),
    'red': (0.9, 0.2, 0.2, 1),
    'gray': (0.5, 0.5, 0.5, 1),
    'white': (1, 1, 1, 1),
    'cyan': (0.2, 0.8, 0.9, 1),
    'magenta': (0.8, 0.2, 0.8, 1),
}

# ── Database Manager ───────────────────────────────────────────────────────────

class DBManager:
    def __init__(self):
        self.init_main_db()
        self.init_security_db()

    def init_main_db(self):
        con = sqlite3.connect(DB_PATH)
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dictionary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kogui TEXT NOT NULL,
                spanish TEXT NOT NULL,
                categoria TEXT DEFAULT 'general',
                notas TEXT DEFAULT '',
                fecha TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT DEFAULT 'minka_voz',
                message TEXT DEFAULT '',
                texto_traducido TEXT DEFAULT '',
                direccion TEXT DEFAULT 'k2e',
                fuente TEXT DEFAULT 'api',
                fecha TEXT DEFAULT ''
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dict_kogui ON dictionary(LOWER(kogui))")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dict_spanish ON dictionary(LOWER(spanish))")
        con.commit()
        con.close()

    def init_security_db(self):
        con = sqlite3.connect(USERS_DB)
        con.execute("PRAGMA foreign_keys = ON")
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TEXT DEFAULT '',
                last_login TEXT DEFAULT '',
                login_attempts INTEGER DEFAULT 0,
                locked_until TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                data_key TEXT NOT NULL,
                data_value TEXT NOT NULL,
                created_at TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        con.commit()
        con.close()

    def add_word(self, kogui, spanish, categoria="general", notas=""):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("SELECT id FROM dictionary WHERE LOWER(kogui) = LOWER(?)", (kogui,))
        if cur.fetchone():
            con.close()
            return False, "ya existe"
        cur.execute("""
            INSERT INTO dictionary (kogui, spanish, categoria, notas, fecha)
            VALUES (?, ?, ?, ?, ?)
        """, (kogui.strip(), spanish.strip(), categoria.strip(), notas.strip(),
              datetime.now().strftime("%Y-%m-%d %H:%M")))
        con.commit()
        con.close()
        return True, "agregada"

    def search_word(self, term):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            SELECT id, kogui, spanish, categoria, notas
            FROM dictionary
            WHERE LOWER(kogui) LIKE LOWER(?) OR LOWER(spanish) LIKE LOWER(?)
            ORDER BY spanish
        """, (f"%{term}%", f"%{term}%"))
        results = cur.fetchall()
        con.close()
        return results

    def get_all_words(self):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("SELECT id, kogui, spanish, categoria, notas FROM dictionary ORDER BY spanish")
        words = cur.fetchall()
        con.close()
        return words

    def delete_word(self, word_id):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("DELETE FROM dictionary WHERE id = ?", (word_id,))
        deleted = cur.rowcount > 0
        con.commit()
        con.close()
        return deleted

    def translate(self, text, direction="k2e"):
        words = text.strip().split()
        found = {}
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        for w in words:
            clean = w.strip(".,!?;:")
            if direction == "k2e":
                cur.execute("SELECT spanish FROM dictionary WHERE LOWER(kogui) = LOWER(?)", (clean,))
            else:
                cur.execute("SELECT kogui FROM dictionary WHERE LOWER(spanish) = LOWER(?)", (clean,))
            r = cur.fetchone()
            if r:
                found[w] = r[0]
        con.close()

        if not found:
            return None, "no_encontrado"

        result = []
        all_found = True
        for w in words:
            clean = w.strip(".,!?;:")
            if clean in found:
                result.append(found[clean])
            else:
                all_found = False
                result.append(f"[{clean}]")

        joined = " ".join(result)
        source = "diccionario" if all_found else "diccionario_parcial"
        return joined, source

    def save_conversation(self, original, translated, direction, source, user="minka_voz"):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            INSERT INTO conversations (user, message, texto_traducido, direccion, fuente, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user, original, translated, direction, source,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        con.commit()
        con.close()

    def get_history(self, user="minka_voz", limit=20):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            SELECT id, message, texto_traducido, direccion, fuente, fecha
            FROM conversations WHERE user = ?
            ORDER BY fecha DESC LIMIT ?
        """, (user, limit))
        history = cur.fetchall()
        con.close()
        return history

    def get_stats(self, user=None):
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM dictionary")
        total_words = cur.fetchone()[0]

        where = "WHERE user = ?" if user else "WHERE 1=1"
        params = (user,) if user else ()

        cur.execute(f"SELECT COUNT(*) FROM conversations {where}", params)
        total_conv = cur.fetchone()[0]
        con.close()
        return {"words": total_words, "conversations": total_conv}

    # ── Security ──

    def _get_salt(self):
        if os.path.exists(SALT_FILE):
            with open(SALT_FILE, 'rb') as f:
                return f.read()
        salt = os.urandom(16)
        with open(SALT_FILE, 'wb') as f:
            f.write(salt)
        return salt

    def hash_password(self, password):
        import bcrypt
        salt = self._get_salt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode(), salt.decode()

    def verify_password(self, password, stored_hash):
        import bcrypt
        try:
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        except:
            return False

    def create_user(self, username, password, role="user"):
        if len(username) < 3:
            return False, "Mínimo 3 caracteres"
        if len(password) < 8:
            return False, "Contraseña muy corta"

        try:
            con = sqlite3.connect(USERS_DB)
            cur = con.cursor()
            pw_hash, salt = self.hash_password(password)
            cur.execute("""
                INSERT INTO users (username, password_hash, salt, role, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (username.lower(), pw_hash, salt, role,
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            con.commit()
            con.close()
            return True, "Usuario creado"
        except sqlite3.IntegrityError:
            return False, "El usuario ya existe"

    def authenticate(self, username, password):
        con = sqlite3.connect(USERS_DB)
        cur = con.cursor()
        cur.execute("""
            SELECT id, username, password_hash, role, login_attempts, locked_until, is_active
            FROM users WHERE username = ?
        """, (username.lower(),))
        user = cur.fetchone()

        if not user:
            con.close()
            return None, "Usuario no encontrado"

        uid, uname, p_hash, role, attempts, locked, active = user
        if not active:
            con.close()
            return None, "Cuenta desactivada"

        if locked:
            try:
                lock_time = datetime.strptime(locked, "%Y-%m-%d %H:%M:%S")
                if datetime.now() < lock_time:
                    con.close()
                    return None, "Cuenta bloqueada temporalmente"
                else:
                    cur.execute("UPDATE users SET login_attempts = 0, locked_until = '' WHERE id = ?", (uid,))
                    con.commit()
            except:
                pass

        if not self.verify_password(password, p_hash):
            attempts += 1
            if attempts >= 5:
                lock_until = datetime.now() + timedelta(minutes=15)
                cur.execute("UPDATE users SET login_attempts = ?, locked_until = ? WHERE id = ?",
                           (attempts, lock_until.strftime("%Y-%m-%d %H:%M:%S"), uid))
            else:
                cur.execute("UPDATE users SET login_attempts = ? WHERE id = ?", (attempts, uid))
            con.commit()
            con.close()
            remaining = max(0, 5 - attempts)
            return None, f"Contraseña incorrecta ({remaining} restantes)"

        cur.execute("UPDATE users SET login_attempts = 0, locked_until = '', last_login = ? WHERE id = ?",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid))
        con.commit()
        con.close()

        session = {"user_id": uid, "username": uname, "role": role}
        return session, "OK"

# ── Screens ────────────────────────────────────────────────────────────────────

class LoginScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        layout.add_widget(Label(
            text="MINKA VOZ",
            font_size=32,
            color=COLORS['green'],
            size_hint_y=0.15
        ))

        layout.add_widget(Label(
            text="🔒 Inicio de Sesión",
            font_size=18,
            color=COLORS['white'],
            size_hint_y=0.08
        ))

        self.username_input = TextInput(
            hint_text="Usuario",
            multiline=False,
            font_size=18,
            size_hint_y=0.1,
            background_color=COLORS['bg_card'],
            foreground_color=COLORS['white']
        )
        layout.add_widget(self.username_input)

        self.password_input = TextInput(
            hint_text="Contraseña",
            password=True,
            multiline=False,
            font_size=18,
            size_hint_y=0.1,
            background_color=COLORS['bg_card'],
            foreground_color=COLORS['white']
        )
        layout.add_widget(self.password_input)

        self.message_label = Label(
            text="",
            font_size=14,
            color=COLORS['yellow'],
            size_hint_y=0.08
        )
        layout.add_widget(self.message_label)

        btn_login = Button(
            text="Iniciar Sesión",
            font_size=18,
            background_color=COLORS['green'],
            color=COLORS['white'],
            size_hint_y=0.1
        )
        btn_login.bind(on_press=self.do_login)
        layout.add_widget(btn_login)

        btn_register = Button(
            text="Crear Cuenta",
            font_size=16,
            background_color=COLORS['blue'],
            color=COLORS['white'],
            size_hint_y=0.08
        )
        btn_register.bind(on_press=self.do_register)
        layout.add_widget(btn_register)

        btn_guest = Button(
            text="Entrar como invitado",
            font_size=14,
            background_color=COLORS['gray'],
            color=COLORS['white'],
            size_hint_y=0.08
        )
        btn_guest.bind(on_press=self.do_guest)
        layout.add_widget(btn_guest)

        layout.add_widget(Label(size_hint_y=0.15))
        self.add_widget(layout)

    def do_login(self, *args):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()

        if not username or not password:
            self.message_label.text = "Completa todos los campos"
            return

        session, msg = self.db.authenticate(username, password)
        if session:
            self.manager.current_session = session
            self.manager.current = 'home'
            self.manager.get_screen('home').build_ui()
        else:
            self.message_label.text = msg

    def do_register(self, *args):
        self.manager.current = 'register'

    def do_guest(self, *args):
        self.manager.current_session = {"user_id": 0, "username": "invitado", "role": "guest"}
        self.manager.current = 'home'
        self.manager.get_screen('home').build_ui()


class RegisterScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        layout.add_widget(Label(
            text="Crear Cuenta",
            font_size=24,
            color=COLORS['cyan'],
            size_hint_y=0.12
        ))

        self.username_input = TextInput(
            hint_text="Usuario (mín. 3 caracteres)",
            multiline=False,
            font_size=18,
            size_hint_y=0.1,
            background_color=COLORS['bg_card'],
            foreground_color=COLORS['white']
        )
        layout.add_widget(self.username_input)

        self.password_input = TextInput(
            hint_text="Contraseña (mín. 8, 1 mayúscula, 1 número)",
            password=True,
            multiline=False,
            font_size=18,
            size_hint_y=0.1,
            background_color=COLORS['bg_card'],
            foreground_color=COLORS['white']
        )
        layout.add_widget(self.password_input)

        self.confirm_input = TextInput(
            hint_text="Confirmar contraseña",
            password=True,
            multiline=False,
            font_size=18,
            size_hint_y=0.1,
            background_color=COLORS['bg_card'],
            foreground_color=COLORS['white']
        )
        layout.add_widget(self.confirm_input)

        self.message_label = Label(
            text="",
            font_size=14,
            color=COLORS['yellow'],
            size_hint_y=0.08
        )
        layout.add_widget(self.message_label)

        btn_register = Button(
            text="Crear Cuenta",
            font_size=18,
            background_color=COLORS['green'],
            color=COLORS['white'],
            size_hint_y=0.1
        )
        btn_register.bind(on_press=self.do_register)
        layout.add_widget(btn_register)

        btn_back = Button(
            text="Volver al Login",
            font_size=16,
            background_color=COLORS['gray'],
            color=COLORS['white'],
            size_hint_y=0.08
        )
        btn_back.bind(on_press=lambda x: setattr(self.manager, 'current', 'login'))
        layout.add_widget(btn_back)

        layout.add_widget(Label(size_hint_y=0.22))
        self.add_widget(layout)

    def do_register(self, *args):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        confirm = self.confirm_input.text.strip()

        if not username or not password:
            self.message_label.text = "Completa todos los campos"
            return

        if password != confirm:
            self.message_label.text = "Las contraseñas no coinciden"
            return

        ok, msg = self.db.create_user(username, password)
        if ok:
            self.message_label.text = "✓ Cuenta creada. Inicia sesión."
            self.manager.current = 'login'
        else:
            self.message_label.text = msg


class HomeScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db

    def build_ui(self):
        self.clear_widgets()
        session = self.manager.current_session
        username = session.get('username', 'invitado')

        layout = BoxLayout(orientation='vertical', padding=15, spacing=8)

        layout.add_widget(Label(
            text="MINKA VOZ",
            font_size=28,
            color=COLORS['green'],
            size_hint_y=0.08
        ))

        layout.add_widget(Label(
            text=f"Hola, {username}",
            font_size=16,
            color=COLORS['gray'],
            size_hint_y=0.05
        ))

        stats = self.db.get_stats(username if username != "invitado" else None)
        layout.add_widget(Label(
            text=f"Palabras: {stats['words']}  |  Traducciones: {stats['conversations']}",
            font_size=14,
            color=COLORS['gray'],
            size_hint_y=0.05
        ))

        menu_items = [
            ("📖 Diccionario", COLORS['green'], 'dictionary'),
            ("🔄 Traducir", COLORS['blue'], 'translate'),
            ("📜 Historial", COLORS['cyan'], 'history'),
            ("📊 Estadísticas", COLORS['magenta'], 'stats'),
            ("👤 Mi Perfil", COLORS['yellow'], 'profile'),
        ]

        for text, color, screen_name in menu_items:
            btn = Button(
                text=text,
                font_size=20,
                background_color=color,
                color=COLORS['white'],
                size_hint_y=0.12
            )
            btn.bind(on_press=lambda s, sn=screen_name: self.go_to(sn))
            layout.add_widget(btn)

        btn_logout = Button(
            text="Cerrar Sesión",
            font_size=16,
            background_color=COLORS['red'],
            color=COLORS['white'],
            size_hint_y=0.08
        )
        btn_logout.bind(on_press=self.logout)
        layout.add_widget(btn_logout)

        self.add_widget(layout)

    def go_to(self, screen_name):
        screen = self.manager.get_screen(screen_name)
        if hasattr(screen, 'build_ui'):
            screen.build_ui()
        self.manager.current = screen_name

    def logout(self, *args):
        self.manager.current_session = None
        login = self.manager.get_screen('login')
        login.build_ui()
        self.manager.current = 'login'


class DictionaryScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db

    def build_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=15, spacing=8)

        layout.add_widget(Label(
            text="📖 Diccionario Kogui",
            font_size=24,
            color=COLORS['magenta'],
            size_hint_y=0.08
        ))

        self.search_input = TextInput(
            hint_text="Buscar palabra...",
            multiline=False,
            font_size=18,
            size_hint_y=0.08,
            background_color=COLORS['bg_card'],
            foreground_color=COLORS['white']
        )
        layout.add_widget(self.search_input)

        btn_search = Button(
            text="🔍 Buscar",
            font_size=16,
            background_color=COLORS['blue'],
            color=COLORS['white'],
            size_hint_y=0.08
        )
        btn_search.bind(on_press=self.do_search)
        layout.add_widget(btn_search)

        self.results_layout = BoxLayout(orientation='vertical', spacing=5)
        scroll = ScrollView()
        scroll.add_widget(self.results_layout)
        layout.add_widget(scroll)

        btn_add = Button(
            text="➕ Agregar palabra",
            font_size=16,
            background_color=COLORS['green'],
            color=COLORS['white'],
            size_hint_y=0.08
        )
        btn_add.bind(on_press=self.show_add)
        layout.add_widget(btn_add)

        btn_back = Button(
            text="← Volver",
            font_size=16,
            background_color=COLORS['gray'],
            color=COLORS['white'],
            size_hint_y=0.06
        )
        btn_back.bind(on_press=lambda x: setattr(self.manager, 'current', 'home'))
        layout.add_widget(btn_back)

        self.add_widget(layout)
        self.show_all_words()

    def show_all_words(self, *args):
        self.results_layout.clear_widgets()
        words = self.db.get_all_words()

        if not words:
            self.results_layout.add_widget(Label(
                text="Diccionario vacío",
                font_size=16,
                color=COLORS['yellow'],
                size_hint_y=0.1
            ))
            return

        current_cat = None
        for wid, kogui, spanish, cat, notas in words:
            if cat != current_cat:
                current_cat = cat
                self.results_layout.add_widget(Label(
                    text=f"▸ {cat.upper()}",
                    font_size=14,
                    color=COLORS['cyan'],
                    size_hint_y=0.06,
                    halign='left'
                ))

            item = BoxLayout(orientation='horizontal', size_hint_y=0.08, spacing=5)
            item.add_widget(Label(
                text=f"{spanish} → {kogui}",
                font_size=14,
                color=COLORS['white'],
                halign='left'
            ))
            del_btn = Button(
                text="🗑",
                size_hint_x=0.15,
                background_color=COLORS['red'],
                color=COLORS['white'],
                font_size=12
            )
            del_btn.bind(on_press=lambda s, i=wid: self.delete_word(i))
            item.add_widget(del_btn)
            self.results_layout.add_widget(item)

    def do_search(self, *args):
        term = self.search_input.text.strip()
        if not term:
            self.show_all_words()
            return

        self.results_layout.clear_widgets()
        results = self.db.search_word(term)

        if not results:
            self.results_layout.add_widget(Label(
                text=f"No se encontró '{term}'",
                font_size=16,
                color=COLORS['yellow'],
                size_hint_y=0.1
            ))
            return

        for wid, kogui, spanish, cat, notas in results:
            item = BoxLayout(orientation='horizontal', size_hint_y=0.08, spacing=5)
            item.add_widget(Label(
                text=f"{spanish} → {kogui} [{cat}]",
                font_size=14,
                color=COLORS['white'],
                halign='left'
            ))
            self.results_layout.add_widget(item)

    def delete_word(self, word_id):
        self.db.delete_word(word_id)
        self.show_all_words()

    def show_add(self, *args):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)

        kogui_input = TextInput(hint_text="Palabra en Kogui", multiline=False, font_size=16)
        spanish_input = TextInput(hint_text="Traducción Español", multiline=False, font_size=16)
        cat_input = TextInput(hint_text="Categoría [general]", multiline=False, font_size=16, text="general")

        content.add_widget(Label(text="Nueva Palabra", font_size=18, color=COLORS['green']))
        content.add_widget(kogui_input)
        content.add_widget(spanish_input)
        content.add_widget(cat_input)

        btn_save = Button(text="Guardar", font_size=16, background_color=COLORS['green'], color=COLORS['white'])
        btn_cancel = Button(text="Cancelar", font_size=16, background_color=COLORS['red'], color=COLORS['white'])

        btns = BoxLayout(spacing=10, size_hint_y=0.15)
        btns.add_widget(btn_cancel)
        btns.add_widget(btn_save)
        content.add_widget(btns)

        popup = Popup(title="Agregar Palabra", content=content, size_hint=(0.9, 0.7))

        def save(*args):
            k = kogui_input.text.strip()
            s = spanish_input.text.strip()
            c = cat_input.text.strip() or "general"
            if k and s:
                self.db.add_word(k, s, c)
                self.show_all_words()
                popup.dismiss()

        btn_save.bind(on_press=save)
        btn_cancel.bind(on_press=lambda x: popup.dismiss())
        popup.open()


class TranslateScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db
        self.direction = "k2e"

    def build_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=15, spacing=8)

        dir_text = f"Kogui → Español" if self.direction == "k2e" else "Español → Kogui"
        layout.add_widget(Label(
            text=f"🔄 Traducir ({dir_text})",
            font_size=24,
            color=COLORS['blue'],
            size_hint_y=0.08
        ))

        btn_dir = Button(
            text="Cambiar dirección",
            font_size=14,
            background_color=COLORS['yellow'],
            color=COLORS['white'],
            size_hint_y=0.06
        )
        btn_dir.bind(on_press=self.toggle_direction)
        layout.add_widget(btn_dir)

        self.input_text = TextInput(
            hint_text="Escribe para traducir...",
            multiline=True,
            font_size=18,
            size_hint_y=0.25,
            background_color=COLORS['bg_card'],
            foreground_color=COLORS['white']
        )
        layout.add_widget(self.input_text)

        btn_translate = Button(
            text="🌐 Traducir",
            font_size=18,
            background_color=COLORS['green'],
            color=COLORS['white'],
            size_hint_y=0.1
        )
        btn_translate.bind(on_press=self.do_translate)
        layout.add_widget(btn_translate)

        self.result_label = Label(
            text="",
            font_size=18,
            color=COLORS['green'],
            size_hint_y=0.15,
            halign='left',
            valign='top',
            text_size=(Window.width - 40, None)
        )
        layout.add_widget(self.result_label)

        self.source_label = Label(
            text="",
            font_size=14,
            color=COLORS['gray'],
            size_hint_y=0.05
        )
        layout.add_widget(self.source_label)

        layout.add_widget(Label(size_hint_y=0.1))

        btn_back = Button(
            text="← Volver",
            font_size=16,
            background_color=COLORS['gray'],
            color=COLORS['white'],
            size_hint_y=0.06
        )
        btn_back.bind(on_press=lambda x: setattr(self.manager, 'current', 'home'))
        layout.add_widget(btn_back)

        self.add_widget(layout)

    def toggle_direction(self, *args):
        self.direction = "e2k" if self.direction == "k2e" else "k2e"
        self.build_ui()

    def do_translate(self, *args):
        text = self.input_text.text.strip()
        if not text:
            self.result_label.text = "Escribe algo para traducir"
            return

        translated, source = self.db.translate(text, self.direction)

        if not translated:
            self.result_label.text = "Palabra no encontrada en el diccionario"
            self.source_label.text = "Agrécala en Diccionario"
            return

        self.result_label.text = translated

        source_text = "[diccionario]" if source == "diccionario" else "[parcial]"
        self.source_label.text = source_text

        session = self.manager.current_session
        user = session.get('username', 'minka_voz') if session else 'minka_voz'
        self.db.save_conversation(text, translated, self.direction, source, user)


class HistoryScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db

    def build_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=15, spacing=8)

        layout.add_widget(Label(
            text="📜 Historial",
            font_size=24,
            color=COLORS['cyan'],
            size_hint_y=0.08
        ))

        scroll = ScrollView()
        history_layout = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        history_layout.bind(minimum_height=history_layout.setter('height'))

        session = self.manager.current_session
        user = session.get('username', 'minka_voz') if session else 'minka_voz'
        history = self.db.get_history(user)

        if not history:
            history_layout.add_widget(Label(
                text="No hay traducciones aún",
                font_size=16,
                color=COLORS['yellow'],
                size_hint_y=0.1,
                height=40
            ))
        else:
            for hid, original, translated, direction, source, fecha in history:
                arrow = "K→E" if direction == "k2e" else "E→K"
                item = BoxLayout(
                    orientation='vertical',
                    size_hint_y=None,
                    height=60,
                    spacing=2
                )
                item.add_widget(Label(
                    text=f"{fecha[11:16]} [{arrow}] [{source}]",
                    font_size=12,
                    color=COLORS['gray'],
                    halign='left',
                    size_hint_y=0.4
                ))
                item.add_widget(Label(
                    text=f"{original} → {translated}",
                    font_size=14,
                    color=COLORS['white'],
                    halign='left',
                    size_hint_y=0.6
                ))
                history_layout.add_widget(item)

        scroll.add_widget(history_layout)
        layout.add_widget(scroll)

        btn_back = Button(
            text="← Volver",
            font_size=16,
            background_color=COLORS['gray'],
            color=COLORS['white'],
            size_hint_y=0.08
        )
        btn_back.bind(on_press=lambda x: setattr(self.manager, 'current', 'home'))
        layout.add_widget(btn_back)

        self.add_widget(layout)


class StatsScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db

    def build_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=15, spacing=8)

        layout.add_widget(Label(
            text="📊 Estadísticas",
            font_size=24,
            color=COLORS['magenta'],
            size_hint_y=0.08
        ))

        session = self.manager.current_session
        user = session.get('username', None) if session else None
        if user == "invitado":
            user = None

        stats = self.db.get_stats(user)

        info = f"""
Palabras en diccionario: {stats['words']}

Total traducciones: {stats['conversations']}
        """.strip()

        layout.add_widget(Label(
            text=info,
            font_size=18,
            color=COLORS['white'],
            size_hint_y=0.5,
            halign='left',
            valign='top',
            text_size=(Window.width - 40, None)
        ))

        layout.add_widget(Label(size_hint_y=0.2))

        btn_back = Button(
            text="← Volver",
            font_size=16,
            background_color=COLORS['gray'],
            color=COLORS['white'],
            size_hint_y=0.08
        )
        btn_back.bind(on_press=lambda x: setattr(self.manager, 'current', 'home'))
        layout.add_widget(btn_back)

        self.add_widget(layout)


class ProfileScreen(Screen):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self.db = db

    def build_ui(self):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=15, spacing=8)

        session = self.manager.current_session
        username = session.get('username', 'invitado') if session else 'invitado'
        role = session.get('role', 'guest') if session else 'guest'

        layout.add_widget(Label(
            text="👤 Mi Perfil",
            font_size=24,
            color=COLORS['yellow'],
            size_hint_y=0.1
        ))

        layout.add_widget(Label(
            text=f"Usuario: {username}\nRol: {role}",
            font_size=16,
            color=COLORS['white'],
            size_hint_y=0.15
        ))

        layout.add_widget(Label(size_hint_y=0.3))

        btn_back = Button(
            text="← Volver",
            font_size=16,
            background_color=COLORS['gray'],
            color=COLORS['white'],
            size_hint_y=0.08
        )
        btn_back.bind(on_press=lambda x: setattr(self.manager, 'current', 'home'))
        layout.add_widget(btn_back)

        self.add_widget(layout)


# ── App ────────────────────────────────────────────────────────────────────────

class MinkaVozApp(App):
    def build(self):
        self.title = "MINKA VOZ"
        Window.clearcolor = COLORS['bg']

        self.db = DBManager()
        sm = ScreenManager()
        sm.current_session = None

        sm.add_widget(LoginScreen(self.db, name='login'))
        sm.add_widget(RegisterScreen(self.db, name='register'))
        sm.add_widget(HomeScreen(self.db, name='home'))
        sm.add_widget(DictionaryScreen(self.db, name='dictionary'))
        sm.add_widget(TranslateScreen(self.db, name='translate'))
        sm.add_widget(HistoryScreen(self.db, name='history'))
        sm.add_widget(StatsScreen(self.db, name='stats'))
        sm.add_widget(ProfileScreen(self.db, name='profile'))

        return sm


if __name__ == "__main__":
    MinkaVozApp().run()
