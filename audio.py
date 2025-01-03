import os
import shutil
import subprocess
import sys
import json
from pathlib import Path


def get_audio_info(file_path):
    # Use ffprobe to get audio track information in JSON format
    ffprobe_command = [
        "/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries", "stream=index,codec_type,codec_name,channels,channel_layout,bit_rate,duration,language,tags",
        "-of", "json", file_path
    ]
    result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise Exception(f"ffprobe failed: {result.stderr.decode()}")

    probe_data = json.loads(result.stdout)
    audio_tracks = []
    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "audio":
            audio_tracks.append({
                "index": stream["index"],
                "format": stream["codec_name"],
                "channels": int(stream["channels"])
            })
    return audio_tracks

def convert_audio(file_path, output_path):
    # Get audio track information
    audio_tracks = get_audio_info(file_path)

    # Build the ffmpeg command
    ffmpeg_command = ["/opt/homebrew/bin/ffmpeg", "-i", file_path, "-map", "0"]

    for track in audio_tracks:
        index = track["index"]
        format = track["format"]
        channels = track["channels"]

        if format == "dts":
            ffmpeg_command.extend(["-c:a:{}".format(index), "eac3", "-ac", "6"])
        elif channels > 6:
            ffmpeg_command.extend(["-c:a:{}".format(index), "copy", "-ac", "6"])
        else:
            ffmpeg_command.extend(["-c:a:{}".format(index), "copy"])

    ffmpeg_command.extend(["-threads", "4"])
    ffmpeg_command.extend(["-c:v", "copy", "-c:s", "copy", output_path])

    subprocess.run(ffmpeg_command, check=True)

def process_directory(directory):
    home_dir = str(Path.home())

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".mkv"):
                file_path = os.path.join(root, file)
                output_path = os.path.splitext(file_path)[0] + ".remuxed.mkv"

                audio_tracks = get_audio_info(file_path)
                needs_conversion = any(
                    track["format"] == "dts" or track["channels"] > 6
                    for track in audio_tracks
                )

                if needs_conversion:
                    output_file_name = os.path.splitext(file)[0] + ".remuxed.mkv"
                    temp_output_path = os.path.join(home_dir, output_file_name)
                    final_output_path = os.path.join(root, output_file_name)

                    print(f"Processing: {file_path}")

                    convert_audio(file_path, temp_output_path)
                    print(f"Saved to: {temp_output_path}")

                    shutil.move(temp_output_path, final_output_path)
                    print(f"Saved to: {final_output_path}")
                else:
                    print(f"Skipping: {file_path} (no conversion needed)")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert_audio.py <directory_path>")
        sys.exit(1)

    directory = sys.argv[1].strip()
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory.")
        sys.exit(1)

    process_directory(directory)