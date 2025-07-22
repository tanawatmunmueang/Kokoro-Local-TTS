# voice_mixer.py

import os
import torch
import gradio as gr

import config
from tts_logic import text_to_speech, update_model

# The consistent filename we will use and overwrite.
VOICE_MIX_FILENAME = "weighted_normalised_voices.pt"

# --- Logic for Voice Mixing ---
def get_voices():
    voices = {}
    voices_dir = "./KOKORO/voices"
    if not os.path.isdir(voices_dir): return {}, {}
    for i in os.listdir(voices_dir):
        if i.endswith(".pt"):
            voice_name = i.replace(".pt", "")
            voices[voice_name] = torch.load(f"./KOKORO/voices/{i}", map_location=config.DEVICE, weights_only=True)

    slider_configs = {}
    for i in voices:
        if i == "af": slider_configs["af"]= "Default 👩🇺🇸"; continue
        if i == "af_nicole": slider_configs["af_nicole"]="Nicole 😏🇺🇸"; continue
        if i == "af_bella": slider_configs["af_bella"]="Bella 🤗🇺🇸"; continue
        country = "🇺🇸" if i.startswith("a") else "🇬🇧"
        if "f_" in i: display_name = f"{i.split('_')[-1].capitalize()} 👩{country}"
        elif "m_" in i or "b_" in i: display_name = f"{i.split('_')[-1].capitalize()} 👨{country}"
        else: display_name = f"{i.capitalize()} 😐"
        slider_configs[i] = display_name
    return voices, slider_configs

voices, _ = get_voices()

def parse_voice_formula(formula):
    if not formula.strip(): raise ValueError("Empty voice formula")
    if not voices: raise ValueError("No voices loaded.")
    weighted_sum = torch.zeros_like(next(iter(voices.values())))
    total_weight = 0
    for term in formula.split('+'):
        parts = term.strip().split('*')
        if len(parts) != 2: raise ValueError(f"Invalid term format: {term.strip()}")
        voice_name, weight_str = parts[0].strip(), parts[1].strip()
        weight = float(weight_str)
        if voice_name not in voices: raise ValueError(f"Unknown voice: {voice_name}")
        weighted_sum += weight * voices[voice_name]
        total_weight += weight
    return weighted_sum / total_weight if total_weight > 0 else None

def get_new_voice_path(formula):
    """
    Generates a new voice mix, saves it to a file, and returns the FILE PATH.
    """
    try:
        weighted_voices = parse_voice_formula(formula)
        if weighted_voices is None: raise ValueError("Could not generate a voice from the formula.")

        voice_pack_dir = os.path.join(config.BASE_PATH, "dummy")
        os.makedirs(voice_pack_dir, exist_ok=True)
        voice_pack_path = os.path.join(voice_pack_dir, VOICE_MIX_FILENAME)

        torch.save(weighted_voices.to('cpu'), voice_pack_path)
        print(f"Successfully SAVED new voice mix to: {voice_pack_path}")

        # <<< CHANGE: Return the file path, just like the original script.
        return voice_pack_path
    except Exception as e:
        raise gr.Error(f"Failed to create voice: {e}")

def generate_custom_audio(text_input, formula_text, model_name, speed, remove_silence):
    print(f"Generating audio with formula: '{formula_text}'")
    if not formula_text:
        raise gr.Error("Voice formula is empty. Please select and enable at least one voice.")
    update_model(model_name)
    try:
        # <<< CHANGE: This now receives a file path.
        new_voice_pack_path = get_new_voice_path(formula_text)

        audio_output_path = text_to_speech(
            text=text_input,
            model_name=model_name,
            voice_name="af", # Placeholder, will be overridden by custom_voicepack
            speed=speed,
            remove_silence=remove_silence,
            # <<< CHANGE: Pass the file path directly.
            custom_voicepack=new_voice_pack_path
        )

        # For the download button, we return the same known path.
        return audio_output_path, new_voice_pack_path
    except Exception as e:
        raise gr.Error(f"Failed to generate audio: {e}")
