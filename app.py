import os
import sys
import tempfile
import threading
import time
import zipfile
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk

from core.compressor import pack
from core.extractor import unpack_all, extract_file
from core.inspector import list_contents
from core.media_optimizer import optimize_image

# Configuración global estética Dark Tech
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Paleta de color Cyber / Dark Tech
BG_DARK = "#0b0f19"         # Fondo principal profundo
PANEL_BG = "#111827"        # Contenedores y tarjetas
PANEL_BORDER = "#1f2937"    # Bordes sutiles
ACCENT_CYAN = "#0ea5e9"     # Cyan primario
ACCENT_HOVER = "#0284c7"    # Cyan hover
ACCENT_GREEN = "#10b981"    # Verde esmeralda de éxito
ACCENT_AMBER = "#f59e0b"    # Acento warning/media
TEXT_MUTED = "#9ca3af"      # Texto secundario


class SmartPackStudio(ctk.CTk):
    def __init__(self, initial_spk: str = None):
        super().__init__()
        self.title("SmartPack Engine // Enterprise Compression Suite")
        self.geometry("980x640")
        self.minsize(900, 600)
        self.configure(fg_color=BG_DARK)

        self.current_open_spk = initial_spk
        self.active_frame = None

        # Configurar estilos de la tabla nativa (ttk) para que no desentone
        self._configure_treeview_styles()

        # Layout general: Sidebar lateral fija + Panel de contenido dinámico
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_areas()

        # Abrir la primera vista por defecto (Explorador si se pasó archivo, o Empaquetador)
        if initial_spk and os.path.isfile(initial_spk):
            self.show_view("explorer")
            self.entry_exp_path.insert(0, initial_spk)
            self.load_archive_view(initial_spk)
        else:
            self.show_view("pack")

    def _configure_treeview_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=PANEL_BG,
            foreground="#f3f4f6",
            fieldbackground=PANEL_BG,
            rowheight=32,
            font=("Consolas", 10),
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background="#1e293b",
            foreground="#94a3b8",
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
            relief="flat"
        )
        style.map("Treeview", background=[("selected", "#1e3a5f")], foreground=[("selected", "#38bdf8")])
        style.map("Treeview.Heading", background=[("active", "#334155")])

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#090d16", border_width=1, border_color="#1e293b")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(6, weight=1)

        # Logotipo / Header de la app
        lbl_logo = ctk.CTkLabel(
            sidebar, 
            text="⚡ SMARTPACK", 
            font=("Segoe UI", 20, "bold"),
            text_color="#f8fafc"
        )
        lbl_logo.grid(row=0, column=0, padx=20, pady=(24, 4), sticky="w")
        
        lbl_sub = ctk.CTkLabel(
            sidebar, 
            text="v4.2 // Solid Zstandard", 
            font=("Consolas", 11),
            text_color=ACCENT_CYAN
        )
        lbl_sub.grid(row=1, column=0, padx=22, pady=(0, 25), sticky="w")

        # Botones de navegación lateral
        self.nav_buttons = {}
        items = [
            ("pack", "📦 Empaquetador", self.show_view),
            ("explorer", "📂 Visor .SPK", self.show_view),
            ("media", "🖼️ Optimizador", self.show_view),
            ("bench", "⚡ Rendimiento", self.show_view)
        ]

        for i, (key, label, cmd) in enumerate(items, start=2):
            btn = ctk.CTkButton(
                sidebar,
                text=label,
                font=("Segoe UI", 13, "bold"),
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                text_color="#94a3b8",
                hover_color="#1e293b",
                command=lambda k=key: cmd(k)
            )
            btn.grid(row=i, column=0, padx=14, pady=4, sticky="ew")
            self.nav_buttons[key] = btn

        # Telemetría de estado en el footer lateral
        status_card = ctk.CTkFrame(sidebar, fg_color="#0d1424", border_width=1, border_color="#1e293b", corner_radius=8)
        status_card.grid(row=7, column=0, padx=14, pady=20, sticky="ew")

        ctk.CTkLabel(status_card, text="ENGINE STATUS", font=("Consolas", 9, "bold"), text_color="#64748b").pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkLabel(status_card, text="● CPU Ready (Zstd L22)", font=("Consolas", 10), text_color="#10b981").pack(anchor="w", padx=10, pady=(0, 8))

    def _build_content_areas(self):
        self.container = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.views = {
            "pack": self._view_pack(),
            "explorer": self._view_explorer(),
            "media": self._view_media(),
            "bench": self._view_bench()
        }

    def show_view(self, key):
        # Ocultar vista anterior
        if self.active_frame:
            self.active_frame.grid_forget()
        
        # Actualizar colores de selección en el menú
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color="#1e293b", text_color=ACCENT_CYAN)
            else:
                btn.configure(fg_color="transparent", text_color="#94a3b8")

        self.active_frame = self.views[key]
        self.active_frame.grid(row=0, column=0, sticky="nsew")

    # ==================== VISTA 1: EMPAQUETADOR ====================
    def _view_pack(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        
        # Header de sección
        ctk.CTkLabel(f, text="Empaquetado Sólido de Nueva Generación", font=("Segoe UI", 22, "bold"), text_color="#f8fafc").pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f, text="Agrupa flujos continuos y elimina redundancias cruzadas a nivel binario.", font=("Segoe UI", 12), text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 20))

        # Tarjeta de compresión
        card = ctk.CTkFrame(f, fg_color=PANEL_BG, border_width=1, border_color=PANEL_BORDER, corner_radius=12)
        card.pack(fill="x", pady=10, padx=2)

        ctk.CTkLabel(card, text="DIRECTORIO ORIGEN", font=("Consolas", 10, "bold"), text_color=ACCENT_CYAN).pack(anchor="w", padx=20, pady=(18, 6))
        
        box_input = ctk.CTkFrame(card, fg_color="transparent")
        box_input.pack(fill="x", padx=20, pady=(0, 15))
        self.entry_pack_src = ctk.CTkEntry(box_input, placeholder_text="Selecciona la carpeta a comprimir...", height=40, font=("Consolas", 11), border_color="#374151")
        self.entry_pack_src.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(box_input, text="Examinar", width=100, height=40, fg_color="#1f2937", hover_color="#374151", command=self._browse_pack).pack(side="right")

        # Nivel de compresión / Parámetros
        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(opts, text="Nivel de compresión ZSTD: Ultra (Nivel 22)", font=("Segoe UI", 12), text_color="#e2e8f0").pack(side="left")
        
        self.btn_pack_run = ctk.CTkButton(
            card, 
            text="⚡ INICIAR COMPRESIÓN SÓLIDA (.SPK)", 
            height=46, 
            corner_radius=8,
            font=("Segoe UI", 13, "bold"), 
            fg_color=ACCENT_CYAN, 
            hover_color=ACCENT_HOVER,
            command=self._start_pack_thread
        )
        self.btn_pack_run.pack(fill="x", padx=20, pady=(0, 20))

        # Monitor de estado y progreso
        self.card_status = ctk.CTkFrame(f, fg_color="#090d16", border_width=1, border_color="#1e293b", corner_radius=10)
        self.card_status.pack(fill="x", pady=15, padx=2)
        
        self.lbl_pack_telemetry = ctk.CTkLabel(
            self.card_status, 
            text="Esperando selección de archivo para inicializar flujo...", 
            font=("Consolas", 11), 
            text_color="#64748b"
        )
        self.lbl_pack_telemetry.pack(anchor="w", padx=16, pady=12)

        return f

    # ==================== VISTA 2: VISOR EXPLORADOR ====================
    def _view_explorer(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        
        ctk.CTkLabel(f, text="Visor e Índice Instantáneo (.SPK)", font=("Segoe UI", 22, "bold"), text_color="#f8fafc").pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f, text="Inspecciona el manifiesto o extrae elementos puntuales sin descomprimir el contenedor completo.", font=("Segoe UI", 12), text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 15))

        top = ctk.CTkFrame(f, fg_color=PANEL_BG, border_width=1, border_color=PANEL_BORDER, corner_radius=10)
        top.pack(fill="x", pady=(0, 15), padx=2)

        self.entry_exp_path = ctk.CTkEntry(top, placeholder_text="Ruta del contenedor .spk...", height=38, font=("Consolas", 11), border_color="#374151")
        self.entry_exp_path.pack(side="left", fill="x", expand=True, padx=12, pady=10)

        ctk.CTkButton(top, text="Abrir .SPK", width=95, height=38, fg_color="#1f2937", hover_color="#374151", command=self._browse_spk).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Extraer Todo", width=110, height=38, fg_color=ACCENT_GREEN, hover_color="#059669", font=("Segoe UI", 12, "bold"), command=self._extract_all).pack(side="left", padx=(4, 12))

        # Tabla estilo terminal moderna
        table_container = ctk.CTkFrame(f, fg_color=PANEL_BG, border_width=1, border_color=PANEL_BORDER, corner_radius=10)
        table_container.pack(fill="both", expand=True, padx=2, pady=(0, 10))

        cols = ("name", "size")
        self.tree = ttk.Treeview(table_container, columns=cols, show="headings")
        self.tree.heading("name", text="  NOMBRE DEL ARCHIVO / RUTA INTERNA")
        self.tree.heading("size", text="TAMAÑO  ")
        self.tree.column("name", width=520, anchor="w")
        self.tree.column("size", width=140, anchor="e")

        sb = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="right", fill="y", pady=8, padx=4)

        self.tree.bind("<Double-1>", self._on_double_click)

        self.lbl_exp_info = ctk.CTkLabel(f, text="💡 Consejo: Haz doble clic en cualquier fila para previsualizar el archivo de inmediato en Windows.", font=("Segoe UI", 11), text_color="#64748b")
        self.lbl_exp_info.pack(anchor="w", padx=4)

        return f

    # ==================== VISTA 3: OPTIMIZADOR MULTIMEDIA ====================
    def _view_media(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        
        ctk.CTkLabel(f, text="Optimizador Cuántico de Imágenes", font=("Segoe UI", 22, "bold"), text_color="#f8fafc").pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f, text="Aplica cuantización octree inteligente y preservación de canal alfa para formatos WebP.", font=("Segoe UI", 12), text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 20))

        card = ctk.CTkFrame(f, fg_color=PANEL_BG, border_width=1, border_color=PANEL_BORDER, corner_radius=12)
        card.pack(fill="x", pady=10, padx=2)

        ctk.CTkLabel(card, text="IMAGEN ORIGEN (PNG / JPG / WEBP)", font=("Consolas", 10, "bold"), text_color=ACCENT_AMBER).pack(anchor="w", padx=20, pady=(18, 6))

        box = ctk.CTkFrame(card, fg_color="transparent")
        box.pack(fill="x", padx=20, pady=(0, 15))
        self.entry_img = ctk.CTkEntry(box, placeholder_text="Selecciona un recurso gráfico...", height=40, font=("Consolas", 11), border_color="#374151")
        self.entry_img.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(box, text="Examinar", width=100, height=40, fg_color="#1f2937", hover_color="#374151", command=self._browse_img).pack(side="right")

        # Controles
        ctrls = ctk.CTkFrame(card, fg_color="transparent")
        ctrls.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(ctrls, text="Calidad de salida:", font=("Segoe UI", 12)).pack(side="left", padx=(0, 10))
        self.slider_q = ctk.CTkSlider(ctrls, from_=50, to=95, number_of_steps=45, width=220)
        self.slider_q.set(80)
        self.slider_q.pack(side="left", padx=10)

        self.lbl_q_val = ctk.CTkLabel(ctrls, text="80%", font=("Consolas", 12, "bold"), text_color=ACCENT_CYAN)
        self.lbl_q_val.pack(side="left", padx=6)
        self.slider_q.configure(command=lambda val: self.lbl_q_val.configure(text=f"{int(val)}%"))

        ctk.CTkButton(
            card, 
            text="✨ EJECUTAR OPTIMIZACIÓN", 
            height=46, 
            corner_radius=8, 
            font=("Segoe UI", 13, "bold"),
            fg_color=ACCENT_AMBER, 
            hover_color="#d97706",
            command=self._run_media_opt
        ).pack(fill="x", padx=20, pady=(0, 20))

        # Log de resultados
        self.txt_media_log = ctk.CTkTextbox(f, fg_color="#090d16", border_width=1, border_color="#1e293b", corner_radius=10, font=("Consolas", 11), height=140)
        self.txt_media_log.pack(fill="both", expand=True, padx=2, pady=10)

        return f

    # ==================== VISTA 4: BENCHMARK ====================
    def _view_bench(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        
        ctk.CTkLabel(f, text="Benchmark en Vivo vs ZIP Clásico", font=("Segoe UI", 22, "bold"), text_color="#f8fafc").pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(f, text="Compara directamente la ratio de compresión y eficiencia de bytes frente al estándar de Windows.", font=("Segoe UI", 12), text_color=TEXT_MUTED).pack(anchor="w", pady=(0, 20))

        top = ctk.CTkFrame(f, fg_color=PANEL_BG, border_width=1, border_color=PANEL_BORDER, corner_radius=10)
        top.pack(fill="x", pady=(0, 15), padx=2)

        self.entry_bench = ctk.CTkEntry(top, placeholder_text="Selecciona carpeta para medir...", height=38, font=("Consolas", 11), border_color="#374151")
        self.entry_bench.pack(side="left", fill="x", expand=True, padx=12, pady=10)

        ctk.CTkButton(top, text="Examinar", width=95, height=38, fg_color="#1f2937", hover_color="#374151", command=self._browse_bench).pack(side="left", padx=4)
        self.btn_run_b = ctk.CTkButton(top, text="⚡ Medir Ahora", width=120, height=38, fg_color="#6366f1", hover_color="#4f46e5", font=("Segoe UI", 12, "bold"), command=self._start_bench)
        self.btn_run_b.pack(side="left", padx=(4, 12))

        self.txt_bench_out = ctk.CTkTextbox(f, fg_color="#090d16", border_width=1, border_color="#1e293b", corner_radius=10, font=("Consolas", 12), height=260)
        self.txt_bench_out.pack(fill="both", expand=True, padx=2, pady=10)

        return f

    # ==================== LÓGICA DE NEGOCIO ====================
    def _browse_pack(self):
        p = filedialog.askdirectory()
        if p:
            self.entry_pack_src.delete(0, "end")
            self.entry_pack_src.insert(0, p)

    def _browse_spk(self):
        p = filedialog.askopenfilename(filetypes=[("SmartPack Archive", "*.spk")])
        if p:
            self.entry_exp_path.delete(0, "end")
            self.entry_exp_path.insert(0, p)
            self.load_archive_view(p)

    def _browse_img(self):
        p = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")])
        if p:
            self.entry_img.delete(0, "end")
            self.entry_img.insert(0, p)

    def _browse_bench(self):
        p = filedialog.askdirectory()
        if p:
            self.entry_bench.delete(0, "end")
            self.entry_bench.insert(0, p)

    def load_archive_view(self, spk_path):
        self.current_open_spk = spk_path
        for r in self.tree.get_children():
            self.tree.delete(r)
        try:
            items = list_contents(spk_path)
            for it in items:
                size_str = f"{it['size']/1024:.2f} KB" if it['size'] >= 1024 else f"{it['size']} B"
                self.tree.insert("", "end", values=(it["path"], size_str))
            self.lbl_exp_info.configure(text=f"Total: {len(items)} archivos indexados en este contenedor.", text_color=ACCENT_CYAN)
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al leer paquete: {e}")

    def _on_double_click(self, event):
        sel = self.tree.selection()
        if not sel or not self.current_open_spk:
            return
        filename = self.tree.item(sel[0], "values")[0]
        extracted = extract_file(self.current_open_spk, filename, tempfile.gettempdir())
        if extracted and os.path.exists(extracted):
            os.startfile(extracted)

    def _extract_all(self):
        if not self.current_open_spk:
            messagebox.showwarning("Aviso", "Primero abre un archivo .spk válido.")
            return
        dest = filedialog.askdirectory(title="Carpeta destino para desempacar")
        if dest:
            count = unpack_all(self.current_open_spk, dest)
            messagebox.showinfo("SmartPack", f"Extracción completa: {count} archivos restaurados.")

    def _start_pack_thread(self):
        src = self.entry_pack_src.get().strip()
        if not os.path.isdir(src):
            messagebox.showerror("Error", "Selecciona una carpeta válida.")
            return
        out = filedialog.asksaveasfilename(defaultextension=".spk", filetypes=[("SmartPack Archive", "*.spk")])
        if not out:
            return

        def _worker():
            self.btn_pack_run.configure(state="disabled")
            self.lbl_pack_telemetry.configure(text="Procesando árbol de archivos y reduciendo redundancias con Zstd L22...", text_color=ACCENT_CYAN)
            t0 = time.perf_counter()
            raw_s, comp_s, count = pack(src, out)
            dur = time.perf_counter() - t0
            pct = (1 - (comp_s / raw_s)) * 100 if raw_s else 0
            self.lbl_pack_telemetry.configure(
                text=f"✔ Empaquetado exitoso: {count} archivos | {raw_s/1024/1024:.2f} MB -> {comp_s/1024/1024:.2f} MB ({pct:.1f}% ahorro) en {dur:.2f}s",
                text_color=ACCENT_GREEN
            )
            self.btn_pack_run.configure(state="normal")

        threading.Thread(target=_worker, daemon=True).start()

    def _run_media_opt(self):
        src = self.entry_img.get().strip()
        if not os.path.isfile(src):
            messagebox.showerror("Error", "Selecciona una imagen existente.")
            return
        q = int(self.slider_q.get())
        out_f, orig, new, pct = optimize_image(src, quality=q)
        self.txt_media_log.delete("1.0", "end")
        self.txt_media_log.insert("end", f"[+] Proceso completado con éxito:\n")
        self.txt_media_log.insert("end", f"    Archivo generado: {out_f}\n")
        self.txt_media_log.insert("end", f"    Tamaño original : {orig/1024:.2f} KB\n")
        self.txt_media_log.insert("end", f"    Tamaño final    : {new/1024:.2f} KB\n")
        sign = "+" if pct > 0 else ""
        self.txt_media_log.insert("end", f"    Eficiencia      : {sign}{pct:.2f}% de reducción\n")

    def _start_bench(self):
        folder = self.entry_bench.get().strip()
        if not os.path.isdir(folder):
            messagebox.showerror("Error", "Selecciona una carpeta válida.")
            return

        def _worker():
            self.btn_run_b.configure(state="disabled")
            self.txt_bench_out.delete("1.0", "end")
            self.txt_bench_out.insert("end", f"Iniciando telemetría de rendimiento para: {folder}\n\n")
            
            z_temp, spk_temp = "b_temp.zip", "b_temp.spk"

            # Test ZIP
            t0 = time.perf_counter()
            with zipfile.ZipFile(z_temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                for r, _, files in os.walk(folder):
                    for fl in files:
                        fp = os.path.join(r, fl)
                        zf.write(fp, os.path.relpath(fp, folder))
            zt = time.perf_counter() - t0
            zs = os.path.getsize(z_temp)

            # Test SPK
            t0 = time.perf_counter()
            raw_s, spk_s, count = pack(folder, spk_temp)
            spkt = time.perf_counter() - t0

            diff = zs - spk_s
            pct = (diff / zs) * 100

            out_text =  f"{'MÉTRICA':<18} | {'ZIP ESTÁNDAR':<16} | {'SMARTPACK SÓLIDO':<16}\n"
            out_text += f"{'-'*56}\n"
            out_text += f"{'Tamaño final':<18} | {zs/1024/1024:8.2f} MB       | {spk_s/1024/1024:8.2f} MB\n"
            out_text += f"{'Tiempo CPU':<18} | {zt:8.2f} s        | {spkt:8.2f} s\n"
            out_text += f"{'Ahorro neto':<18} | {'Base (0%)':<16} | {pct:+6.2f}% menor que ZIP\n"
            out_text += f"{'-'*56}\n"
            out_text += f"Diferencia de espacio liberado: {diff/1024:.2f} KB\n"

            self.txt_bench_out.insert("end", out_text)
            self.btn_run_b.configure(state="normal")
            
            for f in [z_temp, spk_temp]:
                if os.path.exists(f): os.remove(f)

        threading.Thread(target=_worker, daemon=True).start()


if __name__ == "__main__":
    initial_file = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith(".spk") else None
    app = SmartPackStudio(initial_file)
    app.mainloop()