from flask import Blueprint, request, render_template, redirect, session, url_for, flash
from services.database import get_connection
import bcrypt
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # --- BLOK VALIDASI BARU ---
        errors = [] # List untuk mengumpulkan semua pesan error

        if not password or not confirm_password:
            errors.append("Password dan konfirmasi password tidak boleh kosong.")
        else:
            if password != confirm_password:
                errors.append("Password dan konfirmasi password tidak cocok.")
            
            if len(password) < 8:
                errors.append("Password minimal harus 8 karakter.")
            
            if not re.search(r'[a-z]', password):
                errors.append("Password harus mengandung setidaknya satu huruf kecil.")
                
            if not re.search(r'[A-Z]', password):
                errors.append("Password harus mengandung setidaknya satu huruf besar (kapital).")

            if not re.search(r'[0-9]', password):
                errors.append("Password harus mengandung setidaknya satu angka.")
        
        # Jika ada error di dalam list, gabungkan dan flash sebagai satu pesan
        if errors:
            # Gabungkan semua error menjadi satu pesan dengan baris baru
            error_message = "Harap perbaiki kesalahan berikut: " + ", ".join(errors)
            flash(error_message)
            return redirect(url_for('auth.register'))
        # --- AKHIR BLOK VALIDASI ---

        # Jika lolos, lanjutkan proses hashing
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_password.decode('utf-8'))
            )
            conn.commit()
            flash('Registrasi berhasil! Silakan login.')
            return redirect(url_for('auth.login'))
        except Exception as e:
            conn.rollback()
            if 'Duplicate entry' in str(e):
                flash('Username sudah digunakan. Silakan pilih username lain.')
            else:
                flash(f'Terjadi kesalahan saat registrasi: {e}')
            return redirect(url_for('auth.register'))
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session.clear() 
            session['user_id'] = user['id']
            session['username'] = user['username']
            session.permanent = True # Mengaktifkan sesi permanen
            return redirect(url_for('chat.index')) 
        else:
            flash('Username atau password salah.')
            return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))