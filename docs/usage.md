# auto-notes 使用手册

自动下载在线视频，提取语音转文字 + 画面 OCR，再由 LLM 整理成结构化 Markdown 笔记。

## 目录

- [基本用法](#基本用法)
- [可选模式](#可选模式)
- [输出控制](#输出控制)
- [LLM 配置](#llm-配置)
- [平台适配](#平台适配)
- [完整示例](#完整示例)
- [配置文文件](#配置文件)
- [常见问题](#常见问题)

---

## 基本用法

```bash
auto-notes <URL>
```

自动完成：下载 → 抽帧 → ASR + OCR 并行 → LLM 整理 → 输出 `.md` 文件。

输出默认在当前目录的 `notes/` 下，中间产物保留在 `workspace/`。

---

## 可选模式

### `--audio`：仅音频模式

跳过视频下载、抽帧、OCR，只下载音频做语音识别后 LLM 整理。

```bash
auto-notes "https://..." --audio
```

适合：播客、纯讲座、网课录音。省流量、省时间、省 GPU。

### `--no-audio`：完整模式（默认）

```bash
auto-notes "https://..."
```

下载视频 + 音频，提取关键帧做 OCR，与 ASR 并行处理后合并送 LLM。

---

## 输出控制

### `-o, --output <PATH>`

指定笔记输出目录（默认 `./notes`）：

```bash
auto-notes "https://..." -o ./my_notes
```

### `--workdir <PATH>`

指定中间文件目录（默认 `./workspace`）：

```bash
auto-notes "https://..." --workdir /tmp/auto_notes_cache
```

### `--keep / --no-keep`

是否保留中间文件（下载的视频、音频、ASR 和 OCR 结果）：

```bash
auto-notes "https://..." --no-keep    # 用完即删
auto-notes "https://..." --keep       # 保留（默认）
```

保留时重复运行同一 URL 会跳过已完成的步骤。

---

## LLM 配置

### `--llm <provider>`

LLM 后端，目前支持：

| 值 | 说明 | 依赖 |
|----|------|------|
| `openai` | OpenAI 兼容 API（含 DeepSeek 等） | `openai` 包 |
| `ollama` | 本地 Ollama 模型 | `ollama` 包 |

### `-m, --model <NAME>`

指定模型名：

| 提供商 | 示例 |
|--------|------|
| OpenAI | `gpt-4o`, `gpt-4o-mini` |
| DeepSeek | `deepseek-chat`, `deepseek/deepseek-v4-flash` |
| Ollama | `qwen3`, `qwen2.5`, `deepseek-r1` |

### `--base-url <URL>`

设置 API 地址（用于 OpenAI 兼容的第三方 API）：

```bash
# DeepSeek
auto-notes "https://..." --llm openai -m deepseek-chat \
  --base-url https://api.deepseek.com/v1

# 自定义 API
auto-notes "https://..." --llm openai -m my-model \
  --base-url https://my-api.example.com/v1
```

API Key 通过环境变量 `OPENAI_API_KEY` 设置。

### `--lang <CODE>`

音频语言（传递给 faster-whisper）：

| 值 | 说明 |
|----|------|
| `auto` | 自动检测（默认） |
| `zh` | 中文 |
| `en` | 英文 |
| `ja` | 日语 |

```bash
# 明确指定中文
auto-notes "https://..." --lang zh
```

---

## 平台适配

### YouTube — 直接使用

```bash
auto-notes "https://youtube.com/watch?v=xxx"
auto-notes "https://youtu.be/xxx"
```

### Bilibili — 需要浏览器 Cookie

Bilibili 有反爬机制，需要从浏览器提取已登录的 Cookie：

```bash
auto-notes "https://www.bilibili.com/video/BVxxx" --cookies chrome
```

支持的浏览器：`chrome`, `firefox`, `safari`, `chromium`, `edge`。

### 代理设置

如果下载视频需要代理（如 yt-dlp 连不上）：

```bash
auto-notes "https://youtube.com/..." --proxy http://127.0.0.1:7890
```

---

## 完整示例

### YouTube 中文视频 → DeepSeek

```bash
export OPENAI_API_KEY="sk-xxx"

auto-notes "https://youtube.com/watch?v=xxx" \
  --lang zh \
  --llm openai \
  -m deepseek-chat \
  --base-url https://api.deepseek.com/v1
```

### Bilibili 纯音频（仅下载声）

```bash
export OPENAI_API_KEY="sk-xxx"

auto-notes "https://www.bilibili.com/video/BVxxx?p=5" \
  --audio \
  --lang zh \
  --cookies chrome \
  --llm openai \
  -m gpt-4o-mini
```

### 本地 Ollama + 英文视频

```bash
auto-notes "https://youtube.com/watch?v=xxx" \
  --lang en \
  --llm ollama \
  -m qwen2.5
```

### 快速试用（仅转写，不整理）

```bash
# 当前仅支持完整流程。如需纯转写输出 SRT，可提 issue。
```

---

## 配置文件

`auto-notes` 支持 TOML 配置文件，查找顺序：

1. `--config <PATH>` 指定路径
2. 当前目录 `./auto_notes.toml`
3. 用户目录 `~/.config/auto_notes.toml`

示例 `auto_notes.toml`：

```toml
output_dir = "notes"
working_dir = "workspace"
lang = "zh"
llm_provider = "openai"
llm_model = "deepseek-chat"
llm_base_url = "https://api.deepseek.com/v1"
max_keyframes = 120
keep_intermediates = true
```

---

## 常见问题

**Q: 首次运行很慢？**
A: faster-whisper（~1.5GB）和 PaddleOCR（~200MB）会在首次使用时自动下载模型。之后完全离线。

**Q: 如何查看进度？**
A: `--audio` 模式有下载进度条 + ASR 进度。完整模式还有关键帧提取 + OCR 进度。

**Q: 如果中断了能续跑吗？**
A: 可以。默认 `--keep` 模式下，已下载的视频/音频、ASR 转录、OCR 结果都会缓存，下次跳过已完成的步骤。

**Q: 提示 `ffmpeg not found`？**
A: auto-notes 已不再需要 ffmpeg。OpenCV 替代了帧提取，yt-dlp 直接下载音频。

**Q: Bilibili 报 `412 Precondition Failed`？**
A: 需要 `--cookies chrome`（或 firefox/safari）从已登录的浏览器提取 Cookie。
