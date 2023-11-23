import subprocess
import re
import os
import logging
from utils import handle_subprocess_error


class FFmpegHandler:
    def run_subprocess(
        self, command: list, progress_callback=None
    ) -> subprocess.CompletedProcess:
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            for line in iter(process.stdout.readline, ""):
                if progress_callback:
                    progress_callback(line)
            process.stdout.close()
            return_code = process.wait()
            if return_code != 0:
                raise subprocess.CalledProcessError(return_code, command)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running command {' '.join(command)}: {e.stderr}")
            return None

    def extract_frames(self, video_file: str, destination_folder: str) -> str:
        frame_folder = os.path.join(destination_folder, "temporary_frames")
        os.makedirs(frame_folder, exist_ok=True)
        frame_rate = self.get_frame_rate(video_file)
        output_path = os.path.join(frame_folder, "frame_%04d.jpg")
        ffmpeg_command = [
            "ffmpeg",
            "-i",
            video_file,
            "-vf",
            f"fps={frame_rate}",
            "-q:v",
            "2",
            output_path,
        ]

        logging.info(f"Running FFmpeg command: {' '.join(ffmpeg_command)}")
        result = self.run_subprocess(ffmpeg_command)
        if result is None:
            logging.error(f"Failed to extract frames from {video_file}")
            return None

        return frame_folder

    def get_frame_rate(self, video_file: str) -> str:
        ffprobe_command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_file,
        ]

        try:
            result = subprocess.run(
                ffprobe_command, capture_output=True, text=True, check=True
            )
            frame_rate_str = result.stdout.strip()
            # Frame rate is usually in the format 'num/den', we calculate it as a float
            num, den = map(int, frame_rate_str.split("/"))
            return str(num / den)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error extracting frame rate: {e}")
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
