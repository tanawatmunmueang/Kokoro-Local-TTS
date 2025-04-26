gradio_url="http://127.0.0.1:7860/"

from gradio_client import Client
import json
import os
import shutil
from rich.console import Console
from rich.text import Text
import simpleaudio as sa

# Initialize the Gradio client
client = Client(gradio_url)

console = Console()

voice_dict = None
voices = {}
output_dir = "api_output"

def get_voice_names():
    global voice_dict
    # Get the result from the client
    result = client.predict(api_name="/get_voice_names")
    # Convert the result string into a Python dictionary
    voice_dict = json.loads(result)
    id = 1
    for key in voice_dict:
        if len(voice_dict[key]) > 0:
            for i in voice_dict[key]:
                voices[id] = i
                id += 1
    return voice_dict

def display_voice_names():
    global voice_dict
    id_num = 1
    for key in voice_dict:
        if len(voice_dict[key]) > 0:
            gender = key.replace("_", " ").capitalize()
            console.print(f"[bold cyan]{gender}:[/bold cyan]")
            for voice in voice_dict[key]:
                console.print(f"[green]{id_num}. {voice}[/green]")
                id_num += 1
            # console.print()

def text_to_speech(
    text="Hello!!",
    model_name="kokoro-v0_19.pth",
    voice_name="af_bella",
    speed=1,
    pad_between_segments=0,
    remove_silence=False,
    minimum_silence=0.05,
    custom_voicepack=None,
):
    # Call the API with provided parameters
    result = client.predict(
        text=text,
        model_name=model_name,
        voice_name=voice_name,
        speed=speed,
        pad_between_segments=pad_between_segments,
        remove_silence=remove_silence,
        minimum_silence=minimum_silence,
        custom_voicepack=custom_voicepack,
        api_name="/text_to_speech"
    )
    # Save the audio file in the specified directory
    save_at = f"{output_dir}/{os.path.basename(result)}"
    shutil.move(result, save_at)
    return save_at

def choose_voice():
    while True:
        display_voice_names()
        
        user_input = console.input("[bold yellow]Choose a voice ID number or type 'exit' to quit: [/bold yellow]")
        try:
            voice_number = int(user_input)
            if voice_number in voices:
                selected_voice = voices[voice_number]
                console.print(f"[bold green]You selected: {selected_voice}[/bold green]\n")
                return selected_voice
            else:
                console.print("[bold red]Invalid number. Please choose a valid voice number.[/bold red]")
        except ValueError:
            if user_input.lower() == "exit":
                console.print("[bold red]Exiting voice selection.[/bold red]")
                return None
            else:
                console.print("[bold red]Invalid input. Please enter a valid number or 'exit'.[/bold red]")

def play_audio(filename):
    wave_obj = sa.WaveObject.from_wave_file(filename)
    play_obj = wave_obj.play()
    play_obj.wait_done()

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

voice_dict = get_voice_names()

def text_to_speech_cli():
    while True:
        voice_name = choose_voice()
        if not voice_name:
            break
        # print(
        #         "Type 'C' to change voice or 'q' to quit"
        #     )
        while True:
            
            text = console.input(
                "[bold green]Enter Text ('C' to change voice, 'q' for quit): [/bold green]"
            )
            if text.lower() == "q":
                console.print("[bold red]Exiting text-to-speech CLI.[/bold red]")
                return
            elif text.lower() == "c":
                console.print("[bold yellow]Changing voice...[/bold yellow]")
                break  # Break the inner loop to select a new voice
            else:
                audio_path = text_to_speech(text=text, voice_name=voice_name)
                play_audio(audio_path)
                # console.print("[bold green]Audio played successfully![/bold green]\n")

if __name__ == "__main__":
    console.print("[bold blue]Welcome to the Text-to-Speech CLI![/bold blue]\n")
    text_to_speech_cli()
