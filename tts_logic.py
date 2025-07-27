# tts_logic.py

import torch
import gc
import os
import gradio as gr
import platform
import subprocess
import tempfile
import shutil

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
    """A wrapper for the core KOKORO TTS function that handles large text by chunking based on newlines."""
    text_chunks = [chunk for chunk in text.split('\n') if chunk.strip()]

    with tempfile.TemporaryDirectory() as temp_dir:
        chunk_files = []
        for i, chunk in enumerate(text_chunks):
            yield None # Allows the event to be cancelled
            print(f"Processing chunk {i + 1}/{len(text_chunks)}...")
            chunk_save_path = os.path.join(temp_dir, f"chunk_{i}.wav")
            tts(
                config.MODEL, config.DEVICE, chunk, voice_name,
                speed=speed, trim=trim, pad_between_segments=pad_between,
                output_file=chunk_save_path, remove_silence=remove_silence, minimum_silence=minimum_silence
            )
            if os.path.exists(chunk_save_path):
                chunk_files.append(chunk_save_path)

        if not chunk_files:
            yield None
            return

        if len(chunk_files) == 1:
            print("Single audio chunk created, skipping concatenation.")
            shutil.copy2(chunk_files[0], save_path)
        else:
            concat_list_path = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_list_path, 'w', encoding='utf-8') as f:
                for file_path in chunk_files:
                    f.write(f"file '{os.path.abspath(file_path)}'\n")

            print("Concatenating audio chunks with FFmpeg...")
            ffmpeg_path = os.path.join("ffmpeg", "ffmpeg.exe") if platform.system() == "Windows" else os.path.join("ffmpeg", "ffmpeg")

            command = [
                ffmpeg_path, '-y', '-f', 'concat', '-safe', '0', '-i',
                concat_list_path, '-c', 'copy', os.path.abspath(save_path)
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Temporary audio chunks have been cleaned up.")
    yield save_path

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

    output_dir = "kokoro_audio"
    os.makedirs(output_dir, exist_ok=True)

    base_filename = tts_file_name(text)
    sanitized_filename = base_filename.replace('\n', '_').replace('\r', '')
    save_at = os.path.join(output_dir, sanitized_filename)

    # # A tuple containing all the English standard voice prefixes.
    standard_prefixes = ("am_", "af_", "bm_", "bf_")

    final_voice_arg = voice_name
    voicepack_path = None

    if custom_voicepack:
        if hasattr(custom_voicepack, 'name'):
            voicepack_path = custom_voicepack.name
        elif isinstance(custom_voicepack, str):
            voicepack_path = custom_voicepack
    elif not voice_name.startswith(standard_prefixes):
        voices_dir = "./KOKORO/voices"
        filename = f"{voice_name}.pt"
        voicepack_path = os.path.join( voices_dir, filename )


    if voicepack_path:
        if manage_files(voicepack_path):
            print(f"Using custom voice pack: {voicepack_path}")
            final_voice_arg = voicepack_path
        else:
            gr.Warning("Invalid or oversized .pt file. Using the selected voice pack instead.")

    audio_path = None
    for path in tts_maker(
        text, final_voice_arg, speed, trim, pad_between_segments,
        save_at, remove_silence, keep_silence
    ):
        audio_path = path
        yield path

    if audio_path and os.path.exists(audio_path):
        print(f"Final audio file saved at: {os.path.abspath(audio_path)}")


def podcast_maker(text, remove_silence=False, minimum_silence=50, speed=0.9, model_name="kokoro-v0_19.pth"):
    """Handles the podcast-style generation with multiple voices."""
    update_model(model_name)

    if not minimum_silence:
        minimum_silence = 0.05
    keep_silence = int(minimum_silence * 1000)

    output_dir = "kokoro_audio"
    os.makedirs(output_dir, exist_ok=True)

    podcast_save_at = podcast(
        config.MODEL, config.DEVICE, text,
        remove_silence=remove_silence, minimum_silence=keep_silence, speed=speed
    )

    if podcast_save_at and os.path.exists(podcast_save_at):
        final_path = os.path.join(output_dir, os.path.basename(podcast_save_at))
        shutil.move(podcast_save_at, final_path)
        print(f"Final podcast audio file saved at: {os.path.abspath(final_path)}")
        return final_path

    return podcast_save_at
