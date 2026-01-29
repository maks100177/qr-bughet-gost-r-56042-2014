import customtkinter as ctk
from tkinter import messagebox, filedialog, Menu
import tkinter as tk 
from PIL import Image
import qrcode
import json
import os
import sys
import platform

# Настройки темы
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- ЛОГИКА СОХРАНЕНИЯ В APPDATA (НА ЛОКАЛЬНЫЙ ДИСК) ---
def get_history_file_path():
    # 1. Получаем путь к папке AppData (C:\Users\Name\AppData\Roaming)
    app_data = os.getenv('APPDATA')
    if not app_data:
        app_data = os.path.expanduser("~") # Если вдруг AppData нет, берем корень пользователя
    
    # 2. Создаем подпапку для нашей программы
    save_folder = os.path.join(app_data, "QRBudgetHistory")
    if not os.path.exists(save_folder):
        try:
            os.makedirs(save_folder)
        except Exception as e:
            print(f"Не удалось создать папку: {e}")

    # 3. Формируем имя файла (ИмяКомпьютера.json)
    pc_name = platform.node()
    if not pc_name:
        pc_name = "unknown_pc"
    
    filename = f"{pc_name}.json"
    
    # Итоговый путь: C:\Users\User\AppData\Roaming\QRBudgetHistory\PC-NAME.json
    return os.path.join(save_folder, filename)

HISTORY_FILE = get_history_file_path()

class ModernQRApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Генератор QR (Сохранение в: {HISTORY_FILE})")
        self.geometry("950x800")

        self.history = self.load_history()
        self.entries = {} 
        self.qr_image_object = None 

        # Меню ПКМ
        self.context_menu = Menu(self, tearoff=0)
        self.context_menu.add_command(label="Копировать", command=self.copy_text_context)
        self.context_menu.add_command(label="Вставить", command=self.paste_text_context)
        self.context_menu.add_command(label="Вырезать", command=self.cut_text_context)
        self.target_widget = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === ЛЕВОЕ МЕНЮ ===
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="QR Бюджет", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_gen = ctk.CTkButton(self.sidebar_frame, text="Сгенерировать", command=self.generate_qr, fg_color="#28a745", hover_color="#218838")
        self.btn_gen.grid(row=1, column=0, padx=20, pady=10)

        self.btn_save = ctk.CTkButton(self.sidebar_frame, text="Сохранить PNG", command=self.save_image, state="disabled", fg_color="#007bff", hover_color="#0056b3")
        self.btn_save.grid(row=2, column=0, padx=20, pady=10)
        
        self.btn_clear = ctk.CTkButton(self.sidebar_frame, text="Очистить память", command=self.clear_history_file, fg_color="#dc3545", hover_color="#c82333")
        self.btn_clear.grid(row=3, column=0, padx=20, pady=10)

        self.scaling_label = ctk.CTkLabel(self.sidebar_frame, text="Масштаб:", anchor="w")
        self.scaling_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["80%", "90%", "100%", "110%", "120%", "150%"], command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 20))
        self.scaling_optionemenu.set("100%")

        # === ПРАВАЯ ЧАСТЬ ===
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Реквизиты платежа")
        self.scroll_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.create_form()

        self.qr_label = ctk.CTkLabel(self.scroll_frame, text="")
        self.qr_label.pack(pady=20)

    # --- КЛАВИАТУРА ---
    def bind_hotkeys(self, entry_widget):
        entry_widget.bind("<Control-c>", self.copy_text_event)
        entry_widget.bind("<Control-v>", self.paste_text_event)
        entry_widget.bind("<Control-x>", self.cut_text_event)
        entry_widget.bind("<Control-C>", self.copy_text_event)
        entry_widget.bind("<Control-V>", self.paste_text_event)
        entry_widget.bind("<Control-X>", self.cut_text_event)

    def copy_text_event(self, event):
        try:
            text = event.widget.selection_get()
            self.clipboard_clear()
            self.clipboard_append(text)
            return "break"
        except: pass

    def paste_text_event(self, event):
        try:
            text = self.clipboard_get()
            event.widget.insert(tk.INSERT, text)
            return "break"
        except: pass

    def cut_text_event(self, event):
        try:
            text = event.widget.selection_get()
            self.clipboard_clear()
            self.clipboard_append(text)
            event.widget.delete("sel.first", "sel.last")
            return "break"
        except: pass

    # --- МЫШЬ (ПКМ) ---
    def show_context_menu(self, event):
        self.target_widget = event.widget
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def copy_text_context(self):
        if self.target_widget:
            try:
                text = self.target_widget.selection_get()
                self.clipboard_clear()
                self.clipboard_append(text)
            except: pass

    def paste_text_context(self):
        if self.target_widget:
            try:
                text = self.clipboard_get()
                self.target_widget.insert(tk.INSERT, text)
            except: pass

    def cut_text_context(self):
        if self.target_widget:
            try:
                text = self.target_widget.selection_get()
                self.clipboard_clear()
                self.clipboard_append(text)
                self.target_widget.delete("sel.first", "sel.last")
            except: pass

    # --- ИСТОРИЯ ---
    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return {}
        return {}

    def save_history_to_file(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=4)
        except Exception as e:
            # Можно вывести ошибку в консоль или тихо проигнорировать
            print(f"Ошибка сохранения: {e}")

    # --- ФОРМА ---
    def create_form(self):
        # 1. ПОЛУЧАТЕЛЬ
        self.add_section("ПОЛУЧАТЕЛЬ")
        self.add_field("Наименование получателя *", "Name", "")
        self.add_field("Номер счета получателя *", "PersonalAcc", "")
        
        row1 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row1.pack(fill="x")
        self.add_field("ИНН получателя", "PayeeINN", "", parent=row1, side="left")
        self.add_field("КПП получателя", "KPP", "", parent=row1, side="left")

        # 2. БАНК
        self.add_section("БАНК ПОЛУЧАТЕЛЯ")
        self.add_field("БИК банка *", "BIC", "")
        self.add_field("Наименование банка *", "BankName", "")
        self.add_field("Номер кор. счета банка *", "CorrespAcc", "")

        # 3. БЮДЖЕТ
        self.add_section("БЮДЖЕТНЫЕ РЕКВИЗИТЫ")
        self.add_field("КБК", "CBC", "")
        self.add_field("ОКТМО", "OKTMO", "")

        # Мелкие поля
        grid_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        grid_frame.pack(fill="x", pady=5)
        
        fields_small = [
            ("Статус (101)", "DrawerStatus"), ("Основание (106)", "PaytReason"), ("Период (107)", "TaxPeriod"),
            ("Док. № (108)", "DocNo"), ("Дата док. (109)", "DocDate"), ("Тип (110)", "PaytKind")
        ]
        
        for i, (lbl, key) in enumerate(fields_small):
            fr = ctk.CTkFrame(grid_frame, fg_color="transparent")
            fr.grid(row=i//3, column=i%3, padx=5, pady=5, sticky="ew")
            grid_frame.grid_columnconfigure(i%3, weight=1)
            
            l = ctk.CTkLabel(fr, text=lbl, anchor="w", font=ctk.CTkFont(size=12, weight="bold"))
            l.pack(fill="x")
            
            vals = self.history.get(key, [])
            vals_str = [str(x) for x in vals]
            
            cb = ctk.CTkComboBox(fr, values=vals_str)
            cb.pack(fill="x")
            
            # Если есть история - берем последнее
            if vals_str:
                cb.set(vals_str[0])
            else:
                cb.set("")
            
            cb._entry.bind("<Button-3>", self.show_context_menu)
            self.bind_hotkeys(cb._entry)
            
            self.entries[key] = cb

        # 4. ПЛАТЕЖ
        self.add_section("ДАННЫЕ ПЛАТЕЖА")
        row2 = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row2.pack(fill="x")
        self.add_field("Сумма (руб.)", "SumRub", "", parent=row2, side="left")
        self.add_field("ИНН Плательщика", "PayerINN", "", parent=row2, side="left")
        
        self.add_field("Назначение платежа", "Purpose", "")

    def add_section(self, text):
        lbl = ctk.CTkLabel(self.scroll_frame, text=text, font=ctk.CTkFont(size=16, weight="bold"), text_color=("#3a7ebf", "#1f6aa5"))
        lbl.pack(fill="x", pady=(20, 5), anchor="w")

    def add_field(self, label_text, key, default_val, parent=None, side="top"):
        if parent is None: parent = self.scroll_frame
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", side=side, padx=5, pady=5, expand=True)

        lbl = ctk.CTkLabel(container, text=label_text, anchor="w", font=ctk.CTkFont(size=13))
        lbl.pack(fill="x")

        saved_values = self.history.get(key, [])
        values_str = [str(x) for x in saved_values]
        
        cb = ctk.CTkComboBox(container, values=values_str)
        
        # Если есть история - берем последнее
        if values_str:
            cb.set(values_str[0]) 
        else:
            cb.set(default_val)
            
        cb.pack(fill="x")
        cb._entry.bind("<Button-3>", self.show_context_menu)
        self.bind_hotkeys(cb._entry)
        
        self.entries[key] = cb

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        ctk.set_widget_scaling(new_scaling_float)

    def update_history(self, data):
        for key, value in data.items():
            if not value: continue
            if key not in self.history: self.history[key] = []
            if value in self.history[key]: self.history[key].remove(value)
            self.history[key].insert(0, value)
            self.history[key] = self.history[key][:10]
            
            if key in self.entries:
                self.entries[key].configure(values=[str(x) for x in self.history[key]])
        self.save_history_to_file()

    def clear_history_file(self):
        if messagebox.askyesno("Сброс", f"Удалить историю с этого ПК?"):
            self.history = {}
            if os.path.exists(HISTORY_FILE): os.remove(HISTORY_FILE)
            for key, cb in self.entries.items():
                cb.configure(values=[])
                cb.set("")

    def generate_qr(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        self.update_history(data)

        required_fields = {
            'Name': 'Наименование получателя',
            'PersonalAcc': 'Номер счета получателя',
            'BIC': 'БИК банка',
            'BankName': 'Наименование банка',
            'CorrespAcc': 'Номер кор. счета'
        }

        missing = []
        for key, label in required_fields.items():
            if not data.get(key):
                missing.append(label)

        if missing:
            messagebox.showerror("Ошибка валидации", "Не заполнены:\n" + "\n".join(missing))
            return

        qr_string = "ST00012"
        fields_map = [
            'Name', 'PersonalAcc', 'BankName', 'BIC', 'CorrespAcc',
            'PayeeINN', 'KPP', 'CBC', 'OKTMO', 'PayerINN', 'Purpose',
            'DrawerStatus', 'PaytReason', 'TaxPeriod', 'DocNo', 'DocDate', 'PaytKind'
        ]

        for key in fields_map:
            val = data.get(key)
            if val: qr_string += f"|{key}={val}"

        try:
            rub = data.get('SumRub')
            if rub:
                kopecks = int(float(rub.replace(',', '.')) * 100)
                qr_string += f"|Sum={kopecks}"
        except: pass

        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(qr_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.get_image()

        self.qr_image_object = img
        preview_img = ctk.CTkImage(light_image=img, dark_image=img, size=(300, 300))
        self.qr_label.configure(image=preview_img, text="")
        self.btn_save.configure(state="normal")

    def save_image(self):
        if self.qr_image_object:
            fp = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
            if fp:
                self.qr_image_object.save(fp)
                messagebox.showinfo("Успех", "Сохранено!")

if __name__ == "__main__":
    app = ModernQRApp()
    app.mainloop()