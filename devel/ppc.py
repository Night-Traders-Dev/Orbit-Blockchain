import ast
import base64
import getpass
import hashlib
import hmac
import math
import os
import random
import struct
import sys
from functools import lru_cache

# ======== Core Crypto Functions ========

def is_prime(n):
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    for i in range(5, int(n**0.5) + 1, 6):
        if n % i == 0 or n % (i + 2) == 0:
            return False
    return True

@lru_cache(maxsize=32)
def generate_prime_sequence(length, seed):
    sequence = []
    current = seed
    while len(sequence) < length:
        for candidate in range(current, current + 1000):
            if is_prime(candidate):
                sequence.append(candidate)
                if len(sequence) >= length:
                    break
        current += 1000
    return sequence

def dynamic_sbox(seed: str):
    hash_digest = hashlib.sha256(seed.encode('utf-8')).digest()
    seed_int = int.from_bytes(hash_digest, byteorder='big')
    rng = random.Random(seed_int)
    sbox = list(range(256))
    rng.shuffle(sbox)
    inv_sbox = [0] * 256
    for i, val in enumerate(sbox):
        inv_sbox[val] = i
    return sbox, inv_sbox

def rotate_bits(value, rotation):
    return ((value << rotation) | (value >> (8 - rotation))) & 0xFF

def enhance_iv_with_primes(iv, primes, sbox):
    enhanced_iv = bytearray(iv)
    for i in range(len(enhanced_iv)):
        enhanced_iv[i] ^= primes[i % len(primes)] & 0xFF
        enhanced_iv[i] = sbox[enhanced_iv[i]]
    return enhanced_iv

def mix_bytes(a, b, c, d, sbox):
    a = sbox[a]
    b = sbox[(b + a) & 0xFF]
    c = sbox[(c + b) & 0xFF]
    d = sbox[(d + c) & 0xFF]
    a = rotate_bits(a, 1) ^ rotate_bits(d, 3)
    b = rotate_bits(b, 2) ^ rotate_bits(a, 1)
    c = rotate_bits(c, 3) ^ rotate_bits(b, 2)                                                                                                                                        d = rotate_bits(d, 4) ^ rotate_bits(c, 3)
    return a, b, c, d

def password_to_key_material(password, salt, iterations=100_000):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations, dklen=64)

def derive_complex_keystream(primes, length, key_material_chunk, sbox):
    seed = int.from_bytes(key_material_chunk[:8], 'big')
    keystream = bytearray(length)
    state = bytearray(16)
    for i in range(16):
        state[i] = (seed >> (i * 8)) & 0xFF if i < 8 else key_material_chunk[i]
    for _ in range(4):
        for i in range(0, 16, 4):
            state[i], state[i+1], state[i+2], state[i+3] = mix_bytes(state[i], state[i+1], state[i+2], state[i+3], sbox)
    for block_start in range(0, length, 16):
        block_end = min(block_start + 16, length)
        for i in range(16):
            prime_influence = primes[(block_start + i) % len(primes)] & 0xFF
            state[i] ^= prime_influence
            state[i] = sbox[state[i]]
        for _ in range(8):
            for i in range(0, 16, 4):
                state[i], state[i+1], state[i+2], state[i+3] = mix_bytes(state[i], state[i+1], state[i+2], state[i+3], sbox)
            for i in range(4):
                a, b, c, d = state[i], state[i+4], state[i+8], state[i+12]
                state[i], state[i+4], state[i+8], state[i+12] = mix_bytes(a, b, c, d, sbox)
            for i in range(16):
                state[i] ^= (i ^ _) & 0xFF
        for i in range(block_end - block_start):
            keystream[block_start + i] = state[i]
    return keystream

def encrypt(plaintext_bytes, password):
    pbkdf2_salt = os.urandom(16)
    prime_salt = os.urandom(8)
    iv = os.urandom(16)
    prime_salt_int = int.from_bytes(prime_salt, 'big')
    key_material = password_to_key_material(password, pbkdf2_salt)
    prime_seed = int.from_bytes(key_material[:8], 'big')
    hmac_key = key_material[40:]
    sbox, _ = dynamic_sbox(password)
    block_size = 16
    padded_length = ((len(plaintext_bytes) + block_size - 1) // block_size) * block_size
    seed = (prime_seed ^ prime_salt_int) % (1 << 32)
    primes = generate_prime_sequence(padded_length // 4 + 16, seed)
    prime_iv = enhance_iv_with_primes(iv, primes, sbox)
    keystream = derive_complex_keystream(primes, padded_length, key_material[:16], sbox)
    ciphertext = bytearray(padded_length)
    previous_block = bytearray(prime_iv)
    for block_start in range(0, padded_length, block_size):
        block_end = min(block_start + block_size, len(plaintext_bytes))
        current_block = bytearray(block_size)
        for i in range(block_start, block_end):
            current_block[i - block_start] = plaintext_bytes[i]
        padding_value = padded_length - len(plaintext_bytes)
        for i in range(block_end - block_start, block_size):
            current_block[i] = padding_value
        for i in range(block_size):
            current_block[i] ^= previous_block[i]
        for i in range(block_size):
            current_block[i] = sbox[current_block[i]]
        for i in range(block_size):
            ciphertext[block_start + i] = current_block[i] ^ keystream[block_start + i]
        previous_block = ciphertext[block_start:block_start + block_size]
    full_ciphertext = pbkdf2_salt + prime_salt + iv + struct.pack("<I", len(plaintext_bytes)) + ciphertext
    mac = hmac.new(hmac_key, full_ciphertext, hashlib.sha256).digest()
    return base64.b64encode(full_ciphertext + mac)

def decrypt(encrypted_b64, password):
    final_package = base64.b64decode(encrypted_b64)
    pbkdf2_salt = final_package[:16]
    prime_salt = final_package[16:24]
    iv = final_package[24:40]
    plaintext_length = struct.unpack("<I", final_package[40:44])[0]
    mac_received = final_package[-32:]
    ciphertext = final_package[44:-32]
    prime_salt_int = int.from_bytes(prime_salt, 'big')
    key_material = password_to_key_material(password, pbkdf2_salt)
    prime_seed = int.from_bytes(key_material[:8], 'big')
    hmac_key = key_material[40:]
    sbox, inv_sbox = dynamic_sbox(password)
    expected_mac = hmac.new(hmac_key, final_package[:-32], hashlib.sha256).digest()
    if not hmac.compare_digest(expected_mac, mac_received):
        raise ValueError("HMAC verification failed — file is corrupted or wrong password.")
    block_size = 16
    padded_length = len(ciphertext)
    seed = (prime_seed ^ prime_salt_int) % (1 << 32)
    primes = generate_prime_sequence(padded_length // 4 + 16, seed)
    prime_iv = enhance_iv_with_primes(iv, primes, sbox)
    keystream = derive_complex_keystream(primes, padded_length, key_material[:16], sbox)
    plaintext_bytes = bytearray(padded_length)
    previous_block = bytearray(prime_iv)
    for block_start in range(0, padded_length, block_size):
        block_end = min(block_start + block_size, padded_length)
        current_cipher_block = ciphertext[block_start:block_end]
        temp_block = bytearray(block_size)
        for i in range(len(current_cipher_block)):
            temp_block[i] = current_cipher_block[i] ^ keystream[block_start + i]
        for i in range(len(current_cipher_block)):
            temp_block[i] = inv_sbox[temp_block[i]]
        for i in range(len(current_cipher_block)):
            temp_value = temp_block[i] ^ previous_block[i]
            plaintext_bytes[block_start + i] = temp_value
        previous_block = bytearray(current_cipher_block)
    padding_value = plaintext_bytes[padded_length - 1]
    if padding_value > 0 and padding_value <= block_size:
        if all(plaintext_bytes[padded_length - i - 1] == padding_value for i in range(padding_value)):
            plaintext_length = padded_length - padding_value
        else:
            raise ValueError("Invalid padding detected.")
    return plaintext_bytes[:plaintext_length]

# ======== Public Key Cryptography Functions ========

def generate_prime(bits):
    while True:
        p = random.getrandbits(bits) | (1 << (bits - 1)) | 1
        if is_probably_prime(p, 10):
            return p

def is_probably_prime(n, k=40):
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0:
        return False
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    for _ in range(k):
        a = random.randint(2, n - 2)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    else:
        gcd, x, y = extended_gcd(b % a, a)
        return gcd, y - (b // a) * x, x

def mod_inverse(a, m):
    gcd, x, y = extended_gcd(a, m)
    if gcd != 1:
        raise ValueError("Modular inverse does not exist")
    else:
        return x % m

def generate_keypair(bits=2048):
    p = generate_prime(bits // 2)
    q = generate_prime(bits // 2)
    while p == q:
        q = generate_prime(bits // 2)
    n = p * q
    phi = (p - 1) * (q - 1)
    e = 65537
    while math.gcd(e, phi) != 1:
        e += 2
    d = mod_inverse(e, phi)
    return {
        'private': {'d': d, 'n': n, 'p': p, 'q': q},
        'public': {'e': e, 'n': n}
    }

def save_keypair(keypair, private_file, public_file, passphrase=None):
    private_key_data = {
        'd': keypair['private']['d'],
        'n': keypair['private']['n'],
        'p': keypair['private']['p'],
        'q': keypair['private']['q']
    }
    private_key_bytes = str(private_key_data).encode('utf-8')
    if passphrase:
        encrypted_private_key = encrypt(private_key_bytes, passphrase)
        with open(private_file, 'wb') as f:
            f.write(encrypted_private_key)
    else:
        with open(private_file, 'w') as f:
            f.write(base64.b64encode(private_key_bytes).decode('utf-8'))
    public_key_data = {
        'e': keypair['public']['e'],
        'n': keypair['public']['n']
    }
    with open(public_file, 'w') as f:
        f.write(base64.b64encode(str(public_key_data).encode('utf-8')).decode('utf-8'))

def load_public_key(public_file):
    with open(public_file, 'r') as f:
        public_key_b64 = f.read().strip()
    public_key_str = base64.b64decode(public_key_b64).decode('utf-8')
    public_key_data = ast.literal_eval(public_key_str)
    return {
        'e': public_key_data['e'],
        'n': public_key_data['n']
    }

def load_private_key(private_file, passphrase=None):
    with open(private_file, 'rb') as f:
        private_key_data = f.read()
    try:
        if passphrase:
            private_key_bytes = decrypt(private_key_data, passphrase)
            private_key_str = private_key_bytes.decode('utf-8')
        else:
            private_key_str = base64.b64decode(private_key_data).decode('utf-8')
        private_key_data = ast.literal_eval(private_key_str)
        return {
            'd': private_key_data['d'],
            'n': private_key_data['n'],
            'p': private_key_data['p'],
            'q': private_key_data['q']
        }
    except Exception as e:
        raise ValueError(f"Failed to load private key: {e}")

def rsa_encrypt(message, public_key):
    chunk_size = (public_key['n'].bit_length() // 8) - 11
    if len(message) > chunk_size:
        raise ValueError(f"Message too long for RSA encryption (max {chunk_size} bytes)")
    padded = os.urandom(8) + message
    m = int.from_bytes(padded, byteorder='big')
    c = pow(m, public_key['e'], public_key['n'])
    return c.to_bytes((c.bit_length() + 7) // 8, byteorder='big')

def rsa_decrypt(ciphertext, private_key):
    c = int.from_bytes(ciphertext, byteorder='big')
    m = pow(c, private_key['d'], private_key['n'])
    decrypted = m.to_bytes((m.bit_length() + 7) // 8, byteorder='big')
    return decrypted[8:]

def hybrid_encrypt(plaintext_bytes, recipient_public_key_file):
    symmetric_key = os.urandom(32).hex()
    encrypted_data = encrypt(plaintext_bytes, symmetric_key)
    public_key = load_public_key(recipient_public_key_file)
    encrypted_key = rsa_encrypt(symmetric_key.encode('utf-8'), public_key)
    key_length = len(encrypted_key)
    package = struct.pack("<I", key_length) + encrypted_key + encrypted_data
    return package

def hybrid_decrypt(encrypted_package, private_key_file, passphrase=None):
    key_length = struct.unpack("<I", encrypted_package[:4])[0]
    encrypted_key = encrypted_package[4:4+key_length]
    encrypted_data = encrypted_package[4+key_length:]
    private_key = load_private_key(private_key_file, passphrase)
    symmetric_key = rsa_decrypt(encrypted_key, private_key).decode('utf-8')
    decrypted_data = decrypt(encrypted_data, symmetric_key)
    return decrypted_data

SHA256_ASN1_PREFIX = bytes.fromhex(
    "3031300d060960864801650304020105000420"
)

def emsa_pkcs1_v1_5_encode(hash_bytes, em_len):
    t = SHA256_ASN1_PREFIX + hash_bytes
    if em_len < len(t) + 11:
        raise ValueError("Intended encoded message length too short")
    ps = b'\xFF' * (em_len - len(t) - 3)
    return b'\x00\x01' + ps + b'\x00' + t

def sign_message(message: bytes, private_key: dict) -> bytes:
    msg_hash = hashlib.sha256(message).digest()
    k = (private_key['n'].bit_length() + 7) // 8
    em = emsa_pkcs1_v1_5_encode(msg_hash, k)
    m_int = int.from_bytes(em, 'big')
    sig_int = pow(m_int, private_key['d'], private_key['n'])
    return sig_int.to_bytes(k, 'big')

def verify_signature(message: bytes, signature: bytes, public_key: dict) -> bool:
    try:
        sig_int = int.from_bytes(signature, 'big')
        m_int = pow(sig_int, public_key['e'], public_key['n'])
        k = (public_key['n'].bit_length() + 7) // 8
        em = m_int.to_bytes(k, 'big')
        msg_hash = hashlib.sha256(message).digest()
        expected_em = emsa_pkcs1_v1_5_encode(msg_hash, k)
        return em == expected_em
    except Exception as e:
        print(f"Verification error: {e}")
        return False


# ======== CLI Handling ========

def encrypt_file(input_file, output_file, password):
    with open(input_file, 'rb') as f:
        plaintext = f.read()
    encrypted = encrypt(plaintext, password)
    with open(output_file, 'wb') as f:
        f.write(encrypted)
    print(f"Encrypted {input_file} -> {output_file}")

def decrypt_file(input_file, output_file, password):
    with open(input_file, 'rb') as f:
        encrypted = f.read()
    decrypted = decrypt(encrypted, password)
    with open(output_file, 'wb') as f:
        f.write(decrypted)
    print(f"Decrypted {input_file} -> {output_file}")

def generate_keys(private_key_file, public_key_file, bits=2048):
    print(f"Generating {bits}-bit RSA key pair...")
    keypair = generate_keypair(bits)
    use_passphrase = input("Secure private key with a passphrase? (y/n): ").lower() == 'y'
    passphrase = None
    if use_passphrase:
        passphrase = getpass.getpass(prompt="Enter passphrase for private key: ")
        passphrase_confirm = getpass.getpass(prompt="Confirm passphrase: ")
        if passphrase != passphrase_confirm:
            print("Error: Passphrases do not match")
            return
    save_keypair(keypair, private_key_file, public_key_file, passphrase)
    print(f"Keys generated and saved to {private_key_file} and {public_key_file}")

def pk_encrypt_file(input_file, output_file, public_key_file):
    with open(input_file, 'rb') as f:
        plaintext = f.read()
    encrypted = hybrid_encrypt(plaintext, public_key_file)
    with open(output_file, 'wb') as f:
        f.write(encrypted)
    print(f"Encrypted {input_file} -> {output_file} using public key from {public_key_file}")

def pk_decrypt_file(input_file, output_file, private_key_file):
    with open(input_file, 'rb') as f:
        encrypted = f.read()
    passphrase = None
    try:
        load_private_key(private_key_file)
    except:
        passphrase = getpass.getpass(prompt="Enter passphrase for private key: ")
    decrypted = hybrid_decrypt(encrypted, private_key_file, passphrase)
    with open(output_file, 'wb') as f:
        f.write(decrypted)
    print(f"Decrypted {input_file} -> {output_file} using private key from {private_key_file}")


def print_usage():
    print("Usage:")
    print("  encrypt <input_file> <output_file>")
    print("  decrypt <input_file> <output_file>")
    print("  genkeys <private_key_file> <public_key_file> [bits]")
    print("  pkencrypt <input_file> <output_file> <public_key_file>")
    print("  pkdecrypt <input_file> <output_file> <private_key_file>")
    print("  sign <input_file> <signature_output_file> <private_key_file>")
    print("  verify <input_file> <signature_file> <public_key_file>")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    mode = sys.argv[1]

    try:
        if mode == 'encrypt' and len(sys.argv) == 4:
            input_file = sys.argv[2]
            output_file = sys.argv[3]
            password = getpass.getpass(prompt="Enter password: ")
            encrypt_file(input_file, output_file, password)

        elif mode == 'decrypt' and len(sys.argv) == 4:
            input_file = sys.argv[2]
            output_file = sys.argv[3]
            password = getpass.getpass(prompt="Enter password: ")
            decrypt_file(input_file, output_file, password)

        elif mode == 'genkeys' and len(sys.argv) >= 4:
            private_key_file = sys.argv[2]
            public_key_file = sys.argv[3]
            bits = int(sys.argv[4]) if len(sys.argv) > 4 else 2048
            generate_keys(private_key_file, public_key_file, bits)

        elif mode == 'pkencrypt' and len(sys.argv) == 5:
            input_file = sys.argv[2]
            output_file = sys.argv[3]
            public_key_file = sys.argv[4]
            pk_encrypt_file(input_file, output_file, public_key_file)

        elif mode == 'pkdecrypt' and len(sys.argv) == 5:
            input_file = sys.argv[2]
            output_file = sys.argv[3]
            private_key_file = sys.argv[4]
            pk_decrypt_file(input_file, output_file, private_key_file)

        elif mode == 'sign' and len(sys.argv) == 5:
            input_file = sys.argv[2]
            signature_file = sys.argv[3]
            private_key_file = sys.argv[4]
            with open(input_file, 'rb') as f:
                message = f.read()
            private_key = load_private_key(private_key_file)
            signature = sign_message(message, private_key)
            with open(signature_file, 'wb') as f:
                f.write(signature)
            print("Message signed successfully.")

        elif mode == 'verify' and len(sys.argv) == 5:
            input_file = sys.argv[2]
            signature_file = sys.argv[3]
            public_key_file = sys.argv[4]
            with open(input_file, 'rb') as f:
                message = f.read()
            with open(signature_file, 'rb') as f:
                signature = f.read()
            public_key = load_public_key(public_key_file)
            if verify_signature(message, signature, public_key):
                print("Signature is valid.")
            else:
                print("Signature is INVALID.")

        else:
            print_usage()
            sys.exit(1)

    except Exception as e:
        print("Error:", e)
        sys.exit(1)