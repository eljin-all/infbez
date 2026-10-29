import math
import tkinter as tk
from tkinter import messagebox, ttk

DEFAULT_MAGIC_SQUARE = [
    16, 3, 2, 13,
    5, 10, 11, 8,
    9, 6, 7, 12,
    4, 15, 14, 1
]

def parse_key(key_str):
    try:
        nums = [int(x) for x in key_str.strip().split()]
    except ValueError:
        raise ValueError("Ключ должен состоять только из целых чисел, разделенных пробелом.")
    
    total = len(nums)
    n = int(math.isqrt(total))
    if n * n != total or total < 4:
        raise ValueError(f"Количество чисел ({total}) должно быть точным квадратом N x N (например, 9, 16, 25).")
    
    if sorted(nums) != list(range(1, total + 1)):
        raise ValueError(f"Ключ должен содержать все числа от 1 до {total} без повторений.")
    
    return nums, total


def encrypt_magic_raw(text, key_square, block_size):
    pad_len = (block_size - (len(text) % block_size)) % block_size
    padded_text = text + (' ' * pad_len)
    
    result = []
    for i in range(0, len(padded_text), block_size):
        block = padded_text[i:i + block_size]
        new_block = [' '] * block_size
        for orig_pos, target_pos in enumerate(key_square):
            new_block[target_pos - 1] = block[orig_pos]
        result.append("".join(new_block))
    return "".join(result)

def decrypt_magic_raw(cipher_text, key_square, block_size):
    if len(cipher_text) % block_size != 0:
        cipher_text += ' ' * ((block_size - (len(cipher_text) % block_size)) % block_size)
        
    result = []
    for i in range(0, len(cipher_text), block_size):
        block = cipher_text[i:i + block_size]
        orig_block = [' '] * block_size
        for orig_pos, target_pos in enumerate(key_square):
            orig_block[orig_pos] = block[target_pos - 1]
        result.append("".join(orig_block))
    return "".join(result)

def encrypt_magic(text, key_square, block_size):
    cipher_body = encrypt_magic_raw(text, key_square, block_size)
    return f"{len(text)}|{cipher_body}"

def decrypt_magic(cipher_text, key_square, block_size):
    if "|" in cipher_text:
        meta, body = cipher_text.split("|", 1)
        if meta.isdigit():
            orig_len = int(meta)
            decrypted = decrypt_magic_raw(body, key_square, block_size)
            return decrypted[:orig_len]
    return decrypt_magic_raw(cipher_text, key_square, block_size).rstrip()


def xor_gamma(text, key_square):
    res = []
    k_len = len(key_square)
    for idx, ch in enumerate(text):
        gamma = key_square[idx % k_len]
        res.append(chr(ord(ch) ^ gamma))
    return "".join(res)

def encrypt_modified(text, key_square, block_size):
    transposed = encrypt_magic_raw(text, key_square, block_size)
    xored = xor_gamma(transposed, key_square)
    return f"{len(text)}|{xored}"

def decrypt_modified(cipher_text, key_square, block_size):
    if "|" in cipher_text:
        meta, body = cipher_text.split("|", 1)
        if meta.isdigit():
            orig_len = int(meta)
            un_xored = xor_gamma(body, key_square)
            decrypted = decrypt_magic_raw(un_xored, key_square, block_size)
            return decrypted[:orig_len]
    un_xored = xor_gamma(cipher_text, key_square)
    return decrypt_magic_raw(un_xored, key_square, block_size).rstrip()

class MagicCipherApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("750x700")
        self.root.resizable(True, True)
        self.full_result_cache = ""
        self.build_ui()

    def build_ui(self):
        key_frame = ttk.LabelFrame(self.root, text=" 1. Настройки алгоритма и ключ ")
        key_frame.pack(fill="x", padx=10, pady=5)

        self.mode_var = tk.StringVar(value="basic")
        ttk.Radiobutton(key_frame, text="Базовый шифр (перестановка по квадрату)", 
                        variable=self.mode_var, value="basic").grid(row=0, column=0, padx=10, pady=3, sticky="w")
        ttk.Radiobutton(key_frame, text="Модифицированный шифр (квадрат + гамма)", 
                        variable=self.mode_var, value="modified").grid(row=0, column=1, padx=10, pady=3, sticky="w")

        ttk.Label(key_frame, text="Ключ (числа от 1 до N² через пробел):").grid(row=1, column=0, padx=10, pady=3, sticky="w")
        default_key_str = " ".join(map(str, DEFAULT_MAGIC_SQUARE))
        self.key_entry = ttk.Entry(key_frame, width=70)
        self.key_entry.insert(0, default_key_str)
        self.key_entry.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        text_frame = ttk.LabelFrame(self.root, text=" 2. Текст для обработки ")
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.input_text = tk.Text(text_frame, height=7, wrap="word")
        self.input_text.pack(fill="both", expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(text_frame)
        btn_frame.pack(fill="x", pady=3)
        ttk.Button(btn_frame, text="Зашифровать введенный текст", command=self.on_encrypt_text).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Расшифровать введенный текст", command=self.on_decrypt_text).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Очистить поле", command=lambda: self.input_text.delete("1.0", tk.END)).pack(side="right", padx=5)

        file_frame = ttk.LabelFrame(self.root, text=" 3. Работа с файлами ")
        file_frame.pack(fill="x", padx=10, pady=5)

        file_in_subframe = ttk.Frame(file_frame)
        file_in_subframe.pack(fill="x", padx=5, pady=3)
        ttk.Label(file_in_subframe, text="Имя входного файла:").pack(side="left", padx=2)
        self.file_in_entry = ttk.Entry(file_in_subframe, width=25)
        self.file_in_entry.insert(0, "input.txt")
        self.file_in_entry.pack(side="left", padx=5)

        ttk.Button(file_in_subframe, text="Зашифровать из файла", command=lambda: self.process_file(encrypt=True)).pack(side="left", padx=3)
        ttk.Button(file_in_subframe, text="Расшифровать из файла", command=lambda: self.process_file(encrypt=False)).pack(side="left", padx=3)

        file_out_subframe = ttk.Frame(file_frame)
        file_out_subframe.pack(fill="x", padx=5, pady=3)
        ttk.Label(file_out_subframe, text="Имя файла для сохранения:").pack(side="left", padx=2)
        self.file_out_entry = ttk.Entry(file_out_subframe, width=25)
        self.file_out_entry.insert(0, "output.txt")
        self.file_out_entry.pack(side="left", padx=5)

        ttk.Button(file_out_subframe, text="Сохранить текущий результат в файл", command=self.save_result_to_file).pack(side="left", padx=3)

        out_frame = ttk.LabelFrame(self.root, text=" 4. Результат (предпросмотр) ")
        out_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.preview_info_label = ttk.Label(out_frame, text="Показаны первые символы результата:")
        self.preview_info_label.pack(anchor="w", padx=5, pady=2)

        self.output_text = tk.Text(out_frame, height=7, wrap="word")
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)

    def get_cipher_params(self):
        raw_key = self.key_entry.get()
        key_square, block_size = parse_key(raw_key)
        mode = self.mode_var.get()
        return key_square, block_size, mode

    def update_result_view(self, full_text):
        self.full_result_cache = full_text
        preview_limit = 500
        
        self.output_text.delete("1.0", tk.END)
        if len(full_text) > preview_limit:
            self.output_text.insert(tk.END, full_text[:preview_limit] + "\n\n... [ТЕКСТ ОБРЕЗАН ДЛЯ ПРЕДПРОСМОТРА. Используйте кнопку сохранения в файл]")
            self.preview_info_label.config(text=f"Показаны первые {preview_limit} из {len(full_text)} символов:")
        else:
            self.output_text.insert(tk.END, full_text)
            self.preview_info_label.config(text=f"Полный результат ({len(full_text)} символов):")

    def on_encrypt_text(self):
        try:
            key_square, block_size, mode = self.get_cipher_params()
            txt = self.input_text.get("1.0", "end-1c")
            if not txt:
                messagebox.showwarning("Внимание", "Введите текст для шифрования!")
                return
            
            encrypted = encrypt_magic(txt, key_square, block_size) if mode == "basic" else encrypt_modified(txt, key_square, block_size)
            self.update_result_view(encrypted)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def on_decrypt_text(self):
        try:
            key_square, block_size, mode = self.get_cipher_params()
            txt = self.input_text.get("1.0", "end-1c")
            if not txt:
                messagebox.showwarning("Внимание", "Введите текст для расшифрования!")
                return
            
            decrypted = decrypt_magic(txt, key_square, block_size) if mode == "basic" else decrypt_modified(txt, key_square, block_size)
            self.update_result_view(decrypted)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def process_file(self, encrypt=True):
        filename = self.file_in_entry.get().strip()
        if not filename:
            messagebox.showwarning("Внимание", "Укажите имя входного файла!")
            return
        
        try:
            with open(filename, "r", encoding="utf-8", newline="") as f:
                content = f.read()
        except FileNotFoundError:
            messagebox.showerror("Ошибка", f"Файл '{filename}' не найден!")
            return
        except Exception as e:
            messagebox.showerror("Ошибка чтения файла", str(e))
            return

        try:
            key_square, block_size, mode = self.get_cipher_params()
            if encrypt:
                res = encrypt_magic(content, key_square, block_size) if mode == "basic" else encrypt_modified(content, key_square, block_size)
            else:
                res = decrypt_magic(content, key_square, block_size) if mode == "basic" else decrypt_modified(content, key_square, block_size)
            
            self.update_result_view(res)
            messagebox.showinfo("Успех", "Файл успешно обработан! Результат загружен в поле предпросмотра.")
        except Exception as e:
            messagebox.showerror("Ошибка обработки", str(e))

    def save_result_to_file(self):
        if not self.full_result_cache:
            messagebox.showwarning("Внимание", "Нет результата для сохранения!")
            return
        
        filename = self.file_out_entry.get().strip()
        if not filename:
            messagebox.showwarning("Внимание", "Укажите имя файла для сохранения!")
            return
        
        try:
            with open(filename, "w", encoding="utf-8", newline="") as f:
                f.write(self.full_result_cache)
            messagebox.showinfo("Сохранено", f"Результат успешно сохранен в файл '{filename}'!")
        except Exception as e:
            messagebox.showerror("Ошибка записи файла", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = MagicCipherApp(root)
    root.mainloop()