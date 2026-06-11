"""全局配置：默认值、目录路径、TOML/环境变量加载。

所有字段都有合理默认值，可通过环境变量或 TOML 配置文件覆盖。
优先级：CLI 参数 > TOML 配置文件 > 环境变量 > 代码默认值。

`.env` 文件由 cli.py 自动加载，支持的变量见 `.env.example`。
"""

import os
from pathlib import Path
from typing import Optional

import tomli

_ENV_MAP = {
    "AUTO_NOTES_LANG": ("lang", str),
    "AUTO_NOTES_LLM_PROVIDER": ("llm_provider", str),
    "AUTO_NOTES_LLM_MODEL": ("llm_model", str),
    "AUTO_NOTES_LLM_BASE_URL": ("llm_base_url", str),
    "AUTO_NOTES_COOKIES": ("cookies_from_browser", str),
    "AUTO_NOTES_PROXY": ("proxy", str),
    "AUTO_NOTES_OUTPUT_DIR": ("output_dir", lambda v: Path(v)),
    "AUTO_NOTES_WORKING_DIR": ("working_dir", lambda v: Path(v)),
    "AUTO_NOTES_KEEP": ("keep_intermediates", lambda v: v.lower() in ("1", "true", "yes")),
    "AUTO_NOTES_AUDIO_ONLY": ("audio_only", lambda v: v.lower() in ("1", "true", "yes")),
    "AUTO_NOTES_MAX_KEYFRAMES": ("max_keyframes", int),
}


class Config:
    """集中管理所有运行时参数。

    优先级：CLI 参数 > TOML 配置文件 > 环境变量 > 代码默认值。
    环境变量以 AUTO_NOTES_ 为前缀，详见 .env.example。
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        # ── 输出与工作目录 ──────────────────────────────────
        self.output_dir: Path = Path("notes")       # 笔记 Markdown 输出目录
        self.working_dir: Path = Path("workspace")  # 中间文件（音频/帧/缓存）目录
        self.keep_intermediates: bool = True        # 完成后保留中间文件（用于续跑）

        # ── ASR 语音识别 ────────────────────────────────────
        self.lang: str = "zh"                       # 音频语言：zh / en / auto

        # ── LLM 整理 ────────────────────────────────────
        self.llm_provider: str = "openai"            # LLM 后端：openai / ollama
        self.llm_model: Optional[str] = None         # 模型名（如 deepseek-chat）
        self.llm_base_url: Optional[str] = os.getenv("OPENAI_BASE_URL")  # API 地址

        # ── 完整模式（--full）专用 ──────────────────────
        self.max_keyframes: int = 120                # 最多抽取帧数
        self.long_video_threshold: int = 1800        # 长视频阈值（秒），≥此值则分段
        self.segment_duration: int = 600             # 每段长度（秒）

        # ── 下载 ───────────────────────────────────────
        self.yt_dlp_path: str = "yt-dlp"             # yt-dlp 可执行文件路径
        self.ffmpeg_path: str = "ffmpeg"             # ffmpeg 路径（仅--full模式合并用）
        self.cookies_from_browser: str = "chrome"    # 浏览器 Cookie（B 站必需）
        self.proxy: Optional[str] = None             # 下载代理

        # ── 模式 ───────────────────────────────────────
        # 默认仅音频模式，--full 开启视频下载+抽帧+OCR
        self.audio_only: bool = True

        self._load_env_overrides()
        self._load_config(config_path)

    def _load_env_overrides(self) -> None:
        """从 AUTO_NOTES_* 环境变量加载配置（优先级高于代码默认值）。"""
        for env_key, (cfg_key, converter) in _ENV_MAP.items():
            val = os.getenv(env_key)
            if val is not None:
                setattr(self, cfg_key, converter(val))

    def _load_config(self, config_path: Optional[Path]) -> None:
        """按优先级查找并加载 TOML 配置文件。"""
        candidates = [
            config_path,
            Path("auto_notes.toml"),
            Path.home() / ".config" / "auto_notes.toml",
        ]
        for p in candidates:
            if p and p.exists():
                data = tomli.loads(p.read_text())
                for key in [
                    "output_dir", "working_dir", "lang",
                    "llm_provider", "llm_model", "llm_base_url",
                    "long_video_threshold", "segment_duration",
                    "max_keyframes", "keep_intermediates",
                    "ffmpeg_path", "yt_dlp_path", "cookies_from_browser",
                    "proxy", "audio_only",
                ]:
                    if key in data:
                        setattr(self, key, data[key])
                if "output_dir" in data:
                    self.output_dir = Path(data["output_dir"])
                if "working_dir" in data:
                    self.working_dir = Path(data["working_dir"])
                break

    @property
    def audio_path(self) -> Path:
        return self.working_dir / "audio.wav"

    @property
    def frames_dir(self) -> Path:
        return self.working_dir / "frames"

    @property
    def transcript_path(self) -> Path:
        return self.working_dir / "transcript.json"

    @property
    def ocr_path(self) -> Path:
        return self.working_dir / "ocr.json"

    def ensure_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
