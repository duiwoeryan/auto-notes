"""mlx-whisper 语音转文字引擎（Apple Silicon GPU 加速）。

音频解码由 mlx-whisper 内部调用 ffmpeg 完成（需要本机安装 ffmpeg）。
"""

import json
from pathlib import Path
from typing import Optional

from rich.progress import Progress, TaskID


class ASREngine:
    """封装 mlx-whisper，利用 Apple Silicon GPU 加速语音识别。"""

    def __init__(self) -> None:
        self._model_path = "mlx-community/whisper-medium-mlx"

    def transcribe(
        self,
        audio_path: Path,
        lang: str = "auto",
        progress: Optional[Progress] = None,
    ) -> list[dict]:
        """
        转写音频文件，返回按时间排序的片段列表：
            [{"start": float, "end": float, "text": str}, ...]

        音频解码由 mlx-whisper 内部调用 ffmpeg 处理。
        """
        import mlx_whisper

        task_id: Optional[TaskID] = None
        if progress:
            task_id = progress.add_task("Transcribing audio...", total=None)

        language: str | None = None if lang == "auto" else lang

        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=self._model_path,
            language=language,
        )

        segments = [
            {
                "start": round(seg["start"], 2),
                "end": round(seg["end"], 2),
                "text": seg["text"].strip(),
            }
            for seg in result["segments"]
        ]

        if task_id is not None and progress:
            progress.remove_task(task_id)

        return segments

    def save_transcript(self, segments: list[dict], path: Path) -> None:
        path.write_text(json.dumps(segments, ensure_ascii=False, indent=2))

    def load_transcript(self, path: Path) -> list[dict]:
        return json.loads(path.read_text())
