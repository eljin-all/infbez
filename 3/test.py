import time
from PIL import Image
from main import (
    embed_lsb_basic, extract_lsb_basic,
    embed_lsb_modified, extract_lsb_modified,
    apply_crop_attack, apply_vertical_flip
)

img = Image.new("RGB", (250, 250), color=(120, 150, 180))
w, h = img.size
key = "SecretKey_2026"

tests = [
    ("Базовый LSB (без атак)", "Basic_Test_1", False, False, "basic"),
    ("Базовый LSB + Флип", "Basic_Test_2", True, False, "basic"),
    ("Модификация: Без атак", "Watermark_Clean_2026", False, False, "mod"),
    ("Модификация: Вертикальный флип", "Flip_Resistant_OK", True, False, "mod"),
    ("Модификация: Кадрирование 8%", "Crop_Resistant_OK", False, True, "mod"),
    ("Модификация: Флип + Кадрирование", "All_Attacks_Survived", True, True, "mod"),
    ("Модификация: Длинная метка", "Copyright (c) 2026 ICIT SibFU", True, True, "mod"),
    ("Модификация: Символы и цифры", "ID: 032428518!@#$", True, True, "mod"),
    ("Модификация: Неверный ключ", "Secret_Data", False, False, "wrong_key"),
    ("Модификация: Экстремальный флип", "Check_10_Success", True, False, "mod")
]

print(f"{'№':<3} | {'Тип теста':<32} | {'Атаки':<22} | {'Целостность':<12} | {'Результат'}")
print("-" * 90)

for i, (name, msg, flip, crop, mode) in enumerate(tests, 1):
    attacks_str = []
    if flip: attacks_str.append("Flip")
    if crop: attacks_str.append("Crop 8%")
    att_label = "+".join(attacks_str) if attacks_str else "Нет"
    
    if mode == "basic":
        stego = embed_lsb_basic(img, msg, k_lsb=1)
        if flip: stego = apply_vertical_flip(stego)
        if crop: stego = apply_crop_attack(stego, 0.08)
        ext, ok = extract_lsb_basic(stego, k_lsb=1)
    elif mode == "wrong_key":
        stego = embed_lsb_modified(img, msg, key)
        ext, ok = extract_lsb_modified(stego, "Wrong_Key_123", w, h)
    else:
        stego = embed_lsb_modified(img, msg, key)
        if flip: stego = apply_vertical_flip(stego)
        if crop: stego = apply_crop_attack(stego, 0.08)
        ext, ok = extract_lsb_modified(stego, key, w, h)
        
    status = "УСПЕХ" if ok else "ОШИБКА"
    print(f"{i:<3} | {name:<32} | {att_label:<22} | {status:<12} | {ext[:20]}")