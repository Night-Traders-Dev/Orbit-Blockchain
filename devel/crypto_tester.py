import os
import tempfile
import base64
import time
import random
import string
import statistics
from enhanced_prime_crypto import encrypt, decrypt, encrypt_file, decrypt_file

def banner(title):
    print("\n" + "=" * 10 + f" {title} " + "=" * 10)

# ======= Functional & Security Tests =======

def test_basic_encryption_decryption():
    banner("Basic Encrypt/Decrypt")
    plaintext = b"Test message for encryption"
    password = "secure123"
    encrypted = encrypt(plaintext, password)
    decrypted = decrypt(encrypted, password)
    assert decrypted == plaintext
    print("PASSED: Basic encryption/decryption.")                                                                                                                                                                                                                                                                                                                 def test_padding_edge_case():                                                                                                                                                        banner("Padding Edge Case")                                                                                                                                                      plaintext = b"A" * 15  # One byte less than block size
    password = "edgecase123"                                                                                                                                                         encrypted = encrypt(plaintext, password)                                                                                                                                         decrypted = decrypt(encrypted, password)                                                                                                                                         assert decrypted == plaintext
    print("PASSED: Padding edge case handled correctly.")                                                                                                                                                                                                                                                                                                         def test_hmac_tampering():                                                                                                                                                           banner("HMAC Tamper Detection")                                                                                                                                                  plaintext = b"Data to protect"
    password = "tamper123"                                                                                                                                                           encrypted = bytearray(encrypt(plaintext, password))                                                                                                                              encrypted[-10] ^= 0xFF  # Flip a byte in HMAC
    try:
        decrypt(encrypted, password)
        print("FAILED: Tampered data was not detected!")
    except ValueError:
        print("PASSED: Tampering correctly detected.")                                                                                                                           
def test_wrong_password():                                                                                                                                                           banner("Wrong Password Detection")                                                                                                                                               plaintext = b"Sensitive Data"                                                                                                                                                    correct_pass = "correcthorsebatterystaple"                                                                                                                                       wrong_pass = "123456"                                                                                                                                                            encrypted = encrypt(plaintext, correct_pass)                                                                                                                                     try:                                                                                                                                                                                 decrypt(encrypted, wrong_pass)                                                                                                                                                   print("FAILED: Decryption should fail with wrong password!")                                                                                                                 except ValueError:                                                                                                                                                                   print("PASSED: Wrong password rejected.")                                                                                                                                                                                                                                                                                                                 def test_file_encryption_decryption():                                                                                                                                               banner("File Encrypt/Decrypt Roundtrip")                                                                                                                                         password = "filetest123"                                                                                                                                                         content = os.urandom(1024)  # 1KB of random data                                                                                                                                                                                                                                                                                                                  with tempfile.NamedTemporaryFile(delete=False) as plain, \                                                                                                                            tempfile.NamedTemporaryFile(delete=False) as encrypted, \                                                                                                                        tempfile.NamedTemporaryFile(delete=False) as decrypted:                                                                                                                                                                                                                                                                                                          plain.write(content)                                                                                                                                                             plain.flush()                                                                                                                                                                                                                                                                                                                                                     encrypt_file(plain.name, encrypted.name, password)                                                                                                                               decrypt_file(encrypted.name, decrypted.name, password)

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

# ======= Test Runner =======

def run_all_tests():
    tests = [
        test_basic_encryption_decryption,
        test_padding_edge_case,
        test_hmac_tampering,
        test_wrong_password,
        test_file_encryption_decryption,
        test_ciphertext_randomness,
        test_performance,
        test_fuzz_decrypt_stability,
        test_side_channel_timing,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"FAILED: {test.__name__}")
            print("Error:", e)

if __name__ == "__main__":
    run_all_tests()