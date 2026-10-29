import time
from main import generate_rsa_keys, rsa_encrypt, rsa_decrypt

p, q, n, phi, e, d = generate_rsa_keys(31)

test_cases = [
    "HELLO",
    "RSA CIPHER TEST",
    "АЛГОРИТМ RSA 2026",
    "Information Security ICIT",
    "1234567890!@#$%^&*()",
    "Short",
    "Длинная тестовая фраза для проверки блочного разбиения",
    "A",
    "ASCII & UTF-8 compatibility test",
    "СИБИРСКИЙ ФЕДЕРАЛЬНЫЙ УНИВЕРСИТЕТ"
]

print(f"Ключевые параметры (Вариант 1):\nМодуль n ({len(str(n))} знаков): {n}\ne: {e}\nd: {d}\n")
print(f"{'№':<3} | {'Статус':<7} | {'Время ш/р (мс)':<15} | {'Исходный текст':<25} | {'Расшифровано'}")
print("-" * 80)

for i, text in enumerate(test_cases, 1):
    t0 = time.perf_counter()
    cipher = rsa_encrypt(text, e, n)
    t_enc = time.perf_counter() - t0

    t1 = time.perf_counter()
    decrypted = rsa_decrypt(cipher, d, n)
    t_dec = time.perf_counter() - t1

    status = "УСПЕХ" if text == decrypted else "СБОЙ"
    total_ms = (t_enc + t_dec) * 1000

    print(f"{i:<3} | {status:<7} | {total_ms:<15.3f} | {text[:23]:<25} | {decrypted[:23]}")