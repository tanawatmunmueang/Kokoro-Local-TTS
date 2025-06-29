# app.py

import os
import gradio as gr
import click

# Import our new, separated modules
import config
from KOKORO.models import build_model
from ui_tabs import (
    create_batch_tts_tab,
    create_multi_speech_tab,
    create_srt_dubbing_tab,
    create_voice_list_tab
)
from voice_mixer import create_voice_mix_ui

def initialize_app():
    """Initializes the application state, loading models and cleaning folders."""
    config.clean_folder_before_start()
    print("Cleaned up old folders.")

    print("Loading model...")
    print(f'Using device: {config.DEVICE}')

    # Initialize the global model and current_model variables in the config module
    model_path = os.path.join("./KOKORO", config.MODEL_LIST[0])
    config.MODEL = build_model(model_path, config.DEVICE)
    config.CURRENT_MODEL = config.MODEL_LIST[0]

    print("Model loaded successfully.")

@click.command()
@click.option("--debug", is_flag=True, default=False, help="Enable debug mode.")
@click.option("--share", is_flag=True, default=False, help="Enable sharing of the interface.")
def main(debug, share):
    """Builds the Gradio UI and launches the application."""

    # Create the UI for each tab by calling the functions from our UI modules
    demo1 = create_batch_tts_tab()
    demo2 = create_multi_speech_tab()
    demo3 = create_srt_dubbing_tab()
    demo4 = create_voice_mix_ui()
    demo5 = create_voice_list_tab()

    with gr.Blocks(theme=gr.themes.Ocean(), title="Kokoro TTS - Local Generator") as demo:
        gr.HTML("""
        <div style="text-align: center; margin-bottom: 1.5rem;">
          <h1 style="font-size: 2em; background: linear-gradient(to right, #0083B0, #00B4DB); -webkit-background-clip: text; background-clip: text; color: transparent;">
            🎶 Kokoro-TTS Generator - Offline 🎙️
          </h1>
        </div>
        """)

        with gr.Tabs():
            with gr.Tab("Batched TTS"):
                demo1.render()
            with gr.Tab("Multiple Speech-Type Generation"):
                demo2.render()
            with gr.Tab("SRT Dubbing"):
                demo3.render()
            with gr.Tab("Voice Mixer"):
                demo4.render()
            with gr.Tab("Available Voice Names"):
                demo5.render()

    print("Launching Gradio interface...")
    demo.queue().launch(debug=debug, share=share, server_port=8080, inbrowser=True)

if __name__ == "__main__":
    initialize_app()
    main()
