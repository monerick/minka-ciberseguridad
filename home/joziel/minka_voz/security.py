#!/usr/bin/env python3
"""
security.py — MINKA VOZ
Sistema de autenticación y base de datos encriptada
"""

import os
import sys
import json
import secrets
import sqlite3
import getpass
import time
from datetime import datetime, timedelta

try:
    import bcrypt
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
except ImportError:
    print("Instalando dependencias de seguridad...")
    os.system(f"{sys.executable} -m pip install bcrypt cryptography")
    import bcrypt
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64

HIDDEN_DB_DIR = os.path.expanduser("~/.minka_secure")
USERS_DB = os.path.join(HIDDEN_DB_DIR, "users.db")
SESSION_FILE = os.path.join(HIDDEN_DB_DIR, ".session")
SALT_FILE = os.path.join(HIDDEN_DB_DIR, ".salt")
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

R  = "\033[0m"
G  = "\033[92m"
B  = "\033[94m"
Y  = "\033[93m"
RD = "\033[91m"
GR = "\033[90m"
CY = "\033[96m"
BO = "\033[1m"

def linea(t=""):
    print(f"  {t}")

def cls():
    os.system('clear')

# ── Encriptación ────────────────────────────────────────────────────────────────

def _ensure_hidden_dir():
    os.makedirs(HIDDEN_DB_DIR, mode=0o700, exist_ok=True)

def _get_salt():
    if os.path.exists(SALT_FILE):
        with open(SALT_FILE, 'rb') as f:
            return f.read()
    salt = os.urandom(16)
    with open(SALT_FILE, 'wb') as f:
        f.write(salt)
    return salt

def _derive_key(master_password):
    salt = _get_salt()
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

def _get_fernet(master_password):
    return Fernet(_derive_key(master_password))

# ── Base de datos ───────────────────────────────────────────────────────────────

def init_security_db():
    _ensure_hidden_dir()
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
        CREATE TABLE IF NOT EXISTS secure_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data_key TEXT NOT NULL,
            data_value TEXT NOT NULL,
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            ip_address TEXT DEFAULT 'local',
            timestamp TEXT DEFAULT ''
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_secure_user ON secure_data(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)")

    con.commit()
    con.close()

# ── Contraseñas ────────────────────────────────────────────────────────────────

def hash_password(password, salt=None):
    if salt is None:
        salt = bcrypt.gensalt(rounds=12)
    elif isinstance(salt, str):
        salt = salt.encode()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode(), salt.decode()

def verify_password(password, stored_hash):
    try:
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    except (ValueError, TypeError):
        return False

def _valid_password(password):
    if len(password) < 8:
        return False, "Contraseña muy corta (mínimo 8 caracteres)"
    if not any(c.isupper() for c in password):
        return False, "Debe tener al menos una mayúscula"
    if not any(c.isdigit() for c in password):
        return False, "Debe tener al menos un número"
    if not any(c.islower() for c in password):
        return False, "Debe tener al menos una minúscula"
    return True, "OK"

def _valid_username(username):
    if len(username) < 3:
        return False, "Mínimo 3 caracteres"
    if len(username) > 20:
        return False, "Máximo 20 caracteres"
    if not username.isalnum() and not '_' in username:
        return False, "Solo letras, números y _"
    return True, "OK"

# ── Auditoría ──────────────────────────────────────────────────────────────────

def _log_audit(cur, username, action, details=""):
    try:
        cur.execute("""
            INSERT INTO audit_log (user_id, action, details, timestamp)
            VALUES ((SELECT id FROM users WHERE username = ?), ?, ?, ?)
        """, (username, action, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    except sqlite3.Error:
        pass

def get_audit_log(limit=50):
    con = sqlite3.connect(USERS_DB)
    cur = con.cursor()
    cur.execute("""
        SELECT a.id, u.username, a.action, a.details, a.timestamp
        FROM audit_log a LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.timestamp DESC LIMIT ?
    """, (limit,))
    logs = cur.fetchall()
    con.close()
    return logs

# ── Usuarios ───────────────────────────────────────────────────────────────────

def create_user(username, password, role="user"):
    _ensure_hidden_dir()
    init_security_db()

    ok, msg = _valid_username(username)
    if not ok:
        return False, msg

    ok, msg = _valid_password(password)
    if not ok:
        return False, msg

    con = sqlite3.connect(USERS_DB)
    cur = con.cursor()

    try:
        password_hash, salt = hash_password(password)
        cur.execute("""
            INSERT INTO users (username, password_hash, salt, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (username.lower(), password_hash, salt, role,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        con.commit()
        _log_audit(cur, username, "USER_CREATED", f"Rol: {role}")
        con.commit()
        return True, "Usuario creado exitosamente"
    except sqlite3.IntegrityError:
        return False, "El usuario ya existe"
    finally:
        con.close()

def authenticate(username, password):
    init_security_db()
    con = sqlite3.connect(USERS_DB)
    cur = con.cursor()

    cur.execute("""
        SELECT id, username, password_hash, role, login_attempts, locked_until, is_active
        FROM users WHERE username = ?
    """, (username.lower(),))
    user = cur.fetchone()

    if not user:
        con.close()
        return False, "Usuario no encontrado", None

    user_id, uname, p_hash, role, attempts, locked_until, is_active = user

    if not is_active:
        con.close()
        return False, "Cuenta desactivada", None

    if locked_until:
        try:
            lock_time = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")
            if datetime.now() < lock_time:
                remaining = max(1, (lock_time - datetime.now()).seconds // 60 + 1)
                con.close()
                return False, f"Cuenta bloqueada. Intenta en {remaining} minutos", None
            else:
                cur.execute("UPDATE users SET login_attempts = 0, locked_until = '' WHERE id = ?", (user_id,))
                con.commit()
        except ValueError:
            cur.execute("UPDATE users SET locked_until = '' WHERE id = ?", (user_id,))
            con.commit()

    if not verify_password(password, p_hash):
        attempts += 1
        if attempts >= MAX_LOGIN_ATTEMPTS:
            lock_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
            cur.execute("""
                UPDATE users SET login_attempts = ?, locked_until = ? WHERE id = ?
            """, (attempts, lock_until.strftime("%Y-%m-%d %H:%M:%S"), user_id))
            _log_audit(cur, uname, "ACCOUNT_LOCKED", "Max attempts reached")
        else:
            cur.execute("UPDATE users SET login_attempts = ? WHERE id = ?", (attempts, user_id))
        con.commit()
        con.close()
        remaining = max(0, MAX_LOGIN_ATTEMPTS - attempts)
        return False, f"Contraseña incorrecta ({remaining} intentos restantes)", None

    cur.execute("""
        UPDATE users SET login_attempts = 0, locked_until = '', last_login = ? WHERE id = ?
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    _log_audit(cur, uname, "LOGIN_SUCCESS", "")
    con.commit()
    con.close()

    session = _create_session(user_id, uname, role)
    return True, "Autenticación exitosa", session

def _create_session(user_id, username, role):
    session = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "token": secrets.token_urlsafe(32),
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=8)).isoformat()
    }
    _ensure_hidden_dir()
    with open(SESSION_FILE, 'w') as f:
        json.dump(session, f)
    os.chmod(SESSION_FILE, 0o600)
    return session

def get_current_session():
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, 'r') as f:
            session = json.load(f)
        if datetime.fromisoformat(session["expires_at"]) < datetime.now():
            logout()
            return None
        return session
    except (json.JSONDecodeError, KeyError, ValueError):
        logout()
        return None

def logout():
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except OSError:
            pass

def get_all_users():
    con = sqlite3.connect(USERS_DB)
    cur = con.cursor()
    cur.execute("SELECT id, username, role, created_at, last_login, is_active FROM users ORDER BY created_at DESC")
    users = cur.fetchall()
    con.close()
    return users

def change_user_role(user_id, new_role):
    con = sqlite3.connect(USERS_DB)
    cur = con.cursor()
    cur.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    changed = cur.rowcount > 0
    con.commit()
    con.close()
    return changed

def deactivate_user(user_id):
    con = sqlite3.connect(USERS_DB)
    cur = con.cursor()
    cur.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
    changed = cur.rowcount > 0
    con.commit()
    con.close()
    return changed

# ── Datos encriptados ──────────────────────────────────────────────────────────

def save_secure_data(user_id, data_key, data_value, master_password):
    if not master_password:
        return False
    init_security_db()
    fernet = _get_fernet(master_password)
    encrypted_value = fernet.encrypt(data_value.encode()).decode()

    con = sqlite3.connect(USERS_DB)
    cur = con.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("SELECT id FROM secure_data WHERE user_id = ? AND data_key = ?", (user_id, data_key))
    if cur.fetchone():
        cur.execute("UPDATE secure_data SET data_value = ?, updated_at = ? WHERE user_id = ? AND data_key = ?",
                    (encrypted_value, now, user_id, data_key))
    else:
        cur.execute("INSERT INTO secure_data (user_id, data_key, data_value, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, data_key, encrypted_value, now, now))
    con.commit()
    con.close()
    return True

def load_secure_data(user_id, data_key, master_password):
    if not master_password:
        return None
    init_security_db()
    con = sqlite3.connect(USERS_DB)
    cur = con.cursor()
    cur.execute("SELECT data_value FROM secure_data WHERE user_id = ? AND data_key = ?", (user_id, data_key))
    result = cur.fetchone()
    con.close()

    if not result:
        return None
    try:
        fernet = _get_fernet(master_password)
        return fernet.decrypt(result[0].encode()).decode()
    except Exception:
        return None

def delete_secure_data(user_id, data_key):
    init_security_db()
    con = sqlite3.connect(USERS_DB)
    cur = con.cursor()
    cur.execute("DELETE FROM secure_data WHERE user_id = ? AND data_key = ?", (user_id, data_key))
    con.commit()
    con.close()

def list_secure_keys(user_id):
    init_security_db()
    con = sqlite3.connect(USERS_DB)
    cur = con.cursor()
    cur.execute("SELECT data_key, created_at, updated_at FROM secure_data WHERE user_id = ?", (user_id,))
    keys = cur.fetchall()
    con.close()
    return keys

# ── Cambio de contraseña ────────────────────────────────────────────────────────

def change_password(session, current_password, new_password):
    ok, msg = _valid_password(new_password)
    if not ok:
        return False, msg

    con = sqlite3.connect(USERS_DB)
    cur = con.cursor()
    cur.execute("SELECT password_hash FROM users WHERE id = ?", (session["user_id"],))
    result = cur.fetchone()

    if not result or not verify_password(current_password, result[0]):
        con.close()
        return False, "Contraseña actual incorrecta"

    new_hash, salt = hash_password(new_password)
    cur.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (new_hash, salt, session["user_id"]))
    _log_audit(cur, session["username"], "PASSWORD_CHANGED", "")
    con.commit()
    con.close()
    return True, "Contraseña actualizada"

# ── Interfaz ───────────────────────────────────────────────────────────────────

def pantalla_login():
    init_security_db()

    while True:
        cls()
        print(f"""
{G}{BO}  ╔══════════════════════════════════════════╗
  ║   🔒  MINKA VOZ — SEGURIDAD  🔒         ║
  ║   Inicio de sesión requerido             ║
  ╚══════════════════════════════════════════╝{R}
""")
        linea(f"  {BO}[1]{R}  Iniciar sesión")
        linea(f"  {BO}[2]{R}  Crear cuenta")
        linea(f"  {BO}[Q]{R}  Salir")
        print()

        op = input("  › ").strip().lower()

        if op == 'q':
            return None, None
        elif op == '1':
            session = _intentar_login()
            if session:
                return session, _solicitar_master_password(session)
        elif op == '2':
            _crear_cuenta()

def _intentar_login():
    cls()
    print(f"\n{CY}{BO}  ═══ INICIAR SESIÓN ═══{R}\n")
    username = input("  Usuario: ").strip()
    password = getpass.getpass("  Contraseña: ").strip()

    if not username or not password:
        linea(f"{RD}  Completa todos los campos{R}")
        input("  ENTER para continuar...")
        return None

    print(f"\n  {CY}Verificando credenciales...{R}")
    success, message, session = authenticate(username, password)

    if success:
        linea(f"{G}  ✓ {message}{R}")
        time.sleep(0.5)
        return session
    else:
        linea(f"{RD}  ✗ {message}{R}")
        input("  ENTER para continuar...")
        return None

def _crear_cuenta():
    cls()
    print(f"\n{CY}{BO}  ═══ CREAR CUENTA ═══{R}\n")
    username = input("  Usuario (mín. 3, solo letras/números/_): ").strip()
    password = getpass.getpass("  Contraseña (mín. 8, 1 mayúscula, 1 número): ").strip()
    confirm = getpass.getpass("  Confirmar contraseña: ").strip()

    if password != confirm:
        linea(f"{RD}  Las contraseñas no coinciden{R}")
        input("  ENTER para continuar...")
        return

    print(f"\n  {CY}Creando cuenta...{R}")
    success, message = create_user(username, password)

    if success:
        linea(f"{G}  ✓ {message}{R}")
        linea(f"{G}  Ahora puedes iniciar sesión{R}")
    else:
        linea(f"{RD}  ✗ {message}{R}")
    input("  ENTER para continuar...")

def _solicitar_master_password(session):
    print(f"""
{Y}{BO}  ═══ CONTRASEÑA MAESTRA ═══{R}
  {GR}Necesaria para acceder a datos encriptados{R}
  {GR}Usa la misma contraseña para futuras sesiones{R}
""")
    master = getpass.getpass("  Contraseña maestra (ENTER para omitir): ").strip()
    if not master:
        linea(f"{Y}  Continuando sin encriptación...{R}")
        return None
    return master
