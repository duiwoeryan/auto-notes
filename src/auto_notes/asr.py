"""mlx-whisper 语音转文字引擎（Apple Silicon GPU 加速）。

用 av 库解码音频（无需 ffmpeg），再传给 mlx-whisper 做 GPU 推理。
"""

import json
from pathlib import Path
from typing import Optional

import av
import numpy as np
from rich.progress import Progress, TaskID


class ASREngine:
    """封装 mlx-whisper，利用 Apple Silicon GPU 加速语音识别。"""

    def __init__(self) -> None:
        self._model_path = "mlx-community/whisper-medium-mlx"

    def _decode_audio(self, path: str) -> np.ndarray:
        """用 av 重采样为 16kHz 单声道 float32（归一化到 [-1, 1]）。"""
        import mlx_whisper.audio as audio_module

        SAMPLE_RATE = audio_module.SAMPLE_RATE

        with av.open(path) as container:
            stream = container.streams.audio[0]
            resampler = av.AudioResampler(
                format="flt",
                layout="mono",
                rate=SAMPLE_RATE,
            )
            out_frames = []
            for frame in container.decode(stream):
                if frame is None:
                    continue
                for r in resampler.resample(frame):
                    out_frames.append(r.to_ndarray())

        if not out_frames:
            raise RuntimeError(f"No audio found in {path}")

        raw = np.concatenate(out_frames, axis=1).ravel()
        return raw

    def transcribe(
        self,
        audio_path: Path,
        lang: str = "auto",
        progress: Optional[Progress] = None,
    ) -> list[dict]:
        """
        转写音频文件，返回按时间排序的片段列表：
            [{"start": float, "end": float, "text": str}, ...]
        """
        import mlx_whisper

        task_id: Optional[TaskID] = None
        if progress:
            task_id = progress.add_task("Transcribing audio...", total=None)

        audio = self._decode_audio(str(audio_path))
        language: str | None = None if lang == "auto" else lang

        result = mlx_whisper.transcribe(
            audio,
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
        """将转录结果写入 JSON 文件（可用于后续缓存复用）。"""
        path.write_text(json.dumps(segments, ensure_ascii=False, indent=2))

    def load_transcript(self, path: Path) -> list[dict]:
        """从 JSON 文件加载已缓存的转录结果。"""
        return json.loads(path.read_text())
