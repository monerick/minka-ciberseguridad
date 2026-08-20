#!/usr/bin/env python3
"""
MINKA VOZ — Dashboard Web para Profesores
"""

import os
import sys
import sqlite3
import json
import secrets
from datetime import datetime, timedelta
from functools import wraps

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'home', 'joziel', 'minka_voz'))
import security as sec
import database as db

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

@app.before_request
def before_request():
    if request.endpoint and request.endpoint not in ('login', 'static'):
        if 'user' not in session:
            return redirect(url_for('login'))

@app.context_processor
def inject_user():
    return dict(current_user=session.get('user'))

# ── Database ──

def get_db():
    con = sqlite3.connect(os.path.expanduser("~/minka/minka.db"))
    con.row_factory = sqlite3.Row
    return con

def get_users_db():
    con = sqlite3.connect(os.path.join(os.path.expanduser("~"), ".minka_secure", "users.db"))
    con.row_factory = sqlite3.Row
    return con

# ── Auth ──

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        success, msg, s = sec.authenticate(username, password)
        if success:
            if s['role'] not in ('admin', 'teacher'):
                flash('Acceso denegado — se requiere rol de profesor', 'error')
                return render_template('login.html')
            session['user'] = s
            return redirect(url_for('dashboard'))
        flash(msg, 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ── Dashboard ──

@app.route('/')
def dashboard():
    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) as cnt FROM dictionary")
    total_words = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM conversations")
    total_conversations = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(DISTINCT user) as cnt FROM conversations")
    total_users = cur.fetchone()['cnt']

    cur.execute("""
        SELECT user, COUNT(*) as cnt
        FROM conversations
        GROUP BY user
        ORDER BY cnt DESC
        LIMIT 10
    """)
    top_users = cur.fetchall()

    cur.execute("""
        SELECT DATE(fecha) as dia, COUNT(*) as cnt
        FROM conversations
        WHERE fecha != ''
        GROUP BY dia
        ORDER BY dia DESC
        LIMIT 7
    """)
    daily_activity = cur.fetchall()

    cur.execute("""
        SELECT message, texto_traducido, user, fecha
        FROM conversations
        ORDER BY fecha DESC
        LIMIT 10
    """)
    recent = cur.fetchall()

    con.close()

    return render_template('dashboard.html',
                         total_words=total_words,
                         total_conversations=total_conversations,
                         total_users=total_users,
                         top_users=top_users,
                         daily_activity=daily_activity,
                         recent=recent)

# ── Diccionario ──

@app.route('/dictionary')
def dictionary():
    con = get_db()
    cur = con.cursor()

    search = request.args.get('search', '').strip()
    if search:
        cur.execute("""
            SELECT id, kogui, spanish, categoria, notas, fecha
            FROM dictionary
            WHERE LOWER(kogui) LIKE LOWER(?) OR LOWER(spanish) LIKE LOWER(?)
            ORDER BY spanish
        """, (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT id, kogui, spanish, categoria, notas, fecha FROM dictionary ORDER BY spanish")

    words = cur.fetchall()
    con.close()

    return render_template('dictionary.html', words=words, search=search)

@app.route('/dictionary/add', methods=['POST'])
def add_word():
    kogui = request.form.get('kogui', '').strip()
    spanish = request.form.get('spanish', '').strip()
    categoria = request.form.get('categoria', 'general').strip()
    notas = request.form.get('notas', '').strip()

    if kogui and spanish:
        con = get_db()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO dictionary (kogui, spanish, categoria, notas, fecha)
            VALUES (?, ?, ?, ?, ?)
        """, (kogui, spanish, categoria, notas, datetime.now().strftime("%Y-%m-%d %H:%M")))
        con.commit()
        con.close()
        flash(f'✓ "{kogui}" agregada', 'success')

    return redirect(url_for('dictionary'))

@app.route('/dictionary/edit/<int:word_id>', methods=['GET', 'POST'])
def edit_word(word_id):
    con = get_db()
    cur = con.cursor()

    if request.method == 'POST':
        kogui = request.form.get('kogui', '').strip()
        spanish = request.form.get('spanish', '').strip()
        categoria = request.form.get('categoria', '').strip()
        notas = request.form.get('notas', '').strip()
        cur.execute("""
            UPDATE dictionary SET kogui=?, spanish=?, categoria=?, notas=?
            WHERE id=?
        """, (kogui, spanish, categoria, notas, word_id))
        con.commit()
        con.close()
        flash('✓ Palabra actualizada', 'success')
        return redirect(url_for('dictionary'))

    cur.execute("SELECT id, kogui, spanish, categoria, notas FROM dictionary WHERE id=?", (word_id,))
    word = cur.fetchone()
    con.close()

    if not word:
        flash('Palabra no encontrada', 'error')
        return redirect(url_for('dictionary'))

    return render_template('edit_word.html', word=word)

@app.route('/dictionary/delete/<int:word_id>')
def delete_word(word_id):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM dictionary WHERE id=?", (word_id,))
    con.commit()
    con.close()
    flash('✓ Palabra eliminada', 'success')
    return redirect(url_for('dictionary'))

# ── Usuarios ──

@app.route('/users')
def users():
    users = sec.get_all_users()
    return render_template('users.html', users=users)

@app.route('/users/create', methods=['POST'])
def create_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'user').strip()

    ok, msg = sec.create_user(username, password, role)
    if ok:
        flash(f'✓ {msg}', 'success')
    else:
        flash(f'✗ {msg}', 'error')

    return redirect(url_for('users'))

@app.route('/users/role/<int:user_id>', methods=['POST'])
def change_role(user_id):
    new_role = request.form.get('role', 'user')
    sec.change_user_role(user_id, new_role)
    flash('✓ Rol actualizado', 'success')
    return redirect(url_for('users'))

@app.route('/users/deactivate/<int:user_id>')
def deactivate_user(user_id):
    sec.deactivate_user(user_id)
    flash('✓ Usuario desactivado', 'success')
    return redirect(url_for('users'))

# ── Historial ──

@app.route('/history')
def history():
    con = get_db()
    cur = con.cursor()

    search = request.args.get('search', '').strip()
    if search:
        cur.execute("""
            SELECT id, user, message, texto_traducido, direccion, fuente, fecha
            FROM conversations
            WHERE LOWER(message) LIKE LOWER(?) OR LOWER(texto_traducido) LIKE LOWER(?)
            ORDER BY fecha DESC
            LIMIT 100
        """, (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("""
            SELECT id, user, message, texto_traducido, direccion, fuente, fecha
            FROM conversations
            ORDER BY fecha DESC
            LIMIT 100
        """)

    history = cur.fetchall()
    con.close()

    return render_template('history.html', history=history, search=search)

# ── Audit Log ──

@app.route('/audit')
def audit():
    logs = sec.get_audit_log(100)
    return render_template('audit.html', logs=logs)

# ── API (para gráficos) ──

@app.route('/api/stats')
def api_stats():
    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) as cnt FROM dictionary")
    words = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(*) as cnt FROM conversations")
    convs = cur.fetchone()['cnt']

    cur.execute("SELECT COUNT(DISTINCT user) as cnt FROM conversations")
    users = cur.fetchone()['cnt']

    cur.execute("""
        SELECT DATE(fecha) as dia, COUNT(*) as cnt
        FROM conversations WHERE fecha != ''
        GROUP BY dia ORDER BY dia DESC LIMIT 30
    """)
    daily = [{"date": r['dia'], "count": r['cnt']} for r in cur.fetchall()]

    cur.execute("""
        SELECT user, COUNT(*) as cnt
        FROM conversations GROUP BY user ORDER BY cnt DESC LIMIT 10
    """)
    by_user = [{"user": r['user'], "count": r['cnt']} for r in cur.fetchall()]

    con.close()

    return jsonify({
        "words": words,
        "conversations": convs,
        "users": users,
        "daily": daily,
        "by_user": by_user
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
