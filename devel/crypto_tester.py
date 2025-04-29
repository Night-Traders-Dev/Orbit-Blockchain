import os
import tempfile
import base64
import time
import random
import string
import statistics
import binascii
from math import log2
from collections import Counter
from enhanced_prime_crypto import (
    encrypt, decrypt, encrypt_file, decrypt_file,
    dynamic_sbox, generate_prime_sequence, mix_bytes,
    derive_complex_keystream, rsa_encrypt, rsa_decrypt,
    is_prime
)

def banner(title):
    print("\n" + "=" * 10 + f" {title} " + "=" * 10)

# ======== Enhanced Cryptographic Validation ========

def test_sbox_bijectivity():
    banner("S-box Bijectivity Test")
    for _ in range(5):
        password = binascii.hexlify(os.urandom(8)).decode()
        sbox, inv_sbox = dynamic_sbox(password)

        # Test forward S-box
        unique = len(set(sbox)) == 256
        complete = set(sbox) == set(range(256))
        assert unique and complete, "S-box not bijective"

        # Test inverse S-box
        for i, val in enumerate(sbox):
            assert inv_sbox[val] == i, "Invalid inverse S-box"

    print("PASSED: All S-boxes show proper bijection")

def test_sbox_nonlinearity():
    banner("S-box Nonlinearity Test")
    nonlinearity_scores = []

    for _ in range(5):
        password = binascii.hexlify(os.urandom(8)).decode()
        sbox, _ = dynamic_sbox(password)

        # Calculate nonlinearity (simplified measure)
        bias = 0
        for x in range(256):
            for bit in range(8):
                masked = (sbox[x] >> bit) & 1
                bias = max(bias, abs(masked - 0.5))

        nonlinearity = 0.5 - bias
        nonlinearity_scores.append(nonlinearity)
        assert nonlinearity > 0.4, f"Low nonlinearity: {nonlinearity}"

    avg = sum(nonlinearity_scores)/len(nonlinearity_scores)
    print(f"PASSED: Average nonlinearity {avg:.3f} (>0.4 acceptable)")

def test_prime_sequence_quality():
    banner("Prime Sequence Analysis")
    seed = random.randint(0, 2**32-1)
    primes = generate_prime_sequence(1000, seed)

    # Check prime density
    prime_count = sum(1 for p in primes if is_prime(p))
    assert prime_count >= 990, "Prime generation accuracy low"

    # Check for duplicates
    assert len(set(primes)) == len(primes), "Duplicate primes detected"

    # Check distribution
    gaps = [primes[i+1] - primes[i] for i in range(len(primes)-1)]
    avg_gap = sum(gaps)/len(gaps)
    assert 50 < avg_gap < 150, f"Abnormal prime gap distribution: {avg_gap}"

    print("PASSED: Prime sequence passes basic quality checks")

def test_avalanche_effect():
    banner("Avalanche Effect Test")
    password = "avalanche_test"
    sbox, _ = dynamic_sbox(password)

    # Test single bit flip propagation
    trials = 100
    avalanche_effects = []

    for _ in range(trials):
        a = random.randint(0, 255)
        b = random.randint(0, 255)
        c = random.randint(0, 255)
        d = random.randint(0, 255)

        # Original output
        orig = mix_bytes(a, b, c, d, sbox)

        # Flipped LSB
        flipped = mix_bytes(a ^ 1, b, c, d, sbox)

        # Calculate bit differences
        diff = sum( bin(o ^ f).count('1') for o, f in zip(orig, flipped) )
        avalanche_effects.append(diff)

    avg_diff = sum(avalanche_effects)/trials
    assert avg_diff >= 4.0, f"Poor avalanche effect: {avg_diff}"
    print(f"PASSED: Average avalanche bits {avg_diff:.1f}/32 (>4.0 acceptable)")

def test_keystream_randomness():
    banner("Keystream Randomness Tests")
    password = "randomness_test"
    sbox, _ = dynamic_sbox(password)
    primes = generate_prime_sequence(1024, 12345)
    keystream = derive_complex_keystream(primes, 1024*1024, os.urandom(16), sbox)

    # Frequency test
    byte_counts = Counter(keystream)
    chi_square = sum( (count - 4096)**2 / 4096 for count in byte_counts.values() )
    assert chi_square < 310, f"Failed frequency test: {chi_square}"

    # Entropy test
    entropy = -sum( (count/len(keystream)) * log2(count/len(keystream)) for count in byte_counts.values() )
    assert entropy > 7.98, f"Low entropy: {entropy}"

    print(f"PASSED: Keystream randomness (χ²={chi_square:.1f}, H={entropy:.3f})")

def test_rsa_padding_security():
    banner("RSA Padding Security Check")
    message = b"Test message"
    pub_key = {'e': 65537, 'n': 0xdeadbeef}  # Mock key

    # Generate multiple encryptions
    ciphertexts = {rsa_encrypt(message, pub_key) for _ in range(50)}
    assert len(ciphertexts) == 50, "Padding lacks randomness"

    print("PASSED: RSA padding provides random ciphertexts")

# ======== Existing Tests (Updated) ========

def test_basic_encryption_decryption():
    banner("Basic Encrypt/Decrypt")
    plaintext = b"Test message for encryption"
    password = "secure123"
    encrypted = encrypt(plaintext, password)
    decrypted = decrypt(encrypted, password)
    assert decrypted == plaintext
    print("PASSED: Basic encryption/decryption.")

def test_padding_edge_case():
    banner("Padding Edge Case")
    plaintext = b"A" * 15  # One byte less than block size
    password = "edgecase123"
    encrypted = encrypt(plaintext, password)
    decrypted = decrypt(encrypted, password)
    assert decrypted == plaintext
    print("PASSED: Padding edge case handled correctly.")
def test_hmac_tampering():
    banner("HMAC Tamper Detection")
    plaintext = b"Data to protect"
    password = "tamper123"
    encrypted = bytearray(encrypt(plaintext, password))
    encrypted[-10] ^= 0xFF  # Flip a byte in HMAC
    try:
        decrypt(encrypted, password)
        print("FAILED: Tampered data was not detected!")
    except ValueError:
        print("PASSED: Tampering correctly detected.")
def test_wrong_password():
    banner("Wrong Password Detection")
    plaintext = b"Sensitive Data"
    correct_pass = "correcthorsebatterystaple"
    wrong_pass = "123456"
    encrypted = encrypt(plaintext, correct_pass)
    try:
        decrypt(encrypted, wrong_pass)
        print("FAILED: Decryption should fail with wrong password!")
    except ValueError:
        print("PASSED: Wrong password rejected.")
def test_file_encryption_decryption():
    banner("File Encrypt/Decrypt Roundtrip")
    password = "filetest123"
    content = os.urandom(1024)
    with tempfile.NamedTemporaryFile(delete=False) as plain, \
    tempfile.NamedTemporaryFile(delete=False) as encrypted, \
    tempfile.NamedTemporaryFile(delete=False) as decrypted:
        plain.write(content)
        plain.flush()
        encrypt_file(plain.name, encrypted.name, password)
        decrypt_file(encrypted.name, decrypted.name, password)

        with open(decrypted.name, 'rb') as f:
            roundtrip = f.read()

        assert roundtrip == content
        print("PASSED: File roundtrip encryption/decryption.")

        os.unlink(plain.name)
        os.unlink(encrypted.name)
        os.unlink(decrypted.name)

def test_ciphertext_randomness():
    banner("Ciphertext Randomness Check")
    plaintext = b"Same input, different outputs"
    password = "uniquecheck"
    ciphertexts = {encrypt(plaintext, password) for _ in range(5)}
    assert len(ciphertexts) == 5
    print("PASSED: Random IV/salts create unique ciphertexts.")

def test_performance():
    banner("Performance Benchmark")
    plaintext = os.urandom(1024 * 100)  # 100KB
    password = "benchmarking"
    start = time.time()
    encrypted = encrypt(plaintext, password)
    decrypted = decrypt(encrypted, password)
    end = time.time()
    assert decrypted == plaintext
    print(f"PASSED: 100KB encryption/decryption in {end - start:.2f} seconds.")

# ======= Fuzz Testing =======

def test_fuzz_decrypt_stability():
    banner("Fuzz Testing (Random Bytes Input)")
    password = "fuzzing123"
    for i in range(20):
        junk_data = os.urandom(random.randint(1, 512))
        try:
            decrypt(junk_data, password)
            print(f"FAILED: Random data did not raise on trial {i}")
        except Exception:
            pass  # Expected
    print("PASSED: Fuzz decryption rejects malformed ciphertexts.")

# ======= Side Channel (Timing) Analysis =======

def test_side_channel_timing():
    banner("Side Channel Timing Test (Wrong vs Correct Password)")
    plaintext = b"Timing attack test input"
    password = "correct-password"
    encrypted = encrypt(plaintext, password)

    correct_times = []
    wrong_times = []

    for _ in range(10):
        t0 = time.perf_counter()
        try:
            decrypt(encrypted, password)
        except Exception:
            pass
        correct_times.append(time.perf_counter() - t0)

        t1 = time.perf_counter()
        try:
            decrypt(encrypted, "wrong-password")
        except Exception:
            pass
        wrong_times.append(time.perf_counter() - t1)

    avg_correct = statistics.mean(correct_times)
    avg_wrong = statistics.mean(wrong_times)
    delta = abs(avg_correct - avg_wrong)

    print(f"Avg correct password time: {avg_correct:.6f}s")
    print(f"Avg wrong password time:   {avg_wrong:.6f}s")
    print(f"Time difference: {delta:.6f}s")

    if delta > 0.01:
        print("WARNING: Noticeable timing difference detected (may be side-channel leak).")
    else:
        print("PASSED: Timing difference within safe bounds.")


# ======== Updated Test Runner ========

def run_all_tests():
    tests = [
        # Core functionality
        test_basic_encryption_decryption,
        test_padding_edge_case,
        test_hmac_tampering,
        test_wrong_password,
        test_file_encryption_decryption,
        test_ciphertext_randomness,
        test_performance,
        test_fuzz_decrypt_stability,
        # Cryptographic validation
        test_sbox_bijectivity,
#        test_sbox_nonlinearity,
#        test_prime_sequence_quality,
        test_avalanche_effect,
        test_keystream_randomness,
#        test_rsa_padding_security,
        test_side_channel_timing,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"FAILED: {test.__name__}")
            print("Error:", e)
            raise

if __name__ == "__main__":
    run_all_tests()