#!/usr/bin/env python3
"""
profesor_dashboard.py — MINKA VOZ
Panel de administración para profesores
"""

import os
import sys
import time
import sqlite3
from datetime import datetime, timedelta
import database as db
import security as sec

R  = "\033[0m"
G  = "\033[92m"
B  = "\033[94m"
Y  = "\033[93m"
RD = "\033[91m"
GR = "\033[90m"
CY = "\033[96m"
BO = "\033[1m"
MG = "\033[95m"

def cls():
    os.system('clear')

def banner():
    cls()
    print(f"""
{CY}{BO}  ╔══════════════════════════════════════════╗
  ║   📊  MINKA VOZ — PANEL PROFESOR        ║
  ║   Gestión y monitoreo del diccionario    ║
  ╚══════════════════════════════════════════╝{R}
""")

def linea(t=""):
    print(f"  {t}")

def separador():
    linea(f"{GR}──────────────────────────────────────────{R}")

def esperar_enter():
    input(f"\n  {GR}Presiona ENTER para continuar...{R}")

# ── Gestión de Diccionario ─────────────────────────────────────────────────────

def gestion_diccionario():
    while True:
        banner()
        linea(f"{MG}{BO}📖 Gestión del Diccionario Kogui{R}")
        print()
        s = db.estadisticas()
        linea(f"  {GR}Total palabras: {s['palabras']}{R}")
        print()
        separador()
        print()
        linea(f"  {BO}[1]{R}  Ver todas las palabras")
        linea(f"  {BO}[2]{R}  Buscar palabra")
        linea(f"  {BO}[3]{R}  Agregar palabra nueva")
        linea(f"  {BO}[4]{R}  Editar palabra")
        linea(f"  {BO}[5]{R}  Eliminar palabra")
        linea(f"  {BO}[6]{R}  Agregar varias palabras")
        linea(f"  {BO}[B]{R}  Volver")
        print()

        op = input("  › ").strip().lower()
        if op == 'b':
            break
        elif op == '1':
            _ver_todas_palabras()
        elif op == '2':
            _buscar_palabra()
        elif op == '3':
            _agregar_palabra()
        elif op == '4':
            _editar_palabra()
        elif op == '5':
            _eliminar_palabra()
        elif op == '6':
            _agregar_varias()

def _ver_todas_palabras():
    banner()
    linea(f"{MG}{BO}📖 Todas las palabras{R}")
    print()
    palabras = db.obtener_todas_palabras()
    if not palabras:
        linea(f"{Y}Diccionario vacío{R}")
    else:
        cat_actual = None
        for pid, kogui, espanol, categoria, notas, fecha in palabras:
            if categoria != cat_actual:
                cat_actual = categoria
                print()
                linea(f"{CY}{BO}▸ {categoria.upper()}{R}")
            nota = f"  {GR}({notas}){R}" if notas else ""
            linea(f"   {G}#{pid:<5}{R} {espanol:<22} →  {kogui}{nota}")
        print()
        linea(f"{GR}Total: {len(palabras)} palabras{R}")
    esperar_enter()

def _buscar_palabra():
    banner()
    linea(f"{MG}{BO}🔍 Buscar palabra{R}")
    print()
    termino = input("  Buscar: ").strip()
    if not termino:
        return
    resultados = db.buscar_palabra(termino)
    print()
    if not resultados:
        linea(f"{Y}No se encontró '{termino}'{R}")
    else:
        for pid, kogui, espanol, categoria, notas, fecha in resultados:
            linea(f"  {G}#{pid}{R}  {BO}{espanol:<22}{R} →  {kogui}  {GR}[{categoria}]{R}")
            if notas:
                linea(f"     {GR}Nota: {notas}{R}")
        linea(f"\n{GR}Encontradas: {len(resultados)}{R}")
    esperar_enter()

def _agregar_palabra():
    banner()
    linea(f"{MG}{BO}➕ Agregar palabra{R}")
    print()
    kogui = input("  Palabra en Kogui:    ").strip()
    if not kogui:
        return
    espanol = input("  Traducción Español:  ").strip()
    if not espanol:
        return
    print()
    linea(f"{GR}Categorías: saludo, familia, naturaleza, animal, accion, numero, general{R}")
    categoria = input("  Categoría [general]: ").strip() or "general"
    notas = input("  Notas (opcional):    ").strip()
    print()
    linea(f"  {CY}Kogui:{R}     {kogui}")
    linea(f"  {CY}Español:{R}   {espanol}")
    linea(f"  {CY}Categoría:{R} {categoria}")
    print()
    if input(f"  {Y}¿Agregar? [s/n]: {R}").strip().lower() == 's':
        ok, msg = db.agregar_palabra(kogui, espanol, categoria, notas)
        linea(f"\n  {G}✓ Agregada{R}" if ok else f"\n  {Y}⚠ {msg}{R}")
    else:
        linea(f"\n  {GR}Cancelado{R}")
    esperar_enter()

def _editar_palabra():
    banner()
    linea(f"{MG}{BO}✏ Editar palabra{R}")
    print()
    termino = input("  Buscar palabra a editar: ").strip()
    if not termino:
        return
    resultados = db.buscar_palabra(termino)
    if not resultados:
        linea(f"{Y}No se encontró '{termino}'{R}")
        esperar_enter()
        return
    for pid, kogui, espanol, categoria, notas, fecha in resultados:
        linea(f"  {G}#{pid}{R}  {BO}{espanol}{R} →  {kogui}  {GR}[{categoria}]{R}")

    print()
    try:
        pid_edit = int(input("  ID a editar (0 cancelar): ").strip())
        if pid_edit == 0:
            return

        con = db.conectar()
        cur = con.cursor()
        cur.execute("SELECT kogui, spanish, categoria, notas FROM dictionary WHERE id = ?", (pid_edit,))
        actual = cur.fetchone()
        con.close()

        if not actual:
            linea(f"{Y}  ID no encontrado{R}")
            esperar_enter()
            return

        old_kogui, old_spanish, old_cat, old_notas = actual
        print()
        linea(f"  {GR}Deja vacío para mantener el valor actual{R}")
        print()
        kogui = input(f"  Kogui [{old_kogui}]: ").strip() or old_kogui
        espanol = input(f"  Español [{old_spanish}]: ").strip() or old_spanish
        categoria = input(f"  Categoría [{old_cat}]: ").strip() or old_cat
        notas = input(f"  Notas [{old_notas}]: ").strip() or old_notas

        con = db.conectar()
        cur = con.cursor()
        cur.execute("""
            UPDATE dictionary SET kogui = ?, spanish = ?, categoria = ?, notas = ?
            WHERE id = ?
        """, (kogui, espanol, categoria, notas, pid_edit))
        con.commit()
        con.close()
        linea(f"\n  {G}✓ Palabra #{pid_edit} actualizada{R}")
    except ValueError:
        linea(f"  {RD}ID inválido{R}")
    esperar_enter()

def _eliminar_palabra():
    banner()
    linea(f"{MG}{BO}🗑 Eliminar palabra{R}")
    print()
    termino = input("  Buscar palabra a eliminar: ").strip()
    if not termino:
        return
    resultados = db.buscar_palabra(termino)
    print()
    if not resultados:
        linea(f"{Y}No se encontró '{termino}'{R}")
        esperar_enter()
        return
    for pid, kogui, espanol, categoria, notas, fecha in resultados:
        linea(f"  {G}#{pid}{R}  {BO}{espanol:<22}{R} →  {kogui}  {GR}[{categoria}]{R}")
    print()
    try:
        pid_del = int(input("  ID a eliminar (0 cancelar): ").strip())
        if pid_del == 0:
            return
        if input(f"  {RD}¿Eliminar #{pid_del}? [s/n]: {R}").strip().lower() == 's':
            ok = db.eliminar_palabra(pid_del)
            linea(f"\n  {G}✓ Eliminada{R}" if ok else f"\n  {Y}⚠ ID no encontrado{R}")
    except ValueError:
        linea(f"  {RD}ID inválido{R}")
    esperar_enter()

def _agregar_varias():
    banner()
    linea(f"{MG}{BO}➕ Agregar varias palabras{R}")
    print()
    linea(f"{GR}Formato: kogui|español|categoría{R}")
    linea(f"{GR}Ejemplo: saki|hola|saludo{R}")
    print()
    agregadas = 0
    while True:
        linea(f"{GR}--- Palabra #{agregadas + 1} (vacío para terminar) ---{R}")
        linea = input("  > ").strip()
        if not linea:
            break
        partes = linea.split("|")
        if len(partes) < 2:
            linea(f"{Y}  Formato: kogui|español|categoría{R}")
            continue
        kogui = partes[0].strip()
        espanol = partes[1].strip()
        categoria = partes[2].strip() if len(partes) > 2 else "general"
        ok, msg = db.agregar_palabra(kogui, espanol, categoria)
        if ok:
            agregadas += 1
            linea(f"{G}  ✓ {kogui} → {espanol}{R}")
        else:
            linea(f"{Y}  ⚠ {kogui}: {msg}{R}")

    linea(f"\n{G}✓ {agregadas} palabras agregadas{R}")
    esperar_enter()

# ── Monitoreo ──────────────────────────────────────────────────────────────────

def monitoreo():
    while True:
        banner()
        linea(f"{CY}{BO}📊 Monitoreo{R}")
        print()
        separador()
        print()
        linea(f"  {BO}[1]{R}  📈 Estadísticas globales")
        linea(f"  {BO}[2]{R}  👥 Actividad por usuario")
        linea(f"  {BO}[3]{R}  📅 Actividad reciente")
        linea(f"  {BO}[4]{R}  🔍 Audit log")
        linea(f"  {BO}[B]{R}  Volver")
        print()

        op = input("  › ").strip().lower()
        if op == 'b':
            break
        elif op == '1':
            _estadisticas_globales()
        elif op == '2':
            _actividad_usuarios()
        elif op == '3':
            _actividad_reciente()
        elif op == '4':
            _ver_audit_log()

def _estadisticas_globales():
    banner()
    linea(f"{CY}{BO}📈 Estadísticas Globales{R}")
    print()
    s = db.estadisticas_globales()
    linea(f"  {BO}Diccionario{R}")
    linea(f"  {G}●{R} Total palabras:         {BO}{s['palabras']}{R}")
    print()
    linea(f"  {BO}Actividad{R}")
    linea(f"  {G}●{R} Total traducciones:     {BO}{s['conversaciones']}{R}")
    linea(f"  {G}●{R} Usuarios activos:        {BO}{s['usuarios_activos']}{R}")

    if s['por_usuario']:
        print()
        linea(f"  {BO}Por usuario:{R}")
        for user, cnt in s['por_usuario'][:10]:
            barra = "█" * min(cnt, 30)
            linea(f"  {G}{user:<20}{R} {barra} {cnt}")

    if s['por_dia']:
        print()
        linea(f"  {BO}Actividad últimos días:{R}")
        for dia, cnt in s['por_dia'][:7]:
            barra = "█" * min(cnt, 30)
            linea(f"  {G}{dia:<12}{R} {barra} {cnt}")

    esperar_enter()

def _actividad_usuarios():
    banner()
    linea(f"{CY}{BO}👥 Actividad por usuario{R}")
    print()

    con = db.conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT user, COUNT(*) as total,
               MIN(fecha) as primera,
               MAX(fecha) as ultima
        FROM conversations
        GROUP BY user ORDER BY total DESC
    """)
    usuarios = cur.fetchall()
    con.close()

    if not usuarios:
        linea(f"{Y}No hay actividad registrada{R}")
    else:
        for user, total, primera, ultima in usuarios:
            linea(f"  {G}●{R} {BO}{user}{R}")
            linea(f"    Traducciones: {total}")
            if primera:
                linea(f"    Primera vez:  {primera[:16]}")
            if ultima:
                linea(f"    Última vez:   {ultima[:16]}")
            print()

    esperar_enter()

def _actividad_reciente():
    banner()
    linea(f"{CY}{BO}📅 Actividad reciente (últimas 24h){R}")
    print()

    con = db.conectar()
    cur = con.cursor()
    cur.execute("""
        SELECT user, message, texto_traducido, direccion, fecha
        FROM conversations
        WHERE fecha >= datetime('now', '-1 day')
        ORDER BY fecha DESC LIMIT 30
    """)
    recientes = cur.fetchall()
    con.close()

    if not recientes:
        linea(f"{Y}No hay actividad en las últimas 24 horas{R}")
    else:
        for user, original, traducido, direccion, fecha in recientes:
            flecha = "K→E" if direccion == "k2e" else "E→K"
            linea(f"  {GR}{fecha[11:16]}{R} {G}{user:<15}{R} [{flecha}] {original} → {traducido}")
        print()
        linea(f"{GR}Total: {len(recientes)} traducciones{R}")

    esperar_enter()

def _ver_audit_log():
    banner()
    linea(f"{CY}{BO}🔍 Audit Log{R}")
    print()
    logs = sec.get_audit_log(30)
    if not logs:
        linea(f"{Y}No hay registros de auditoría{R}")
    else:
        for lid, user, action, details, ts in logs:
            color = G if "SUCCESS" in action else (RD if "LOCKED" in action else Y)
            linea(f"  {color}{ts}  {user or '?':<15}  {action}{R}")
            if details:
                linea(f"  {GR}  └─ {details}{R}")
    esperar_enter()

# ── Gestión de usuarios ────────────────────────────────────────────────────────

def gestion_usuarios():
    while True:
        banner()
        linea(f"{CY}{BO}👥 Gestión de Usuarios{R}")
        print()
        separador()
        print()
        linea(f"  {BO}[1]{R}  Ver todos los usuarios")
        linea(f"  {BO}[2]{R}  Crear usuario")
        linea(f"  {BO}[3]{R}  Cambiar rol")
        linea(f"  {BO}[4]{R}  Desactivar usuario")
        linea(f"  {BO}[B]{R}  Volver")
        print()

        op = input("  › ").strip().lower()
        if op == 'b':
            break
        elif op == '1':
            _ver_usuarios()
        elif op == '2':
            _crear_usuario_profesor()
        elif op == '3':
            _cambiar_rol()
        elif op == '4':
            _desactivar_usuario()

def _ver_usuarios():
    banner()
    linea(f"{CY}{BO}👥 Todos los usuarios{R}")
    print()
    users = sec.get_all_users()
    if not users:
        linea(f"{Y}No hay usuarios registrados{R}")
    else:
        for uid, username, role, created, last_login, active in users:
            estado = f"{G}●{R}" if active else f"{RD}●{R}"
            rol_color = CY if role == "admin" else G
            linea(f"  {estado} {BO}{username:<20}{R}  {rol_color}[{role}]{R}")
            linea(f"    Creado: {created[:16] if created else '?'}")
            if last_login:
                linea(f"    Último login: {last_login[:16]}")
            print()
        linea(f"{GR}Total: {len(users)} usuarios{R}")
    esperar_enter()

def _crear_usuario_profesor():
    banner()
    linea(f"{CY}{BO}➕ Crear usuario{R}")
    print()
    username = input("  Usuario: ").strip()
    password = input("  Contraseña: ").strip()
    print()
    linea(f"{GR}Roles: user, teacher, admin{R}")
    role = input("  Rol [teacher]: ").strip() or "teacher"
    print()

    ok, msg = sec.create_user(username, password, role)
    if ok:
        linea(f"{G}  ✓ {msg}{R}")
    else:
        linea(f"{RD}  ✗ {msg}{R}")
    esperar_enter()

def _cambiar_rol():
    banner()
    linea(f"{CY}{BO}🔄 Cambiar rol{R}")
    print()
    users = sec.get_all_users()
    for uid, username, role, _, _, active in users:
        linea(f"  {G}#{uid}{R}  {username:<20}  [{role}]")
    print()
    try:
        uid = int(input("  ID de usuario: ").strip())
        print()
        linea(f"{GR}Roles: user, teacher, admin{R}")
        new_role = input("  Nuevo rol: ").strip()
        if new_role in ("user", "teacher", "admin"):
            if sec.change_user_role(uid, new_role):
                linea(f"{G}  ✓ Rol actualizado{R}")
            else:
                linea(f"{Y}  ⚠ Usuario no encontrado{R}")
        else:
            linea(f"{RD}  Rol inválido{R}")
    except ValueError:
        linea(f"{RD}  ID inválido{R}")
    esperar_enter()

def _desactivar_usuario():
    banner()
    linea(f"{RD}{BO}🚫 Desactivar usuario{R}")
    print()
    users = sec.get_all_users()
    for uid, username, role, _, _, active in users:
        estado = f"{G}● Activo{R}" if active else f"{RD}● Inactivo{R}"
        linea(f"  {G}#{uid}{R}  {username:<20}  [{role}]  {estado}")
    print()
    try:
        uid = int(input("  ID a desactivar (0 cancelar): ").strip())
        if uid == 0:
            return
        if input(f"  {RD}¿Desactivar usuario #{uid}? [s/n]: {R}").strip().lower() == 's':
            if sec.deactivate_user(uid):
                linea(f"{G}  ✓ Usuario desactivado{R}")
            else:
                linea(f"{Y}  ⚠ Usuario no encontrado{R}")
    except ValueError:
        linea(f"{RD}  ID inválido{R}")
    esperar_enter()

# ── Menú principal ─────────────────────────────────────────────────────────────

def menu_profesor():
    while True:
        banner()
        linea(f"{GR}Bienvenido, {current_session['username']}{R}")
        print()
        separador()
        print()
        linea(f"  {BO}[1]{R}  📖  Gestión del Diccionario")
        linea(f"  {BO}[2]{R}  📊  Monitoreo")
        linea(f"  {BO}[3]{R}  👥  Gestión de Usuarios")
        linea(f"  {BO}[4]{R}  📊  Mis estadísticas")
        linea(f"  {BO}[5]{R}  👤  Mi Perfil")
        linea(f"  {BO}[Q]{R}  Salir")
        print()
        separador()
        print()

        op = input("  › ").strip().lower()
        if op == 'q':
            sec.logout()
            cls()
            linea(f"{G}  Hasta pronto 🌿{R}\n")
            break
        elif op == '1':
            gestion_diccionario()
        elif op == '2':
            monitoreo()
        elif op == '3':
            gestion_usuarios()
        elif op == '4':
            _mis_estadisticas()
        elif op == '5':
            _mi_perfil()

def _mis_estadisticas():
    banner()
    linea(f"{CY}{BO}📊 Mis estadísticas{R}")
    print()
    user = current_session["username"]
    s = db.estadisticas(user)
    linea(f"  {BO}Diccionario{R}")
    linea(f"  {G}●{R} Palabras totales:     {BO}{s['palabras']}{R}")
    print()
    linea(f"  {BO}Mis traducciones{R}")
    linea(f"  {G}●{R} Total:                {BO}{s['conversaciones']}{R}")
    linea(f"  {G}●{R} Kogui → Español:      {BO}{s['kogui_a_esp']}{R}")
    linea(f"  {G}●{R} Español → Kogui:      {BO}{s['esp_a_kogui']}{R}")
    linea(f"  {G}●{R} Desde diccionario:    {BO}{s['desde_diccionario']}{R}")
    esperar_enter()

def _mi_perfil():
    banner()
    linea(f"{CY}{BO}👤 Mi Perfil{R}")
    print()
    linea(f"  {BO}Usuario:{R}  {current_session['username']}")
    linea(f"  {BO}Rol:{R}      {current_session['role']}")
    linea(f"  {BO}Sesión:{R}   {current_session['created_at'][:10]}")
    print()
    separador()
    print()
    linea(f"  {BO}[1]{R}  Cambiar contraseña")
    linea(f"  {BO}[B]{R}  Volver")
    print()

    op = input("  › ").strip().lower()
    if op == '1':
        print()
        import getpass
        current = getpass.getpass("  Contraseña actual: ").strip()
        new_pass = getpass.getpass("  Nueva contraseña: ").strip()
        confirm = getpass.getpass("  Confirmar: ").strip()
        if new_pass != confirm:
            linea(f"{RD}  Las contraseñas no coinciden{R}")
        else:
            ok, msg = sec.change_password(current_session, current, new_pass)
            if ok:
                linea(f"{G}  ✓ {msg}{R}")
            else:
                linea(f"{RD}  ✗ {msg}{R}")
        esperar_enter()

# ── Main ───────────────────────────────────────────────────────────────────────

current_session = None

def main():
    global current_session

    sec.init_security_db()

    session = sec.get_current_session()
    if session:
        current_session = session
    else:
        session, master_password = sec.pantalla_login()
        if not session:
            cls()
            linea(f"{G}  Hasta pronto 🌿{R}\n")
            return
        current_session = session

    if current_session["role"] not in ("admin", "teacher"):
        cls()
        linea(f"{RD}  Acceso denegado — se requiere rol de profesor o admin{R}")
        linea(f"{GR}  Tu rol actual: {current_session['role']}{R}")
        print()
        linea(f"  USA la app principal: python3 minka_voz.py")
        print()
        return

    banner()
    linea(f"{G}  Bienvenido, profesor {current_session['username']}{R}")
    if current_session['role'] == 'admin':
        linea(f"{CY}  Rol: Administrador{R}")
    time.sleep(1)

    db.inicializar_db()
    menu_profesor()

if __name__ == "__main__":
    main()
