# ui_tabs.py

import gradio as gr
import json
import os

# Assuming these are local modules as in the original code
import config
from tts_logic import text_to_speech, podcast_maker
from srt_logic import srt_process
from voice_mixer import generate_custom_audio, get_voices

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

        gr.Markdown("# Batched TTS")
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Upload file(s) OR type in the box below")
                batch_file_uploader = gr.File(
                    label="Upload Text File(s) (.txt)",
                    file_types=['.txt'],
                    file_count="multiple",
                    type="filepath" # Set to filepath to match code 1
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
                    # Add the cancel button right here
                    cancel_btn = gr.Button('Cancel', variant='secondary')

                with gr.Accordion('Audio Settings', open=True):
                    model_name=gr.Dropdown(config.MODEL_LIST,label="Model",value=config.MODEL_LIST[0])
                    speed = gr.Slider(minimum=0.1, maximum=2, value=1, step=0.1, label='⚡️Speed')
                    remove_silence = gr.Checkbox(value=False, label='✂️ Remove Silence From TTS')
                    minimum_silence = gr.Number(label="Keep Silence Upto (In seconds)", value=0.05)
                    pad_between = gr.Slider(minimum=0, maximum=2, value=0, step=0.1, label='🔇 Pad Between')
                    custom_voicepack = gr.File(label='Upload Custom VoicePack .pt file')

            with gr.Column():
                audio = gr.Audio(interactive=False, label='Output Audio', autoplay=True)
                with gr.Accordion('Enable Autoplay', open=True):
                    autoplay = gr.Checkbox(value=True, label='Autoplay')
                    autoplay.change(toggle_autoplay, inputs=[autoplay], outputs=[audio])

        # This function updates file count, text content, and char count all at once.
        def update_files_and_text(files_list):
            text_content = read_multiple_files(files_list)
            return update_file_count(files_list), text_content, update_char_count(text_content)

        def toggle_default_voices(current_state):
            """Hides or shows default voices, updating the button's appearance and dropdown choices."""
            standard_prefixes = ("am_", "af_", "bm_", "bf_")

            if current_state == "shown":
                new_state = "hidden"
                new_button_update = gr.update(value="Show Default Voices", variant='primary')
                new_choices = [v for v in config.VOICE_LIST if not v.startswith(standard_prefixes)]
                new_value = new_choices[0] if new_choices else None

                return gr.update(choices=new_choices, value=new_value), new_button_update, new_state
            else: # current_state == "hidden"
                new_state = "shown"
                new_button_update = gr.update(value="Hide Default Voices", variant='secondary')
                new_choices = config.VOICE_LIST
                new_value = 'am_michael'

                return gr.update(choices=new_choices, value=new_value), new_button_update, new_state

        def filter_voice_list(filter_text, current_voice_value, current_state):
            """Filters dropdown choices based on text input and whether default voices are hidden."""
            standard_prefixes = ("am_", "af_", "bm_", "bf_")

            # Determine the source list based on the current visibility state.
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

        # --- Event Listeners ---

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

        # Assign the click and submit events to variables
        tts_event = text.submit(text_to_speech, inputs=inputs, outputs=[audio])
        generate_event = generate_btn.click(text_to_speech, inputs=inputs, outputs=[audio])

        # Add the cancel event handler
        cancel_btn.click(
            fn=None,
            inputs=None,
            outputs=None,
            cancels=[tts_event, generate_event]
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
