# tts_logic.py

import torch
import gc
import os
import gradio as gr

# Import from local modules
from KOKORO.models import build_model
from KOKORO.utils import tts, tts_file_name, podcast
import config

def update_model(model_name):
    """Updates the TTS model only if the specified model is not already loaded."""
    if config.CURRENT_MODEL == model_name:
        return f"Model already set to {model_name}"

    model_path = os.path.join("./KOKORO", model_name)
    if model_name == "kokoro-v0_19-half.pth":
        model_path = os.path.join("./KOKORO/fp16", model_name)

    del config.MODEL
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print(f"Loading new model: {model_name}")
    config.MODEL = build_model(model_path, config.DEVICE)
    config.CURRENT_MODEL = model_name
    return f"Model updated to {model_name}"

def tts_maker(text, voice_name="af_bella", speed=0.8, trim=0, pad_between=0, save_path="temp.wav", remove_silence=False, minimum_silence=50):
    """A wrapper for the core KOKORO TTS function."""
    save_path = save_path.replace('\n', '').replace('\r', '')
    audio_path = tts(
        config.MODEL, config.DEVICE, text, voice_name,
        speed=speed, trim=trim, pad_between_segments=pad_between,
        output_file=save_path, remove_silence=remove_silence, minimum_silence=minimum_silence
    )
    return audio_path

def manage_files(file_path):
    """Validates and manages uploaded .pt files to ensure they are safe and valid."""
    if file_path and os.path.exists(file_path):
        file_extension = os.path.splitext(file_path)[1]
        file_size = os.path.getsize(file_path)
        if file_extension == ".pt" and file_size <= 5 * 1024 * 1024:
            return True
        else:
            os.remove(file_path)
            return False
    return False

def text_to_speech(text, model_name="kokoro-v0_19.pth", voice_name="af_bella", speed=1.0, pad_between_segments=0, remove_silence=True, minimum_silence=0.20, custom_voicepack=None, trim=0.0):
    """Handles the full text-to-speech generation process for the UI."""
    update_model(model_name)

    if not minimum_silence:
        minimum_silence = 0.05
    keep_silence = int(minimum_silence * 1000)
    save_at = tts_file_name(text)

    final_voice_arg = voice_name

    # <<< CHANGE: Revert to the simpler, original logic that works.
    voicepack_path = None
    if custom_voicepack:
        # Handle Gradio File uploads
        if hasattr(custom_voicepack, 'name'):
            voicepack_path = custom_voicepack.name
        # Handle path strings from the voice mixer
        elif isinstance(custom_voicepack, str):
            voicepack_path = custom_voicepack

    if voicepack_path:
        if manage_files(voicepack_path):
            print(f"Using custom voice pack: {voicepack_path}")
            final_voice_arg = voicepack_path
        else:
            gr.Warning("Invalid or oversized .pt file. Using the selected voice pack instead.")

    audio_path = tts_maker(
        text, final_voice_arg, speed, trim, pad_between_segments,
        save_at, remove_silence, keep_silence
    )
    return audio_path

def podcast_maker(text, remove_silence=False, minimum_silence=50, speed=0.9, model_name="kokoro-v0_19.pth"):
    """Handles the podcast-style generation with multiple voices."""
    update_model(model_name)

    if not minimum_silence:
        minimum_silence = 0.05
    keep_silence = int(minimum_silence * 1000)

    podcast_save_at = podcast(
        config.MODEL, config.DEVICE, text,
        remove_silence=remove_silence, minimum_silence=keep_silence, speed=speed
    )
    return podcast_save_at
