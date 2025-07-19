from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, make_response, send_from_directory
from services.database import get_connection
from services.encryption_service import encrypt, decrypt
import os
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

# --- ENDPOINTS UTAMA & PRIBADI ---
@chat_bp.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    return render_template('chat.html', username=session.get('username'), user_id=session.get('user_id'))

@chat_bp.route('/chat/search_user')
def search_user():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    query = request.args.get('q', '').strip()
    if len(query) < 1: return jsonify({'users': []})
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username FROM users WHERE username LIKE %s AND id != %s LIMIT 10", (f'%{query}%', session['user_id']))
    users = cursor.fetchall(); cursor.close(); conn.close()
    return jsonify({'users': users})

@chat_bp.route('/chat/private_chats', methods=['GET'])
def get_private_chats():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT DISTINCT u.id, u.username
        FROM users u
        JOIN messages m ON u.id = m.user_id OR u.id = m.receiver_id
        WHERE (m.user_id = %s OR m.receiver_id = %s) AND u.id != %s
        AND (m.deleted_by_user_id_1 IS NULL OR m.deleted_by_user_id_1 != %s)
        AND (m.deleted_by_user_id_2 IS NULL OR m.deleted_by_user_id_2 != %s)
    """, (user_id, user_id, user_id, user_id, user_id))
    users = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify({'private_chats': users})

@chat_bp.route('/chat/history')
def private_chat_history():
    if 'user_id' not in session: return jsonify({"error": "Unauthorized"}), 401
    receiver_id = request.args.get('receiver_id')
    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT m.*, u.username as sender_username,
               replied.content as replied_content,
               replied_user.username as replied_username
        FROM messages m
        JOIN users u ON m.user_id = u.id
        LEFT JOIN messages replied ON m.reply_to_message_id = replied.id
        LEFT JOIN users replied_user ON replied.user_id = replied_user.id
        WHERE ((m.user_id = %s AND m.receiver_id = %s) OR (m.user_id = %s AND m.receiver_id = %s))
          AND (m.deleted_by_user_id_1 IS NULL OR m.deleted_by_user_id_1 != %s)
          AND (m.deleted_by_user_id_2 IS NULL OR m.deleted_by_user_id_2 != %s)
        ORDER BY m.timestamp ASC
    """
    cursor.execute(query, (user_id, receiver_id, receiver_id, user_id, user_id, user_id))
    history = cursor.fetchall()

    processed_history = process_history_with_markers(history, user_id, int(receiver_id), 'private', cursor)
    
    cursor.close()
    conn.close()
    return jsonify({'history': processed_history})


# --- ENDPOINTS GRUP ---
@chat_bp.route('/groups', methods=['GET'])
def get_user_groups():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT g.id, g.name, g.creator_id FROM groups g
        JOIN group_members gm ON g.id = gm.group_id
        WHERE gm.user_id = %s
    """, (user_id,))
    groups = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({'groups': groups})

@chat_bp.route('/groups/create', methods=['POST'])
def create_group():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    group_name = request.json.get('name')
    if not group_name:
        return jsonify({'error': 'Nama grup tidak boleh kosong'}), 400
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("INSERT INTO groups (name, creator_id) VALUES (%s, %s)", (group_name, user_id))
        group_id = cursor.lastrowid
        # Set a role as 'creator'
        cursor.execute("INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, 'creator')", (group_id, user_id))
        conn.commit()
        cursor.execute("SELECT * FROM groups WHERE id = %s", (group_id,))
        new_group = cursor.fetchone()
        return jsonify({'status': 'ok', 'group': new_group})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': 'Gagal membuat grup di server'}), 500
    finally:
        cursor.close()
        conn.close()

@chat_bp.route('/groups/<int:group_id>/history', methods=['GET'])
def group_chat_history(group_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'error': 'Akses ditolak'}), 403

    query = """
        SELECT m.*, u.username as sender_username,
               replied.content as replied_content,
               replied_user.username as replied_username
        FROM messages m
        JOIN users u ON m.user_id = u.id
        LEFT JOIN messages replied ON m.reply_to_message_id = replied.id
        LEFT JOIN users replied_user ON replied.user_id = replied_user.id
        WHERE m.group_id = %s
        ORDER BY m.timestamp ASC
    """
    cursor.execute(query, (group_id,))
    history = cursor.fetchall()
    
    processed_history = process_history_with_markers(history, user_id, group_id, 'group', cursor)

    # Fetch member list with roles
    cursor.execute("""
        SELECT u.id, u.username, gm.role
        FROM users u
        JOIN group_members gm ON u.id = gm.user_id
        WHERE gm.group_id = %s
        ORDER BY u.username
    """, (group_id,))
    members = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({'history': processed_history, 'members': members})


@chat_bp.route('/groups/<int:group_id>/non_members')
def get_non_group_members(group_id):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT creator_id FROM groups WHERE id = %s", (group_id,))
    group = cursor.fetchone()
    if not group or group['creator_id'] != session['user_id']:
        cursor.close(); conn.close()
        return jsonify({'error': 'Hanya admin yang dapat menambah anggota'}), 403
    query = request.args.get('q', '').strip()
    cursor.execute("""
        SELECT id, username FROM users
        WHERE id NOT IN (SELECT user_id FROM group_members WHERE group_id = %s)
        AND username LIKE %s AND id != %s LIMIT 10
    """, (group_id, f'%{query}%', session['user_id']))
    users = cursor.fetchall(); cursor.close(); conn.close()
    return jsonify({'users': users})

# --- ENDPOINTS NOTIFIKASI ---
@chat_bp.route('/chat/unread_counts', methods=['GET'])
def get_unread_counts():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    unread_counts = {}
    private_query = """
        SELECT m.user_id AS chat_id, COUNT(m.id) AS unread_count
        FROM messages m
        LEFT JOIN chat_read_timestamps rts ON m.user_id = rts.chat_id AND rts.chat_type = 'private' AND rts.user_id = %s
        WHERE m.receiver_id = %s AND m.timestamp > IFNULL(rts.last_read_timestamp, '1970-01-01')
        GROUP BY m.user_id
    """
    cursor.execute(private_query, (user_id, user_id))
    private_counts = cursor.fetchall()
    for row in private_counts:
        unread_counts[f"private_{row['chat_id']}"] = row['unread_count']
    group_query = """
        SELECT m.group_id AS chat_id, COUNT(m.id) AS unread_count
        FROM messages m
        LEFT JOIN chat_read_timestamps rts ON m.group_id = rts.chat_id AND rts.chat_type = 'group' AND rts.user_id = %s
        WHERE m.group_id IN (SELECT group_id FROM group_members WHERE user_id = %s)
        AND m.user_id != %s
        AND m.timestamp > IFNULL(rts.last_read_timestamp, '1970-01-01')
        GROUP BY m.group_id
    """
    cursor.execute(group_query, (user_id, user_id, user_id))
    group_counts = cursor.fetchall()
    for row in group_counts:
        unread_counts[f"group_{row['chat_id']}"] = row['unread_count']
    cursor.close(); conn.close()
    return jsonify(unread_counts)

@chat_bp.route('/chat/mark_as_read', methods=['POST'])
def mark_as_read():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    data = request.json
    chat_id = data.get('chat_id')
    chat_type = data.get('chat_type')
    if not all([chat_id, chat_type]):
        return jsonify({'error': 'Data tidak lengkap'}), 400
    conn = get_connection(); cursor = conn.cursor()
    query = """
        INSERT INTO chat_read_timestamps (user_id, chat_id, chat_type, last_read_timestamp)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE last_read_timestamp = %s
    """
    now = datetime.now()
    cursor.execute(query, (user_id, chat_id, chat_type, now, now))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'status': 'ok'})

# --- ENDPOINTS FILE ---
@chat_bp.route('/files/upload/private', methods=['POST'])
def upload_private_file():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang diunggah'}), 400
    file = request.files['file']
    user_id = session['user_id']
    receiver_id = request.form.get('receiver_id')
    filename = "".join(c for c in file.filename if c.isalnum() or c in ('.', '_')).rstrip()
    encrypted_filename = encrypt(filename)
    user_dir = os.path.join('files', str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    file.save(os.path.join(user_dir, filename))
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        INSERT INTO messages (user_id, receiver_id, message_type, content)
        VALUES (%s, %s, 'file', %s)
    """, (user_id, receiver_id, encrypted_filename))
    conn.commit()
    last_id = cursor.lastrowid
    cursor.execute("SELECT m.*, u.username as sender_username FROM messages m JOIN users u ON m.user_id = u.id WHERE m.id = %s", (last_id,))
    new_message = cursor.fetchone()
    cursor.close(); conn.close()
    if new_message:
        new_message['timestamp'] = new_message['timestamp'].isoformat()
        new_message['content'] = decrypt(new_message['content'])
    return jsonify({'status': True, 'message': new_message})

@chat_bp.route('/files/upload/group/<int:group_id>', methods=['POST'])
def upload_group_file(group_id):
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada file yang diunggah'}), 400
    file = request.files['file']
    user_id = session['user_id']
    filename = "".join(c for c in file.filename if c.isalnum() or c in ('.', '_')).rstrip()
    encrypted_filename = encrypt(filename)
    conn = get_connection(); cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
    if not cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'Akses ditolak'}), 403
    try:
        group_dir = os.path.join('files', f'group_{group_id}')
        os.makedirs(group_dir, exist_ok=True)
        file.save(os.path.join(group_dir, filename))
        cursor.execute("""
            INSERT INTO messages (user_id, group_id, message_type, content)
            VALUES (%s, %s, 'file', %s)
        """, (user_id, group_id, encrypted_filename))
        conn.commit()
        last_id = cursor.lastrowid
        cursor.execute("SELECT m.*, u.username as sender_username FROM messages m JOIN users u ON m.user_id = u.id WHERE m.id = %s", (last_id,))
        new_message = cursor.fetchone()
        if new_message:
            new_message['timestamp'] = new_message['timestamp'].isoformat()
            new_message['content'] = decrypt(new_message['content'])
        cursor.close(); conn.close()
        return jsonify({'status': True, 'message': new_message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/files/<path:file_path>')
def download_file(file_path):
    if 'user_id' not in session: return "Unauthorized", 401
    if '..' in file_path or file_path.startswith('/'):
        return "Invalid path", 400
    directory = os.path.abspath('files')
    try:
        return send_from_directory(directory, file_path, as_attachment=True)
    except FileNotFoundError:
        return "File not found", 404
    
def process_history_with_markers(history, user_id, chat_id, chat_type, cursor):
    processed_history = []
    last_date_str = None
    unread_marker_added = False

    cursor.execute(
        "SELECT last_read_timestamp FROM chat_read_timestamps WHERE user_id = %s AND chat_id = %s AND chat_type = %s",
        (user_id, chat_id, chat_type)
    )
    last_read = cursor.fetchone()
    
    last_read_timestamp = last_read['last_read_timestamp'] if last_read else datetime.min

    for message in history:
        current_timestamp = message['timestamp']
        current_date_str = current_timestamp.strftime('%Y-%m-%d')

        if not unread_marker_added and current_timestamp > last_read_timestamp and message['user_id'] != user_id:
            processed_history.append({'type': 'unread_separator'})
            unread_marker_added = True

        if current_date_str != last_date_str:
            processed_history.append({'type': 'date_separator', 'date': current_date_str})
            last_date_str = current_date_str
        
        message['timestamp'] = message['timestamp'].isoformat()
        if not message.get('is_deleted'):
            if message.get('content'):
                message['content'] = decrypt(message['content'])
        if message.get('replied_content'):
            message['replied_content'] = decrypt(message['replied_content'])
        
        processed_history.append(message)
    
    return processed_history

@chat_bp.route('/users/all')
def get_all_users():
    if 'user_id' not in session: return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username FROM users WHERE id != %s ORDER BY username ASC", (user_id,))
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({'users': users})