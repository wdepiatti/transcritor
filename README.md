# Transcritor de Vídeos do YouTube

## 📋 Sobre o Script

O `transcreva.py` é uma aplicação GUI (interface gráfica) desenvolvida em Python que permite transcrever vídeos do YouTube para arquivos de texto (.txt).

### Funcionalidades Principais

- 🎬 **Transcrição de Vídeos**: Baixa o áudio de vídeos do YouTube e transcreve usando Whisper (OpenAI)
- 📝 **Múltiplos Formatos**: Suporta 3 formatos de saída:
  - **Simples**: Texto contínuo sem formatação
  - **Segmentos**: Texto dividido em parágrafos por segmento
  - **Timestamps**: Texto com marcação de tempo (HH:MM)
- 🎯 **Múltiplos Vídeos**: Processa vários vídeos em lote
- 💾 **Sistema de Cache**: Armazena transcrições para evitar re-processamento
- 🌍 **Detecção Automática de Idioma**: Detecta automaticamente o idioma do vídeo
- ⏱️ **Timer de Processamento**: Mostra tempo decorrido e estimativa durante transcrição
- 📊 **Barra de Progresso**: Visualização do progresso em tempo real
- 🎨 **Interface Gráfica Moderna**: Interface intuitiva com tooltips explicativos

### Tecnologias Utilizadas

- **Python 3.x**
- **tkinter**: Interface gráfica
- **Whisper (OpenAI)**: Modelo de transcrição de áudio
- **yt-dlp**: Download de áudio do YouTube
- **PyInstaller**: Geração de executável

### Requisitos do Sistema

- Windows 10/11 (64-bit)
- Python 3.8 ou superior
- Conexão com internet (para download de vídeos)
- Espaço em disco: ~500MB para o executável + espaço para cache e arquivos de áudio

### Localização de Arquivos

- **Cache**: `C:\Users\seu-nome\.cache_transcritor\`
- **Saída Padrão**: `C:\Users\seu-nome\Downloads\`
- **Nomes de Arquivo**: Aleatórios (ex: `transcricao_k7m9p2q5r8s1t4v6.txt`)

---

## 🔨 Como Fazer o Build do Executável

### Pré-requisitos

1. Instale Python 3.8 ou superior
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

### Método 1: Usando o Script Python (Recomendado)

1. Execute o script de build:
```bash
python build_exe.py
```

2. O executável estará em: `dist/TranscritorYouTube.exe`

### Método 2: Usando o Script Batch (Windows)

1. Execute o arquivo:
```bash
build_exe.bat
```

### Método 3: Manualmente com PyInstaller

```bash
# Instalar PyInstaller
pip install pyinstaller

# Gerar executável
pyinstaller --name="TranscritorYouTube" \
    --onefile \
    --windowed \
    --noconsole \
    --hidden-import=whisper \
    --hidden-import=yt_dlp \
    --hidden-import=yt_dlp.extractor \
    --hidden-import=yt_dlp.downloader \
    --hidden-import=tkinter \
    --hidden-import=tkinter.ttk \
    --hidden-import=tkinter.filedialog \
    --hidden-import=tkinter.messagebox \
    --hidden-import=tkinter.scrolledtext \
    --collect-all=whisper \
    --collect-all=yt_dlp \
    --clean \
    transcreva.py
```

---

## 📦 Notas Importantes sobre o Build

### Tamanho do Executável

O arquivo `.exe` terá aproximadamente **200-500 MB** porque inclui:
- Python runtime completo
- Whisper e seus modelos de IA
- yt-dlp e todas as dependências
- Bibliotecas do tkinter

### Primeira Execução

- Pode demorar alguns segundos para iniciar na primeira vez
- Uma splash screen aparecerá mostrando o carregamento
- O Whisper será carregado em memória

### Antivírus

- Alguns antivírus podem marcar o `.exe` como suspeito (falso positivo)
- Isso é comum com executáveis gerados por PyInstaller
- Se isso acontecer, adicione uma exceção no seu antivírus

### Distribuição

- Você pode distribuir apenas o arquivo `.exe`
- **Não é necessário** instalar Python no computador de destino
- O executável é totalmente independente

---

## 🛠️ Solução de Problemas

### Erro: "PyInstaller não encontrado"
```bash
pip install pyinstaller
```

### Erro: "ModuleNotFoundError"
Adicione o módulo faltante com `--hidden-import`:
```bash
pyinstaller --hidden-import=nome_do_modulo transcreva.py
```

### Erro: "yt-dlp não encontrado"
O script usa o módulo Python `yt_dlp` que é incluído automaticamente no build. Se houver problemas:
```bash
pip install yt-dlp
```

### Executável muito grande
Use `--exclude-module` para remover módulos não usados:
```bash
pyinstaller --exclude-module=matplotlib --exclude-module=numpy transcreva.py
```

### Executável não inicia
Tente gerar sem `--noconsole` para ver erros:
```bash
pyinstaller --onefile --windowed transcreva.py
```

### Executável abre múltiplas vezes
O script tem proteção contra múltiplas instâncias. Se isso acontecer:
- Feche todas as instâncias abertas
- Verifique se não há processos Python rodando em background
- Reinicie o computador se necessário

---

## 📖 Como Usar o Aplicativo

### Executando o Script Python

```bash
python transcreva.py
```

### Executando o Executável

1. Navegue até a pasta `dist/`
2. Execute `TranscritorYouTube.exe`
3. Aguarde a splash screen carregar
4. Cole a URL do vídeo do YouTube
5. Configure as opções (modelo, idioma, formato)
6. Clique em "▶ Processar"

### Opções Disponíveis

- **Modelo Whisper**: Escolha entre tiny, base, small, medium, large
  - `base` é recomendado para a maioria dos casos
- **Idioma**: Deixe vazio para detecção automática ou especifique (pt, en, es, etc.)
- **Formato**: 
  - `simples`: Texto contínuo
  - `segmentos`: Parágrafos separados
  - `timestamps`: Com marcação de tempo
- **Cache**: Ative para evitar re-processar vídeos já transcritos
- **Manter Áudio**: Salva o arquivo MP3 junto com a transcrição

### Dicas

- 💡 Clique com **botão direito** ou **Ctrl+Clique** em qualquer campo para ver ajuda detalhada
- 📁 Os arquivos são salvos em `Downloads` por padrão
- ⚡ Use cache para processar o mesmo vídeo mais rápido
- 🎯 Para melhor precisão, use modelos `small` ou `medium`

---

## 📝 Estrutura do Projeto

```
a28/
├── transcreva.py          # Script principal
├── build_exe.py           # Script de build (Python)
├── build_exe.bat          # Script de build (Batch)
├── requirements.txt       # Dependências
├── README_BUILD.md       # Este arquivo
└── dist/                  # Pasta de saída do build
    └── TranscritorYouTube.exe
```

---

## 🔄 Atualizações e Manutenção

### Atualizar Dependências

```bash
pip install --upgrade openai-whisper yt-dlp pyinstaller
```

### Limpar Cache

- Use o botão "🗑 Limpar Cache" na interface
- Ou delete manualmente: `C:\Users\seu-nome\.cache_transcritor\`

### Rebuild do Executável

Após atualizar o código:
1. Delete as pastas `build/` e `dist/`
2. Execute `python build_exe.py` novamente

---

## 📄 Licença

Este projeto é fornecido "como está" para uso pessoal e educacional.

---

## 🤝 Suporte

Para problemas ou dúvidas:
1. Verifique os logs na interface do aplicativo
2. Consulte a seção "Solução de Problemas" acima
3. Verifique se todas as dependências estão instaladas
