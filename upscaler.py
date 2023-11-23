import tkinter as tk
from tkinter import filedialog
import subprocess
import os
import shutil
import re
from typing import List, Optional
import threading
import logging

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class VideoProcessor:
    def __init__(self):
        self.destination_folder = self.select_destination_folder()
        os.makedirs(self.destination_folder, exist_ok=True)
        self.video_files = self.select_files_or_folder()

    @staticmethod
    def run_subprocess(
        command: List[str], capture_output: bool = False
    ) -> subprocess.CompletedProcess:
        """
        Runs a subprocess with the given command and optional output capture.
        """
        try:
            return subprocess.run(command, text=True, capture_output=capture_output)
        except subprocess.SubprocessError as e:
            logging.error(f"Error running command {' '.join(command)}: {e}")
            return None

    @staticmethod
    def get_frame_rate(video_file: str) -> str:
        """
        Extracts the frame rate of the given video file using FFmpeg.
        """
        result = VideoProcessor.run_subprocess(
            ["ffmpeg", "-i", video_file], capture_output=True
        )
        if result and result.stderr:
            matches = re.search(r"(\d{1,3}\.\d{1,2}) fps", result.stderr)
            return (
                matches.group(1) if matches else "25"
            )  # Default to 25 fps if not detected
        return "25"

    @staticmethod
    def select_files_or_folder() -> List[str]:
        """
        Opens a dialog to select either a single video file or a folder containing videos.
        """
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select a Video File",
            filetypes=[("Video files", "*.mp4 *.avi *.mkv")],
        )
        if file_path:
            return [file_path]
        folder_path = filedialog.askdirectory(title="Select Folder Containing Videos")
        if folder_path:
            return [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.endswith((".mp4", ".avi", ".mkv"))
            ]
        return []

    @staticmethod
    def select_destination_folder() -> str:
        """
        Opens a dialog to select the destination folder for upscaled videos.
        """
        root = tk.Tk()
        root.withdraw()
        folder_path = filedialog.askdirectory(
            title="Select Destination Folder for Upscaled Videos"
        )
        return folder_path if folder_path else "upscaled_videos"

    def process_video(self, video_file: str):
        """
        Process a single video file.
        """
        logging.info(f"Processing {video_file}...")
        frame_folder = self.extract_frames(video_file)
        self.upscale_frames(frame_folder)
        self.reassemble_video(video_file, frame_folder)

    def extract_frames(self, video_file: str) -> str:
        """
        Extracts frames from the given video file using the detected frame rate.
        """
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
            "2",  # Quality scale for JPEG
            os.path.join(frame_folder, "frame_%04d.jpg"),
        ]
        self.run_subprocess(ffmpeg_command)
        return frame_folder

    def upscale_frames(self, frame_folder: str):
        """
        Upscales the frames using realesrgan-ncnn-vulkan.
        """
        output_folder = os.path.join(os.path.dirname(frame_folder), "out_frames")
        os.makedirs(output_folder, exist_ok=True)

        # Path to the realesrgan-ncnn-vulkan executable
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
        """
        Reassembles the video from the upscaled frames and original audio.
        """
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
        """
        Process all selected video files.
        """
        for video_file in self.video_files:
            self.process_video(video_file)


def main():
    video_processor = VideoProcessor()
    video_processor.run()


if __name__ == "__main__":
    main()
