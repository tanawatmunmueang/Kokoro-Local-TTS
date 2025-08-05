# video_logic.py

import os
import platform
import subprocess
import shutil
import tempfile

def format_duration_hhmmss(seconds_float):
    """Formats seconds into a HH:MM:SS or MM:SS string."""
    if seconds_float is None or not isinstance(seconds_float, (int, float)) or seconds_float < 0:
        return "N/A"
    total_seconds = int(round(seconds_float))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def get_audio_duration(audio_path):
    """Gets the exact duration of an audio file using ffprobe."""
    if not audio_path or not os.path.exists(audio_path):
        return None

    ffprobe_path = os.path.join("ffmpeg", "ffprobe.exe") if platform.system() == "Windows" else os.path.join("ffmpeg", "ffprobe")
    if not os.path.exists(ffprobe_path):
        return None

    command = [ffprobe_path, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=10)
        return float(result.stdout.strip())
    except Exception:
        return None

def get_media_details(media_path):
    """Gets filename, size, and duration for a given media file."""
    if not media_path or not os.path.exists(media_path):
        return "N/A", "N/A", "N/A"

    filename = os.path.basename(media_path)
    try:
        size_str = f"{os.path.getsize(media_path) / (1024*1024):.2f} MB"
    except OSError:
        size_str = "N/A"

    duration_str = format_duration_hhmmss(get_audio_duration(media_path))

    return filename, size_str, duration_str

def generate_video_from_media(audio_path, cover_path, resolution_choice, encoder_choice, frame_rate_str):
    """
    Generates a video by looping a SINGLE cover media for the duration of an audio file.
    This is used for standard generation and as the second step for sequence generation.
    """
    ffmpeg_path = os.path.join("ffmpeg", "ffmpeg.exe") if platform.system() == "Windows" else os.path.join("ffmpeg", "ffmpeg")
    if not os.path.exists(ffmpeg_path):
        return None, "❌ Video Generation Error: ffmpeg.exe not found."

    if not audio_path or not os.path.exists(audio_path): return None, "❌ Video Generation Error: Audio file is missing."
    if not cover_path or not os.path.exists(cover_path): return None, "❌ Video Generation Error: Cover file is missing."

    audio_duration_seconds = get_audio_duration(audio_path)

    IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.webp']
    is_image_cover = os.path.splitext(cover_path)[1].lower() in IMAGE_EXTENSIONS

    width, height = (1280, 720) if resolution_choice == "720p (Fast)" else (1920, 1080)
    # This filter scales and pads the cover to fit the target resolution without stretching.
    vf_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"

    output_dir = "kokoro_videos"
    os.makedirs(output_dir, exist_ok=True)
    video_name = os.path.splitext(os.path.basename(audio_path))[0] + ".mp4"
    final_video_path = os.path.join(output_dir, video_name)

    command = [ffmpeg_path, '-y']

    # Configure inputs based on whether the cover is an image or a video
    if is_image_cover:
        command.extend(['-loop', '1', '-framerate', str(frame_rate_str), '-i', cover_path, '-i', audio_path])
    else:
        command.extend(['-stream_loop', '-1', '-i', cover_path, '-i', audio_path])
        command.extend(['-map', '0:v:0', '-map', '1:a:0'])

    command.extend(['-vf', vf_filter])

    # Configure video encoder settings
    if 'nvenc' in encoder_choice:
        encoder_params = ['-c:v', 'h264_nvenc', '-preset', 'p4', '-cq', '22', '-pix_fmt', 'yuv420p']
    else:
        tune_param = ['-tune', 'stillimage'] if is_image_cover else []
        encoder_params = ['-c:v', 'libx264', *tune_param, '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p']

    command.extend(encoder_params)

    # Configure audio settings and video duration
    command.extend(['-c:a', 'aac', '-b:a', '192k'])
    if audio_duration_seconds and audio_duration_seconds > 0:
        command.extend(['-t', f"{audio_duration_seconds:.3f}"]) # Use exact duration
    else:
        command.extend(['-shortest']) # Fallback if duration is unknown

    command.extend(['-r', str(frame_rate_str)])
    command.append(final_video_path)

    try:
        print(f"Executing FFmpeg: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')

        print(f"Saved video to: {final_video_path}")
        filename, size, duration = get_media_details(final_video_path)
        info_text = (f"Generated File: {filename}\n"
                     f"Resolution: {resolution_choice.split(' ')[0]}\n"
                     f"Size: {size}\n"
                     f"Duration: {duration}\n"
                     f"Encoder: {encoder_choice.split('(')[0].strip()}\n"
                     f"---\n"
                     f"Saved to '{output_dir}' folder.")
        return final_video_path, info_text
    except subprocess.CalledProcessError as e:
        # If FFmpeg fails, log the error to the console for debugging.
        print(f"FFmpeg failed with exit code {e.returncode}")
        print(f"Stderr: {e.stderr}")
        return None, f"❌ Video Generation Error: FFmpeg failed. Check console for details."
    except Exception as e:
        import traceback; traceback.print_exc()
        return None, f"❌ An unexpected error occurred: {e}"

def generate_video_from_sequence(audio_path, cover_paths, resolution_choice, encoder_choice, frame_rate_str):
    """
    Generates a video by creating and looping a visual sequence from multiple cover media.
    This is the core of the "Shuffle & Sequence" mode.
    """
    ffmpeg_path = os.path.join("ffmpeg", "ffmpeg.exe") if platform.system() == "Windows" else os.path.join("ffmpeg", "ffmpeg")
    if not os.path.exists(ffmpeg_path):
        return None, "❌ Video Generation Error: ffmpeg.exe not found."

    temp_concat_video_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_f:
            temp_concat_video_path = temp_f.name

        width, height = (1280, 720) if resolution_choice == "720p (Fast)" else (1920, 1080)
        IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.webp']

        concat_cmd = [ffmpeg_path, '-y']
        filter_complex_parts = []
        concat_inputs = ""

        for i, path in enumerate(cover_paths):
            is_image = os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS
            if is_image:
                concat_cmd.extend(['-loop', '1', '-t', '1', '-framerate', str(frame_rate_str), '-i', path])
            else:
                concat_cmd.extend(['-i', path])

            filter_complex_parts.append(f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,setpts=PTS-STARTPTS[v{i}]")
            concat_inputs += f"[v{i}]"

        filter_complex_parts.append(f"{concat_inputs}concat=n={len(cover_paths)}:v=1:a=0[outv]")
        concat_cmd.extend(['-filter_complex', ";".join(filter_complex_parts)])
        concat_cmd.extend(['-map', '[outv]'])

        # This block checks the user's choice and applies it to the temporary file creation.
        # We use faster presets here because this file is temporary and speed is the priority.
        if 'nvenc' in encoder_choice:
            # Use GPU with a fast preset if selected
            print("Using GPU for temporary sequence creation.")
            temp_encoder_params = ['-c:v', 'h264_nvenc', '-preset', 'p1', '-cq', '28', '-pix_fmt', 'yuv420p']
        else:
            # Default to CPU with a very fast preset
            print("Using CPU for temporary sequence creation.")
            temp_encoder_params = ['-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p']

        concat_cmd.extend(temp_encoder_params)

        concat_cmd.extend(['-r', str(frame_rate_str), temp_concat_video_path])

        print(f"Creating temporary sequence clip: {' '.join(concat_cmd)}")
        subprocess.run(concat_cmd, capture_output=True, text=True, check=True, encoding='utf-8')

        print(f"Combining sequence clip with audio: {audio_path}")
        return generate_video_from_media(audio_path, temp_concat_video_path, resolution_choice, encoder_choice, frame_rate_str)

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg failed during sequence creation with exit code {e.returncode}")
        print(f"Stderr: {e.stderr}")
        return None, f"❌ Sequence Generation Error: FFmpeg failed. Check console for details."
    except Exception as e:
        import traceback; traceback.print_exc()
        return None, f"❌ An unexpected error occurred during sequence creation: {e}"
    finally:
        if temp_concat_video_path and os.path.exists(temp_concat_video_path):
            try:
                os.remove(temp_concat_video_path)
                print(f"Removed temporary file: {temp_concat_video_path}")
            except OSError as e:
                print(f"Error removing temporary file {temp_concat_video_path}: {e}")
