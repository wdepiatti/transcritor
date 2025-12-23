#!/usr/bin/env python3
import os
import sys
import tempfile
import subprocess
import hashlib
import json
import shutil
import threading
import time
from pathlib import Path
from datetime import timedelta, datetime
from googletrans import Translator

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
except ImportError:
    sys.exit(1)

whisper = None

# --- Classes de Suporte ---

class ToolTip:
    def __init__(self, widget, text, delay=1000):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tipwindow = None
        self.id = None
        self.root = widget.winfo_toplevel()
    
    def _schedule(self):
        self.cancel()
        self.id = self.root.after(self.delay, self._show_tooltip)
    
    def cancel(self):
        if self.id: self.root.after_cancel(self.id)
        self.id = None
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None
    
    def _show_tooltip(self):
        if self.tipwindow: return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.root)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", 
                 relief=tk.SOLID, borderwidth=1, font=("Arial", 9), padx=5, pady=5).pack()

def adicionar_tooltip(widget, text):
    tip = ToolTip(widget, text)
    widget.bind('<Enter>', lambda e: tip._schedule())
    widget.bind('<Leave>', lambda e: tip.cancel())

# --- Funções de Processamento com Progresso ---

def formatar_tempo(segundos):
    return str(timedelta(seconds=int(segundos)))

def baixar_audio(url, output_dir, callback):
    callback(f"⬇️ Baixando áudio do YouTube...")
    out_tmpl = os.path.join(output_dir, "audio.%(ext)s")
    subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", "-o", out_tmpl, url], 
                   capture_output=True, check=True)
    return str(list(Path(output_dir).glob("audio.*"))[0])

# --- Interface ---

class TranscricaoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Transcritor & Tradutor YouTube Pro")
        self.root.geometry("900x850")
        self.translator = Translator()
        self.processando = False
        self._criar_widgets()

    def _criar_widgets(self):
        main = ttk.Frame(self.root, padding="15")
        main.pack(fill=tk.BOTH, expand=True)

        # URLs
        lbl_urls = ttk.Label(main, text="URLs do YouTube:", font=("Arial", 10, "bold"))
        lbl_urls.pack(anchor=tk.W)
        self.text_urls = scrolledtext.ScrolledText(main, height=6, font=("Consolas", 10))
        self.text_urls.pack(fill=tk.X, pady=5)

        # Configurações
        opts = ttk.LabelFrame(main, text=" Opções e Ferramentas ", padding="10")
        opts.pack(fill=tk.X, pady=10)

        # Modelo e Formato
        ttk.Label(opts, text="Modelo:").grid(row=0, column=0, sticky=tk.W)
        self.var_modelo = tk.StringVar(value="base")
        cb_mod = ttk.Combobox(opts, textvariable=self.var_modelo, values=["tiny", "base", "small", "medium"], width=10)
        cb_mod.grid(row=0, column=1, sticky=tk.W, pady=5)
        adicionar_tooltip(cb_mod, "tiny: Mais rápido\nbase/small: Equilibrado\nmedium: Alta precisão")

        ttk.Label(opts, text="Formato:").grid(row=0, column=2, padx=10, sticky=tk.W)
        self.var_formato = tk.StringVar(value="simples")
        cb_form = ttk.Combobox(opts, textvariable=self.var_formato, values=["simples", "segmentos", "timestamps"], width=12)
        cb_form.grid(row=0, column=3, sticky=tk.W)

        # Tradução
        self.var_traduzir = tk.BooleanVar(value=False)
        chk_trad = ttk.Checkbutton(opts, text="Traduzir para:", variable=self.var_traduzir)
        chk_trad.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.var_lang_dest = tk.StringVar(value="pt")
        ttk.Entry(opts, textvariable=self.var_lang_dest, width=5).grid(row=1, column=1, sticky=tk.W)
        ttk.Label(opts, text="(Ex: pt, en, fr, es)").grid(row=1, column=2, sticky=tk.W)

        # Pasta de Saída
        ttk.Label(opts, text="Salvar em:").grid(row=2, column=0, sticky=tk.W)
        self.var_out = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        f_out = ttk.Frame(opts)
        f_out.grid(row=2, column=1, columnspan=3, sticky="ew", pady=5)
        f_out.columnconfigure(0, weight=1)
        ttk.Entry(f_out, textvariable=self.var_out).grid(row=0, column=0, sticky="ew")
        ttk.Button(f_out, text="📁", width=3, command=lambda: self.var_out.set(filedialog.askdirectory())).grid(row=0, column=1, padx=2)

        # Progresso e Timer
        self.lbl_timer = ttk.Label(main, text="Tempo Decorrido: 00:00:00", font=("Arial", 9, "italic"))
        self.lbl_timer.pack(pady=2)
        self.progress = ttk.Progressbar(main, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=5)

        # Botão
        self.btn_run = ttk.Button(main, text="▶ INICIAR PROCESSO", command=self._iniciar)
        self.btn_run.pack(pady=10)

        # Log
        self.text_log = scrolledtext.ScrolledText(main, height=12, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9))
        self.text_log.pack(fill=tk.BOTH, expand=True)

    def _log(self, msg):
        self.text_log.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.text_log.see(tk.END)
        self.root.update_idletasks()

    def _atualizar_timer(self, inicio, ativo):
        while ativo[0]:
            decorrido = time.time() - inicio
            self.lbl_timer.config(text=f"Tempo Decorrido: {formatar_tempo(decorrido)}")
            time.sleep(1)

    def _traduzir_texto(self, texto, destino):
        try:
            max_p = 3000
            partes = [texto[i:i+max_p] for i in range(0, len(texto), max_p)]
            traduzido = []
            for p in partes:
                traduzido.append(self.translator.translate(p, dest=destino).text)
            return "\n".join(traduzido)
        except Exception as e:
            return f"Erro na tradução: {e}"

    def _iniciar(self):
        urls = [u.strip() for u in self.text_urls.get(1.0, tk.END).split("\n") if u.strip()]
        if not urls: return
        self.processando = True
        self.btn_run.config(state="disabled")
        self.progress.start()
        threading.Thread(target=self._processar, args=(urls,), daemon=True).start()

    def _processar(self, urls):
        global whisper
        if whisper is None:
            self._log("Carregando Whisper AI...")
            import whisper as w
            whisper = w
        
        modelo = whisper.load_model(self.var_modelo.get())
        out_dir = Path(self.var_out.get())
        
        for url in urls:
            try:
                self._log(f"🎬 Iniciando vídeo: {url}")
                inicio_video = time.time()
                timer_ativo = [True]
                threading.Thread(target=self._atualizar_timer, args=(inicio_video, timer_ativo), daemon=True).start()

                with tempfile.TemporaryDirectory() as tmp:
                    # Download
                    audio = baixar_audio(url, tmp, self._log)
                    
                    # Transcrição
                    self._log("🧠 IA processando áudio (isso pode demorar)...")
                    res = modelo.transcribe(audio)
                    
                    # Formatação conforme sua escolha original
                    texto_orig = self._formatar(res, self.var_formato.get())
                    
                    hash_id = hashlib.md5(url.encode()).hexdigest()[:6]
                    arq_orig = out_dir / f"ORIGINAL_{hash_id}.txt"
                    arq_orig.write_text(f"URL: {url}\n\n{texto_orig}", encoding="utf-8")
                    self._log(f"✅ Original salvo em {int(time.time()-inicio_video)}s")

                    # Tradução
                    if self.var_traduzir.get():
                        lang = self.var_lang_dest.get().strip()
                        self._log(f"🌍 Traduzindo para {lang}...")
                        texto_trad = self._traduzir_texto(texto_orig, lang)
                        arq_trad = out_dir / f"TRADUCAO_{lang.upper()}_{hash_id}.txt"
                        arq_trad.write_text(f"URL: {url}\n\n{texto_trad}", encoding="utf-8")
                        self._log(f"✅ Tradução ({lang}) concluída!")

                timer_ativo[0] = False
                self._log(f"✨ Vídeo finalizado em {formatar_tempo(time.time()-inicio_video)}")

            except Exception as e:
                self._log(f"❌ Erro: {e}")

        self.processando = False
        self.progress.stop()
        self.btn_run.config(state="normal")
        if messagebox.askyesno("Fim", "Processo concluído! Abrir pasta?"):
            os.startfile(out_dir) if sys.platform == "win32" else subprocess.run(["xdg-open", out_dir])

    def _formatar(self, result, formato):
        if formato == "simples": return result["text"].strip()
        linhas = []
        for s in result.get("segments", []):
            t = s['text'].strip()
            if formato == "timestamps":
                linhas.append(f"[{formatar_tempo(s['start'])}] {t}")
            else: # segmentos
                linhas.append(t)
        return "\n".join(linhas)

if __name__ == "__main__":
    # Splash screen rápida
    s = tk.Tk()
    s.title("Carregando")
    s.geometry("250x100")
    tk.Label(s, text="Iniciando Motores IA...", pady=20).pack()
    s.after(1500, s.destroy)
    s.mainloop()
    
    root = tk.Tk()
    app = TranscricaoGUI(root)
    root.mainloop()
