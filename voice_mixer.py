# voice_mixer.py

import os
import torch
import gradio as gr

import config
from tts_logic import text_to_speech, update_model
from ui_tabs import toggle_autoplay

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

voices, slider_configs = get_voices()

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

# --- UI for Voice Mixer (No changes needed here) ---
def create_voice_mix_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# Kokoro Voice Mixer\nSelect voices and adjust their weights to create a mixed voice.")

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
            voice_text = gr.Textbox(label='Enter Text', lines=3, placeholder="Type text here to preview the custom voice...")
            voice_generator = gr.Button('Generate', variant='primary')
        with gr.Accordion('Audio Settings', open=False):
            model_name=gr.Dropdown(config.MODEL_LIST, label="Model", value=config.MODEL_LIST[0])
            speed = gr.Slider(minimum=0.1, maximum=2, value=1, step=0.1, label='⚡️Speed', info='Adjust speaking speed')
            remove_silence = gr.Checkbox(value=False, label='✂️ Remove Silence')
        with gr.Row():
            voice_audio = gr.Audio(interactive=False, label='Output Audio', autoplay=True)
        with gr.Row():
            mix_voice_download = gr.File(label="Download Mixed VoicePack")
        with gr.Accordion('Enable Autoplay', open=False):
            autoplay = gr.Checkbox(value=True, label='Autoplay')
            autoplay.change(toggle_autoplay, inputs=[autoplay], outputs=[voice_audio])

        voice_generator.click(
            generate_custom_audio,
            inputs=[voice_text, voice_formula, model_name, speed, remove_silence],
            outputs=[voice_audio, mix_voice_download]
        )
    return demo
