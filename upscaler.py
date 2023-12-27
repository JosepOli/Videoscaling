import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import subprocess
import os
import shutil
import json
import concurrent.futures

# Set up the root Tkinter instance
root = tk.Tk()
root.withdraw()

# -----------------------------
# Helper Functions
# -----------------------------


def get_video_properties(video_file):
    try:
        cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -of json "{video_file}"'
        result = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.stderr:
            print("Error in ffprobe:", result.stderr)
            return None
        return json.loads(result.stdout)
    except Exception as e:
        print("Error getting video properties:", e)
        return None


def select_files_or_folder():
    file_path = filedialog.askopenfilename(
        title="Select a Video File", filetypes=[("Video files", "*.mp4 *.avi *.mkv")]
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


def select_destination_folder():
    folder_path = filedialog.askdirectory(
        title="Select Destination Folder for Upscaled Videos"
    )
    return folder_path if folder_path else "upscaled_videos"


def list_upscaling_models(models_folder):
    if not os.path.exists(models_folder):
        raise FileNotFoundError(
            f"The specified models folder does not exist: {models_folder}"
        )
    return [f for f in os.listdir(models_folder) if f.endswith(".bin")]


def user_select_model(models):
    def on_select(evt):
        selection = listbox.get(listbox.curselection())
        user_choice.set(selection)  # Set the user's choice

    user_choice = tk.StringVar(root)  # Variable to store the user's choice
    dialog = tk.Toplevel(root)
    dialog.title("Select Upscaling Model")

    listbox = tk.Listbox(dialog, width=50, height=20)
    listbox.pack(side="left", fill="both", expand=True)

    scrollbar = tk.Scrollbar(dialog, orient="vertical")
    scrollbar.config(command=listbox.yview)
    scrollbar.pack(side="right", fill="y")

    listbox.config(yscrollcommand=scrollbar.set)
    for item in models:
        listbox.insert(tk.END, item)

    listbox.bind("<<ListboxSelect>>", on_select)

    ok_button = tk.Button(dialog, text="OK", command=dialog.destroy)
    ok_button.pack()

    root.wait_window(dialog)  # Wait for the user to make a selection
    return user_choice.get()  # Return the user's choice


# -----------------------------
# Video Processing Functions
# -----------------------------


def extract_and_upscale_frames(
    video_file, destination_folder, frame_rate, scale_factor, model
):
    frame_folder = None
    try:
        frame_folder = os.path.join(
            destination_folder, os.path.basename(video_file) + "_frames"
        )
        os.makedirs(frame_folder, exist_ok=True)

        output_folder = os.path.join(
            destination_folder, os.path.basename(video_file) + "_upscaled"
        )
        os.makedirs(output_folder, exist_ok=True)

        # Adjusted FFmpeg command
        ffmpeg_command = [
            "ffmpeg",
            "-i",
            video_file,
            "-vf",
            f"fps={frame_rate},scale=1280:720:flags=lanczos",
            "-threads",
            "0",
            os.path.join(frame_folder, "frame_%04d.jpg"),
        ]

        print("Running FFmpeg command for frame extraction:", " ".join(ffmpeg_command))
        # Run FFmpeg without capturing the output to see progress in the console
        subprocess.run(ffmpeg_command, check=True)

        # If realesrgan-ncnn-vulkan is not in PATH, provide the full path to the executable
        realesrgan_executable = r"realesrgan"  # Update this to the actual path
        output_folder = os.path.join(
            destination_folder, os.path.basename(video_file) + "_upscaled"
        )
        os.makedirs(output_folder, exist_ok=True)

        # Make sure the paths are correct
        input_frames_path = os.path.join(frame_folder, "frame_%04d.jpg")
        if not os.path.exists(input_frames_path.format(1)):
            raise FileNotFoundError(f"No frames found in {frame_folder}")

        realesrgan_command = [
            realesrgan_executable,
            "-i",
            frame_folder,
            "-o",
            output_folder,
            "-n",
            model,
            "-s",
            str(scale_factor),
        ]

        # Run Real-ESRGAN without capturing the output to see progress in the console
        subprocess.run(realesrgan_command, check=True)

        return output_folder
    except subprocess.CalledProcessError as e:
        print(
            f"Error in subprocess: {e.stderr.decode() if e.stderr else 'Unknown error'}"
        )
        return None
    except Exception as e:
        print(f"Error in extract_and_upscale_frames: {e}")
        return None
    finally:
        if frame_folder and os.path.exists(frame_folder):
            shutil.rmtree(frame_folder)


def reassemble_video(original_video, frame_folder, destination_folder, frame_rate):
    try:
        upscaled_video = os.path.join(
            destination_folder, "upscaled_" + os.path.basename(original_video)
        )
        ffmpeg_command = [
            "ffmpeg",
            "-hwaccel",
            "cuda",
            "-hwaccel_output_format",
            "cuda",
            "-framerate",
            frame_rate,
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
        subprocess.run(ffmpeg_command, check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print("Error in subprocess:", e.stderr.decode())
    except Exception as e:
        print("Error in reassemble_video:", e)


def process_video(video_file, destination_folder, frame_rate, scale_factor, model):
    try:
        print(f"Processing {video_file}...")
        upscaled_frames_folder = extract_and_upscale_frames(
            video_file, destination_folder, frame_rate, scale_factor, model
        )
        reassemble_video(
            video_file, upscaled_frames_folder, destination_folder, frame_rate
        )
        shutil.rmtree(upscaled_frames_folder)
    except Exception as e:
        print("Error in process_video:", e)


# -----------------------------
# Main Function
# -----------------------------


def main():
    print("Starting script...")  # Diagnostic print
    try:
        print("Selecting destination folder...")  # Diagnostic print
        destination_folder = select_destination_folder()
        print(f"Destination folder: {destination_folder}")  # Diagnostic print
        os.makedirs(destination_folder, exist_ok=True)

        print("Selecting video files...")  # Diagnostic print
        video_files = select_files_or_folder()
        print(f"Selected video files: {video_files}")  # Diagnostic print

        models_folder = os.path.abspath("realesrgan/models")
        models = list_upscaling_models(models_folder)
        print(f"Available models: {models}")  # Diagnostic print

        model = user_select_model(models)
        if not model:
            messagebox.showinfo("Info", "No model selected. Exiting.")
            return

        scale_factor = simpledialog.askstring(
            "Input", "Enter scale factor (e.g., 2):", parent=root
        )
        print(f"Selected scale factor: {scale_factor}")  # Diagnostic print

        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = []
            for video_file in video_files:
                video_properties = get_video_properties(video_file)
                if (
                    video_properties
                    and "streams" in video_properties
                    and len(video_properties["streams"]) > 0
                ):
                    frame_rate = video_properties["streams"][0]["r_frame_rate"]
                    output_folder = os.path.join(
                        destination_folder, os.path.basename(video_file) + "_upscaled"
                    )
                    os.makedirs(output_folder, exist_ok=True)
                    future = executor.submit(
                        process_video,
                        video_file,
                        destination_folder,
                        frame_rate,
                        scale_factor,
                        model,
                    )
                    futures.append(future)
                    print(f"Processing started for: {video_file}")
                else:
                    print(f"Failed to get video properties for {video_file}")

            concurrent.futures.wait(futures)
            print("Processing complete for all videos.")
    except FileNotFoundError as e:
        messagebox.showerror("File Not Found Error", str(e))
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        root.destroy()


if __name__ == "__main__":
    main()
