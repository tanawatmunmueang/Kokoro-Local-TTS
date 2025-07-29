# ui_tabs.py

import gradio as gr
import json
import os
import shutil
import time

import config
from tts_logic import text_to_speech, podcast_maker
from srt_logic import srt_process
from voice_mixer import generate_custom_audio, get_voices
from video_logic import generate_video_from_media

# --- Helper Functions ---

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
            import traceback
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
        video_filepath_state = gr.State(value=None)
        cover_filepath_state = gr.State(value=None)

        gr.Markdown("# Audio to Video\nCreate a video from an audio file and a cover (image or video).")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 1. Upload Media")
                audio_input = gr.File(
                    label="Upload Audio File",
                    type="filepath",
                    file_types=["audio"]
                )
                cover_input = gr.File(
                    label="Upload Cover (Image or Video)",
                    type="filepath",
                    file_types=["image", "video"]
                )

                gr.Markdown("### 2. Preview Cover Media")
                max_preview_size_slider = gr.Slider(
                    minimum=1, maximum=500, value=50, step=1,
                    label="Max Preview Size (MB)",
                    info="Set the size limit for loading a preview of the cover media to prevent browser lag.",
                    interactive=True
                )
                cover_preview_image = gr.Image(label="Image Preview", visible=False, interactive=False)
                cover_preview_video = gr.Video(label="Video Preview", visible=False, interactive=False)
                preview_message = gr.Markdown("", visible=False)


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
                    label="Video Frame Rate (FPS)",
                    minimum=1, maximum=60, value=1, step=1
                )

                gr.Markdown("### 4. Save Options (Optional)")
                local_save_path_input = gr.Textbox(
                    label="Save a copy to a local folder",
                    info="Paste a folder path here. If valid, a copy of the video will be saved there.",
                    placeholder="Leave blank to skip",
                    interactive=True,
                )

                gr.Markdown("### 5. Generate")
                generate_video_btn = gr.Button("Generate Video", variant="primary", interactive=False)

            with gr.Column(scale=2):
                gr.Markdown("### 6. Video Output")
                max_output_size_slider = gr.Slider(
                        minimum=0,maximum=1000,
                        step=10,
                        value=200,
                        label="Max Output Preview Size (MB)",
                        info="Prevents browser crashes. Videos over this size are generated but not loaded for preview.",
                        interactive=True
                )
                video_output = gr.Video(label="Generated Video", interactive=False, visible=False)
                video_size_warning = gr.Markdown("", visible=False)
                video_info_display = gr.Textbox(
                    label="Generation Details",
                    lines=8,
                    interactive=False,
                    visible=False
                )

        # --- Helper functions for event handling ---

        def update_button_state(audio_path, cover_path):
            interactive = bool(audio_path and cover_path)
            return gr.update(interactive=interactive)

        def update_cover_preview(cover_path, max_mb):
            if not cover_path or not os.path.exists(cover_path):
                return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), cover_path

            is_image = any(cover_path.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'])
            is_video = any(cover_path.lower().endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.mkv'])

            try:
                max_bytes = max_mb * 1024 * 1024
                file_size_bytes = os.path.getsize(cover_path)

                if file_size_bytes > max_bytes:
                    msg = f"⚠️ Cover file is too large ({file_size_bytes / (1024*1024):.2f} MB) to preview (limit: {max_mb} MB)."
                    return gr.update(visible=False), gr.update(visible=False), gr.update(value=msg, visible=True), cover_path

                if is_image:
                    return gr.update(value=cover_path, visible=True), gr.update(visible=False), gr.update(visible=False), cover_path
                elif is_video:
                    return gr.update(visible=False), gr.update(value=cover_path, visible=True), gr.update(visible=False), cover_path
                else:
                    msg = "⚠️ Unsupported file type for preview. Please use a standard image or video file."
                    return gr.update(visible=False), gr.update(visible=False), gr.update(value=msg, visible=True), cover_path

            except Exception as e:
                msg = f"Error checking cover file: {e}"
                return gr.update(visible=False), gr.update(visible=False), gr.update(value=msg, visible=True), cover_path

        def generation_wrapper(audio_path, cover_path, res, enc, fps, progress=gr.Progress(track_tqdm=True)):
            """
            This generator function calls the video logic and yields progress updates.
            Every yield provides a value for each of the two output components.
            """
            # Update the progress bar, but do NOT yield here. This call just sends an update.
            progress(0, desc="Starting...")

            # Yield the initial UI state. This provides a value for both output components
            # and gives the user immediate feedback.
            yield None, "Video generation process has started, please wait..."

            # Call the long-running video generation function
            progress(0.1, desc="Generating video with FFmpeg...")
            video_path, info_text = generate_video_from_media(audio_path, cover_path, res, enc, fps)

            # Handle generation failure
            if not video_path:
                yield None, info_text  # Yield the error message
                return # End the generator function

            progress(0.9, desc="Finishing up...")

            # Prepare the final state value for the next part of the UI chain
            state_value = {'path': video_path, 'time': time.time()}

            # Yield the final successful result to the output components
            yield state_value, info_text

        def check_output_video_size_and_load(state_value, max_mb):
            if not isinstance(state_value, dict) or not state_value.get('path'):
                return gr.update(value=None, visible=False), gr.update(value="", visible=False)

            video_filepath = state_value['path']

            if not os.path.exists(video_filepath):
                return gr.update(value=None, visible=False), gr.update(value="", visible=False)

            try:
                max_bytes = max_mb * 1024 * 1024
                file_size_bytes = os.path.getsize(video_filepath)

                if file_size_bytes > max_bytes:
                    file_size_mb = file_size_bytes / (1024 * 1024)
                    warning_text = (
                        f"✅ Video generated successfully, but at {file_size_mb:.2f} MB, it exceeds the preview limit of {max_mb} MB. "
                        f"You can find the output file in your `kokoro_videos` folder or the specified save directory."
                    )
                    return gr.update(value=None, visible=False), gr.update(value=warning_text, visible=True)
                else:
                    return gr.update(value=video_filepath, visible=True), gr.update(value="", visible=False)
            except Exception as e:
                return gr.update(value=None, visible=False), gr.update(value=f"⚠️ Error checking video size: {e}", visible=True)

        def save_video_copy(state_value, save_dir):
            if not isinstance(state_value, dict) or not state_value.get('path'):
                return

            video_path = state_value['path']

            if video_path and save_dir and os.path.isdir(save_dir):
                try:
                    shutil.copy2(video_path, save_dir)
                    info_msg = f"Successfully copied generated video to: {os.path.join(save_dir, os.path.basename(video_path))}"
                    gr.Info(info_msg)
                    print(info_msg)
                except Exception as e:
                    warn_msg = f"Could not copy file to '{save_dir}'. Check permissions. Error: {e}"
                    gr.Warning(warn_msg)
                    print(warn_msg)
            elif video_path and save_dir:
                warn_msg = f"Provided save path '{save_dir}' is not a valid directory. File was not copied."
                gr.Warning(warn_msg)
                print(warn_msg)

        def on_start_generation():
            return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

        # --- Event Handling for Video Tab ---

        audio_input.change(
            fn=update_button_state,
            inputs=[audio_input, cover_input],
            outputs=[generate_video_btn]
        )
        cover_input.change(
            fn=update_button_state,
            inputs=[audio_input, cover_input],
            outputs=[generate_video_btn]
        )
        cover_input.change(
            fn=update_cover_preview,
            inputs=[cover_input, max_preview_size_slider],
            outputs=[cover_preview_image, cover_preview_video, preview_message, cover_filepath_state]
        )
        max_preview_size_slider.change(
            fn=update_cover_preview,
            inputs=[cover_filepath_state, max_preview_size_slider],
            outputs=[cover_preview_image, cover_preview_video, preview_message, cover_filepath_state]
        )

        # The main click event starts the process. The show_progress="full" is what
        # activates the progress bar and prevents timeouts.
        generate_video_btn.click(
            fn=on_start_generation,
            outputs=[video_output, video_size_warning, video_info_display]
        ).then(
            fn=generation_wrapper,
            inputs=[audio_input, cover_input, resolution_select, encoder_select, video_frame_rate_slider],
            outputs=[video_filepath_state, video_info_display],
            show_progress="full"  # This is the key to activating the progress bar UI
        )

        # The subsequent UI updates are triggered by the completion of the main task,
        # when the hidden state component is updated.
        video_filepath_state.change(
            fn=check_output_video_size_and_load,
            inputs=[video_filepath_state, max_output_size_slider],
            outputs=[video_output, video_size_warning]
        )
        video_filepath_state.change(
            fn=save_video_copy,
            inputs=[video_filepath_state, local_save_path_input]
        )
        video_filepath_state.change(
            fn=lambda x: gr.update(visible=True) if x else gr.update(),
            inputs=[video_filepath_state],
            outputs=[video_info_display]
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
