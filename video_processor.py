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

    def process_video(self, video_file: str):
        logging.info(f"Processing {video_file}...")
        frame_folder = self.ffmpeg_handler.extract_frames(
            video_file, self.destination_folder
        )
        self.esrgan_handler.upscale_frames(frame_folder)
        self.ffmpeg_handler.reassemble_video(
            video_file, frame_folder, self.destination_folder
        )
        os.rmdir(frame_folder)

    def run(self):
        total_videos = len(self.video_files)
        for index, video_file in enumerate(self.video_files):
            self.process_video(video_file)
            progress = int((index + 1) / total_videos * 100)
            self.progress_updated.emit(progress)
