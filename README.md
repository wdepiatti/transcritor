# 🎙️ Transcritor & Tradutor YouTube Pro

Ferramenta profissional com interface gráfica para transcrição e tradução de vídeos do YouTube utilizando Inteligência Artificial (**OpenAI Whisper**) e processamento local.

## 🚀 Primeiros Passos

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Execute o aplicativo:
   ```bash
   python transcreva.py
   ```

3. Siga as instruções na interface gráfica para começar a transcrever vídeos.

## �️ Recursos Principais

- **Transcrição via IA:** Motor Whisper para conversão precisa de fala em texto.
- **Tradução Multi-idioma:** Tradução automática para `pt`, `en`, `es`, `fr`, `de`, entre outros.
- **Formatos de Saída:**
  - `Simples`: Texto corrido ideal para resumos
  - `Segmentos`: Texto quebrado em parágrafos para leitura fácil
  - `Timestamps`: Marcação de tempo `[00:00:00]` para referência de vídeo
- **Gerenciamento de Cache:** Evita o reprocessamento de URLs já analisadas
- **Interface Amigável:** Barra de progresso, cronômetro e log de eventos

## � Requisitos do Sistema

### 🐍 Python
- **Versão:** 3.11.19 (recomendada)
- *Nota:* Versões mais recentes podem funcionar, mas não foram testadas.

### 📦 Dependências
- **FFmpeg** (obrigatório para extração de áudio)
  - Windows: [Baixar FFmpeg](https://ffmpeg.org/download.html)
  - Linux: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`

## �️ Instalação

### 1. Configurar Ambiente Virtual
```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente (Windows)
.\venv\Scripts\activate

# Ativar ambiente (Linux/macOS)
# source venv/bin/activate
```

### 2. Instalar Dependências
```bash
pip install -r requirements.txt
```

## 🖥️ Como Usar

1. Inicie o programa:
   ```bash
   python transcreva.py
   ```

2. Na interface:
   - Cole uma ou mais URLs do YouTube (uma por linha)
   - Selecione o modelo de IA (quanto maior, mais preciso)
   - Escolha o formato de saída desejado
   - Opcional: ative a tradução e selecione o idioma
   - Clique em "INICIAR PROCESSO"

## 📁 Estrutura de Arquivos

Arquivos gerados na pasta de saída:
- `ORIGINAL_[HASH].txt`: Transcrição no idioma original
- `TRADUCAO_[IDIOMA]_[HASH].txt`: Transcrição traduzida

## ❓ Solução de Problemas

### Erros Comuns
1. **FFmpeg não encontrado**
   - Verifique se o FFmpeg está instalado e no PATH
   - Reinicie o terminal após a instalação

2. **Erro ao instalar dependências**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Problemas de memória**
   - Use modelos menores (tiny ou base) para vídeos longos
   - Feche outros aplicativos pesados

## 📝 Notas Técnicas

- **Cache:** Os arquivos em cache são armazenados em `~/.cache_transcritor_v2`
- **Tradução:** O texto é processado em blocos de 3000 caracteres
- **Instância Única:** A aplicação impede múltiplas execuções simultâneas

## ⚖️ Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais informações.

## 🤝 Como Contribuir

1. Faça um Fork do projeto
2. Crie uma Branch para sua Feature
3. Adicione suas mudanças
4. Envie um Pull Request
