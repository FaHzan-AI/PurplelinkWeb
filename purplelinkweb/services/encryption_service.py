from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64
import os

# Kunci harus 16, 24, atau 32 byte. Gunakan 32 byte (AES-256) untuk keamanan yang lebih baik.
# Ambil kunci dari environment variable untuk keamanan.
# Inilah baris yang diperbaiki, dengan kunci default yang panjangnya sudah benar (32 byte).
ENCRYPTION_KEY = os.environ.get('DATABASE_ENCRYPTION_KEY', 'kunci_dev_default_harus_32_byte!').encode('utf-8')

# Pastikan kunci memiliki panjang yang valid
if len(ENCRYPTION_KEY) not in [16, 24, 32]:
    raise ValueError("Kunci enkripsi harus memiliki panjang 16, 24, atau 32 byte.")

def encrypt(plain_text):
    """
    Mengenkripsi teks menggunakan AES CFB mode.
    IV (Initialization Vector) digabungkan dengan ciphertext dan di-encode ke Base64.
    """
    if plain_text is None:
        return None
    
    # Buat cipher dengan kunci yang diberikan dan IV acak
    iv = get_random_bytes(AES.block_size)
    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CFB, iv=iv)
    
    # Enkripsi pesan
    encrypted_bytes = cipher.encrypt(plain_text.encode('utf-8'))
    
    # Gabungkan IV dan ciphertext, lalu encode ke Base64 untuk penyimpanan yang aman
    return base64.b64encode(iv + encrypted_bytes).decode('utf-8')

def decrypt(encrypted_text_b64):
    """
    Mendekripsi teks yang telah dienkripsi dengan fungsi encrypt di atas.
    """
    if encrypted_text_b64 is None:
        return None
    
    try:
        # Decode dari Base64
        encrypted_data = base64.b64decode(encrypted_text_b64)
        
        # Ekstrak IV dari data yang ter-decode
        iv = encrypted_data[:AES.block_size]
        
        # Buat cipher dengan kunci yang sama dan IV yang diekstrak
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CFB, iv=iv)
        
        # Dekripsi sisa datanya
        decrypted_bytes = cipher.decrypt(encrypted_data[AES.block_size:])
        
        return decrypted_bytes.decode('utf-8')
    except (ValueError, KeyError, base64.binascii.Error):
        # Jika terjadi error saat dekripsi (misal: data korup atau bukan base64)
        # Kembalikan pesan error atau teks aslinya agar aplikasi tidak crash
        return "[Pesan tidak dapat didekripsi]"