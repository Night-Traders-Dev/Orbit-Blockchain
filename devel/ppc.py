import base64
import getpass
import hashlib
import hmac
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
    c = rotate_bits(c, 3) ^ rotate_bits(b, 2)
    d = rotate_bits(d, 4) ^ rotate_bits(c, 3)
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

def print_usage():
    print("Usage:")
    print("  Encrypt: python enhanced_prime_crypto.py encrypt <input_file> <output_file>")
    print("  Decrypt: python enhanced_prime_crypto.py decrypt <input_file> <output_file>")

if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] not in ('encrypt', 'decrypt'):
        print_usage()
        sys.exit(1)

    mode = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3]
    password = getpass.getpass(prompt="Enter password: ")

    try:
        if mode == 'encrypt':
            encrypt_file(input_file, output_file, password)
        else:
            decrypt_file(input_file, output_file, password)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)