## Enhanced Prime Crypto

A hybrid cryptographic utility that combines symmetric and asymmetric encryption using advanced techniques such as dynamic S-boxes, prime-seeded keystreams, and RSA public-key infrastructure.

## Features

Symmetric encryption using a custom stream cipher

Dynamic key and IV handling based on SHA-256, PBKDF2, and prime sequences

Authenticated encryption with HMAC-SHA256

Asymmetric RSA encryption for hybrid key exchange

Secure file encryption/decryption and RSA key management

CLI interface for convenience


## Requirements

Python 3.6+


## Usage

# Symmetric Encryption

```python
python enhanced_prime_crypto.py encrypt <input_file> <output_file>
```

# Symmetric Decryption

```python
python enhanced_prime_crypto.py decrypt <input_file> <output_file>
```

# Generate RSA Keypair

```python
python enhanced_prime_crypto.py genkeys <private_key_file> <public_key_file> [bits]
```

# Public Key Encryption

```python
python enhanced_prime_crypto.py pkencrypt <input_file> <output_file> <recipient_public_key>
```

# Public Key Decryption

```python
python enhanced_prime_crypto.py pkdecrypt <input_file> <output_file> <private_key>
```

## Key Concepts

# Prime-Seeded Keystream

A stream cipher based on a sequence of prime numbers derived from a password-derived seed and enhanced with a dynamic S-box.

# Hybrid Encryption

Combines RSA to encrypt a symmetric key which is then used to encrypt the data. Ensures both confidentiality and secure key exchange.

# HMAC Authentication

Each ciphertext is appended with a MAC computed from part of the password-derived key material, verifying data integrity and authenticity.

## Notes

Key generation uses 2048-bit RSA by default.

Encrypted private keys can be protected with a user passphrase.

The encryption scheme is experimental and not audited for production use.


## License

MIT License

```
Crafted with security and curiosity in mind.
```
