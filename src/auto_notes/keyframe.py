"""OpenCV 关键帧提取：按时间间隔从视频帧中抽样截图。"""

from pathlib import Path

class KeyframeExtractor:
    """以固定间隔从视频中抽取帧画面，用于后续 OCR。"""

    def extract(
        self,
        video_path: Path,
        output_dir: Path,
        max_frames: int = 120,
    ) -> list[tuple[float, Path]]:
        import cv2
        """
        按时间均匀抽取至多 max_frames 帧，返回 [(时间戳, 帧文件路径)]。
        视频不可读时返回空列表。
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        if duration <= 0:
            cap.release()
            return []

        interval = max(1, frame_count // max_frames)
        frames: list[tuple[float, Path]] = []
        idx = 0

        for frame_idx in range(0, frame_count, interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            timestamp = frame_idx / fps
            out_file = output_dir / f"frame_{idx:04d}.png"
            cv2.imwrite(str(out_file), frame)
            frames.append((timestamp, out_file))
            idx += 1

        cap.release()
        return frames
