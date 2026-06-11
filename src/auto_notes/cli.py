"""CLI 入口：typer 命令行，加载 .env，暴露 process 子命令。"""

from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from .config import Config
from .pipeline import Pipeline

load_dotenv()

app = typer.Typer(help="从 Bilibili 视频自动生成结构化 Markdown 笔记")


@app.command()
def process(
    url: str = typer.Argument(..., help="Bilibili 视频链接"),
    output: Optional[Path] = typer.Option(
        None, "-o", "--output", help="笔记输出目录（默认 ./notes）"
    ),
    lang: Optional[str] = typer.Option(
        None, "--lang", help="音频语言：zh / en / auto（默认）"
    ),
    llm: Optional[str] = typer.Option(
        None, "--llm", help="LLM 后端：openai / ollama"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="LLM 模型名（如 deepseek-chat, gpt-4o）"
    ),
    working_dir: Optional[Path] = typer.Option(
        None, "--workdir", help="工作目录（中间产物存放位置）"
    ),
    keep: bool = typer.Option(
        True, "--keep/--no-keep", help="处理完后保留中间文件"
    ),
    config: Optional[Path] = typer.Option(
        None, "-c", "--config", help="TOML 配置文件路径"
    ),
    proxy: Optional[str] = typer.Option(
        None, "--proxy", help="下载代理（如 http://127.0.0.1:7890）"
    ),
    cookies: Optional[str] = typer.Option(
        None, "--cookies",
        help="浏览器 Cookie（默认 chrome，传空字符串禁用）"
    ),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", help="LLM API 自定义地址（如 https://api.deepseek.com/v1）"
    ),
    full: bool = typer.Option(
        False, "--full/--no-full",
        help="完整模式：下载视频+做 OCR 识别画面文字（默认仅音频）"
    ),
) -> None:
    """
    下载 Bilibili 视频，提取语音转文字（+ 画面 OCR），再由 LLM 整理为 Markdown 笔记。
    \n
    默认仅下载音频（快、省流量），加 --full 启用视频抽帧和 OCR。
    需要浏览器 Cookie（默认从 Chrome 提取）才能下载。
    """
    cfg = Config(config)

    if output:
        cfg.output_dir = output
    if lang:
        cfg.lang = lang
    if llm:
        cfg.llm_provider = llm
    if model:
        cfg.llm_model = model
    if base_url:
        cfg.llm_base_url = base_url
    if full:
        cfg.audio_only = False
    if working_dir:
        cfg.working_dir = working_dir
    if proxy:
        cfg.proxy = proxy
    if cookies is not None:
        cfg.cookies_from_browser = cookies
    cfg.keep_intermediates = keep

    pipeline = Pipeline(cfg)
    pipeline.run(url)


if __name__ == "__main__":
    app()
