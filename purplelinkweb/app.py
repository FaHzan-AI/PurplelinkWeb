import os
from flask import Flask, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from routes.auth import auth_bp
from routes.chat import chat_bp
from datetime import timedelta
from services.database import get_connection
from services.encryption_service import encrypt, decrypt
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-for-dev')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY'] = True

socketio = SocketIO(app)

app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)

online_users = {}

@socketio.on('connect')
def handle_connect():
    user_id = session.get('user_id')
    if not user_id:
        return

    online_users[user_id] = request.sid
    emit('user_status_change', {'user_id': user_id, 'status': 'online'}, broadcast=True)
    emit('online_users_list', {'users': list(online_users.keys())})

    join_room(user_id)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT group_id FROM group_members WHERE user_id = %s", (user_id,))
    groups = cursor.fetchall()
    for group in groups:
        join_room(f"group_{group['group_id']}")
    cursor.close()
    conn.close()

@socketio.on('disconnect')
def handle_disconnect():
    user_id = None
    for uid, sid in list(online_users.items()):
        if sid == request.sid:
            user_id = uid
            del online_users[user_id]
            break
    
    if user_id:
        emit('user_status_change', {'user_id': user_id, 'status': 'offline'}, broadcast=True)

def save_and_get_message(query, params):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    last_id = cursor.lastrowid
    conn.commit()
    
    fetch_query = """
        SELECT m.*, u.username as sender_username,
               replied.content as replied_content,
               replied_user.username as replied_username
        FROM messages m
        JOIN users u ON m.user_id = u.id
        LEFT JOIN messages replied ON m.reply_to_message_id = replied.id
        LEFT JOIN users replied_user ON replied.user_id = replied_user.id
        WHERE m.id = %s
    """
    cursor.execute(fetch_query, (last_id,))
    new_message = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if new_message:
        if new_message.get('content') and not new_message.get('is_deleted'):
            new_message['content'] = decrypt(new_message['content'])
        if new_message.get('replied_content'):
            new_message['replied_content'] = decrypt(new_message['replied_content'])
            
    return new_message

@socketio.on('chat_message')
def handle_chat_message(data):
    sender_id = session.get('user_id')
    receiver_id = data.get('receiver_id')
    message_content = data.get('message')
    reply_to = data.get('reply_to_message_id')
    
    if not all([sender_id, receiver_id, message_content]): return

    encrypted_content = encrypt(message_content)
    query = "INSERT INTO messages (user_id, receiver_id, content, reply_to_message_id) VALUES (%s, %s, %s, %s)"
    new_message = save_and_get_message(query, (sender_id, receiver_id, encrypted_content, reply_to))
    
    if new_message:
        message_data = {**new_message, 'timestamp': new_message['timestamp'].isoformat()}
        emit('new_message', message_data, room=receiver_id)
        emit('new_message', message_data, room=sender_id)

@socketio.on('group_message')
def handle_group_message(data):
    sender_id = session.get('user_id')
    group_id = data.get('group_id')
    message_content = data.get('message')
    reply_to = data.get('reply_to_message_id')

    if not all([sender_id, group_id, message_content]): return
    
    encrypted_content = encrypt(message_content)
    query = "INSERT INTO messages (user_id, group_id, content, reply_to_message_id) VALUES (%s, %s, %s, %s)"
    new_message = save_and_get_message(query, (sender_id, group_id, encrypted_content, reply_to))

    if new_message:
        message_data = {**new_message, 'timestamp': new_message['timestamp'].isoformat()}
        emit('new_group_message', message_data, room=f"group_{group_id}")

@socketio.on('delete_message')
def handle_delete_message(data):
    user_id = session.get('user_id')
    message_id = data.get('message_id')
    if not all([user_id, message_id]): return

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, group_id, receiver_id FROM messages WHERE id = %s", (message_id,))
    message = cursor.fetchone()

    if message and message['user_id'] == user_id:
        cursor.execute("UPDATE messages SET content = %s, is_deleted = 1 WHERE id = %s", (encrypt('Pesan ini telah dihapus'), message_id))
        conn.commit()
        
        payload = {'id': message_id}
        if message.get('group_id'):
            emit('message_deleted', payload, room=f"group_{message['group_id']}")
        else:
            emit('message_deleted', payload, room=message['user_id'])
            emit('message_deleted', payload, room=message['receiver_id'])
    
    cursor.close()
    conn.close()

@socketio.on('edit_message')
def handle_edit_message(data):
    user_id = session.get('user_id')
    message_id = data.get('message_id')
    new_content = data.get('new_content')
    if not all([user_id, message_id, new_content]): return

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, group_id, receiver_id FROM messages WHERE id = %s AND is_deleted = 0", (message_id,))
    message = cursor.fetchone()

    if message and message['user_id'] == user_id:
        encrypted_content = encrypt(new_content)
        cursor.execute("UPDATE messages SET content = %s, is_edited = 1 WHERE id = %s", (encrypted_content, message_id))
        conn.commit()
        
        payload = {'id': message_id, 'content': new_content, 'is_edited': True}
        if message.get('group_id'):
            emit('message_updated', payload, room=f"group_{message['group_id']}")
        else:
            emit('message_updated', payload, room=message['user_id'])
            emit('message_updated', payload, room=message['receiver_id'])

    cursor.close()
    conn.close()

@socketio.on('broadcast_file_message')
def handle_file_broadcast(data):
    message = data.get('message')
    if not message:
        return
    
    if message.get('group_id'):
        emit('new_group_message', message, room=f"group_{message['group_id']}")
    elif message.get('receiver_id'):
        emit('new_message', message, room=message['user_id'])
        emit('new_message', message, room=message['receiver_id'])
        
@socketio.on('add_member_to_group')
def handle_add_member(data):
    admin_id = session.get('user_id')
    user_to_add_id = data.get('user_id')
    group_id = data.get('group_id')
    if not all([admin_id, user_to_add_id, group_id]): return
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT role FROM group_members WHERE user_id = %s AND group_id = %s", (admin_id, group_id))
        admin = cursor.fetchone()
        if not admin or admin['role'] not in ['creator', 'admin']:
            emit('add_member_failed', {'error': 'Hanya admin yang dapat menambah anggota.'})
            return
        cursor.execute("INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, 'member')", (group_id, user_to_add_id))
        conn.commit()
        emit('add_member_success')
        cursor.execute("SELECT g.id, g.name, g.creator_id FROM groups g WHERE g.id = %s", (group_id,))
        group_data = cursor.fetchone()
        
        # Add the new user to the socket room
        new_user_sid = online_users.get(user_to_add_id)
        if new_user_sid:
            join_room(f"group_{group_id}", sid=new_user_sid)

        emit('added_to_group', group_data, room=user_to_add_id)
        emit('member_list_changed', {'group_id': group_id}, room=f"group_{group_id}")
    except Exception as e:
        conn.rollback()
        if 'Duplicate entry' in str(e): emit('add_member_failed', {'error': 'Pengguna ini sudah menjadi anggota.'})
        else: emit('add_member_failed', {'error': 'Terjadi kesalahan di server.'})
    finally:
        cursor.close()
        conn.close()
        
@socketio.on('promote_to_admin')
def handle_promote_admin(data):
    promoter_id = session.get('user_id')
    user_to_promote_id = data.get('user_id')
    group_id = data.get('group_id')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT role FROM group_members WHERE user_id = %s AND group_id = %s", (promoter_id, group_id))
    promoter = cursor.fetchone()

    if promoter and promoter['role'] == 'creator':
        cursor.execute("UPDATE group_members SET role = 'admin' WHERE user_id = %s AND group_id = %s", (user_to_promote_id, group_id))
        conn.commit()
        emit('member_list_changed', {'group_id': group_id}, room=f"group_{group_id}")
    cursor.close()
    conn.close()

@socketio.on('remove_from_group')
def handle_remove_from_group(data):
    remover_id = session.get('user_id')
    user_to_remove_id = data.get('user_id')
    group_id = data.get('group_id')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT role FROM group_members WHERE user_id = %s AND group_id = %s", (remover_id, group_id))
    remover = cursor.fetchone()

    cursor.execute("SELECT role FROM group_members WHERE user_id = %s AND group_id = %s", (user_to_remove_id, group_id))
    user_to_remove = cursor.fetchone()

    if remover and remover['role'] in ['creator', 'admin'] and user_to_remove and user_to_remove['role'] != 'creator':
        cursor.execute("DELETE FROM group_members WHERE user_id = %s AND group_id = %s", (user_to_remove_id, group_id))
        conn.commit()
        
        removed_user_sid = online_users.get(user_to_remove_id)
        if removed_user_sid:
            emit('you_were_removed', {'group_id': group_id, 'group_name': 'grup'}, room=removed_user_sid)
            leave_room(f"group_{group_id}", sid=removed_user_sid)

        emit('member_list_changed', {'group_id': group_id}, room=f"group_{group_id}")

    cursor.close()
    conn.close()

@socketio.on('leave_group')
def handle_leave_group(data):
    user_id = session.get('user_id')
    group_id = data.get('group_id')
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT role FROM group_members WHERE user_id = %s AND group_id = %s", (user_id, group_id))
        user_leaving = cursor.fetchone()

        if not user_leaving:
            return # User not in group

        # If the creator is leaving
        if user_leaving['role'] == 'creator':
            # Find the next member to promote (oldest member)
            cursor.execute("SELECT user_id FROM group_members WHERE group_id = %s AND role != 'creator' ORDER BY id ASC LIMIT 1", (group_id,))
            next_admin = cursor.fetchone()

            if next_admin:
                # Promote the next member to be the new creator
                cursor.execute("UPDATE group_members SET role = 'creator' WHERE user_id = %s AND group_id = %s", (next_admin['user_id'], group_id))
                # Update the creator_id in the main groups table
                cursor.execute("UPDATE groups SET creator_id = %s WHERE id = %s", (next_admin['user_id'], group_id))
                # Now, delete the old creator
                cursor.execute("DELETE FROM group_members WHERE user_id = %s AND group_id = %s", (user_id, group_id))
            else:
                # If the creator is the last member, delete the group
                cursor.execute("DELETE FROM groups WHERE id = %s", (group_id,))
                cursor.execute("DELETE FROM group_members WHERE group_id = %s", (group_id,))
                # Also delete messages associated with the group
                cursor.execute("DELETE FROM messages WHERE group_id = %s", (group_id,))
        else:
            # If a regular member or admin leaves
            cursor.execute("DELETE FROM group_members WHERE user_id = %s AND group_id = %s", (user_id, group_id))
        
        conn.commit()
        
        leave_room(f"group_{group_id}")
        emit('leave_group_success', {'group_id': group_id})
        emit('member_list_changed', {'group_id': group_id}, room=f"group_{group_id}")

    except Exception as e:
        conn.rollback()
        print(f"Error during leave group: {e}")
    finally:
        cursor.close()
        conn.close()


@socketio.on('clear_history')
def handle_clear_history(data):
    user_id = session.get('user_id')
    chat_type = data.get('chat_type')
    chat_id = data.get('chat_id')

    if not all([user_id, chat_type, chat_id]) or chat_type != 'private':
        return

    conn = get_connection()
    cursor = conn.cursor()
    try:
        update_query = """
            UPDATE messages
            SET deleted_by_user_id_1 = %s
            WHERE ((user_id = %s AND receiver_id = %s) OR (user_id = %s AND receiver_id = %s))
            AND deleted_by_user_id_1 IS NULL
        """
        cursor.execute(update_query, (user_id, user_id, chat_id, chat_id, user_id))

        if cursor.rowcount == 0:
            update_query_2 = """
                UPDATE messages
                SET deleted_by_user_id_2 = %s
                WHERE ((user_id = %s AND receiver_id = %s) OR (user_id = %s AND receiver_id = %s))
                AND deleted_by_user_id_2 IS NULL
            """
            cursor.execute(update_query_2, (user_id, user_id, chat_id, chat_id, user_id))

        conn.commit()
        emit('history_cleared', {'chat_type': 'private', 'chat_id': chat_id}, room=user_id)
    except Exception as e:
        conn.rollback()
        print(f"Error clearing history: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)