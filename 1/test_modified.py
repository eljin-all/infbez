from main import DEFAULT_MAGIC_SQUARE, encrypt_modified, decrypt_modified

test_cases = [
    "ТЕСТ",
    "МАГИЧЕСКИЙ КВАДРАТ",
    "ИНФОРМАЦИОННАЯ БЕЗОПАСНОСТЬ",
    "Information Security",
    "1234567890!@#$",
    "А",
    "ДЛИНА_РОВНО_16_Б",
    "ДВА_БЛОКА_СИМВОЛОВ_РОВНО_32_ЗНА",
    "Текст с пробелом",
    "Шифр перестановки"
]

key = DEFAULT_MAGIC_SQUARE
block_size = len(key)

def format_text(s, max_len=24):
    if len(s) > max_len:
        return s[:max_len - 3] + "..."
    return s

header = (f"{'№':<3} |  {'Исходный текст':<22} | "
          f"{'Зашифрованный текст (XOR)':<30} | {'Расшифрованный текст':<22}")
print(header)
print("-" * len(header))

for i, text in enumerate(test_cases, 1):
    cipher = encrypt_modified(text, key, block_size)
    decrypted = decrypt_modified(cipher, key, block_size)
    
    src_display = format_text(text, 22)
    enc_display = format_text(cipher, 30)
    dec_display = format_text(decrypted, 22)
    
    print(f"{i:<3}  {src_display:<22} | {enc_display:<30} | {dec_display:<22}")