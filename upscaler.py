import tkinter as tk
from tkinter import filedialog
import subprocess
import os
import shutil

def select_files_or_folder():
    """
    Opens a dialog to select either a single video file or a folder containing videos.
    """
    root = tk.Tk()
    root.withdraw()
    root.title("Select Video Files or Folder")
    file_path = filedialog.askopenfilename(title="Select a Video File", filetypes=[("Video files", "*.mp4 *.avi *.mkv")])
    if file_path:
        return [file_path]
    folder_path = filedialog.askdirectory(title="Select Folder Containing Videos")
    if folder_path:
        return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(('.mp4', '.avi', '.mkv'))]
    return []

def select_destination_folder():
    """
    Opens a dialog to select the destination folder for upscaled videos.
    """
    root = tk.Tk()
    root.withdraw()
    root.title("Select Destination Folder")
    folder_path = filedialog.askdirectory(title="Select Destination Folder for Upscaled Videos")
    return folder_path if folder_path else "upscaled_videos"

def extract_frames(video_file, destination_folder):
    """
    Extracts frames from the given video file using GPU acceleration (if available).
    """
    frame_folder = os.path.join(destination_folder, "temporary_frames")
    os.makedirs(frame_folder, exist_ok=True)

    # Using FFmpeg with hardware-accelerated decoding (NVDEC)
    ffmpeg_command = [
        "ffmpeg", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda", "-i", video_file, 
        "-vf", "hwdownload,format=nv12", "-vsync", "0",
        os.path.join(frame_folder, "frame_%04d.png")
    ]
    subprocess.run(ffmpeg_command)
    return frame_folder

def upscale_frames(frame_folder):
    """
    Upscales the frames using realesrgan-ncnn-vulkan.
    Uses NVENC for GPU-accelerated upscaling.
    """
    output_folder = os.path.join(os.path.dirname(frame_folder), "out_frames")
    os.makedirs(output_folder, exist_ok=True)
    subprocess.run(["./realesrgan-ncnn-vulkan.exe", "-i", frame_folder, "-o", output_folder, "-n", "realesr-animevideov3", "-s", "2", "-f", "png"])
    shutil.rmtree(frame_folder)
    return output_folder

def reassemble_video(original_video, frame_folder, destination_folder):
    """
    Reassembles the video from the upscaled frames and original audio.
    Uses NVENC for GPU-accelerated video encoding.
    """
    upscaled_video = os.path.join(destination_folder, "upscaled_" + os.path.basename(original_video))
    ffmpeg_command = [
        "ffmpeg", "-i", os.path.join(frame_folder, "frame_%04d.png"), 
        "-i", original_video, "-c:v", "h264_nvenc", "-preset", "fast", 
        "-r", "25", "-pix_fmt", "yuv420p", "-vf", "scale=in_range=jpeg:out_range=mpeg", 
        upscaled_video
    ]
    subprocess.run(ffmpeg_command)
    shutil.rmtree(frame_folder)

def main():
    destination_folder = select_destination_folder()
    os.makedirs(destination_folder, exist_ok=True)
    video_files = select_files_or_folder()
    for video_file in video_files:
        print(f"Processing {video_file}...")
        frame_folder = extract_frames(video_file, destination_folder)
        upscale_frames(frame_folder)
        reassemble_video(video_file, frame_folder, destination_folder)

if __name__ == "__main__":
    main()
