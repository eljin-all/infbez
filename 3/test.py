import time
from PIL import Image
from main import (
    embed_lsb_basic, extract_lsb_basic,
    embed_lsb_modified, extract_lsb_modified,
    apply_crop_attack, apply_vertical_flip,
    TILE_SIZE
)

def run_tests():
    img = Image.new("RGB", (250, 250), color=(110, 145, 185))
    key = "SecretKey_2026"
    
    test_cases = [
        ("Базовый LSB (k=1)", "Basic_Test_1", False, 0.0, "basic"),
        ("Базовый LSB + Флип", "Basic_Test_2", True, 0.0, "basic"),
        ("Базовый LSB + Кадрирование", "Basic_Test_3", False, 0.08, "basic"),
        ("Модификация: Без атак", "Watermark_Clean_2026", False, 0.0, "mod"),
        ("Модификация: Вертикальный флип", "Flip_Resistant_OK", True, 0.0, "mod"),
        ("Модификация: Кадрирование 8%", "Crop_Resistant_OK", False, 0.08, "mod"),
        ("Модификация: Флип + Кадрирование", "All_Attacks_Survived", True, 0.08, "mod"),
        ("Модификация: Длинная метка", "Copyright (c) 2026 ICIT", True, 0.08, "mod"),
        ("Модификация: Неверный ключ", "Secret_Payload_Data", False, 0.0, "wrong_key"),
        ("Модификация: Экстремальный флип", "Check_10_Success", True, 0.0, "mod")
    ]
    
    print("=" * 86)
    print(f"{'№':<3} | {'Тип теста':<32} | {'Атаки':<15} | {'Целостность':<12} | {'Результат'}")
    print("=" * 86)
    
    for i, (name, msg, flip, crop, mode) in enumerate(test_cases, 1):
        attacks_list = []
        if flip:
            attacks_list.append("Flip")
        if crop > 0:
            attacks_list.append(f"Crop {int(crop*100)}%")
        attacks_str = "+".join(attacks_list) if attacks_list else "Нет"
        
        extracted_text = ""
        is_ok = False
        
        try:
            if mode == "basic":
                stego = embed_lsb_basic(img, msg, k_lsb=1)
                if flip:
                    stego = apply_vertical_flip(stego)
                if crop > 0:
                    stego = apply_crop_attack(stego, crop)
                extracted_text, is_ok = extract_lsb_basic(stego, k_lsb=1)
                
            elif mode == "wrong_key":
                stego = embed_lsb_modified(img, msg, key, TILE_SIZE)
                extracted_text, is_ok = extract_lsb_modified(stego, "Wrong_Key_12345", TILE_SIZE)
                
            else:  # mode == "mod"
                stego = embed_lsb_modified(img, msg, key, TILE_SIZE)
                if flip:
                    stego = apply_vertical_flip(stego)
                if crop > 0:
                    stego = apply_crop_attack(stego, crop)
                extracted_text, is_ok = extract_lsb_modified(stego, key, TILE_SIZE)
        except Exception:
            is_ok = False
            extracted_text = ""
            
        status = "УСПЕХ" if is_ok else "ОШИБКА"
        res_display = extracted_text if (is_ok and extracted_text) else "[Не извлечено]"
        if len(res_display) > 20:
            res_display = res_display[:17] + "..."
            
        print(f"{i:<3} | {name:<32} | {attacks_str:<15} | {status:<12} | {res_display}")
        
    print("=" * 86)

if __name__ == "__main__":
    run_tests()