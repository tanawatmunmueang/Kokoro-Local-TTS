import gradio as gr
import json
import os

import config
from tts_logic import text_to_speech, podcast_maker
from srt_logic import srt_process

# --- Helper Functions ---

def read_and_combine_files(files_list):
    """
    Takes a list of Gradio file objects, reads them, and returns the combined text.
    """
    if not files_list:
        return ""

    if not isinstance(files_list, list):
        files_list = [files_list]

    combined_content = []
    for file_obj in files_list:
        if file_obj:
            try:
                with open(file_obj.name, 'r', encoding='utf-8') as f:
                    combined_content.append(f.read().strip())
            except Exception as e:
                print(f"Error reading file '{os.path.basename(file_obj.name)}': {e}")
                gr.Warning(f"Could not read file: {os.path.basename(file_obj.name)}")

    # This "\n\n" is what creates the blank line between file contents.
    return "\n\n".join(combined_content)

def update_char_count(text_input):
    """Counts the characters in the input text and returns it as a string."""
    return str(len(text_input))

def update_file_count(files_list):
    """Counts the number of uploaded files and returns it as a string."""
    return str(len(files_list)) if files_list else "0"

def toggle_autoplay(autoplay):
    return gr.Audio(interactive=False, label='Output Audio', autoplay=autoplay)


# --- UI Tab Creation Functions ---

def create_batch_tts_tab():
    with gr.Blocks() as demo:
        gr.Markdown("# Batched TTS")
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Upload file(s) OR type in the box below")
                batch_file_uploader = gr.File(
                    label="Upload Text File(s) (.txt)",
                    file_types=['.txt'],
                    file_count="multiple"
                )
                # ADDED: File counter UI component
                file_counter = gr.Textbox(label="Uploaded File Count", value="0", interactive=False)

                text = gr.Textbox(
                    label='Enter Text',
                    lines=8,
                    max_lines=8,  # This forces a fixed height and enables the scrollbar
                    placeholder="Type your text here, or upload file(s) above..."
                )
                # ADDED: Character counter UI component
                char_counter = gr.Textbox(label="Character Count", value="0", interactive=False)

                with gr.Row():
                    voice = gr.Dropdown(
                        config.VOICE_LIST,
                        value='af_bella',
                        allow_custom_value=False,
                        label='Voice',
                        info='Starred voices are more stable'
                    )
                with gr.Row():
                    generate_btn = gr.Button('Generate', variant='primary')
                with gr.Accordion('Audio Settings', open=False):
                    model_name=gr.Dropdown(config.MODEL_LIST,label="Model",value=config.MODEL_LIST[0])
                    speed = gr.Slider(
                        minimum=0.25, maximum=2, value=1, step=0.1,
                        label='⚡️Speed', info='Adjust the speaking speed'
                    )
                    remove_silence = gr.Checkbox(value=False, label='✂️ Remove Silence From TTS')
                    minimum_silence = gr.Number(
                        label="Keep Silence Upto (In seconds)",
                        value=0.05
                    )
                    pad_between = gr.Slider(
                        minimum=0, maximum=2, value=0, step=0.1,
                        label='🔇 Pad Between', info='Silent Duration between segments [For Large Text]'
                    )
                    custom_voicepack = gr.File(label='Upload Custom VoicePack .pt file')
            with gr.Column():
                audio = gr.Audio(interactive=False, label='Output Audio', autoplay=True)
                with gr.Accordion('Enable Autoplay', open=False):
                    autoplay = gr.Checkbox(value=True, label='Autoplay')
                    autoplay.change(toggle_autoplay, inputs=[autoplay], outputs=[audio])

        # Event handler to populate the text box from uploaded files
        batch_file_uploader.change(fn=read_and_combine_files, inputs=batch_file_uploader, outputs=text)

        # ADDED: Event handlers for the new counters
        batch_file_uploader.change(fn=update_file_count, inputs=batch_file_uploader, outputs=file_counter)
        text.input(fn=update_char_count, inputs=text, outputs=char_counter, show_progress="hidden")

        inputs = [text, model_name, voice, speed, pad_between, remove_silence, minimum_silence, custom_voicepack]
        text.submit(text_to_speech, inputs=inputs, outputs=[audio])
        generate_btn.click(text_to_speech, inputs=inputs, outputs=[audio])
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
                with gr.Accordion('Audio Settings', open=False):
                    speed = gr.Slider(
                        minimum=0.25, maximum=2, value=1, step=0.1,
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
