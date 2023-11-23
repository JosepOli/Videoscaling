import subprocess
import re
import os
import logging


class FFmpegHandler:
    def run_subprocess(self, command: list) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(command, capture_output=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running command {' '.join(command)}: {e}")
            return None

    def extract_frames(self, video_file: str, destination_folder: str) -> str:
        frame_folder = os.path.join(destination_folder, "temporary_frames")
        os.makedirs(frame_folder, exist_ok=True)
        frame_rate = self.get_frame_rate(video_file)
        ffmpeg_command = [
            "ffmpeg",
            "-i",
            video_file,
            "-vf",
            f"fps={frame_rate}",
            "-q:v",
            "2",
            os.path.join(frame_folder, "frame_%04d.jpg"),
        ]
        self.run_subprocess(ffmpeg_command)
        return frame_folder

    def get_frame_rate(self, video_file: str) -> str:
        result = self.run_subprocess(["ffmpeg", "-i", video_file])
        if result:
            match = re.search(r"(\d+) fps", result.stderr)
            if match:
                return match.group(1)
        return "30"  # Default frame rate

    def reassemble_video(
        self, original_video: str, frame_folder: str, destination_folder: str
    ):
        upscaled_video = os.path.join(
            destination_folder, "upscaled_" + os.path.basename(original_video)
        )
        frame_rate = self.get_frame_rate(original_video)
        ffmpeg_command = [
            "ffmpeg",
            "-r",
            frame_rate,
            "-i",
            os.path.join(frame_folder, "frame_%04d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            upscaled_video,
        ]
        self.run_subprocess(ffmpeg_command)
