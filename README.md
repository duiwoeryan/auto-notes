# auto-notes

从 Bilibili 视频自动生成结构化 Markdown 笔记。

## 工作流程

```
B站视频链接 → 下载音频 → mlx-whisper 语音转文字 → LLM 整理 → Markdown 笔记
                                                       （可加 --full 启用视频抽帧 + OCR）
```

## 快速开始

```bash
# 1. 安装
uv sync

# 2. 配置（复制并填写）
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY 等

# 3. 生成笔记
uv run auto-notes 'https://www.bilibili.com/video/BV1xx'
```

默认仅下载音频（快速），加 `--full` 启用视频+OCR。

## 前置依赖

- **yt-dlp** — 视频/音频下载。确保在 PATH 中：`brew install yt-dlp`
- **Apple Silicon Mac** — mlx-whisper 需要 M 系列芯片（M1/M2/M3/M4）获得 GPU 加速

## 使用示例

```bash
# 仅音频（默认，推荐）
uv run auto-notes 'https://www.bilibili.com/video/BV1qG4y1B74U?p=34'

# 完整模式（视频+OCR，更慢）
uv run auto-notes 'https://...' --full

# 指定输出目录
uv run auto-notes 'https://...' -o ./my_notes

# 指定语言
uv run auto-notes 'https://...' --lang en

# 使用 Ollama 本地模型
uv run auto-notes 'https://...' --llm ollama -m qwen3

# 使用 OpenAI
uv run auto-notes 'https://...' --llm openai -m gpt-4o

# 指定 API 地址（如 DeepSeek）
uv run auto-notes 'https://...' --llm openai -m deepseek-chat --base-url https://api.deepseek.com/v1
```

## 配置方式

支持三种配置层级（优先级从高到低）：

1. **CLI 参数** — 命令行直接指定，如 `--lang en --full`
2. **环境变量** — `.env` 文件或 `AUTO_NOTES_*` 环境变量
3. **代码默认值** — 开箱即用

### `.env` 示例

```env
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
AUTO_NOTES_COOKIES=chrome
AUTO_NOTES_LANG=zh
AUTO_NOTES_LLM_MODEL=deepseek-chat
```

完整变量列表见 [.env.example](.env.example)。

## 输出

生成笔记位于 `notes/` 目录，Markdown 格式，每段附带 `[▶](→t=MM:SS)` 时间戳链接可用于跳转。

中间文件（音频、转写结果、帧）默认保留在 `workspace/` 目录，重复运行跳过已完成的步骤。

## 技术栈

| 环节 | 工具 |
|------|------|
| 下载 | yt-dlp |
| 语音转文字 | mlx-whisper（Apple Silicon GPU） |
| 画面文字识别 | PaddleOCR（仅 `--full` 模式） |
| LLM 整理 | OpenAI 兼容 API / Ollama |
| 帧提取 | OpenCV（仅 `--full` 模式） |

## 测试

```bash
uv run pytest tests/
```

## 许可

MIT
