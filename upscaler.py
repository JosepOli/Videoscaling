import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import json


# Function to get frame rate from a video using ffprobe
def get_frame_rate(video_path):
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate",
            "-of",
            "json",
            video_path,
        ]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        frame_rate_info = json.loads(result.stdout)
        frame_rate = eval(frame_rate_info["streams"][0]["r_frame_rate"])
        return frame_rate
    except Exception as e:
        print(f"Error calculating frame rate: {e}")
        return 1


# Function to extract frames from a video using ffmpeg
def extract_frames(video_path, dest_folder, fps):
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    command = [
        "ffmpeg",
        "-i",
        video_path,
        "-vf",
        f"fps={fps}",
        os.path.join(dest_folder, "frame_%04d.png"),
    ]
    try:
        subprocess.run(command, check=True)
        print(f"Frames extracted to {dest_folder}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")


# Upscaling images using Real-ESRGAN
def upscale_image(input_path, output_path, model, progress_callback):
    cmd = [
        "realesrgan-ncnn-vulkan.exe",
        "-i",
        input_path,
        "-o",
        output_path,
        "-m",
        "realesrgan/models",
        "-n",
        model,
    ]
    try:
        subprocess.run(cmd, check=True)
        progress_callback(1)  # Update progress
    except subprocess.CalledProcessError as e:
        print(f"An error occurred during upscaling: {e}")


# Function to reassemble video with original audio
def reassemble_video(frame_folder, audio_file, output_video, frame_rate):
    cmd = [
        "ffmpeg",
        "-r",
        str(frame_rate),
        "-i",
        os.path.join(frame_folder, "frame_%04d.png"),
        "-i",
        audio_file,
        "-c:v",
        "libx264",
        "-c:a",
        "copy",
        "-strict",
        "experimental",
        output_video,
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred during video reassembly: {e}")


# Function to update the progress bar
def update_progress(n):
    progress["value"] += n
    root.update_idletasks()


def populate_models_dropdown():
    models_path = "realesrgan/models"
    try:
        model_files = [f for f in os.listdir(models_path) if f.endswith(".bin")]
        return model_files
    except Exception as e:
        print(f"Error accessing models directory: {e}")
        return []


def get_audio_bitrate(video_path):
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=bit_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        bitrate = int(result.stdout.strip())
        return bitrate
    except Exception as e:
        print(f"Error getting audio bitrate: {e}")
        return None  # Return None or a default value if you prefer


def on_drop(event):
    video_files_raw = event.data.strip().split()
    # Clean file path and reconstruct paths considering spaces and quotes
    video_files = [
        file.replace("{", "").replace("}", "").replace("file:///", "")
        for file in video_files_raw
    ]
    video_files = " ".join(video_files)
    video_files = video_files.split(" '")
    video_files = [file.strip("'") for file in video_files]

    for video_file in video_files:
        video_file = video_file.replace("/", "\\")
        if not os.path.isabs(video_file):
            video_file = f"C:{video_file}"

        try:
            print(f"Processing: {video_file}")
            # Get video frame rate and original audio
            frame_rate = get_frame_rate(video_file)
            filename = os.path.basename(video_file)
            basename = os.path.splitext(filename)[0]
            output_folder = f"extracted_frames_{basename}"
            audio_temp = f"temp_audio_{basename}.aac"  # Temp file for audio

            # Extract frames
            extract_frames(video_file, output_folder, frame_rate)

            original_bitrate = get_audio_bitrate(video_file)
            audio_bitrate_option = (
                f"-b:a {original_bitrate}k" if original_bitrate else ""
            )  # Use original bitrate if available

            # Extract audio with the determined bitrate
            cmd_audio = [
                "ffmpeg",
                "-i",
                video_file,
                "-vn",  # No video
                "-acodec",
                "aac",  # Re-encode audio to AAC
                audio_bitrate_option,  # Apply bitrate
                audio_temp,
            ]
            try:
                subprocess.run(cmd_audio, check=True)
            except subprocess.CalledProcessError as e:
                print(f"An error occurred during audio extraction: {e}")

            # Upscale frames
            frames_folder = os.path.join(output_folder, "frames")
            upscaled_folder = os.path.join(output_folder, "upscaled")
            if not os.path.exists(upscaled_folder):
                os.makedirs(upscaled_folder)
            frame_files = [
                os.path.join(frames_folder, f)
                for f in os.listdir(frames_folder)
                if f.endswith(".png")
            ]

            total_frames = len(frame_files)
            progress["maximum"] = total_frames

            for idx, frame in enumerate(frame_files):
                output_frame = os.path.join(upscaled_folder, f"upscaled_{idx:04d}.png")
                upscale_image(
                    frame,
                    output_frame,
                    model_var.get(),
                    lambda x: update_progress(x / total_frames),
                )
                print(
                    f"Upscaled {idx + 1}/{total_frames} frames"
                )  # Optional verbose output

            # Reassemble video with upscaled frames and original audio
            output_video = f"upscaled_{basename}.mp4"
            reassemble_video(upscaled_folder, audio_temp, output_video, frame_rate)

            # Cleanup
            if messagebox.askyesno(
                "Cleanup", "Do you want to delete the temporary files?"
            ):
                os.remove(audio_temp)
                for f in os.listdir(frames_folder):
                    os.remove(os.path.join(frames_folder, f))
                for f in os.listdir(upscaled_folder):
                    os.remove(os.path.join(upscaled_folder, f))
                os.rmdir(frames_folder)
                os.rmdir(upscaled_folder)

            print(f"Finished processing {video_file}")
        except Exception as e:
            print(f"Failed to process {video_file}: {e}")
            # Optional cleanup or error handling


# Tkinter GUI setup
root = TkinterDnD.Tk()
root.title("Drag and Drop Videos Here")

# Dropdown for model selection
model_var = tk.StringVar()
model_dropdown = ttk.Combobox(
    root, textvariable=model_var, values=populate_models_dropdown()
)
model_dropdown.pack()

# Label for drag and drop
label = tk.Label(root, text="Drag and drop video files here", padx=100, pady=100)
label.pack(fill=tk.BOTH, expand=True)

# Progress Bar
progress = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=100, mode="determinate")
progress.pack()

# Bind drop event and set up the Tkinter DnD window
label.drop_target_register(DND_FILES)
label.dnd_bind("<<Drop>>", on_drop)

root.mainloop()
