"""Pipeline 编排：下载 → 关键帧 + 并行 ASR+OCR → 合并 → LLM → Markdown。"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress

from .asr import ASREngine
from .config import Config
from .downloader import Downloader
from .keyframe import KeyframeExtractor
from .ocr import OCREngine
from .output import build_merged_text, build_output


class Pipeline:
    """一次视频处理的全流程编排。"""

    def __init__(self, config: Config) -> None:
        self.cfg = config
        self.console = Console()

    def run(self, url: str) -> Path:
        """入口：下载 → 抽帧 → ASR+OCR → LLM → 笔记文件。

        - audio_only=True 时跳过视频抽帧和 OCR。
        - 中间文件缓存命中时直接复用（续跑）。
        - 返回生成笔记的路径。
        """
        self.cfg.ensure_dirs()

        with Progress(console=self.console) as progress:
            downloader = Downloader(yt_dlp_path=self.cfg.yt_dlp_path)
            downloader.cookies_from_browser = self.cfg.cookies_from_browser
            if self.cfg.proxy:
                downloader.proxy = self.cfg.proxy
            video_path, audio_path = downloader.download(
                url, self.cfg.working_dir, progress, audio_only=self.cfg.audio_only
            )

            # ---- 视频帧（仅完整模式） ----
            if not self.cfg.audio_only:
                if not video_path.exists():
                    raise FileNotFoundError(f"Video file not found: {video_path}")
                progress.console.print(f"[green]Video: {video_path.name}[/green]")

                extractor = KeyframeExtractor()
                frames = extractor.extract(
                    video_path, self.cfg.frames_dir, self.cfg.max_keyframes
                )
                progress.console.print(f"[green]Extracted {len(frames)} keyframes[/green]")
            else:
                frames = []

            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            progress.console.print(f"[green]Audio: {audio_path.name}[/green]")

            # ---- ASR + OCR（并行或串行） ----
            asr_engine = ASREngine()

            if not self.cfg.audio_only:
                ocr_engine = OCREngine()
                progress.console.print("[bold]Running ASR and OCR in parallel...[/bold]")
                with ThreadPoolExecutor(max_workers=2) as pool:
                    asr_future = pool.submit(
                        self._run_asr, asr_engine, audio_path, progress
                    )
                    ocr_future = pool.submit(
                        self._run_ocr, ocr_engine, frames, progress
                    )
                    segments = asr_future.result()
                    ocr_results = ocr_future.result()
            else:
                progress.console.print("[bold]Running ASR...[/bold]")
                segments = self._run_asr(asr_engine, audio_path, progress)
                ocr_results = []

        if not self.cfg.audio_only:
            progress.console.print(
                f"[green]ASR segments: {len(segments)} | OCR frames with text: {len(ocr_results)}[/green]"
            )
        else:
            progress.console.print(
                f"[green]ASR segments: {len(segments)}[/green]"
            )

        # ---- 合并文本 + LLM 整理 ----
        merged_text = build_merged_text(segments, ocr_results)

        if self.cfg.keep_intermediates:
            merged_path = self.cfg.working_dir / "merged.txt"
            merged_path.write_text(merged_text)

        title = (video_path or audio_path).stem

        progress.console.print("[bold]Generating notes with LLM...[/bold]")
        markdown = build_output(
            merged_text,
            self.cfg.llm_provider,
            self.cfg.llm_model,
            title,
            llm_base_url=self.cfg.llm_base_url,
        )

        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()[:80]
        output_path = self.cfg.output_dir / f"{safe_title}.md"
        output_path.write_text(markdown)

        progress.console.print(f"[bold green]Notes saved to: {output_path}[/bold green]")
        return output_path

    def _run_asr(
        self, engine: ASREngine, audio_path: Path, progress: Optional[Progress] = None
    ) -> list[dict]:
        """执行 ASR 转写，优先从缓存加载。"""
        if self.cfg.transcript_path.exists() and self.cfg.keep_intermediates:
            return engine.load_transcript(self.cfg.transcript_path)
        segments = engine.transcribe(audio_path, self.cfg.lang, progress)
        if self.cfg.keep_intermediates:
            engine.save_transcript(segments, self.cfg.transcript_path)
        return segments

    def _run_ocr(
        self,
        engine: OCREngine,
        frames: list[tuple[float, Path]],
        progress: Optional[Progress] = None,
    ) -> list[dict]:
        """执行 OCR 识别，优先从缓存加载。"""
        if self.cfg.ocr_path.exists() and self.cfg.keep_intermediates:
            return engine.load_result(self.cfg.ocr_path)
        results = engine.extract(frames, progress)
        if self.cfg.keep_intermediates:
            engine.save_result(results, self.cfg.ocr_path)
        return results
