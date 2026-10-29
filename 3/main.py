import io
import math
import os
import random
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import zlib
from PIL import Image

def bytes_to_bits(data: bytes) -> list[int]:
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits

def bits_to_bytes(bits: list[int]) -> bytes:
    byte_arr = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for bit in bits[i:i + 8]:
            byte = (byte << 1) | bit
        byte_arr.append(byte)
    return bytes(byte_arr)

def get_max_payload_basic(width: int, height: int, k_lsb: int) -> int:
    """Максимальная полезная емкость в байтах: (3 * S * k - 64 служебных бит) // 8"""
    total_bits = width * height * 3 * k_lsb
    service_bits = 64 
    if total_bits <= service_bits:
        return 0
    return (total_bits - service_bits) // 8

def embed_lsb_basic(img: Image.Image, message: str, k_lsb: int) -> Image.Image:
    img_rgb = img.convert("RGB")
    data_bytes = message.encode("utf-8")
    crc = zlib.crc32(data_bytes)
    packet = struct.pack(">II", len(data_bytes), crc) + data_bytes
    bits = bytes_to_bits(packet)
    
    pixels = list(img_rgb.getdata())
    total_capacity_bits = len(pixels) * 3 * k_lsb
    if len(bits) > total_capacity_bits:
        raise ValueError(f"Размер ЦВЗ ({len(bits)} бит) превышает вместимость ({total_capacity_bits} бит).")
    
    bit_idx = 0
    num_bits = len(bits)
    mask = ~((1 << k_lsb) - 1) & 0xFF
    
    new_pixels = []
    for r, g, b in pixels:
        channels = [r, g, b]
        for c_idx in range(3):
            if bit_idx < num_bits:
                val = 0
                for _ in range(k_lsb):
                    val = (val << 1) | (bits[bit_idx] if bit_idx < num_bits else 0)
                    bit_idx += 1
                channels[c_idx] = (channels[c_idx] & mask) | val
        new_pixels.append(tuple(channels))
        
    out_img = Image.new("RGB", img_rgb.size)
    out_img.putdata(new_pixels)
    return out_img

def extract_lsb_basic(img: Image.Image, k_lsb: int) -> tuple[str, bool]:
    img_rgb = img.convert("RGB")
    pixels = list(img_rgb.getdata())
    
    extracted_bits = []
    for r, g, b in pixels:
        for ch in (r, g, b):
            for i in range(k_lsb - 1, -1, -1):
                extracted_bits.append((ch >> i) & 1)
                if len(extracted_bits) >= 64:
                    break
            if len(extracted_bits) >= 64:
                break
        if len(extracted_bits) >= 64:
            break
            
    header_bytes = bits_to_bytes(extracted_bits[:64])
    length, expected_crc = struct.unpack(">II", header_bytes)
    
    total_bits_needed = (8 + length) * 8
    max_possible_bits = len(pixels) * 3 * k_lsb
    if total_bits_needed > max_possible_bits or length > 50_000_000 or length < 0:
        return "", False
        
    extracted_bits = []
    for r, g, b in pixels:
        for ch in (r, g, b):
            for i in range(k_lsb - 1, -1, -1):
                extracted_bits.append((ch >> i) & 1)
                if len(extracted_bits) >= total_bits_needed:
                    break
            if len(extracted_bits) >= total_bits_needed:
                break
        if len(extracted_bits) >= total_bits_needed:
            break
            
    full_payload = bits_to_bytes(extracted_bits)
    data_bytes = full_payload[8:8 + length]
    actual_crc = zlib.crc32(data_bytes)
    
    is_valid = (actual_crc == expected_crc)
    text = data_bytes.decode("utf-8", errors="replace")
    return text, is_valid

SYNC_MARKER = b"WMK1" 
SYNC_BITS = bytes_to_bits(SYNC_MARKER)
TILE_SIZE = 48  

def get_max_payload_modified(width: int, height: int, tile_size: int = TILE_SIZE) -> int:
    """Максимальная полезная емкость тайла в байтах"""
    if width < tile_size or height < tile_size:
        return 0
    total_tile_bits = tile_size * tile_size * 3
    service_bits = 96
    return max(0, (total_tile_bits - service_bits) // 8)

def embed_lsb_modified(img: Image.Image, message: str, key_str: str, tile_size: int = TILE_SIZE) -> Image.Image:
    img_rgb = img.convert("RGB")
    w, h = img_rgb.size
    
    data_bytes = message.encode("utf-8")
    crc = zlib.crc32(data_bytes)
    packet = SYNC_MARKER + struct.pack(">II", len(data_bytes), crc) + data_bytes
    packet_bits = bytes_to_bits(packet)
    
    capacity_bits = tile_size * tile_size * 3
    if len(packet_bits) > capacity_bits:
        raise ValueError(f"Размер ЦВЗ ({len(packet_bits)} бит) превышает емкость тайла ({capacity_bits} бит).")
        
    tile_slots = [(tx, ty, c) for ty in range(tile_size) for tx in range(tile_size) for c in range(3)]
    rng = random.Random(key_str)
    rng.shuffle(tile_slots)
    
    slot_map = {}
    for i, b in enumerate(packet_bits):
        slot_map[tile_slots[i]] = b
        
    pixels = img_rgb.load()
    for y in range(h):
        ty = y % tile_size
        for x in range(w):
            tx = x % tile_size
            r, g, b = pixels[x, y]
            channels = [r, g, b]
            modified = False
            for c in range(3):
                slot_key = (tx, ty, c)
                if slot_key in slot_map:
                    target_bit = slot_map[slot_key]
                    channels[c] = (channels[c] & 0xFE) | target_bit
                    modified = True
            if modified:
                pixels[x, y] = tuple(channels)
                
    return img_rgb

def extract_from_tiled(img: Image.Image, key_str: str, tile_size: int = TILE_SIZE) -> tuple[str, bool]:
    w, h = img.size
    if w < tile_size or h < tile_size:
        return "", False
        
    img_rgb = img.convert("RGB")
    pixels = img_rgb.load()
    
    tile_slots = [(tx, ty, c) for ty in range(tile_size) for tx in range(tile_size) for c in range(3)]
    rng = random.Random(key_str)
    rng.shuffle(tile_slots)
    
    sync_slots = tile_slots[:32]
    found_offset = None
    
    # Сканирование 2D-смещения тайла (off_x, off_y)
    for off_y in range(tile_size):
        for off_x in range(tile_size):
            match = True
            for bit_i, (tx, ty, c) in enumerate(sync_slots):
                x_pos = (tx - off_x) % tile_size
                y_pos = (ty - off_y) % tile_size
                if x_pos >= w or y_pos >= h:
                    match = False
                    break
                if (pixels[x_pos, y_pos][c] & 1) != SYNC_BITS[bit_i]:
                    match = False
                    break
            if match:
                found_offset = (off_x, off_y)
                break
        if found_offset:
            break
            
    if not found_offset:
        return "", False
        
    off_x, off_y = found_offset
    header_slots = tile_slots[32:96]
    header_bits = []
    for tx, ty, c in header_slots:
        x_pos = (tx - off_x) % tile_size
        y_pos = (ty - off_y) % tile_size
        if x_pos >= w or y_pos >= h:
            return "", False
        header_bits.append(pixels[x_pos, y_pos][c] & 1)
        
    header_bytes = bits_to_bytes(header_bits)
    length, expected_crc = struct.unpack(">II", header_bytes)
    
    max_payload_bits = len(tile_slots) - 96
    if length * 8 > max_payload_bits or length < 0:
        return "", False
        
    payload_slots = tile_slots[96: 96 + length * 8]
    payload_bits = []
    for tx, ty, c in payload_slots:
        x_pos = (tx - off_x) % tile_size
        y_pos = (ty - off_y) % tile_size
        if x_pos >= w or y_pos >= h:
            return "", False
        payload_bits.append(pixels[x_pos, y_pos][c] & 1)
        
    payload_bytes = bits_to_bytes(payload_bits)
    if zlib.crc32(payload_bytes) == expected_crc:
        return payload_bytes.decode("utf-8", errors="replace"), True
        
    return "", False

def extract_lsb_modified(img: Image.Image, key_str: str, tile_size: int = TILE_SIZE) -> tuple[str, bool]:
    text, ok = extract_from_tiled(img, key_str, tile_size)
    if ok:
        return text, True
        
    flipped = img.transpose(Image.FLIP_TOP_BOTTOM)
    text, ok = extract_from_tiled(flipped, key_str, tile_size)
    if ok:
        return text, True
        
    return "", False
def apply_crop_attack(img: Image.Image, crop_percent: float = 0.08) -> Image.Image:
    """Кадрирование по сторонам (до 10% от длины сторон)"""
    w, h = img.size
    crop_x = int(w * crop_percent)
    crop_y = int(h * crop_percent)
    return img.crop((crop_x, crop_y, w - crop_x, h - crop_y))

def apply_vertical_flip(img: Image.Image) -> Image.Image:
    """Зеркальное отражение по вертикали"""
    return img.transpose(Image.FLIP_TOP_BOTTOM)

class StegoWatermarkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа №5 — Маркирование изображений ЦВЗ (Вариант 1)")
        self.root.geometry("980x790")
        
        self.current_img = None
        self.watermarked_img = None
        
        self.build_ui()
        
    def build_ui(self):
        # 1. Выбор файла и режим
        top_frame = ttk.LabelFrame(self.root, text=" 1. Исходное изображение и режим ")
        top_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(top_frame, text="Выбрать PNG изображение", command=self.load_image).grid(row=0, column=0, padx=5, pady=5)
        self.file_label = ttk.Label(top_frame, text="Файл не выбран", foreground="gray")
        self.file_label.grid(row=0, column=1, sticky="w", padx=5)
        
        self.mode_var = tk.StringVar(value="modified")
        ttk.Radiobutton(top_frame, text="Базовый LSB", variable=self.mode_var, value="basic", command=self.update_capacity).grid(row=0, column=2, padx=10)
        ttk.Radiobutton(top_frame, text="Модифицированный LSB (Вариант 1: Замощение тайлами)", variable=self.mode_var, value="modified", command=self.update_capacity).grid(row=0, column=3, padx=10)

        # Параметры
        params_frame = ttk.Frame(top_frame)
        params_frame.grid(row=1, column=0, columnspan=4, sticky="ew", padx=5, pady=3)
        
        ttk.Label(params_frame, text="Глубина внедрения k (для базового):").pack(side="left", padx=2)
        self.k_spin = ttk.Spinbox(params_frame, from_=1, to=8, width=5, command=self.update_capacity)
        self.k_spin.set(1)
        self.k_spin.pack(side="left", padx=5)
        
        ttk.Label(params_frame, text="Секретный ключ (для модификации):").pack(side="left", padx=10)
        self.key_entry = ttk.Entry(params_frame, width=25)
        self.key_entry.insert(0, "SecretKey_2026")
        self.key_entry.pack(side="left", padx=5)
        
        self.capacity_label = ttk.Label(top_frame, text="Макс. объем ЦВЗ: 0 байт", font=("Segoe UI", 9, "bold"), foreground="blue")
        self.capacity_label.grid(row=2, column=0, columnspan=4, sticky="w", padx=5, pady=3)

        # 2. Ввод ЦВЗ
        msg_frame = ttk.LabelFrame(self.root, text=" 2. Текст цифрового водяного знака (ЦВЗ) ")
        msg_frame.pack(fill="x", padx=10, pady=5)
        
        self.msg_entry = ttk.Entry(msg_frame, width=80)
        self.msg_entry.insert(0, "Copyright (C) 2026 SFI ICIT. All rights reserved.")
        self.msg_entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        ttk.Button(msg_frame, text="Внедрить ЦВЗ", command=self.on_embed).pack(side="right", padx=5)

        # 3. Симуляция атак (Вариант 1)
        attack_frame = ttk.LabelFrame(self.root, text=" 3. Проверка стойкости ЦВЗ к атакам (Вариант 1) ")
        attack_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(attack_frame, text="Атака: Кадрирование (обрезка 8% по краям)", command=self.on_attack_crop).pack(side="left", padx=8, pady=5)
        ttk.Button(attack_frame, text="Атака: Зеркальное отражение по вертикали", command=self.on_attack_flip).pack(side="left", padx=8, pady=5)
        ttk.Button(attack_frame, text="Комбо: Отражение + Кадрирование", command=self.on_attack_combo).pack(side="left", padx=8, pady=5)
        ttk.Button(attack_frame, text="Сохранить результат в PNG", command=self.save_image).pack(side="right", padx=8)

        # 4. Извлечение и валидация
        ext_frame = ttk.LabelFrame(self.root, text=" 4. Извлечение и проверка целостности ЦВЗ ")
        ext_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        btn_ext_box = ttk.Frame(ext_frame)
        btn_ext_box.pack(fill="x", padx=5, pady=3)
        ttk.Button(btn_ext_box, text="Извлечь ЦВЗ из текущего изображения", command=self.on_extract).pack(side="left", padx=5)
        self.integrity_label = ttk.Label(btn_ext_box, text="Целостность: не проверялась", font=("Segoe UI", 9, "bold"))
        self.integrity_label.pack(side="left", padx=15)
        
        self.extracted_text = tk.Text(ext_frame, height=5, wrap="word")
        self.extracted_text.pack(fill="both", expand=True, padx=5, pady=5)

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("PNG images", "*.png"), ("All images", "*.*")])
        if not path:
            return
        try:
            img = Image.open(path)
            self.current_img = img
            self.watermarked_img = img.copy()
            self.file_label.config(text=f"{os.path.basename(path)} ({img.width}x{img.height})", foreground="black")
            self.update_capacity()
        except Exception as ex:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {ex}")

    def update_capacity(self):
        if not self.current_img:
            return
        w, h = self.current_img.size
        mode = self.mode_var.get()
        if mode == "basic":
            k = int(self.k_spin.get() or 1)
            cap = get_max_payload_basic(w, h, k)
            self.capacity_label.config(text=f"Макс. емкость (Базовый LSB, k={k}): {cap} байт (~{cap} символов ASCII)")
        else:
            cap = get_max_payload_modified(w, h, TILE_SIZE)
            self.capacity_label.config(text=f"Макс. емкость (Модифицированный LSB, тайл {TILE_SIZE}x{TILE_SIZE}): {cap} байт (~{cap} символов ASCII)")

    def on_embed(self):
        if not self.current_img:
            messagebox.showwarning("Внимание", "Сначала выберите изображение!")
            return
        msg = self.msg_entry.get().strip()
        if not msg:
            messagebox.showwarning("Внимание", "Введите текст ЦВЗ!")
            return
        mode = self.mode_var.get()
        try:
            if mode == "basic":
                k = int(self.k_spin.get())
                self.watermarked_img = embed_lsb_basic(self.current_img, msg, k)
            else:
                key = self.key_entry.get().strip()
                if not key:
                    messagebox.showwarning("Внимание", "Введите ключ!")
                    return
                self.watermarked_img = embed_lsb_modified(self.current_img, msg, key, TILE_SIZE)
                
            messagebox.showinfo("Успех", "Цифровой водяной знак успешно внедрен в изображение!")
            self.integrity_label.config(text="ЦВЗ внедрен (готов к тестам)", foreground="blue")
        except Exception as ex:
            messagebox.showerror("Ошибка внедрения", str(ex))

    def on_attack_crop(self):
        if not self.watermarked_img:
            return
        self.watermarked_img = apply_crop_attack(self.watermarked_img, crop_percent=0.08)
        messagebox.showinfo("Атака проведена", f"Изображение кадрировано на 8% по краям.\nНовый размер: {self.watermarked_img.size}")

    def on_attack_flip(self):
        if not self.watermarked_img:
            return
        self.watermarked_img = apply_vertical_flip(self.watermarked_img)
        messagebox.showinfo("Атака проведена", "Изображение зеркально отражено по вертикали!")

    def on_attack_combo(self):
        if not self.watermarked_img:
            return
        self.watermarked_img = apply_vertical_flip(self.watermarked_img)
        self.watermarked_img = apply_crop_attack(self.watermarked_img, crop_percent=0.08)
        messagebox.showinfo("Атака проведена", "Применены обе атаки: вертикальный флип и кадрирование!")

    def on_extract(self):
        if not self.watermarked_img:
            messagebox.showwarning("Внимание", "Нет изображения с ЦВЗ!")
            return
        mode = self.mode_var.get()
        try:
            if mode == "basic":
                k = int(self.k_spin.get())
                text, valid = extract_lsb_basic(self.watermarked_img, k)
            else:
                key = self.key_entry.get().strip()
                text, valid = extract_lsb_modified(self.watermarked_img, key, TILE_SIZE)
                
            self.extracted_text.delete("1.0", tk.END)
            self.extracted_text.insert(tk.END, text)
            
            if valid:
                self.integrity_label.config(text="Целостность: УСПЕШНО (CRC32 совпал)", foreground="green")
            else:
                self.integrity_label.config(text="Целостность: ОШИБКА (ЦВЗ поврежден)", foreground="red")
        except Exception as ex:
            messagebox.showerror("Ошибка извлечения", str(ex))

    def save_image(self):
        if not self.watermarked_img:
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG image", "*.png")])
        if path:
            self.watermarked_img.save(path)
            messagebox.showinfo("Сохранено", f"Файл сохранен: {path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = StegoWatermarkApp(root)
    root.mainloop()