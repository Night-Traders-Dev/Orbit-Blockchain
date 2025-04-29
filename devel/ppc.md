### Enhanced Prime Stream Cipher

This project implements a custom symmetric encryption algorithm that combines dynamic S-boxes, prime number sequences, and a complex key schedule to create a robust and highly obfuscated keystream cipher. It includes full file encryption/decryption with HMAC authentication.


---

### Features

Dynamic S-Boxes: Generated from the password using SHA-256, ensuring strong key-dependent nonlinearity.

Prime Sequence Mixing: Injects a deterministic pseudo-random sequence of prime numbers into IV processing and keystream generation.

Enhanced Key Derivation: Uses PBKDF2 with 100,000 iterations to derive strong key material from the password and salt.

Authenticated Encryption: Ensures integrity and authenticity with HMAC-SHA256.

Custom Block Cipher-Like Structure: With substitution, mixing, and rotation steps for each block, echoing AES-like complexity.



---

### How It Works

1. Key Derivation

Uses PBKDF2-HMAC-SHA256 to generate 64 bytes from the password and a 16-byte random salt.

Splits derived key into:

Encryption seed (first 16 bytes)

HMAC key (last 24 bytes)



2. Prime-Based IV Enhancement

A separate 8-byte prime salt is generated.

The IV is mixed with a generated sequence of prime numbers and passed through the dynamic S-box.


3. Dynamic S-Box Generation

Based on a SHA-256 hash of the password.

Ensures every encryption session with the same password produces the same S-box.


4. Keystream Generation

A complex function combines the S-box, prime sequence, and key material to create a non-repeating, block-specific keystream.

Each block is processed with multiple layers of substitution, mixing, and bit-rotation.


5. Encryption Process

Padding is applied in PKCS#7 style.

Each block is:

XORed with the previous ciphertext block (CBC-style).

Substituted via the S-box.

XORed with the keystream.



6. Decryption Process

Uses inverse S-box and the same keystream.

Verifies HMAC to ensure ciphertext integrity before decryption.

Validates padding before removing it.



---

### Security Considerations

Confidentiality: Strong key derivation and complex, password-dependent keystream obfuscation.

Integrity: Authenticated with HMAC-SHA256.

Replay & IV Reuse Protection: Randomized salts and IV ensure ciphertext uniqueness per session.

Brute-Force Resistance: PBKDF2 slows brute-force and dictionary attacks significantly.



---

### Usage

Encrypt a File

python enhanced_prime_crypto.py encrypt <input_file> <output_file>

Decrypt a File

python enhanced_prime_crypto.py decrypt <input_file> <output_file>

You’ll be prompted for the encryption/decryption password.


---

### Requirements

Python 3.6+

No external libraries required (uses only Python standard libraries)



---

### Disclaimer

This is a custom cryptographic algorithm and has not been reviewed by professional cryptographers. It is not recommended for securing highly sensitive or critical data in production environments without formal auditing.

