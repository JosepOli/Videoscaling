import tkinter as tk
from tkinter import filedialog, simpledialog
import subprocess
import os
import shutil
import json
import concurrent.futures


def get_video_properties(video_file):
    """
    Returns the properties of the video file such as frame rate and resolution.
    """
    cmd = f'ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate -of json "{video_file}"'
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)
    return json.loads(result.stdout)


def select_files_or_folder():
    """
    Opens a dialog to select either a single video file or a folder containing videos.
    """
    root = tk.Tk()
    root.withdraw()
    root.title("Select Video Files or Folder")
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
    """
    Opens a dialog to select the destination folder for upscaled videos.
    """
    root = tk.Tk()
    root.withdraw()
    root.title("Select Destination Folder")
    folder_path = filedialog.askdirectory(
        title="Select Destination Folder for Upscaled Videos"
    )
    return folder_path if folder_path else "upscaled_videos"


def list_upscaling_models(models_folder):
    """
    Lists all upscaling models in the specified folder.
    """
    if not os.path.exists(models_folder):
        raise FileNotFoundError(
            f"The specified models folder does not exist: {models_folder}"
        )
    models = [f for f in os.listdir(models_folder) if f.endswith(".bin")]
    print(f"Found models: {models}")  # This line is for debugging purposes
    return models


def user_select_model(models):
    """
    Prompts the user to select an upscaling model from a list using a list box.
    """

    def on_select(evt):
        # Handle event to retrieve selection from the listbox
        index = evt.widget.curselection()
        if index:
            selection = evt.widget.get(index)
            # Set the user's selection
            user_selection.append(selection)
            # Schedule the window to close shortly after
            root.after(100, root.destroy)

    # Initialize the root Tkinter window
    root = tk.Tk()
    root.title("Select Upscaling Model")

    # Create the listbox and populate it with the model names
    listbox = tk.Listbox(root, width=50, height=20)
    for item in models:
        listbox.insert(tk.END, item)
    listbox.pack(side="left", fill="both", expand=True)

    # Create a scrollbar and attach it to the listbox
    scrollbar = tk.Scrollbar(root, orient="vertical")
    scrollbar.config(command=listbox.yview)
    scrollbar.pack(side="right", fill="y")
    listbox.config(yscrollcommand=scrollbar.set)

    # This list will hold the user's selection
    user_selection = []

    # Bind the selection event to the handler function
    listbox.bind("<<ListboxSelect>>", on_select)

    # Start the Tkinter event loop
    root.mainloop()

    # Return the user's selection if one was made
    return user_selection[0] if user_selection else None


def extract_and_upscale_frames(
    video_file, destination_folder, frame_rate, scale_factor, model
):
    """
    Extracts and upscales frames from the given video file.
    """
    frame_folder = os.path.join(
        destination_folder, os.path.basename(video_file) + "_frames"
    )
    os.makedirs(frame_folder, exist_ok=True)

    # Extract frames
    subprocess.run(
        [
            "ffmpeg",
            "-i",
            video_file,
            "-r",
            frame_rate,
            os.path.join(frame_folder, "frame_%04d.png"),
        ]
    )

    # Upscale frames
    output_folder = os.path.join(
        destination_folder, os.path.basename(video_file) + "_upscaled"
    )
    os.makedirs(output_folder, exist_ok=True)
    subprocess.run(
        [
            "./realesrgan/realesrgan_ncnn_vulkan.exe",
            "-i",
            frame_folder,
            "-o",
            output_folder,
            "-n",
            model,
            "-s",
            str(scale_factor),
            "-f",
            "png",
        ]
    )

    shutil.rmtree(frame_folder)
    return output_folder


def reassemble_video(original_video, frame_folder, destination_folder, frame_rate):
    """
    Reassembles the video from the upscaled frames and original audio.
    """
    upscaled_video = os.path.join(
        destination_folder, "upscaled_" + os.path.basename(original_video)
    )
    ffmpeg_command = [
        "ffmpeg",
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
        "-vf",
        "scale=in_range=jpeg:out_range=mpeg",
        upscaled_video,
    ]
    subprocess.run(ffmpeg_command)
    shutil.rmtree(frame_folder)


def process_video(video_file, destination_folder, frame_rate, scale_factor, model):
    """
    Process a single video file by extracting, upscaling frames, and reassembling the video.
    """
    print(f"Processing {video_file}...")
    upscaled_frames_folder = extract_and_upscale_frames(
        video_file, destination_folder, frame_rate, scale_factor, model
    )
    reassemble_video(video_file, upscaled_frames_folder, destination_folder, frame_rate)
    shutil.rmtree(upscaled_frames_folder)


def main():
    destination_folder = select_destination_folder()
    os.makedirs(destination_folder, exist_ok=True)
    video_files = select_files_or_folder()

    models_folder = os.path.abspath("realesrgan/models")
    try:
        models = list_upscaling_models(models_folder)
    except FileNotFoundError as e:
        print(e)
        return
    model = user_select_model(models)
    if not model:
        print("No model selected. Exiting.")
        return

    scale_factor = input("Enter scale factor (e.g., 2): ")

    with concurrent.futures.ProcessPoolExecutor() as executor:
        for video_file in video_files:
            video_properties = get_video_properties(video_file)
            frame_rate = video_properties["streams"][0]["r_frame_rate"]
            executor.submit(
                process_video,
                video_file,
                destination_folder,
                frame_rate,
                scale_factor,
                model,
            )


if __name__ == "__main__":
    main()
