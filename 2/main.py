import math
import secrets
import time
import tkinter as tk
from tkinter import messagebox, ttk

def is_prime_miller_rabin(n, k=40):
    """Тест простоты Миллера — Рабина."""
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False

    r, s = 0, n - 1
    while s % 2 == 0:
        r += 1
        s //= 2

    for _ in range(k):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, s, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def generate_prime_digits(digits):
    """Генерирует случайное простое число с точным числом десятичных знаков."""
    low = 10**(digits - 1)
    high = (10**digits) - 1
    while True:
        candidate = secrets.randbelow(high - low + 1) + low
        if candidate % 2 == 0:
            candidate += 1
        if is_prime_miller_rabin(candidate):
            return candidate

def extended_gcd(a, b):
    """Расширенный алгоритм Евклида: возвращает (gcd, x, y), где a*x + b*y = gcd."""
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y

def mod_inverse(e, phi):
    """Вычисляет d такое, что (d * e) % phi == 1."""
    gcd, x, _ = extended_gcd(e, phi)
    if gcd != 1:
        raise ValueError("Мультипликативное обратное не существует.")
    return (x % phi + phi) % phi

def generate_rsa_keys(n_target_digits=31):
    """Генерация ключей RSA для n из заданного числа десятичных знаков (Вариант 1: 31 знак)."""
    digits_p = n_target_digits // 2
    digits_q = n_target_digits - digits_p

    while True:
        p = generate_prime_digits(digits_p)
        q = generate_prime_digits(digits_q)
        if p == q:
            continue
        n = p * q
        if len(str(n)) == n_target_digits:
            break

    phi = (p - 1) * (q - 1)
    e = 65537
    if math.gcd(e, phi) != 1:
        e = 3
        while math.gcd(e, phi) != 1:
            e += 2

    d = mod_inverse(e, phi)
    return p, q, n, phi, e, d

def rsa_encrypt(text, e, n):
    """Разбивает текст на байтовые блоки, преобразует в числа m_i < n и шифрует: c_i = m_i^e mod n."""
    text_bytes = text.encode("utf-8")
    mod_bytes_len = (n.bit_length() + 7) // 8
    block_size = max(1, mod_bytes_len - 1) 

    cipher_blocks = []
    for i in range(0, len(text_bytes), block_size):
        chunk = text_bytes[i:i + block_size]
        m_int = int.from_bytes(chunk, byteorder="big")
        c_int = pow(m_int, e, n)
        cipher_blocks.append(str(c_int))

    return " ".join(cipher_blocks)

def rsa_decrypt(cipher_str, d, n):
    """Дешифрует список блоков: m_i = c_i^d mod n и восстанавливает строку."""
    tokens = cipher_str.strip().split()
    if not tokens:
        return ""

    mod_bytes_len = (n.bit_length() + 7) // 8
    block_size = max(1, mod_bytes_len - 1)

    recovered_bytes = bytearray()
    for token in tokens:
        c_int = int(token)
        m_int = pow(c_int, d, n)
        
        needed = (m_int.bit_length() + 7) // 8
        if needed == 0:
            chunk = b""
        else:
            chunk = m_int.to_bytes(needed, byteorder="big")
        
        recovered_bytes.extend(chunk)

    return recovered_bytes.decode("utf-8", errors="replace")


class RSACipherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа №3 — Криптосистема RSA (Вариант 1: n = 31 знак)")
        self.root.geometry("820x760")
        self.root.resizable(True, True)

        self.p = None
        self.q = None
        self.n = None
        self.phi = None
        self.e = None
        self.d = None

        self.full_result_cache = ""

        self.build_ui()
        self.on_generate_keys()

    def build_ui(self):
        key_frame = ttk.LabelFrame(self.root, text=" 1. Ключевая информация (Вариант 1: модуль n = 31 десятичный знак) ")
        key_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(key_frame, text="Сгенерировать новую пару ключей RSA", command=self.on_generate_keys).grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        ttk.Label(key_frame, text="Открытая экспонента e:").grid(row=1, column=0, sticky="w", padx=5)
        self.entry_e = ttk.Entry(key_frame, width=80)
        self.entry_e.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(key_frame, text="Модуль n (открытый/закрытый):").grid(row=2, column=0, sticky="w", padx=5)
        self.entry_n = ttk.Entry(key_frame, width=80)
        self.entry_n.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(key_frame, text="Закрытая экспонента d:").grid(row=3, column=0, sticky="w", padx=5)
        self.entry_d = ttk.Entry(key_frame, width=80)
        self.entry_d.grid(row=3, column=1, padx=5, pady=2, sticky="ew")

        self.label_info = ttk.Label(key_frame, text="Длина модуля: 0 знаков", foreground="blue")
        self.label_info.grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=3)

        text_frame = ttk.LabelFrame(self.root, text=" 2. Текст для обработки ")
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.input_text = tk.Text(text_frame, height=6, wrap="word")
        self.input_text.pack(fill="both", expand=True, padx=5, pady=5)

        btn_box = ttk.Frame(text_frame)
        btn_box.pack(fill="x", pady=2)
        ttk.Button(btn_box, text="Зашифровать текст", command=self.on_encrypt_text).pack(side="left", padx=5)
        ttk.Button(btn_box, text="Расшифровать текст", command=self.on_decrypt_text).pack(side="left", padx=5)
        ttk.Button(btn_box, text="Очистить", command=lambda: self.input_text.delete("1.0", tk.END)).pack(side="right", padx=5)

        file_frame = ttk.LabelFrame(self.root, text=" 3. Работа с файлами (ASCII / UTF-8) ")
        file_frame.pack(fill="x", padx=10, pady=5)

        f_in = ttk.Frame(file_frame)
        f_in.pack(fill="x", padx=5, pady=3)
        ttk.Label(f_in, text="Имя входного файла:").pack(side="left")
        self.file_in_entry = ttk.Entry(f_in, width=22)
        self.file_in_entry.insert(0, "input.txt")
        self.file_in_entry.pack(side="left", padx=5)
        ttk.Button(f_in, text="Зашифровать файл", command=lambda: self.process_file(encrypt=True)).pack(side="left", padx=3)
        ttk.Button(f_in, text="Расшифровать файл", command=lambda: self.process_file(encrypt=False)).pack(side="left", padx=3)

        f_out = ttk.Frame(file_frame)
        f_out.pack(fill="x", padx=5, pady=3)
        ttk.Label(f_out, text="Имя выходного файла:").pack(side="left")
        self.file_out_entry = ttk.Entry(f_out, width=22)
        self.file_out_entry.insert(0, "output.txt")
        self.file_out_entry.pack(side="left", padx=5)
        ttk.Button(f_out, text="Сохранить результат в файл", command=self.save_result_to_file).pack(side="left", padx=3)

        out_frame = ttk.LabelFrame(self.root, text=" 4. Результат и метрики производительности ")
        out_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.perf_label = ttk.Label(out_frame, text="Время выполнения: 0.000 мс")
        self.perf_label.pack(anchor="w", padx=5, pady=2)

        self.output_text = tk.Text(out_frame, height=6, wrap="word")
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)

    def on_generate_keys(self):
        try:
            self.p, self.q, self.n, self.phi, self.e, self.d = generate_rsa_keys(31)
            self.entry_e.delete(0, tk.END)
            self.entry_e.insert(0, str(self.e))
            self.entry_n.delete(0, tk.END)
            self.entry_n.insert(0, str(self.n))
            self.entry_d.delete(0, tk.END)
            self.entry_d.insert(0, str(self.d))

            digits_n = len(str(self.n))
            self.label_info.config(
                text=f"Модуль n сгенерирован: {digits_n} десятичных знаков (~{self.n.bit_length()} бит). p: {len(str(self.p))} знаков, q: {len(str(self.q))} знаков."
            )
        except Exception as ex:
            messagebox.showerror("Ошибка генерации ключей", str(ex))

    def get_keys_from_gui(self):
        e = int(self.entry_e.get().strip())
        n = int(self.entry_n.get().strip())
        d = int(self.entry_d.get().strip())
        return e, d, n

    def update_result_view(self, result_str, elapsed_sec):
        self.full_result_cache = result_str
        self.perf_label.config(text=f"Время операции: {elapsed_sec * 1000:.3f} мс | Длина результата: {len(result_str)} символов")

        self.output_text.delete("1.0", tk.END)
        preview_limit = 500
        if len(result_str) > preview_limit:
            self.output_text.insert(tk.END, result_str[:preview_limit] + "\n\n... [ТЕКСТ ОБРЕЗАН ДЛЯ ПРЕДПРОСМОТРА]")
        else:
            self.output_text.insert(tk.END, result_str)

    def on_encrypt_text(self):
        try:
            e, _, n = self.get_keys_from_gui()
            txt = self.input_text.get("1.0", "end-1c")
            if not txt:
                messagebox.showwarning("Внимание", "Введите текст!")
                return

            t0 = time.perf_counter()
            encrypted = rsa_encrypt(txt, e, n)
            t1 = time.perf_counter()

            self.update_result_view(encrypted, t1 - t0)
        except Exception as ex:
            messagebox.showerror("Ошибка шифрования", str(ex))

    def on_decrypt_text(self):
        try:
            _, d, n = self.get_keys_from_gui()
            txt = self.input_text.get("1.0", "end-1c")
            if not txt:
                messagebox.showwarning("Внимание", "Введите шифротекст (числа через пробел)!")
                return

            t0 = time.perf_counter()
            decrypted = rsa_decrypt(txt, d, n)
            t1 = time.perf_counter()

            self.update_result_view(decrypted, t1 - t0)
        except Exception as ex:
            messagebox.showerror("Ошибка расшифрования", str(ex))

    def process_file(self, encrypt=True):
        fname = self.file_in_entry.get().strip()
        try:
            with open(fname, "r", encoding="utf-8", newline="") as f:
                content = f.read()
        except Exception as ex:
            messagebox.showerror("Ошибка чтения файла", str(ex))
            return

        try:
            e, d, n = self.get_keys_from_gui()
            t0 = time.perf_counter()
            res = rsa_encrypt(content, e, n) if encrypt else rsa_decrypt(content, d, n)
            t1 = time.perf_counter()

            self.update_result_view(res, t1 - t0)
            messagebox.showinfo("Успех", "Файл успешно обработан!")
        except Exception as ex:
            messagebox.showerror("Ошибка обработки", str(ex))

    def save_result_to_file(self):
        if not self.full_result_cache:
            messagebox.showwarning("Внимание", "Нет данных для сохранения!")
            return
        fname = self.file_out_entry.get().strip()
        try:
            with open(fname, "w", encoding="utf-8", newline="") as f:
                f.write(self.full_result_cache)
            messagebox.showinfo("Сохранено", f"Данные сохранены в '{fname}'!")
        except Exception as ex:
            messagebox.showerror("Ошибка сохранения", str(ex))

if __name__ == "__main__":
    root = tk.Tk()
    app = RSACipherApp(root)
    root.mainloop()