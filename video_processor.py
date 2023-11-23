import subprocess
import os
import shutil
import re
import logging
from typing import List

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class VideoProcessor:
    def __init__(self, destination_folder: str, video_files: List[str]):
        self.destination_folder = destination_folder
        os.makedirs(self.destination_folder, exist_ok=True)
        self.video_files = video_files

    @staticmethod
    def run_subprocess(
        command: List[str], capture_output: bool = False
    ) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                command, text=True, capture_output=capture_output, check=True
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running command {' '.join(command)}: {e}")
            return None

    @staticmethod
    def get_frame_rate(video_file: str) -> str:
        result = VideoProcessor.run_subprocess(
            ["ffmpeg", "-i", video_file], capture_output=True
        )
        if result and result.stderr:
            matches = re.search(r"(\d{1,3}\.\d{1,2}) fps", result.stderr)
            return matches.group(1) if matches else "25"
        return "25"

    def process_video(self, video_file: str):
        logging.info(f"Processing {video_file}...")
        frame_folder = self.extract_frames(video_file)
        self.upscale_frames(frame_folder)
        self.reassemble_video(video_file, frame_folder)

    def extract_frames(self, video_file: str) -> str:
        frame_folder = os.path.join(self.destination_folder, "temporary_frames")
        os.makedirs(frame_folder, exist_ok=True)
        frame_rate = self.get_frame_rate(video_file)
        ffmpeg_command = [
            "ffmpeg",
            "-i",
            video_file,
            "-vf",
            f"fps=fps={frame_rate}",
            "-q:v",
            "2",
            os.path.join(frame_folder, "frame_%04d.jpg"),
        ]
        self.run_subprocess(ffmpeg_command)
        return frame_folder

    def upscale_frames(self, frame_folder: str):
        output_folder = os.path.join(os.path.dirname(frame_folder), "out_frames")
        os.makedirs(output_folder, exist_ok=True)
        realesrgan_executable = os.path.join(
            "Real-ESRGAN", "realesrgan", "realesrgan-ncnn-vulkan.exe"
        )
        self.run_subprocess(
            [
                realesrgan_executable,
                "-i",
                frame_folder,
                "-o",
                output_folder,
                "-n",
                "realesr-animevideov3",
                "-s",
                "2",
                "-f",
                "png",
            ]
        )

    def reassemble_video(self, original_video: str, frame_folder: str):
        upscaled_video = os.path.join(
            self.destination_folder, "upscaled_" + os.path.basename(original_video)
        )
        frame_rate = self.get_frame_rate(original_video)
        ffmpeg_command = [
            "ffmpeg",
            "-i",
            os.path.join(frame_folder, "frame_%04d.png"),
            "-i",
            original_video,
            "-c:v",
            "h264_nvenc",
            "-preset",
            "fast",
            "-r",
            frame_rate,
            "-pix_fmt",
            "yuv420p",
            upscaled_video,
        ]
        self.run_subprocess(ffmpeg_command)
        shutil.rmtree(frame_folder)

    def run(self):
        for video_file in self.video_files:
            self.process_video(video_file)
