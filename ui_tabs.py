# ui_tabs.py

import gradio as gr
import json
import os
import shutil
import time
import re
import traceback

import config
from tts_logic import text_to_speech, podcast_maker
from srt_logic import srt_process
from voice_mixer import generate_custom_audio, get_voices
from video_logic import generate_video_from_media

# --- Helper Functions ---

def validate_filename(filename):
    """
    Checks if a filename is valid for most operating systems.

    Returns:
        (bool, str or None): A tuple containing a boolean indicating validity
                             and a string with the error message if invalid.
    """
    # Check for empty or whitespace-only strings
    if not filename or not filename.strip():
        return False, "Filename cannot be empty."

    # Check for illegal characters
    illegal_chars = r'[\\/*?:"<>|]'
    found_illegal_chars = re.findall(illegal_chars, filename)
    if found_illegal_chars:
        # Get unique characters to display in the error
        unique_chars = sorted(list(set(found_illegal_chars)))
        return False, f"Filename cannot contain the following characters: {' '.join(unique_chars)}"

    # Check for names that are reserved on Windows
    reserved_names = [
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4",
        "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    ]
    if os.path.splitext(filename)[0].upper() in reserved_names:
        return False, "Filename is a reserved system name and cannot be used."

    # Check for filenames ending with a space or a period
    if filename.endswith('.') or filename.endswith(' '):
        return False, "Filename cannot end with a period or a space."

    return True, None


def save_text(text_to_save, filename, save_dir):
    """Saves the content of the textbox to a specified text file with robust validation and error handling."""
    # 1. Validate inputs before proceeding
    if not save_dir.strip():
        gr.Warning("Please provide a save directory.")
        return

    if not text_to_save.strip():
        gr.Warning("Textbox is empty. Nothing to save.")
        return

    # 2. Validate the filename
    is_valid, error_message = validate_filename(filename)
    if not is_valid:
        gr.Warning(error_message)
        return

    # 3. Check if the directory exists
    if not os.path.isdir(save_dir):
        gr.Warning(f"Save directory not found or is not a valid directory: '{save_dir}'")
        return

    try:
        # 4. Construct the full path and attempt to save
        filepath = os.path.join(save_dir, f"{filename}.txt")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text_to_save)

        gr.Info(f"Text successfully saved to: {filepath}")

    except PermissionError:
        err_msg = f"Permission denied. Cannot write to the directory '{save_dir}'. Please check your folder permissions."
        print(f"ERROR: {err_msg}")
        gr.Error(err_msg)
    except OSError as e:
        err_msg = f"An operating system error occurred while trying to save the file. Details: {e}"
        print(f"ERROR: {err_msg}")
        traceback.print_exc()
        gr.Error(err_msg)
    except Exception as e:
        # Fallback for any other unexpected errors
        err_msg = f"An unexpected error occurred while saving the file: {e}"
        print(f"ERROR: {err_msg}")
        traceback.print_exc() # Log the full error for debugging
        gr.Error(err_msg)


def read_multiple_files(files_list):
    """
    Takes a list of file paths, reads them, and returns the combined text.
    """
    if not files_list:
        return ""
    contents = []
    for file_path in files_list:
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    contents.append(f.read().strip())
            except Exception as e:
                print(f"Error reading file '{os.path.basename(file_path)}': {e}")
                gr.Warning(f"Could not read file: {os.path.basename(file_path)}")
    return "\n\n".join(contents)

def process_files_tts(files_list, model_name, voice, speed, pad_between, remove_silence, minimum_silence, custom_voicepack, local_save_path, progress=gr.Progress()):
    """
    Loops through uploaded files, generates TTS for each, renames it, and returns a list of output paths.
    Also saves a copy to a local directory if specified.
    """
    if not files_list:
        gr.Warning("No files were uploaded to process!")
        return None

    output_paths = []
    progress(0, desc="Starting file processing...")

    for i, file_path in enumerate(files_list):
        progress(i / len(files_list), desc=f"Processing: {os.path.basename(file_path)}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                print(f"Skipping empty file: {os.path.basename(file_path)}")
                continue

            final_path = None
            for path_from_generator in text_to_speech(
                text=content,
                model_name=model_name,
                voice_name=voice,
                speed=speed,
                pad_between_segments=pad_between,
                remove_silence=remove_silence,
                minimum_silence=minimum_silence,
                custom_voicepack=custom_voicepack
            ):
                final_path = path_from_generator

            output_filepath = final_path

            if output_filepath and os.path.exists(output_filepath):
                original_filename_base = os.path.splitext(os.path.basename(file_path))[0]
                output_dir = os.path.dirname(output_filepath)
                audio_extension = os.path.splitext(output_filepath)[1]
                renamed_path = os.path.join(output_dir, f"{original_filename_base}{audio_extension}")

                if os.path.exists(renamed_path):
                    os.remove(renamed_path)
                os.rename(output_filepath, renamed_path)

                output_filepath = renamed_path

                print(f"Successfully generated: {output_filepath}")
                output_paths.append(output_filepath)

                if local_save_path and os.path.isdir(local_save_path):
                    try:
                        shutil.copy2(output_filepath, local_save_path)
                        print(f"Copied generated file to: {os.path.join(local_save_path, os.path.basename(output_filepath))}")
                    except Exception as copy_e:
                        print(f"Error copying file to {local_save_path}: {copy_e}")
                        gr.Warning(f"Could not copy file for '{os.path.basename(file_path)}'. Check permissions.")
                elif local_save_path:
                    gr.Warning(f"Provided save path '{local_save_path}' is not a valid directory. File was not copied.")

            else:
                print(f"File generation failed for: {os.path.basename(file_path)}")

        except Exception as e:
            traceback.print_exc()
            gr.Error(f"A critical error occurred while processing {os.path.basename(file_path)}: {e}")

    if not output_paths:
        gr.Info("No audio files were generated. Please check the console for errors.")
        return None

    gr.Info(f"Successfully generated {len(output_paths)} audio file(s).")
    return gr.update(value=output_paths, visible=True)


def update_char_count(text):
    """Counts the characters in the input text and returns a formatted string."""
    return f"Character Count: {len(text) if text else 0}"

def update_file_count(files_list):
    """Counts the number of uploaded files and returns a formatted string."""
    return f"Files Uploaded: {len(files_list) if files_list else 0}"

def toggle_autoplay(autoplay):
    return gr.Audio(interactive=False, label='Output Audio', autoplay=autoplay)

# --- UI Tab Creation Functions ---

def create_batch_tts_tab():
    with gr.Blocks() as demo:
        # A hidden component to store whether default voices are 'shown' or 'hidden'.
        visibility_state = gr.State(value="shown")
        audio_filepath_state = gr.State(value=None)

        gr.Markdown("# Batched TTS")
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Upload file(s) OR type in the box below")
                batch_file_uploader = gr.File(
                    label="Upload Text File(s) (.txt)",
                    file_types=['.txt'],
                    file_count="multiple",
                    type="filepath"
                )
                file_counter = gr.Markdown("Files Uploaded: 0")

                text = gr.Textbox(
                    label='Enter Text',
                    lines=8,
                    placeholder="Type your text here, or upload file(s) above..."
                )
                char_counter = gr.Markdown("Character Count: 0")

                file_name_input = gr.Textbox(
                    label="Save File Name",
                    info="Provide a name for the text file. The .txt extension is added automatically.",
                    placeholder="e.g., my_story_script"
                )
                save_path_input = gr.Textbox(
                    label="Save to Directory",
                    info="Provide the full path to the folder where the text file should be saved.",
                    placeholder="e.g., C:\\Users\\YourName\\Documents"
                )

                save_text_btn = gr.Button("Save Text", variant='secondary')

                gr.Markdown("### Voice Selection")
                voice_filter = gr.Textbox(
                    label="Filter Voices",
                    placeholder="Type here to filter the voice list below...",
                    interactive=True
                )

                with gr.Row():
                    voice = gr.Dropdown(
                        choices=config.VOICE_LIST,
                        value='am_michael',
                        allow_custom_value=False,
                        label='Voice',
                        info='Default voices are more stable'
                    )

                toggle_voices_btn = gr.Button("Hide Default Voices", variant='secondary')

                with gr.Row():
                    generate_btn = gr.Button('Generate', variant='primary')
                    cancel_btn = gr.Button('Cancel', variant='secondary')

            with gr.Column():
                with gr.Accordion('Audio Output', open=True):
                    max_size_mb = gr.Slider(
                        minimum=0,maximum=1000,
                        step=10,
                        value=200,
                        label="Max Preview File Size (MB)",
                        info="Prevents browser crashes. Files over this size are generated but not loaded for preview.",
                        interactive=True )

                    audio = gr.Audio(interactive=False, label='Output Audio', autoplay=True)

                    audio_path_display = gr.Markdown("", visible=False)
                    audio_download = gr.File(label="Download Audio", interactive=False, visible=False)
                    size_warning = gr.Markdown("", visible=False)

                    autoplay = gr.Checkbox(value=True, label='Autoplay')
                    autoplay.change(toggle_autoplay, inputs=[autoplay], outputs=[audio])

                with gr.Accordion('Audio Settings', open=True):
                    model_name=gr.Dropdown(config.MODEL_LIST,label="Model",value=config.MODEL_LIST[0])
                    speed = gr.Slider(minimum=0.1, maximum=2, value=1, step=0.1, label='⚡️Speed')
                    remove_silence = gr.Checkbox(value=False, label='✂️ Remove Silence From TTS')
                    minimum_silence = gr.Number(label="Keep Silence Upto (In seconds)", value=0.05)
                    pad_between = gr.Slider(minimum=0, maximum=2, value=0, step=0.1, label='🔇 Pad Between')
                    custom_voicepack = gr.File(label='Upload Custom VoicePack .pt file')

        def on_start_generation():
            # Show an info prompt to the user when generation begins.
            gr.Info("TTS generation has started, please wait... ⏳", duration=3)
            print("Log: Generate button pressed.")
            return gr.update(value=None, visible=True), gr.update(value=None, visible=False), gr.update(value="", visible=False)

        def check_audio_size_and_load(audio_filepath, max_mb):
            if not audio_filepath or not os.path.exists(audio_filepath):
                return None, gr.update(value=None, visible=False), gr.update(value="", visible=False)

            try:
                max_bytes = max_mb * 1024 * 1024
                file_size_bytes = os.path.getsize(audio_filepath)

                if file_size_bytes > max_bytes:
                    file_size_mb = file_size_bytes / (1024 * 1024)
                    warning_text = (
                        f"Audio generated successfully, but at {file_size_mb:.2f} MB, it exceeds the preview limit of {max_mb} MB. "
                        f"You can find the output file in your `kokoro_audio` folder."
                    )
                    return (
                        gr.update(visible=False),  # Hide the audio output box
                        gr.update(value=audio_filepath, visible=True),
                        gr.update(value=warning_text, visible=True)
                    )
                else:
                    return (
                    gr.update(value=audio_filepath, visible=True),
                    gr.update(value=audio_filepath, visible=False),
                    gr.update(value="", visible=False)
                )
            except Exception as e:
                return (
                    gr.update(visible=False),  # Hide the audio output box
                    gr.update(visible=False),
                    gr.update(value=f"⚠️ Error checking audio size: {e}", visible=True)
                )

        def update_files_and_text(files_list):
            text_content = read_multiple_files(files_list)
            return update_file_count(files_list), text_content, update_char_count(text_content)

        def toggle_default_voices(current_state):
            standard_prefixes = ("am_", "af_", "bm_", "bf_")

            if current_state == "shown":
                new_state = "hidden"
                new_button_update = gr.update(value="Show Default Voices", variant='primary')
                new_choices = [v for v in config.VOICE_LIST if not v.startswith(standard_prefixes)]
                new_value = new_choices[0] if new_choices else None

                return gr.update(choices=new_choices, value=new_value), new_button_update, new_state
            else:
                new_state = "shown"
                new_button_update = gr.update(value="Hide Default Voices", variant='secondary')
                new_choices = config.VOICE_LIST
                new_value = 'am_michael'

                return gr.update(choices=new_choices, value=new_value), new_button_update, new_state

        def filter_voice_list(filter_text, current_voice_value, current_state):
            standard_prefixes = ("am_", "af_", "bm_", "bf_")
            source_list = config.VOICE_LIST
            if current_state == "hidden":
                source_list = [v for v in config.VOICE_LIST if not v.startswith(standard_prefixes)]

            if not filter_text:
                current_val_in_list = current_voice_value in source_list
                default_val = source_list[0] if source_list else None
                return gr.update(choices=source_list, value=current_voice_value if current_val_in_list else default_val)

            filtered_choices = [v for v in source_list if filter_text.lower() in v.lower()]
            new_value = None
            if current_voice_value in filtered_choices:
                new_value = current_voice_value
            elif filtered_choices:
                new_value = filtered_choices[0]

            return gr.update(choices=filtered_choices, value=new_value)

        toggle_voices_btn.click(
            fn=toggle_default_voices,
            inputs=[visibility_state],
            outputs=[voice, toggle_voices_btn, visibility_state]
        )

        voice_filter.change(
            fn=filter_voice_list,
            inputs=[voice_filter, voice, visibility_state],
            outputs=voice
        )

        save_text_btn.click(
            fn=save_text,
            inputs=[text, file_name_input, save_path_input]
        )

        batch_file_uploader.change(fn=update_files_and_text, inputs=batch_file_uploader, outputs=[file_counter, text, char_counter])
        text.change(fn=update_char_count, inputs=text, outputs=char_counter)

        inputs = [text, model_name, voice, speed, pad_between, remove_silence, minimum_silence, custom_voicepack]
        outputs_to_reset = [audio, audio_download, size_warning]

        tts_event = text.submit(fn=on_start_generation, outputs=outputs_to_reset).then(
            fn=text_to_speech, inputs=inputs, outputs=[audio_filepath_state]
        )

        generate_event = generate_btn.click(fn=on_start_generation, outputs=outputs_to_reset).then(
            fn=text_to_speech, inputs=inputs, outputs=[audio_filepath_state]
        )

        audio_filepath_state.change(
            fn=check_audio_size_and_load,
            inputs=[audio_filepath_state, max_size_mb],
            outputs=[audio, audio_download, size_warning]
        )

        cancel_btn.click(
            fn=None,
            inputs=None,
            outputs=None,
            cancels=[tts_event, generate_event]
        )

    return demo

def create_files_tts_tab():
    with gr.Blocks() as demo:
        visibility_state = gr.State(value="shown")

        gr.Markdown("# Files TTS\nUpload one or more text files to generate a separate audio file for each.")
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 1. Upload File(s)")
                files_uploader = gr.File(
                    label="Upload Text File(s) (.txt)",
                    file_types=['.txt'],
                    file_count="multiple",
                    type="filepath"
                )
                file_counter = gr.Markdown("Files Uploaded: 0")

                gr.Markdown("### 2. Select Voice")
                voice_filter = gr.Textbox(
                    label="Filter Voices",
                    placeholder="Type here to filter the voice list below...",
                    interactive=True
                )

                with gr.Row():
                    voice = gr.Dropdown(
                        choices=config.VOICE_LIST,
                        value='am_michael',
                        allow_custom_value=False,
                        label='Voice',
                        info='Default voices are more stable'
                    )

                toggle_voices_btn = gr.Button("Hide Default Voices", variant='secondary')

                gr.Markdown("### 3. Save Options (Optional)")
                local_save_path_input = gr.Textbox(
                    label="Save a copy to a local folder",
                    info="Paste a folder path here (e.g., C:\\Users\\YourName\\Audio). If valid, a copy of each audio file will be saved there.",
                    placeholder="Leave blank to skip",
                    interactive=True,
                )

                gr.Markdown("### 4. Generate")
                with gr.Row():
                    generate_btn = gr.Button('Generate from Files', variant='primary')

            with gr.Column():
                gr.Markdown("### 5. Download Output")
                output_files = gr.File(
                    label="Download Generated Audio File(s)",
                    file_count="multiple",
                    interactive=False
                )

                with gr.Accordion('Audio Settings', open=True):
                    model_name=gr.Dropdown(config.MODEL_LIST,label="Model",value=config.MODEL_LIST[0])
                    speed = gr.Slider(minimum=0.1, maximum=2, value=1, step=0.1, label='⚡️Speed')
                    remove_silence = gr.Checkbox(value=False, label='✂️ Remove Silence From TTS')
                    minimum_silence = gr.Number(label="Keep Silence Upto (In seconds)", value=0.05)
                    pad_between = gr.Slider(minimum=0, maximum=2, value=0, step=0.1, label='🔇 Pad Between')
                    custom_voicepack = gr.File(label='Upload Custom VoicePack .pt file')

        def toggle_default_voices(current_state):
            standard_prefixes = ("am_", "af_", "bm_", "bf_")

            if current_state == "shown":
                new_state = "hidden"
                new_button_update = gr.update(value="Show Default Voices", variant='primary')
                new_choices = [v for v in config.VOICE_LIST if not v.startswith(standard_prefixes)]
                new_value = new_choices[0] if new_choices else None
                return gr.update(choices=new_choices, value=new_value), new_button_update, new_state
            else:
                new_state = "shown"
                new_button_update = gr.update(value="Hide Default Voices", variant='secondary')
                new_choices = config.VOICE_LIST
                new_value = 'am_michael'
                return gr.update(choices=new_choices, value=new_value), new_button_update, new_state

        def filter_voice_list(filter_text, current_voice_value, current_state):
            standard_prefixes = ("am_", "af_", "bm_", "bf_")
            source_list = config.VOICE_LIST
            if current_state == "hidden":
                source_list = [v for v in config.VOICE_LIST if not v.startswith(standard_prefixes)]

            if not filter_text:
                current_val_in_list = current_voice_value in source_list
                default_val = source_list[0] if source_list else None
                return gr.update(choices=source_list, value=current_voice_value if current_val_in_list else default_val)

            filtered_choices = [v for v in source_list if filter_text.lower() in v.lower()]
            new_value = None
            if current_voice_value in filtered_choices:
                new_value = current_voice_value
            elif filtered_choices:
                new_value = filtered_choices[0]
            return gr.update(choices=filtered_choices, value=new_value)

        def on_start_files_generation():
            gr.Info("TTS generation for files has started... ⏳", duration=3)
            return None

        files_uploader.change(fn=update_file_count, inputs=files_uploader, outputs=file_counter)

        toggle_voices_btn.click(
            fn=toggle_default_voices,
            inputs=[visibility_state],
            outputs=[voice, toggle_voices_btn, visibility_state]
        )

        voice_filter.change(
            fn=filter_voice_list,
            inputs=[voice_filter, voice, visibility_state],
            outputs=voice
        )

        inputs = [files_uploader, model_name, voice, speed, pad_between, remove_silence, minimum_silence, custom_voicepack, local_save_path_input]

        generate_btn.click(
            fn=on_start_files_generation,
            outputs=[output_files]
        ).then(
            fn=process_files_tts,
            inputs=inputs,
            outputs=[output_files]
        )

    return demo

def create_video_generation_tab():
    with gr.Blocks() as demo:
        # States to manage file paths and results robustly
        audio_filepaths_state = gr.State([])
        cover_filepaths_state = gr.State([])
        single_video_result_state = gr.State(None)
        bulk_video_result_state = gr.State(None)

        gr.Markdown("# Audio to Video\nCreate a video from an audio file and a cover (image or video).")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 1. Upload Media")
                bulk_mode_checkbox = gr.Checkbox(label="Bulk Video Generation", value=False, interactive=True)

                audio_input = gr.File(
                    label="Upload Audio File(s)",
                    type="filepath",
                    file_types=["audio"],
                    file_count="single"
                )
                cover_input = gr.File(
                    label="Upload Cover(s) (Image or Video)",
                    type="filepath",
                    file_types=["image", "video"],
                    file_count="single"
                )

                with gr.Accordion("Bulk Mode File Pairings", visible=False) as pairings_accordion:
                    file_pairings_display = gr.Markdown("Upload audio and cover files to see the pairings.")

                gr.Markdown("### 2. Preview Cover Media")
                max_preview_size_slider = gr.Slider(
                    minimum=1, maximum=500, value=50, step=1,
                    label="Max Preview Size (MB)",
                    info="Set the size limit for loading a preview to prevent browser lag.",
                    interactive=True
                )
                preview_message = gr.Markdown("", visible=False)
                cover_preview_image = gr.Image(label="Image Preview", visible=False, interactive=False)
                cover_preview_video = gr.Video(label="Video Preview", visible=False, interactive=False)


                gr.Markdown("### 3. Configure Video Settings")
                resolution_select = gr.Dropdown(
                    label="Output Resolution",
                    choices=["1080p (High Quality)", "720p (Fast)"],
                    value="1080p (High Quality)",
                    interactive=True
                )
                encoder_select = gr.Dropdown(
                    label="Video Encoder",
                    choices=["CPU (libx264 - Compatible)", "NVIDIA GPU (h264_nvenc - Faster)"],
                    value="NVIDIA GPU (h264_nvenc - Faster)",
                    interactive=True
                )
                video_frame_rate_slider = gr.Slider(
                    label="Video Frame Rate (FPS)", minimum=1, maximum=60, value=1, step=1
                )

                gr.Markdown("### 4. Save Options (Optional)")
                local_save_path_input = gr.Textbox(
                    label="Save a copy to a local folder",
                    info="Paste a folder path here. If valid, a copy of the video(s) will be saved there.",
                    placeholder="Leave blank to skip",
                    interactive=True,
                )

                gr.Markdown("### 5. Generate")
                generate_video_btn = gr.Button("Generate Video", variant="primary", interactive=False)

            with gr.Column(scale=2):
                gr.Markdown("### 6. Video Output")
                max_output_size_slider = gr.Slider(
                        minimum=0, maximum=1000, step=10, value=200,
                        label="Max Output Preview Size (MB)",
                        info="Prevents browser crashes. Videos over this size are generated but not loaded for preview.",
                        interactive=True
                )
                progress_log = gr.Textbox(label="Generation Log", lines=8, interactive=False)
                video_output_player = gr.Video(label="Generated Video", interactive=False, visible=False)
                video_size_warning = gr.Markdown("", visible=False)
                bulk_output_files = gr.File(label="Download Generated Videos", interactive=False, visible=False, file_count="multiple")
                video_info_display = gr.Textbox(label="Generation Details", lines=8, interactive=False, visible=False)

        # --- Backend Logic and Event Handling ---

        def update_pairings_display(bulk_mode, audio_paths, cover_paths):
            if not bulk_mode or not audio_paths or not cover_paths:
                return gr.update(visible=False), ""

            num_audio, num_cover = len(audio_paths), len(cover_paths)
            audio_filenames = [os.path.basename(p) for p in audio_paths]
            cover_filenames = [os.path.basename(p) for p in cover_paths]
            pairing_text = "### Audio-Cover Pairings\n\n"

            if num_cover == 1:
                pairing_text += f"**Cover:** `{cover_filenames[0]}` will be used for all audio files.\n\n"
                for i, audio_file in enumerate(audio_filenames):
                    pairing_text += f"{i+1}. **Audio:** `{audio_file}` → **Cover:** `{cover_filenames[0]}`\n"
            elif num_audio == num_cover:
                pairing_text += "Files will be paired one-to-one based on their upload order.\n\n"
                for i, (audio_file, cover_file) in enumerate(zip(audio_filenames, cover_filenames)):
                    pairing_text += f"{i+1}. **Audio:** `{audio_file}` → **Cover:** `{cover_file}`\n"
            else:
                pairing_text = (
                    f"### ⚠️ Mismatched File Count!\n\n"
                    f"You have **{num_audio}** audio files and **{num_cover}** cover files.\n"
                    f"Please provide either **1 cover file** for all audio, or **one cover file for each audio file**."
                )
            return gr.update(visible=True), pairing_text

        def toggle_bulk_mode(bulk_enabled, audio_files, cover_files):
            if bulk_enabled:
                return gr.update(file_count="multiple", value=[]), gr.update(file_count="multiple", value=[])
            else:
                new_audio = audio_files[0] if audio_files else None
                new_cover = cover_files[0] if cover_files else None
                if len(audio_files) > 1 or len(cover_files) > 1:
                    gr.Info("Bulk mode disabled. Keeping only the first audio and cover file.")
                return gr.update(file_count="single", value=new_audio), gr.update(file_count="single", value=new_cover)

        def update_file_inputs(audio_files, cover_files):
            audio_paths = [audio_files] if isinstance(audio_files, str) else (audio_files or [])
            cover_paths = [cover_files] if isinstance(cover_files, str) else (cover_files or [])
            can_generate = bool(audio_paths and cover_paths)
            return gr.update(interactive=can_generate), audio_paths, cover_paths

        def handle_cover_preview(cover_files, max_mb):
            cover_paths = [cover_files] if isinstance(cover_files, str) else (cover_files or [])

            if len(cover_paths) != 1:
                return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

            path = cover_paths[0]
            try:
                max_bytes = max_mb * 1024 * 1024
                file_size_bytes = os.path.getsize(path)

                if file_size_bytes > max_bytes:
                    msg = f"⚠️ Cover file is too large ({file_size_bytes / (1024*1024):.2f} MB) to preview (limit: {max_mb} MB)."
                    return gr.update(visible=False), gr.update(visible=False), gr.update(value=msg, visible=True)

                is_image = any(path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'])
                is_video = any(path.lower().endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.mkv'])

                if is_image:
                    return gr.update(value=path, visible=True), gr.update(visible=False), gr.update(visible=False)
                elif is_video:
                    return gr.update(visible=False), gr.update(value=path, visible=True), gr.update(visible=False)
                else:
                    return gr.update(visible=False), gr.update(visible=False), gr.update(value="⚠️ Unsupported file type for preview.", visible=True)
            except Exception as e:
                return gr.update(visible=False), gr.update(visible=False), gr.update(value=f"Error: {e}", visible=True)

        def on_start_generation():
            # This function clears all previous outputs when generation begins
            return "", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

        def start_generation(bulk_mode, audio_paths, cover_paths, res, enc, fps, save_dir, progress=gr.Progress()):
            log_text = ""
            # Unify single and bulk processing to simplify logic
            if not bulk_mode:
                 pairs = [(audio_paths[0], cover_paths[0])]
            else:
                num_audio, num_cover = len(audio_paths), len(cover_paths)
                if num_cover > 1 and num_cover != num_audio:
                    msg = "Error: Mismatched files. Use one cover for all, or one cover per audio."
                    gr.Error(msg)
                    # Yield an error message to the log
                    yield None, None, msg
                    return
                pairs = list(zip(audio_paths, cover_paths * num_audio)) if num_cover == 1 else list(zip(audio_paths, cover_paths))

            generated_files = []
            final_info_text = ""
            for i, (audio_p, cover_p) in enumerate(pairs):
                status_message = f"Processing file {i + 1} of {len(pairs)}: {os.path.basename(audio_p)}..."
                log_text += status_message + "\n"
                progress(i / len(pairs), desc=status_message)
                # Yield intermediate log progress
                yield None, None, log_text

                video_path, info_text = generate_video_from_media(audio_p, cover_p, res, enc, fps)
                if video_path:
                    generated_files.append(video_path)
                    final_info_text = info_text # Store info for single video case
                    log_text += f"-> Generated: {os.path.basename(video_path)}\n"
                    if save_dir and os.path.isdir(save_dir):
                        try:
                            shutil.copy2(video_path, save_dir)
                            log_text += f"-> Copied to local path.\n"
                        except Exception as e:
                            gr.Warning(f"Could not copy {os.path.basename(video_path)}: {e}")
                            log_text += f"-> WARNING: Failed to copy to local path: {e}\n"
                else:
                    log_text += f"-> FAILED to generate video.\n"
                # Yield intermediate log progress again with the result of the generation
                yield None, None, log_text

            progress(1, desc="Complete.")
            log_text += "\nGeneration complete."

            if not bulk_mode:
                result = {'path': generated_files[0], 'info': final_info_text} if generated_files else None
                yield result, None, log_text
            else:
                yield None, generated_files, log_text

        def handle_single_video_output(result, max_mb):
            if not result or not result.get('path'):
                return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

            video_path, info_text = result['path'], result['info']
            try:
                file_size_bytes = os.path.getsize(video_path)
                if file_size_bytes > max_mb * 1024 * 1024:
                    size_mb = file_size_bytes / (1024*1024)
                    warning = f"✅ Video generated, but at {size_mb:.2f}MB it exceeds the {max_mb}MB preview limit. Find it in `kokoro_videos`."
                    return gr.update(visible=False), gr.update(value=warning, visible=True), gr.update(value=info_text, visible=True)
                else:
                    return gr.update(value=video_path, visible=True), gr.update(visible=False), gr.update(value=info_text, visible=True)
            except Exception as e:
                return gr.update(visible=False), gr.update(value=f"⚠️ Error checking video size: {e}", visible=True), gr.update(visible=False)

        def handle_bulk_video_output(file_list):
            return gr.update(value=file_list, visible=bool(file_list))

        # --- Event Wiring ---

        pairings_inputs = [bulk_mode_checkbox, audio_filepaths_state, cover_filepaths_state]
        pairings_outputs = [pairings_accordion, file_pairings_display]

        bulk_mode_checkbox.change(
            fn=toggle_bulk_mode,
            inputs=[bulk_mode_checkbox, audio_filepaths_state, cover_filepaths_state],
            outputs=[audio_input, cover_input]
        ).then(
            fn=update_pairings_display,
            inputs=pairings_inputs,
            outputs=pairings_outputs
        )

        for comp in [audio_input, cover_input]:
            comp.change(
                fn=update_file_inputs,
                inputs=[audio_input, cover_input],
                outputs=[generate_video_btn, audio_filepaths_state, cover_filepaths_state]
            ).then(
                fn=update_pairings_display,
                inputs=pairings_inputs,
                outputs=pairings_outputs
            )

        for comp in [cover_input, max_preview_size_slider]:
            comp.change(
                fn=handle_cover_preview,
                inputs=[cover_input, max_preview_size_slider],
                outputs=[cover_preview_image, cover_preview_video, preview_message]
            )

        generate_video_btn.click(
            fn=on_start_generation,
            outputs=[progress_log, video_output_player, video_size_warning, bulk_output_files, video_info_display]
        ).then(
            fn=start_generation,
            inputs=[bulk_mode_checkbox, audio_filepaths_state, cover_filepaths_state, resolution_select, encoder_select, video_frame_rate_slider, local_save_path_input],
            outputs=[single_video_result_state, bulk_video_result_state, progress_log],
            show_progress="full"
        )

        single_video_result_state.change(
            fn=handle_single_video_output,
            inputs=[single_video_result_state, max_output_size_slider],
            outputs=[video_output_player, video_size_warning, video_info_display]
        )

        max_output_size_slider.change(
            fn=handle_single_video_output,
            inputs=[single_video_result_state, max_output_size_slider],
            outputs=[video_output_player, video_size_warning, video_info_display]
        )

        bulk_video_result_state.change(
            fn=handle_bulk_video_output,
            inputs=[bulk_video_result_state],
            outputs=[bulk_output_files]
        )

    return demo

def create_multi_speech_tab():
    dummpy_example="""{af_sky} If you haven’t subscribed to The Devil Panda yet... what are you even doing?
{af_bella} Smash that like button, or I might just cry.
{af_nicole} Comment below with your favorite part or I’ll haunt your notifications!
{bm_george} Panda deserves more subs. I said what I said.
{am_santa} Subscribe now… or miss out on the coolest content this side of YouTube."""
    with gr.Blocks() as demo:
        gr.Markdown(
            """
        # Multiple Speech-Type Generation
        This section lets you generate multiple speech styles or apply different voice packs using a single text input. Just follow the format below to assign a specific voice to each line. If no voice is specified, the system will default to the "af" voice.
        Format:
        `{voice_name} your text here.`
        """
        )
        with gr.Row():
            gr.Markdown(f"**Example Input:**\n```\n{dummpy_example}\n```")
        with gr.Row():
            with gr.Column():
                text = gr.Textbox(
                    label='Enter Text',
                    lines=7,
                    placeholder=dummpy_example
                )
                with gr.Row():
                    generate_btn = gr.Button('Generate', variant='primary')
                with gr.Accordion('Audio Settings', open=True):
                    speed = gr.Slider(
                        minimum=0.1, maximum=2, value=1, step=0.1,
                        label='⚡️Speed', info='Adjust the speaking speed'
                    )
                    remove_silence = gr.Checkbox(value=False, label='✂️ Remove Silence From TTS')
                    minimum_silence = gr.Number(
                        label="Keep Silence Upto (In seconds)",
                        value=0.20
                    )
            with gr.Column():
                audio = gr.Audio(interactive=False, label='Output Audio', autoplay=True)
                with gr.Accordion('Enable Autoplay', open=False):
                    autoplay = gr.Checkbox(value=True, label='Autoplay')
                    autoplay.change(toggle_autoplay, inputs=[autoplay], outputs=[audio])

        inputs = [text, remove_silence, minimum_silence, speed]
        text.submit(podcast_maker, inputs=inputs, outputs=[audio])
        generate_btn.click(podcast_maker, inputs=inputs, outputs=[audio])
    return demo

def create_srt_dubbing_tab():
    with gr.Blocks() as demo:
        gr.Markdown("# Generate Audio File From Subtitle\nUpload a `.srt` file to generate dubbed audio.")
        with gr.Row():
            with gr.Column():
                srt_file = gr.File(label='Upload .srt Subtitle File Only')
                with gr.Row():
                    voice = gr.Dropdown(
                        config.VOICE_LIST,
                        value='af_bella',
                        allow_custom_value=False,
                        label='Voice',
                    )
                with gr.Row():
                    generate_btn_ = gr.Button('Generate', variant='primary')
                with gr.Accordion('Audio Settings', open=False):
                    custom_voicepack = gr.File(label='Upload Custom VoicePack .pt file')
            with gr.Column():
                audio = gr.Audio(interactive=False, label='Output Audio', autoplay=True)
                with gr.Accordion('Enable Autoplay', open=False):
                    autoplay = gr.Checkbox(value=True, label='Autoplay')
                    autoplay.change(toggle_autoplay, inputs=[autoplay], outputs=[audio])

        generate_btn_.click(
            srt_process,
            inputs=[srt_file, voice, custom_voicepack],
            outputs=[audio]
        )
    return demo

# --- UI for Voice Mixer  ---
def create_voice_mix_tab():
    with gr.Blocks() as demo:
        gr.Markdown("# Kokoro Voice Mixer\nSelect voices and adjust their weights to create a mixed voice.")

        voices, slider_configs = get_voices()

        voice_components = {}
        voice_names = list(voices.keys())
        female_voices = sorted([name for name in voice_names if "f_" in name or name == "af"])
        male_voices = sorted([name for name in voice_names if "m_" in name or "b_" in name])
        neutral_voices = sorted([name for name in voice_names if name not in female_voices and name not in male_voices])

        num_columns = 3
        def generate_ui_row(voice_list):
            for i in range(0, len(voice_list), num_columns):
                with gr.Row():
                    for voice_name in voice_list[i:i+num_columns]:
                        with gr.Column():
                            checkbox = gr.Checkbox(label=slider_configs.get(voice_name, voice_name), value=False)
                            slider = gr.Slider(minimum=0, maximum=1, value=1.0, step=0.01, interactive=False)
                            voice_components[voice_name] = (checkbox, slider)
                            checkbox.change(fn=lambda x: gr.update(interactive=x), inputs=[checkbox], outputs=[slider])

        if female_voices: gr.Markdown("### Female Voices"); generate_ui_row(female_voices)
        if male_voices: gr.Markdown("### Male Voices"); generate_ui_row(male_voices)
        if neutral_voices: gr.Markdown("### Other Voices"); generate_ui_row(neutral_voices)

        sorted_keys = sorted(voice_components.keys())
        formula_inputs = [comp for key in sorted_keys for comp in voice_components[key]]

        with gr.Row():
            voice_formula = gr.Textbox(label="Voice Formula", interactive=False)

        def update_voice_formula(*args):
            formula_parts = []
            for i, key in enumerate(sorted_keys):
                checkbox_val = args[i*2]
                slider_val = args[i*2+1]
                if checkbox_val:
                    formula_parts.append(f"{key} * {slider_val:.3f}")

            formula_string = " + ".join(formula_parts)
            return formula_string

        for checkbox, slider in voice_components.values():
            checkbox.change(update_voice_formula, inputs=formula_inputs, outputs=[voice_formula])
            slider.change(update_voice_formula, inputs=formula_inputs, outputs=[voice_formula])

        with gr.Row():
            voice_text = gr.Textbox(label='Enter Text',
                                    lines=10,
                                    max_lines=10,
                                    placeholder="Type text here to preview the custom voice...")

            with gr.Accordion('Audio Settings', open=True):
                model_name=gr.Dropdown(config.MODEL_LIST, label="Model", value=config.MODEL_LIST[0])
                speed = gr.Slider(minimum=0.1, maximum=2, value=1, step=0.1, label='⚡️Speed', info='Adjust speaking speed')
                remove_silence = gr.Checkbox(value=False, label='✂️ Remove Silence')

        with gr.Row():
            voice_generator = gr.Button('Generate', variant='primary')
        with gr.Row():
            voice_audio = gr.Audio(interactive=False, label='Output Audio', autoplay=True)
        with gr.Accordion('Enable Autoplay', open=True):
            autoplay = gr.Checkbox(value=True, label='Autoplay')
            autoplay.change(toggle_autoplay, inputs=[autoplay], outputs=[voice_audio])
        with gr.Row():
            mix_voice_download = gr.File(label="Download Mixed VoicePack")

        voice_generator.click(
            generate_custom_audio,
            inputs=[voice_text, voice_formula, model_name, speed, remove_silence],
            outputs=[voice_audio, mix_voice_download]
        )
    return demo

def get_voice_names_json():
    """Categorizes and returns voice names as a formatted JSON string."""
    male, female, other = [], [], []
    for name in config.VOICE_LIST:
        if "m_" in name:
            male.append(name)
        elif "f_" in name or name == "af":
            female.append(name)
        else:
            other.append(name)
    return json.dumps({"female_voices": female, "male_voices": male, "other_voices": other}, indent=4)

def create_voice_list_tab():
    with gr.Blocks() as demo:
        gr.Markdown(f"# Available Voice Names")
        get_voice_button = gr.Button("Get Voice Names (JSON format)")
        voice_names_output = gr.Textbox(label="Voice Names", lines=20, interactive=False, placeholder="Click the button to see the categorized list of available voices.")
        get_voice_button.click(get_voice_names_json, outputs=[voice_names_output])
    return demo
