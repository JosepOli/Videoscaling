import os
import logging
import subprocess


class ESRGANHandler:
    def __init__(self):
        self.realesrgan_executable = os.path.join(
            "Real-ESRGAN", "realesrgan_ncnn_vulkan.exe"
        )

    def run_subprocess(self, command: list):
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running Real-ESRGAN command: {e}")

    def upscale_frames(self, frame_folder: str):
        output_folder = os.path.join(os.path.dirname(frame_folder), "upscaled_frames")
        os.makedirs(output_folder, exist_ok=True)
        realesrgan_command = [
            self.realesrgan_executable,
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
        self.run_subprocess(realesrgan_command)
