#!/usr/bin/env python3
"""
Aplicação GUI para transcrever vídeos do YouTube para arquivo TXT.
Usa yt-dlp para baixar o áudio e Whisper para transcrever.
Suporta múltiplos vídeos, cache, barra de progresso e formatação avançada.
"""

import os
import sys
import tempfile
import subprocess
import hashlib
import json
import shutil
import threading
import socket
import time
import random
import string
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import timedelta, datetime

# Importa tkinter primeiro (leve)
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
except ImportError:
    print("Erro: tkinter não encontrado.")
    print("No Windows, tkinter geralmente já vem instalado com Python.")
    sys.exit(1)

# Whisper será importado depois (pesado)
whisper = None


class ToolTip:
    """Classe para criar tooltips (dicas ao passar o mouse)."""
    
    def __init__(self, widget, text='widget info', delay=1500):
        self.widget = widget
        self.text = text
        self.delay = delay  # Delay maior para não atrapalhar
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        # Obter a janela raiz para usar after()
        self.root = widget.winfo_toplevel()
    
    def _schedule(self):
        self.cancel()
        # Delay maior para não aparecer muito rápido
        self.id = self.root.after(self.delay, self._show_tooltip)
    
    def cancel(self):
        if self.id:
            self.root.after_cancel(self.id)
            self.id = None
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None
    
    def _show_tooltip(self):
        # Só mostra se o mouse ainda estiver sobre o widget
        try:
            # Obter posição do widget
            widget_x = self.widget.winfo_rootx()
            widget_y = self.widget.winfo_rooty()
            widget_width = self.widget.winfo_width()
            widget_height = self.widget.winfo_height()
            
            # Posicionar tooltip abaixo do widget, alinhado à esquerda
            x = widget_x
            y = widget_y + widget_height + 5
            
            # Se não couber abaixo, colocar acima
            screen_height = self.root.winfo_screenheight()
            if y + 250 > screen_height:
                y = widget_y - 250
            
            # Se não couber à direita, ajustar
            screen_width = self.root.winfo_screenwidth()
            if x + 420 > screen_width:
                x = screen_width - 420 - 10
            
            if x < 10:
                x = 10
            
        except:
            # Fallback: usar posição do mouse
            x = self.root.winfo_pointerx() + 15
            y = self.root.winfo_pointery() + 15
        
        # Verificar se já existe tooltip
        if self.tipwindow:
            return
        
        self.tipwindow = tw = tk.Toplevel(self.root)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        
        # Não bloquear eventos - tooltip não intercepta cliques
        tw.attributes('-topmost', True)
        try:
            tw.attributes('-alpha', 0.98)  # Levemente transparente (se suportado)
        except:
            pass
        
        # Frame principal com sombra visual
        frame = tk.Frame(tw, bg="#ffffe0", relief=tk.SOLID, borderwidth=2)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Label com texto
        label = tk.Label(
            frame,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            foreground="#000000",
            font=("Arial", 9),
            wraplength=400,
            padx=10,
            pady=8
        )
        label.pack(ipadx=2, ipady=2)
        
        # Fechar ao clicar em qualquer lugar ou ao pressionar ESC
        def fechar_tooltip(event=None):
            self.cancel()
        
        tw.bind('<Button-1>', fechar_tooltip)
        tw.bind('<Button-2>', fechar_tooltip)
        tw.bind('<Button-3>', fechar_tooltip)
        tw.bind('<Escape>', fechar_tooltip)
        label.bind('<Button-1>', fechar_tooltip)
        frame.bind('<Button-1>', fechar_tooltip)
        
        # Fechar quando mouse sair da tooltip também
        def on_leave_tooltip(event=None):
            self.root.after(300, self.cancel)
        
        tw.bind('<Leave>', on_leave_tooltip)
    
    def _enter(self, event=None):
        self._schedule()
    
    def _leave(self, event=None):
        # Delay antes de fechar para permitir mover mouse para tooltip
        self.root.after(200, self.cancel)
    
    def _motion(self, event=None):
        # Se mouse se mover, cancela e agenda novamente
        self._schedule()


def criar_tooltip(widget, text, delay=2000, modo='hover'):
    """
    Função helper para criar tooltip em um widget.
    
    Args:
        widget: Widget para adicionar tooltip
        text: Texto do tooltip
        delay: Delay em ms antes de mostrar (padrão: 2000ms = 2 segundos)
        modo: 'hover' (ao passar mouse) ou 'click' (ao clicar com botão direito)
    """
    tooltip = ToolTip(widget, text, delay=delay)
    
    if modo == 'click':
        # Modo click: só mostra ao clicar com botão direito
        def mostrar_ajuda(event=None):
            tooltip._show_tooltip()
        
        widget.bind('<Button-3>', mostrar_ajuda)  # Botão direito
        widget.bind('<Control-Button-1>', mostrar_ajuda)  # Ctrl + Clique esquerdo
    else:
        # Modo hover: mostra ao passar mouse (com delay maior)
        widget.bind('<Enter>', tooltip._enter)
        widget.bind('<Leave>', tooltip._leave)
        widget.bind('<Motion>', tooltip._motion)
    
    return tooltip


class CacheManager:
    """Gerencia cache de transcrições para evitar re-processamento."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        # Usa pasta do usuário por padrão: C:\Users\nome-usuario\.cache_transcritor
        if cache_dir is None:
            user_home = os.path.expanduser("~")
            cache_dir = os.path.join(user_home, ".cache_transcritor")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata = self._carregar_metadata()
    
    def _carregar_metadata(self) -> Dict:
        """Carrega metadados do cache."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _salvar_metadata(self):
        """Salva metadados do cache."""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
    
    def _hash_url(self, url: str) -> str:
        """Gera hash da URL para usar como identificador."""
        return hashlib.md5(url.encode()).hexdigest()
    
    def obter_caminho_cache(self, url: str) -> Optional[Path]:
        """Retorna o caminho do arquivo em cache se existir."""
        url_hash = self._hash_url(url)
        cache_file = self.cache_dir / f"{url_hash}.txt"
        
        if cache_file.exists() and url_hash in self.metadata:
            return cache_file
        return None
    
    def salvar_cache(self, url: str, texto: str, formato: str = "simples"):
        """Salva transcrição no cache."""
        url_hash = self._hash_url(url)
        cache_file = self.cache_dir / f"{url_hash}.txt"
        
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(texto)
        
        self.metadata[url_hash] = {
            "url": url,
            "formato": formato,
            "tamanho": len(texto)
        }
        self._salvar_metadata()
    
    def limpar_cache(self):
        """Remove todos os arquivos de cache."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            return True
        return False


def encontrar_ytdlp() -> Optional[str]:
    """
    Encontra o executável yt-dlp ou retorna None para usar módulo Python.
    Funciona tanto em desenvolvimento quanto no executável PyInstaller.
    """
    # Se está rodando como executável PyInstaller, sempre usa módulo Python
    if getattr(sys, 'frozen', False):
        try:
            import yt_dlp
            return None  # Usa módulo Python
        except ImportError:
            raise Exception(
                "yt-dlp não encontrado no executável.\n\n"
                "O módulo yt_dlp deveria estar incluído no build.\n"
                "Reconstrua o executável com: python build_exe.py"
            )
    
    # Modo desenvolvimento: tenta executável primeiro, depois módulo Python
    # Procura executável yt-dlp
    ytdlp_paths = [
        shutil.which("yt-dlp"),
        "yt-dlp.exe",  # Windows
        "yt-dlp"  # Linux/Mac
    ]
    
    # Testa cada caminho de executável
    for ytdlp_path in ytdlp_paths:
        if ytdlp_path:
            try:
                # Verifica se é um arquivo executável válido
                if os.path.isfile(ytdlp_path) and not ytdlp_path.endswith('.py'):
                    # Testa se funciona
                    result = subprocess.run(
                        [ytdlp_path, "--version"],
                        capture_output=True,
                        check=True,
                        timeout=5
                    )
                    return ytdlp_path
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue
    
    # Se não encontrou executável, tenta usar yt_dlp como módulo Python
    try:
        import yt_dlp
        return None  # Indica uso do módulo Python
    except ImportError:
        raise Exception(
            "yt-dlp não encontrado.\n\n"
            "Soluções:\n"
            "1. Instale: pip install yt-dlp\n"
            "2. Ou baixe yt-dlp.exe e coloque no PATH do sistema"
        )


def obter_info_video(url: str) -> Dict:
    """Obtém informações do vídeo usando yt-dlp."""
    try:
        ytdlp_cmd = encontrar_ytdlp()
        
        # Se encontrou o executável
        if ytdlp_cmd:
            cmd = [
                ytdlp_cmd,
                "--dump-json",
                "--no-playlist",
                url
            ]
            result = subprocess.run(cmd, capture_output=True, check=True, text=True, timeout=30)
            return json.loads(result.stdout)
        else:
            # Usa módulo Python
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
    except Exception as e:
        return {}


def baixar_audio_youtube(url: str, output_dir: str, callback=None) -> str:
    """Baixa o áudio de um vídeo do YouTube usando yt-dlp."""
    ytdlp_cmd = encontrar_ytdlp()
    
    output_path = os.path.join(output_dir, "audio.%(ext)s")
    
    if ytdlp_cmd:
        # Usa executável yt-dlp
        cmd = [
            ytdlp_cmd,
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", output_path,
            "--quiet",
            "--no-warnings",
            url
        ]
        
        if callback:
            callback(f"Baixando áudio: {url}")
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=600)
            
            audio_files = list(Path(output_dir).glob("audio.*"))
            if audio_files:
                return str(audio_files[0])
            else:
                raise FileNotFoundError("Arquivo de áudio não encontrado após download")
                
        except subprocess.TimeoutExpired:
            raise Exception("Timeout ao baixar o vídeo (muito longo ou conexão lenta)")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Erro ao baixar o vídeo: {e.stderr.decode() if e.stderr else str(e)}")
    else:
        # Usa módulo Python yt_dlp
        try:
            import yt_dlp
            
            if callback:
                callback(f"Baixando áudio: {url}")
            
            # Tenta baixar como MP3 primeiro, se não conseguir, baixa o melhor formato disponível
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(output_dir, 'audio.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }
            
            # Tenta adicionar conversão para MP3 se FFmpeg estiver disponível
            try:
                # Verifica se ffmpeg está disponível
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=2)
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # FFmpeg não disponível, baixa no formato original
                if callback:
                    callback("FFmpeg não encontrado, baixando no formato original")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Procura arquivo de áudio (qualquer extensão)
            audio_files = list(Path(output_dir).glob("audio.*"))
            if audio_files:
                return str(audio_files[0])
            else:
                raise FileNotFoundError("Arquivo de áudio não encontrado após download")
                
        except ImportError:
            raise Exception(
                "yt-dlp não encontrado.\n\n"
                "Soluções:\n"
                "1. Instale: pip install yt-dlp\n"
                "2. Ou baixe yt-dlp.exe e coloque no PATH do sistema"
            )
        except Exception as e:
            raise Exception(f"Erro ao baixar o vídeo: {str(e)}")


def formatar_tempo(segundos: float) -> str:
    """Formata segundos em formato HH:MM:SS."""
    td = timedelta(seconds=int(segundos))
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def formatar_tempo_curto(segundos: float) -> str:
    """Formata segundos em formato HH:MM (sem segundos)."""
    td = timedelta(seconds=int(segundos))
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def gerar_nome_aleatorio(comprimento: int = 12) -> str:
    """Gera um nome aleatório para arquivos."""
    caracteres = string.ascii_lowercase + string.digits
    return ''.join(random.choice(caracteres) for _ in range(comprimento))


def formatar_transcricao(result: Dict, formato: str = "simples") -> str:
    """Formata a transcrição de acordo com o formato especificado."""
    if formato == "simples":
        return result["text"]
    
    elif formato == "segmentos":
        linhas = []
        for segment in result.get("segments", []):
            texto = segment["text"].strip()
            if texto:
                linhas.append(texto)
        return "\n\n".join(linhas)
    
    elif formato == "timestamps":
        linhas = []
        segments = result.get("segments", [])
        
        if not segments:
            # Se não há segments, retorna texto simples com aviso
            return result.get("text", "")
        
        for segment in segments:
            inicio_seg = segment.get("start", 0)
            texto = segment.get("text", "").strip()
            
            if texto:
                # Formato: timestamp em uma linha (HH:MM), texto na próxima
                inicio_formatado = formatar_tempo_curto(inicio_seg)
                linhas.append(inicio_formatado)
                linhas.append(texto)
        
        # Retorna com quebras de linha entre timestamp e texto
        return "\n".join(linhas)
    
    else:
        return result["text"]


def formatar_tempo_decorrido(segundos: float) -> str:
    """Formata tempo decorrido em formato legível."""
    if segundos < 60:
        return f"{int(segundos)}s"
    elif segundos < 3600:
        minutos = int(segundos // 60)
        segs = int(segundos % 60)
        return f"{minutos}m {segs}s"
    else:
        horas = int(segundos // 3600)
        minutos = int((segundos % 3600) // 60)
        segs = int(segundos % 60)
        return f"{horas}h {minutos}m {segs}s"


def estimar_tempo_transcricao(tamanho_arquivo_mb: float, model_name: str) -> float:
    """
    Estima tempo de transcrição baseado no tamanho do arquivo e modelo.
    Retorna estimativa em segundos.
    """
    # Fatores de velocidade aproximados (segundos por MB de áudio)
    fatores = {
        "tiny": 2.0,    # ~2s por MB
        "base": 3.5,    # ~3.5s por MB
        "small": 6.0,   # ~6s por MB
        "medium": 12.0, # ~12s por MB
        "large": 25.0   # ~25s por MB
    }
    
    fator = fatores.get(model_name, 3.5)
    return tamanho_arquivo_mb * fator


def transcrever_audio(
    audio_path: str,
    model_name: str = "base",
    language: Optional[str] = None,
    callback=None,
    callback_progresso=None
) -> Dict:
    """Transcreve um arquivo de áudio usando Whisper."""
    global whisper
    
    if whisper is None:
        raise Exception("Whisper não foi carregado. Reinicie a aplicação.")
    
    inicio = time.time()
    
    if callback:
        callback(f"Carregando modelo Whisper: {model_name}")
    
    model = whisper.load_model(model_name)
    
    # Obtém informações do arquivo para estimativa
    try:
        tamanho_mb = os.path.getsize(audio_path) / (1024 * 1024)
        tempo_estimado = estimar_tempo_transcricao(tamanho_mb, model_name)
        if callback:
            callback(f"Arquivo de áudio: {tamanho_mb:.2f} MB")
            callback(f"Tempo estimado: ~{formatar_tempo_decorrido(tempo_estimado)}")
    except:
        pass
    
    if callback:
        callback(f"Transcrevendo áudio...")
    
    # Inicia timer de atualização
    timer_ativo = [True]
    
    def atualizar_timer():
        """Atualiza timer enquanto transcrição está em andamento."""
        while timer_ativo[0]:
            tempo_decorrido = time.time() - inicio
            if callback_progresso:
                callback_progresso(f"Tempo decorrido: {formatar_tempo_decorrido(tempo_decorrido)}")
            time.sleep(1)  # Atualiza a cada segundo
    
    timer_thread = threading.Thread(target=atualizar_timer, daemon=True)
    timer_thread.start()
    
    try:
        result = model.transcribe(
            audio_path,
            language=language,
            verbose=False,
            word_timestamps=False  # Não precisa de timestamps por palavra
        )
        
        # Garante que segments existam no resultado
        if "segments" not in result or not result["segments"]:
            # Se não há segments, cria um segment único com todo o texto
            if "text" in result:
                result["segments"] = [{
                    "start": 0.0,
                    "end": 0.0,
                    "text": result["text"]
                }]
    finally:
        timer_ativo[0] = False
    
    tempo_total = time.time() - inicio
    
    if callback:
        idioma_detectado = result.get("language", "desconhecido")
        callback(f"Idioma detectado: {idioma_detectado}")
        callback(f"✓ Transcrição concluída em {formatar_tempo_decorrido(tempo_total)}")
    
    return result


def processar_video(
    url: str,
    model_name: str = "base",
    language: Optional[str] = None,
    formato: str = "simples",
    cache: Optional[CacheManager] = None,
    usar_cache: bool = True,
    manter_audio: bool = False,
    output_dir: Optional[str] = None,
    callback=None,
    callback_progresso=None
) -> Tuple[str, str]:
    """Processa um único vídeo: baixa, transcreve e formata."""
    if usar_cache and cache:
        cache_file = cache.obter_caminho_cache(url)
        if cache_file:
            if callback:
                callback(f"✓ Usando transcrição em cache")
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read(), ""
    
    info = obter_info_video(url)
    titulo = info.get("title", "Vídeo sem título")
    if callback:
        callback(f"📹 Processando: {titulo}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = baixar_audio_youtube(url, temp_dir, callback)
        result = transcrever_audio(
            audio_path, 
            model_name, 
            language, 
            callback,
            callback_progresso
        )
        texto_formatado = formatar_transcricao(result, formato)
        
        if cache:
            cache.salvar_cache(url, texto_formatado, formato)
        
        audio_final = ""
        if manter_audio and output_dir:
            audio_dest = Path(output_dir) / f"{hashlib.md5(url.encode()).hexdigest()}.mp3"
            shutil.copy2(audio_path, audio_dest)
            audio_final = str(audio_dest)
        
        return texto_formatado, audio_final


class TranscricaoGUI:
    """Interface gráfica para transcrição de vídeos do YouTube."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Transcritor de Vídeos do YouTube")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Variáveis
        self.cache = CacheManager()
        self.processando = False
        self.thread_processamento = None
        self.tempo_inicio_processamento = None
        
        # Configurar estilo
        self._configurar_estilo()
        
        # Criar interface
        self._criar_widgets()
        
        # Centralizar janela
        self._centralizar_janela()
    
    def _configurar_estilo(self):
        """Configura o estilo da interface."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Cores personalizadas
        self.cor_primaria = "#2c3e50"
        self.cor_secundaria = "#3498db"
        self.cor_sucesso = "#27ae60"
        self.cor_erro = "#e74c3c"
    
    def _centralizar_janela(self):
        """Centraliza a janela na tela."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def _criar_widgets(self):
        """Cria todos os widgets da interface."""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Título
        titulo = ttk.Label(
            main_frame,
            text="🎬 Transcritor de Vídeos do YouTube",
            font=("Arial", 16, "bold")
        )
        titulo.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # URLs
        ttk.Label(main_frame, text="URL(s) do(s) Vídeo(s):", font=("Arial", 10, "bold")).grid(
            row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 5)
        )
        
        self.text_urls = scrolledtext.ScrolledText(
            main_frame,
            height=4,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.text_urls.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        criar_tooltip(
            self.text_urls,
            "Cole uma ou mais URLs do YouTube aqui.\n"
            "Para múltiplos vídeos, coloque uma URL por linha.\n"
            "Exemplo:\n"
            "https://www.youtube.com/watch?v=VIDEO1\n"
            "https://www.youtube.com/watch?v=VIDEO2\n\n"
            "💡 Clique com botão direito ou Ctrl+Clique para ver esta ajuda.",
            modo='click'
        )
        
        # Frame de opções
        frame_opcoes = ttk.LabelFrame(main_frame, text="Opções de Transcrição", padding="10")
        frame_opcoes.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        frame_opcoes.columnconfigure(1, weight=1)
        
        # Modelo
        label_modelo = ttk.Label(frame_opcoes, text="Modelo Whisper:")
        label_modelo.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.var_modelo = tk.StringVar(value="base")
        combo_modelo = ttk.Combobox(
            frame_opcoes,
            textvariable=self.var_modelo,
            values=["tiny", "base", "small", "medium", "large"],
            state="readonly",
            width=15
        )
        combo_modelo.grid(row=0, column=1, sticky=tk.W, pady=5)
        criar_tooltip(
            combo_modelo,
            "Modelo Whisper: Define a precisão e velocidade da transcrição.\n\n"
            "• tiny: Mais rápido, menos preciso (~39MB, ~1GB RAM)\n"
            "• base: Equilíbrio recomendado (~74MB, ~1GB RAM) ✓ Padrão\n"
            "• small: Mais preciso, mais lento (~244MB, ~2GB RAM)\n"
            "• medium: Alta precisão, lento (~769MB, ~5GB RAM)\n"
            "• large: Máxima precisão, muito lento (~1550MB, ~10GB RAM)\n\n"
            "Recomendação: Use 'base' para a maioria dos casos.\n\n"
            "💡 Clique com botão direito ou Ctrl+Clique para ver esta ajuda.",
            modo='click'
        )
        
        # Idioma
        label_idioma = ttk.Label(frame_opcoes, text="Idioma:")
        label_idioma.grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.var_idioma = tk.StringVar(value="")
        entry_idioma = ttk.Entry(frame_opcoes, textvariable=self.var_idioma, width=15)
        entry_idioma.grid(row=1, column=1, sticky=tk.W, pady=5)
        label_idioma_help = ttk.Label(frame_opcoes, text="(vazio = detecção automática, ex: pt, en, es)", 
                 font=("Arial", 8))
        label_idioma_help.grid(row=1, column=2, sticky=tk.W, padx=(10, 0))
        criar_tooltip(
            entry_idioma,
            "Idioma do vídeo para transcrição.\n\n"
            "• Deixe vazio: O Whisper detecta automaticamente o idioma\n"
            "• Especifique: Use código ISO 639-1 (2 letras)\n\n"
            "Exemplos:\n"
            "• pt = Português\n"
            "• en = Inglês\n"
            "• es = Espanhol\n"
            "• fr = Francês\n"
            "• de = Alemão\n\n"
            "Recomendação: Deixe vazio para detecção automática.\n\n"
            "💡 Clique com botão direito ou Ctrl+Clique para ver esta ajuda.",
            modo='click'
        )
        
        # Formato
        label_formato = ttk.Label(frame_opcoes, text="Formato:")
        label_formato.grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.var_formato = tk.StringVar(value="simples")
        combo_formato = ttk.Combobox(
            frame_opcoes,
            textvariable=self.var_formato,
            values=["simples", "segmentos", "timestamps"],
            state="readonly",
            width=15
        )
        combo_formato.grid(row=2, column=1, sticky=tk.W, pady=5)
        criar_tooltip(
            combo_formato,
            "Formato de saída da transcrição:\n\n"
            "• simples: Texto contínuo sem formatação especial\n"
            "• segmentos: Texto dividido em parágrafos por segmento de fala\n"
            "• timestamps: Texto com marcação de tempo [HH:MM:SS -> HH:MM:SS]\n\n"
            "Exemplo timestamps:\n"
            "[00:00:10 -> 00:00:15] Olá, bem-vindos ao vídeo\n"
            "[00:00:15 -> 00:00:20] Hoje vamos falar sobre...\n\n"
            "💡 Clique com botão direito ou Ctrl+Clique para ver esta ajuda.",
            modo='click'
        )
        
        # Diretório de saída (padrão: Downloads do usuário)
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        ttk.Label(frame_opcoes, text="Diretório de Saída:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        self.var_output_dir = tk.StringVar(value=downloads_dir)
        entry_output = ttk.Entry(frame_opcoes, textvariable=self.var_output_dir, width=40)
        entry_output.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        btn_browse = ttk.Button(frame_opcoes, text="📂", command=self._selecionar_diretorio, width=3)
        btn_browse.grid(row=3, column=2, padx=(5, 0))
        criar_tooltip(
            btn_browse,
            "Clique para selecionar uma pasta onde salvar as transcrições.\n\n"
            "💡 Clique com botão direito ou Ctrl+Clique para ver esta ajuda.",
            modo='click'
        )
        
        # Checkboxes
        self.var_usar_cache = tk.BooleanVar(value=True)
        check_cache = ttk.Checkbutton(
            frame_opcoes,
            text="Usar cache",
            variable=self.var_usar_cache
        )
        check_cache.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        criar_tooltip(
            check_cache,
            "Cache: Armazena transcrições já processadas.\n\n"
            "✓ Ativado: Se você transcrever o mesmo vídeo novamente,\n"
            "  a transcrição será recuperada do cache instantaneamente,\n"
            "  sem precisar baixar e processar novamente.\n\n"
            "Recomendação: Mantenha ativado para economizar tempo.\n\n"
            "💡 Clique com botão direito ou Ctrl+Clique para ver esta ajuda.",
            modo='click'
        )
        
        self.var_manter_audio = tk.BooleanVar(value=False)
        check_audio = ttk.Checkbutton(
            frame_opcoes,
            text="Manter arquivo de áudio",
            variable=self.var_manter_audio
        )
        check_audio.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)
        criar_tooltip(
            check_audio,
            "Manter arquivo de áudio: Salva o arquivo MP3 baixado.\n\n"
            "• Desativado: O áudio é baixado, transcrito e depois deletado\n"
            "• Ativado: O arquivo MP3 é salvo junto com a transcrição\n\n"
            "Use quando:\n"
            "• Quiser reutilizar o áudio depois\n"
            "• Precisar do arquivo para outras ferramentas\n"
            "• Quiser economizar banda (evitar re-download)\n\n"
            "Atenção: Arquivos de áudio podem ocupar muito espaço!\n\n"
            "💡 Clique com botão direito ou Ctrl+Clique para ver esta ajuda.",
            modo='click'
        )
        
        # Botões de ação
        frame_botoes = ttk.Frame(main_frame)
        frame_botoes.grid(row=5, column=0, columnspan=3, pady=15)
        
        self.btn_processar = ttk.Button(
            frame_botoes,
            text="▶ Processar",
            command=self._iniciar_processamento,
            style="Accent.TButton"
        )
        self.btn_processar.pack(side=tk.LEFT, padx=5)
        criar_tooltip(
            self.btn_processar,
            "Inicia o processamento dos vídeos.\n\n"
            "O processo inclui:\n"
            "1. Download do áudio do YouTube\n"
            "2. Transcrição usando Whisper\n"
            "3. Formatação do texto\n"
            "4. Salvamento em arquivo TXT\n\n"
            "Acompanhe o progresso na área de log abaixo.\n\n"
            "💡 Clique com botão direito ou Ctrl+Clique para ver esta ajuda.",
            modo='click'
        )
        
        self.btn_limpar_cache = ttk.Button(
            frame_botoes,
            text="🗑 Limpar Cache",
            command=self._limpar_cache
        )
        self.btn_limpar_cache.pack(side=tk.LEFT, padx=5)
        criar_tooltip(
            self.btn_limpar_cache,
            "Remove todas as transcrições armazenadas em cache.\n\n"
            "Use quando:\n"
            "• Quiser liberar espaço em disco\n"
            "• Precisar forçar nova transcrição de vídeos já processados\n"
            "• O cache estiver corrompido\n\n"
            "Atenção: Após limpar, vídeos precisarão ser processados novamente.\n\n"
            "💡 Clique com botão direito ou Ctrl+Clique para ver esta ajuda.",
            modo='click'
        )
        
        self.btn_abrir_pasta = ttk.Button(
            frame_botoes,
            text="📂 Abrir Pasta de Saída",
            command=self._abrir_pasta_saida
        )
        self.btn_abrir_pasta.pack(side=tk.LEFT, padx=5)
        criar_tooltip(
            self.btn_abrir_pasta,
            "Abre a pasta de saída no explorador de arquivos.\n\n"
            "Mostra onde os arquivos de transcrição foram salvos.\n\n"
            "💡 Clique com botão direito ou Ctrl+Clique para ver esta ajuda.",
            modo='click'
        )
        
        # Frame de progresso
        frame_progresso = ttk.Frame(main_frame)
        frame_progresso.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        frame_progresso.columnconfigure(0, weight=1)
        
        # Barra de progresso
        self.progress = ttk.Progressbar(
            frame_progresso,
            mode='indeterminate',
            length=400
        )
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Label de tempo decorrido
        self.label_tempo = ttk.Label(
            frame_progresso,
            text="",
            font=("Arial", 9),
            foreground="gray"
        )
        self.label_tempo.grid(row=0, column=1, sticky=tk.E)
        
        # Área de log
        ttk.Label(main_frame, text="Log de Processamento:", font=("Arial", 10, "bold")).grid(
            row=7, column=0, columnspan=3, sticky=tk.W, pady=(0, 5)
        )
        
        self.text_log = scrolledtext.ScrolledText(
            main_frame,
            height=12,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#f5f5f5"
        )
        self.text_log.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(8, weight=1)
        
        # Dica sobre tooltips
        dica_tooltip = ttk.Label(
            main_frame,
            text="💡 Dica: Clique com botão direito ou Ctrl+Clique em qualquer campo para ver ajuda detalhada",
            font=("Arial", 8),
            foreground="gray"
        )
        dica_tooltip.grid(row=9, column=0, columnspan=3, pady=(5, 0))
        
        # Status bar
        self.status_var = tk.StringVar(value="Pronto")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E))
    
    def _log(self, mensagem: str, incluir_timestamp: bool = True):
        """Adiciona mensagem ao log com timestamp."""
        if incluir_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
            mensagem_completa = f"[{timestamp}] {mensagem}"
        else:
            mensagem_completa = mensagem
        
        self.text_log.insert(tk.END, mensagem_completa + "\n")
        self.text_log.see(tk.END)
        self.root.update_idletasks()
    
    def _atualizar_tempo_progresso(self, mensagem: str):
        """Atualiza o label de tempo de progresso (thread-safe)."""
        # Garante que a atualização seja feita na thread principal
        self.root.after(0, lambda: self.label_tempo.config(text=mensagem))
    
    def _atualizar_status(self, status: str):
        """Atualiza a barra de status."""
        self.status_var.set(status)
        self.root.update_idletasks()
    
    def _selecionar_diretorio(self):
        """Seleciona diretório de saída."""
        diretorio = filedialog.askdirectory(title="Selecionar diretório de saída")
        if diretorio:
            self.var_output_dir.set(diretorio)
    
    def _abrir_pasta_saida(self):
        """Abre a pasta de saída no explorador."""
        output_dir = self.var_output_dir.get()
        if os.path.exists(output_dir):
            if sys.platform == "win32":
                os.startfile(output_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", output_dir])
            else:
                subprocess.run(["xdg-open", output_dir])
        else:
            messagebox.showwarning("Aviso", "Diretório de saída não existe ainda.")
    
    def _limpar_cache(self):
        """Limpa o cache de transcrições."""
        if messagebox.askyesno("Confirmar", "Deseja realmente limpar todo o cache?"):
            if self.cache.limpar_cache():
                self._log("✓ Cache limpo com sucesso")
                messagebox.showinfo("Sucesso", "Cache limpo com sucesso!")
            else:
                self._log("ℹ Cache já estava vazio")
    
    def _obter_urls(self) -> List[str]:
        """Obtém URLs do campo de texto."""
        texto = self.text_urls.get(1.0, tk.END).strip()
        urls = [url.strip() for url in texto.split("\n") if url.strip()]
        return urls
    
    def _processar_videos(self):
        """Processa os vídeos em thread separada."""
        urls = self._obter_urls()
        
        if not urls:
            messagebox.showwarning("Aviso", "Por favor, insira pelo menos uma URL.")
            self._finalizar_processamento()
            return
        
        try:
            output_dir = self.var_output_dir.get()
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            modelo = self.var_modelo.get()
            idioma = self.var_idioma.get().strip() or None
            formato = self.var_formato.get()
            usar_cache = self.var_usar_cache.get()
            manter_audio = self.var_manter_audio.get()
            
            self._log(f"\n{'='*60}")
            self._log(f"Iniciando processamento de {len(urls)} vídeo(s)")
            self._log(f"{'='*60}\n")
            
            resultados = []
            
            for i, url in enumerate(urls, 1):
                self._log(f"\n{'='*60}")
                self._log(f"Vídeo {i}/{len(urls)}")
                self._log(f"{'='*60}")
                
                try:
                    texto, audio_path = processar_video(
                        url=url,
                        model_name=modelo,
                        language=idioma,
                        formato=formato,
                        cache=self.cache if usar_cache else None,
                        usar_cache=usar_cache,
                        manter_audio=manter_audio,
                        output_dir=output_dir,
                        callback=self._log,
                        callback_progresso=self._atualizar_tempo_progresso
                    )
                    
                    # Gera nome aleatório para o arquivo
                    nome_aleatorio = gerar_nome_aleatorio(16)
                    arquivo_saida = Path(output_dir) / f"transcricao_{nome_aleatorio}.txt"
                    
                    with open(arquivo_saida, "w", encoding="utf-8") as f:
                        f.write(f"URL: {url}\n")
                        f.write(f"{'='*60}\n\n")
                        f.write(texto)
                    
                    resultados.append({
                        "url": url,
                        "arquivo": str(arquivo_saida),
                        "sucesso": True,
                        "audio": audio_path
                    })
                    
                    self._log(f"✓ Salvo em: {arquivo_saida}")
                    
                except Exception as e:
                    self._log(f"✗ Erro: {str(e)}")
                    resultados.append({
                        "url": url,
                        "sucesso": False,
                        "erro": str(e)
                    })
            
            # Arquivo consolidado
            arquivo_consolidado = Path(output_dir) / "transcricoes_consolidadas.txt"
            with open(arquivo_consolidado, "w", encoding="utf-8") as f:
                f.write("TRANSCRIÇÕES CONSOLIDADAS\n")
                f.write("="*60 + "\n\n")
                
                for i, resultado in enumerate(resultados, 1):
                    if resultado["sucesso"]:
                        f.write(f"\n{'='*60}\n")
                        f.write(f"VÍDEO {i}: {resultado['url']}\n")
                        f.write(f"{'='*60}\n\n")
                        with open(resultado["arquivo"], "r", encoding="utf-8") as arquivo:
                            f.write(arquivo.read())
                            f.write("\n\n")
            
            sucessos = sum(1 for r in resultados if r["sucesso"])
            self._log(f"\n{'='*60}")
            self._log(f"✓ Processamento concluído!")
            self._log(f"  - Sucessos: {sucessos}/{len(urls)}")
            self._log(f"  - Arquivo consolidado: {arquivo_consolidado}")
            self._log(f"{'='*60}\n")
            
            self._atualizar_status(f"Concluído: {sucessos}/{len(urls)} vídeos processados")
            
            messagebox.showinfo(
                "Concluído",
                f"Processamento concluído!\n\n"
                f"Sucessos: {sucessos}/{len(urls)}\n"
                f"Arquivos salvos em: {output_dir}"
            )
            
        except Exception as e:
            self._log(f"\n✗ Erro fatal: {str(e)}")
            messagebox.showerror("Erro", f"Erro durante processamento:\n{e}")
        finally:
            self._finalizar_processamento()
    
    def _iniciar_processamento(self):
        """Inicia o processamento em thread separada."""
        if self.processando:
            messagebox.showwarning("Aviso", "Já existe um processamento em andamento.")
            return
        
        urls = self._obter_urls()
        if not urls:
            messagebox.showwarning("Aviso", "Por favor, insira pelo menos uma URL.")
            return
        
        self.processando = True
        self.tempo_inicio_processamento = time.time()
        self.btn_processar.config(state="disabled")
        self.btn_limpar_cache.config(state="disabled")
        self.progress.start()
        self.label_tempo.config(text="")
        self.text_log.delete(1.0, tk.END)
        self._atualizar_status("Processando...")
        
        self.thread_processamento = threading.Thread(target=self._processar_videos, daemon=True)
        self.thread_processamento.start()
    
    def _finalizar_processamento(self):
        """Finaliza o processamento e reabilita controles."""
        self.processando = False
        self.progress.stop()
        self.label_tempo.config(text="")
        self.btn_processar.config(state="normal")
        self.btn_limpar_cache.config(state="normal")
        if not self.status_var.get().startswith("Concluído"):
            self._atualizar_status("Pronto")


class SplashScreen:
    """Tela de carregamento que aparece imediatamente ao iniciar."""
    
    def __init__(self):
        self.splash = tk.Tk()
        self.splash.title("Carregando...")
        self.splash.geometry("400x200")
        self.splash.resizable(False, False)
        self.fechada = False  # Flag para controlar se foi fechada
        
        # Remove decoração da janela (opcional, pode deixar)
        # self.splash.overrideredirect(True)
        
        # Centraliza na tela
        self._centralizar()
        
        # Configura para ficar sempre no topo
        self.splash.attributes('-topmost', True)
        
        # Frame principal
        frame = ttk.Frame(self.splash, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        titulo = ttk.Label(
            frame,
            text="🎬 Transcritor de Vídeos",
            font=("Arial", 16, "bold")
        )
        titulo.pack(pady=(0, 10))
        
        # Mensagem
        self.label_status = ttk.Label(
            frame,
            text="Carregando aplicação...",
            font=("Arial", 10)
        )
        self.label_status.pack(pady=10)
        
        # Barra de progresso
        self.progress = ttk.Progressbar(
            frame,
            mode='indeterminate',
            length=300
        )
        self.progress.pack(pady=10)
        self.progress.start(10)
        
        # Label de informação
        info_label = ttk.Label(
            frame,
            text="Por favor, aguarde...",
            font=("Arial", 8),
            foreground="gray"
        )
        info_label.pack(pady=(10, 0))
        
        # Atualiza a interface
        self.splash.update()
    
    def _centralizar(self):
        """Centraliza a janela na tela."""
        self.splash.update_idletasks()
        width = self.splash.winfo_width()
        height = self.splash.winfo_height()
        x = (self.splash.winfo_screenwidth() // 2) - (width // 2)
        y = (self.splash.winfo_screenheight() // 2) - (height // 2)
        self.splash.geometry(f'{width}x{height}+{x}+{y}')
    
    def atualizar_status(self, texto: str):
        """Atualiza o texto de status."""
        if not self.fechada and self.splash.winfo_exists():
            try:
                self.label_status.config(text=texto)
                self.splash.update()
            except tk.TclError:
                # Janela foi destruída, ignora
                pass
    
    def fechar(self):
        """Fecha a splash screen."""
        if not self.fechada:
            self.fechada = True
            try:
                self.progress.stop()
                self.splash.destroy()
            except tk.TclError:
                # Já foi destruída, ignora
                pass
    
    def esta_aberta(self):
        """Verifica se a splash screen ainda está aberta."""
        try:
            return self.splash.winfo_exists() and not self.fechada
        except tk.TclError:
            return False


def verificar_instancia_unica():
    """
    Verifica se já existe uma instância rodando.
    Usa socket para criar um lock.
    """
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        lock_socket.bind(('localhost', 47293))  # Porta única para o app
        return True  # Primeira instância
    except OSError:
        # Porta já em uso = outra instância rodando
        return False
    finally:
        lock_socket.close()


def _carregar_whisper_thread(splash: SplashScreen):
    """Carrega whisper em thread separada."""
    global whisper
    
    try:
        # Atualiza status de forma segura
        def atualizar_carregando():
            if splash.esta_aberta():
                splash.atualizar_status("Carregando bibliotecas...")
        
        if splash.esta_aberta():
            splash.splash.after(0, atualizar_carregando)
        
        # Importa whisper (pode demorar)
        import whisper as whisper_module
        whisper = whisper_module
        
        # Atualiza status e dispara evento de forma segura
        def finalizar_carregamento():
            if splash.esta_aberta():
                splash.atualizar_status("Aplicação pronta!")
                try:
                    splash.splash.event_generate("<<WhisperLoaded>>")
                except tk.TclError:
                    # Janela foi fechada, ignora
                    pass
        
        if splash.esta_aberta():
            splash.splash.after(0, finalizar_carregamento)
    except ImportError:
        def mostrar_erro():
            if splash.esta_aberta():
                _mostrar_erro_whisper(splash)
        if splash.esta_aberta():
            splash.splash.after(0, mostrar_erro)
    except Exception as e:
        def mostrar_erro_gen():
            if splash.esta_aberta():
                _mostrar_erro_carregamento(splash, e)
        if splash.esta_aberta():
            splash.splash.after(0, mostrar_erro_gen)


def _mostrar_erro_whisper(splash: SplashScreen):
    """Mostra erro de importação do whisper."""
    if splash.esta_aberta():
        splash.fechar()
    temp_root = tk.Tk()
    temp_root.withdraw()
    messagebox.showerror(
        "Erro",
        "Biblioteca 'whisper' não encontrada.\n\n"
        "Instale com: pip install openai-whisper"
    )
    temp_root.destroy()


def _mostrar_erro_carregamento(splash: SplashScreen, erro: Exception):
    """Mostra erro genérico de carregamento."""
    if splash.esta_aberta():
        splash.fechar()
    temp_root = tk.Tk()
    temp_root.withdraw()
    messagebox.showerror("Erro", f"Erro ao carregar dependências:\n{erro}")
    temp_root.destroy()


def carregar_dependencias(splash: SplashScreen):
    """Inicia carregamento de dependências pesadas em thread."""
    # Inicia thread para carregar whisper
    thread = threading.Thread(target=lambda: _carregar_whisper_thread(splash), daemon=True)
    thread.start()
    
    # Configura handler para quando whisper carregar
    def on_whisper_loaded(event):
        if splash.esta_aberta():
            splash.splash.after(500, lambda: _finalizar_splash_e_iniciar(splash))
    
    if splash.esta_aberta():
        splash.splash.bind("<<WhisperLoaded>>", on_whisper_loaded)
    
    return True  # Retorna True, mas carregamento continua em background


def _iniciar_aplicacao():
    """Inicia a aplicação principal após carregar tudo."""
    root = tk.Tk()
    app = TranscricaoGUI(root)
    root.mainloop()


def main():
    """Função principal."""
    # Verifica se já existe uma instância rodando
    if not verificar_instancia_unica():
        # Cria uma janela temporária para mostrar a mensagem
        temp_root = tk.Tk()
        temp_root.withdraw()  # Esconde a janela principal
        messagebox.showwarning(
            "Aplicação já em execução",
            "O Transcritor de Vídeos já está aberto!\n\n"
            "Verifique a barra de tarefas."
        )
        temp_root.destroy()
        sys.exit(0)
    
    # Mostra splash screen imediatamente
    splash = SplashScreen()
    
    # Carrega dependências pesadas (bloqueia, mas splash já está visível)
    def carregar_e_iniciar():
        if carregar_dependencias(splash):
            # Pequeno delay para mostrar "pronto" e fechar splash
            splash.splash.after(500, lambda: _finalizar_splash_e_iniciar(splash))
        else:
            splash.splash.after(100, lambda: splash.fechar())
    
    # Agenda carregamento para depois que splash aparecer
    splash.splash.after(100, carregar_e_iniciar)
    
    splash.splash.mainloop()


def _finalizar_splash_e_iniciar(splash: SplashScreen):
    """Fecha splash e inicia aplicação principal."""
    if splash.esta_aberta():
        splash.fechar()
    _iniciar_aplicacao()


if __name__ == "__main__":
    main()
