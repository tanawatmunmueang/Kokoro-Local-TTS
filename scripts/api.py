# It is helpful if you want to use it in a voice assistant project.
# Know more about {your gradio app url}/?view=api. Example: http://127.0.0.1:7860/?view=api
import shutil
import os
from gradio_client import Client

# Ensure the output directory exists
output_dir = "api_output"
os.makedirs(output_dir, exist_ok=True)

# Initialize the Gradio client
api_url = "http://127.0.0.1:7860/"
client = Client(api_url)




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
    """
    Generates speech from text using a specified model and saves the audio file.

    Parameters:
        text (str): The text to convert to speech.
        model_name (str): The name of the model to use for synthesis.
        voice_name (str): The name of the voice to use.
        speed (float): The speed of speech.
        pad_between_segments (int): Padding between audio segments.
        remove_silence (bool): Whether to remove silence from the audio.
        minimum_silence (float): Minimum silence duration to consider.
        custom_voicepack (str): Path to the custom voice pack to use.
    Returns:
        str: Path to the saved audio file.
    """
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
    print(f"Saved at {save_at}")

    return save_at

# Example usage
if __name__ == "__main__":
    text="This is Kokoro TTS. I am a text-to-speech model and Super Fast."
    model_name="kokoro-v0_19.pth" #kokoro-v0_19-half.pth
    voice_name="af_bella" #get voice names 
    speed=1
    add_silence_between_segments=0 #it use in large text
    remove_silence=False
    keep_silence_upto=0.05 #in seconds
    custom_voicepack=None
    audio_path = text_to_speech(text=text, model_name=model_name, 
                                voice_name=voice_name, speed=speed, 
                                pad_between_segments=add_silence_between_segments,
                                remove_silence=remove_silence,
                                minimum_silence=keep_silence_upto)
    print(f"Audio file saved at: {audio_path}")
