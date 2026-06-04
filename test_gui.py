import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import threading
from logika import WaybillExtractor

class WaybillTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Тестирование извлечения полей накладной")
        self.root.geometry("800x600")

        # Экстрактор (инициализируется при старте, один раз)
        self.extractor = None
        self.init_extractor()

        # Переменные для хранения путей
        self.image1_path = tk.StringVar()
        self.image2_path = tk.StringVar()

        # Виджеты
        self.create_widgets()

    def init_extractor(self):
        """Фоновый запуск инициализации модели (чтобы не заморозить интерфейс)"""
        def load():
            try:
                # Укажите правильный путь к вашему JSON-файлу разметки
                self.extractor = WaybillExtractor(json_path="project-1-at-2026-04-18-05-40-eb2e8e7a.json")
                self.status_label.config(text="Модель загружена", foreground="green")
            except Exception as e:
                self.status_label.config(text=f"Ошибка инициализации: {e}", foreground="red")
        threading.Thread(target=load, daemon=True).start()

    def create_widgets(self):
        # Рамка для выбора файлов
        file_frame = ttk.LabelFrame(self.root, text="Изображения", padding=10)
        file_frame.pack(fill="x", padx=10, pady=5)

        # Первое изображение
        ttk.Label(file_frame, text="Страница 1 (или единственная):").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(file_frame, textvariable=self.image1_path, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="Обзор...", command=lambda: self.browse_file(1)).grid(row=0, column=2)

        # Второе изображение (необязательное)
        ttk.Label(file_frame, text="Страница 2 (опционально):").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(file_frame, textvariable=self.image2_path, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(file_frame, text="Обзор...", command=lambda: self.browse_file(2)).grid(row=1, column=2)

        # Кнопка запуска
        self.run_btn = ttk.Button(self.root, text="Распознать", command=self.run_recognition)
        self.run_btn.pack(pady=10)

        # Статусная строка
        self.status_label = ttk.Label(self.root, text="Инициализация модели...", foreground="blue")
        self.status_label.pack(fill="x", padx=10)

        # Текстовое поле для вывода результата
        output_frame = ttk.LabelFrame(self.root, text="Результат (JSON)", padding=5)
        output_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.output_text = tk.Text(output_frame, wrap="word", font=("Courier", 10))
        scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.output_text.pack(side="left", fill="both", expand=True)

    def browse_file(self, num):
        file_path = filedialog.askopenfilename(
            title=f"Выберите изображение страницы {num}",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"), ("All files", "*.*")]
        )
        if file_path:
            if num == 1:
                self.image1_path.set(file_path)
            else:
                self.image2_path.set(file_path)

    def run_recognition(self):
        path1 = self.image1_path.get().strip()
        if not path1:
            messagebox.showwarning("Нет файла", "Выберите хотя бы одно изображение.")
            return

        paths = [path1]
        path2 = self.image2_path.get().strip()
        if path2:
            paths.append(path2)

        self.run_btn.config(state="disabled")
        self.status_label.config(text="Распознавание...", foreground="orange")
        self.output_text.delete(1.0, tk.END)

        def process():
            try:
                result = self.extractor.extract(paths)
                json_str = json.dumps(result, ensure_ascii=False, indent=2)
                self.root.after(0, self.display_result, json_str)
                self.root.after(0, self.status_label.config, {"text": "Готово", "foreground": "green"})
            except Exception as e:
                self.root.after(0, messagebox.showerror, "Ошибка", str(e))
                self.root.after(0, self.status_label.config, {"text": "Ошибка", "foreground": "red"})
            finally:
                self.root.after(0, lambda: self.run_btn.config(state="normal"))

        threading.Thread(target=process, daemon=True).start()

    def display_result(self, json_str):
        self.output_text.insert(1.0, json_str)

if __name__ == "__main__":
    root = tk.Tk()
    app = WaybillTestApp(root)
    root.mainloop()