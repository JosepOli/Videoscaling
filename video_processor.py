import os
import logging
from PyQt5.QtCore import QObject, pyqtSignal
from ffmpeg_integration import FFmpegHandler
from esrgan_integration import ESRGANHandler
from typing import List
from utils import handle_subprocess_error, setup_logging


class VideoProcessor(QObject):
    progress_updated = pyqtSignal(int)

    def __init__(self, destination_folder: str, video_files: List[str]):
        super().__init__()
        self.destination_folder = destination_folder
        os.makedirs(self.destination_folder, exist_ok=True)
        self.video_files = video_files
        self.ffmpeg_handler = FFmpegHandler()
        self.esrgan_handler = ESRGANHandler()

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def process_video(self, video_file: str):
        logging.info(f"Processing video: {video_file}")

        # Extract the frame rate of the video
        frame_rate = self.ffmpeg_handler.get_frame_rate(video_file)

        frame_folder = os.path.join(self.destination_folder, "temp_frames")
        os.makedirs(frame_folder, exist_ok=True)
        ffmpeg_command = [
            "ffmpeg",
            "-i",
            video_file,
            "-vf",
            f"fps={frame_rate}",
            os.path.join(frame_folder, "frame_%04d.png"),
        ]

        # Run the FFmpeg command and handle progress updates
        self.ffmpeg_handler.run_subprocess(
            ffmpeg_command, progress_callback=self.progress_callback
        )

    def run(self):
        logging.info("Starting video processing")
        total_videos = len(self.video_files)
        for index, video_file in enumerate(self.video_files):
            self.process_video(video_file)
            progress = int((index + 1) / total_videos * 100)
            self.progress_updated.emit(progress)
