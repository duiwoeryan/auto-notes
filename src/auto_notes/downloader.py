"""yt-dlp 封装：视频 / 音频下载，实时进度解析，断点续传。"""

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from rich.progress import Progress, TaskID

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# 匹配 yt-dlp 的 [download]  X% 输出行
PROGRESS_RE = re.compile(r"\[download\]\s+(\d+\.?\d*)%")


class Downloader:
    """管理 yt-dlp 子进程，支持实时进度条和缓存复用。"""

    AUDIO_EXTS = (".m4a", ".webm", ".mp3", ".opus", ".aac", ".ogg")

    def __init__(self, yt_dlp_path: str = "yt-dlp") -> None:
        self.yt_dlp_path = yt_dlp_path
        self.cookies_from_browser: Optional[str] = None
        self.cookiefile: Optional[str] = None
        self.proxy: Optional[str] = None
        self.user_agent: str = USER_AGENT

    def download(
        self, url: str, output_dir: Path, progress: Optional[Progress] = None,
        audio_only: bool = False,
    ) -> tuple[Optional[Path], Path]:
        """下载视频（+音频）或仅音频，返回 (视频路径, 音频路径)。

        - audio_only=True 时视频路径为 None，只下载 bestaudio。
        - 已有缓存文件则跳过下载，直接返回。
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        template = str(output_dir / "%(title).80s.%(ext)s")

        # 先获取元信息（标题、ID），用于缓存检测和后续处理
        info = self._extract_info(url)
        title = info.get("title", "video")

        # ---- 缓存命中检查 ----
        existing_audio = self._find_audio_files(output_dir, title)
        if audio_only:
            if existing_audio:
                return None, existing_audio[-1]
        else:
            existing_mp4 = sorted(output_dir.glob(f"{title[:60]}*.mp4"))
            if existing_mp4 and existing_audio:
                return existing_mp4[-1], existing_audio[-1]

        # ---- 构造下载命令 ----
        args = self._build_base_args()
        args += [
            "--no-playlist",
            "-o", template,
        ]
        if audio_only:
            # 只下载最佳音频流，不写元文件 / 缩略图，最大化速度
            args += ["-f", "bestaudio", "--no-write-info-json", "--no-write-thumbnail"]
        else:
            args += ["--no-write-info-json", "--no-write-thumbnail"]
        args.append(url)

        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # ---- 实时进度条 ----
        task_id: Optional[TaskID] = None
        if progress and proc.stdout:
            task_id = progress.add_task("[cyan]Downloading...", total=100, start=False)
            last_pct = -1.0
            for line in proc.stdout:
                m = PROGRESS_RE.search(line)
                if m:
                    pct = float(m.group(1))
                    # 多段下载（如视频+音频分离）时百分比会重置
                    if pct < last_pct:
                        progress.reset(task_id, total=100, start=False,
                                       description="[cyan]Downloading...")
                    progress.update(task_id, completed=pct)
                    last_pct = pct
                elif "[Merger]" in line:
                    progress.update(task_id, description="[yellow]Merging...")
                elif "[ExtractAudio]" in line:
                    progress.update(task_id, description="[yellow]Processing audio...")

        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"yt-dlp failed with code {proc.returncode}")

        if task_id is not None and progress:
            progress.update(task_id, description="[green]Downloaded[/green]", completed=100)
            progress.remove_task(task_id)

        # ---- 定位实际输出文件 ----
        audio_files = self._find_audio_files(output_dir, title)
        if audio_only:
            if not audio_files:
                raise FileNotFoundError(f"Missing audio. Found: {audio_files}")
            return None, audio_files[-1]

        mp4_files = sorted(output_dir.glob(f"{title[:60]}*.mp4"))
        if not mp4_files or not audio_files:
            raise FileNotFoundError(f"Missing video or audio. Found mp4: {mp4_files}, audio: {audio_files}")
        return mp4_files[-1], audio_files[-1]

    def _find_audio_files(self, output_dir: Path, title: str) -> list[Path]:
        """按标题前缀和已知音频后缀匹配已下载的音频文件。"""
        files: list[Path] = []
        for ext in self.AUDIO_EXTS:
            files.extend(sorted(output_dir.glob(f"{title[:60]}*{ext}")))
        return sorted(files)

    def _extract_info(self, url: str) -> dict:
        """用 yt-dlp --dump-json 获取视频元信息。"""
        args = self._build_base_args()
        args += ["--dump-json", "--no-playlist", url]

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp info extraction failed: {result.stderr}")
        return json.loads(result.stdout)

    def _build_base_args(self) -> list[str]:
        """构造 yt-dlp 基础参数（UA、Referer、Cookie、代理）。"""
        args = [
            self.yt_dlp_path,
            "--user-agent", self.user_agent,
            "--referer", "https://www.bilibili.com",
        ]

        if self.cookies_from_browser:
            args += ["--cookies-from-browser", self.cookies_from_browser]
        elif self.cookiefile:
            args += ["--cookies", self.cookiefile]

        if self.proxy:
            args += ["--proxy", self.proxy]

        return args
