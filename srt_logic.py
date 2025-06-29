# srt_logic.py

import os
import shutil
import subprocess
import json
import pysrt
import uuid
import re
import platform
import datetime
import librosa
import soundfile as sf
import gradio as gr
from pydub import AudioSegment
from tqdm import tqdm

import config
from tts_logic import text_to_speech, manage_files

# --- Module-level variables ---
srt_voice_name = "af_bella"
USE_FFMPEG, FFMPEG_PATH = False, ""

def is_ffmpeg_installed():
    """Checks for a local or system-wide FFmpeg installation."""
    global USE_FFMPEG, FFMPEG_PATH
    local_ffmpeg_path_win = os.path.join("./ffmpeg", "ffmpeg.exe")
    local_ffmpeg_path_unix = "ffmpeg"

    ffmpeg_cmd = local_ffmpeg_path_win if platform.system() == "Windows" and os.path.exists(local_ffmpeg_path_win) else local_ffmpeg_path_unix

    try:
        subprocess.run([ffmpeg_cmd, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        USE_FFMPEG = True
        FFMPEG_PATH = ffmpeg_cmd
    except (FileNotFoundError, subprocess.CalledProcessError):
        USE_FFMPEG = False

is_ffmpeg_installed()

def get_subtitle_dub_path(srt_file_path, language="en"):
    file_name = os.path.splitext(os.path.basename(srt_file_path))[0]
    dub_dir = os.path.join(config.BASE_PATH, "TTS_DUB")
    random_string = str(uuid.uuid4())[:6]
    current_time = datetime.datetime.now().strftime("%I_%M_%p")
    return os.path.join(dub_dir, f"{file_name}_{language}_{current_time}_{random_string}.wav")

def speedup_audio_librosa(input_file, output_file, speedup_factor):
    try:
        y, sr = librosa.load(input_file, sr=None)
        y_stretched = librosa.effects.time_stretch(y, rate=speedup_factor)
        sf.write(output_file, y_stretched, sr)
    except Exception as e:
        gr.Warning(f"Error during speedup with Librosa: {e}")
        shutil.copy(input_file, output_file)

def change_speed(input_file, output_file, speedup_factor):
    if USE_FFMPEG:
        try:
            subprocess.run(
                [FFMPEG_PATH, "-i", input_file, "-filter:a", f"atempo={speedup_factor}", output_file, "-y"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception as e:
            gr.Error(f"Error with FFmpeg: {e}. Falling back to librosa.")
            speedup_audio_librosa(input_file, output_file, speedup_factor)
    else:
        speedup_audio_librosa(input_file, output_file, speedup_factor)

def your_tts_for_srt(text, audio_path, actual_duration):
    model_name = "kokoro-v0_19.pth"
    # Initial generation at normal speed
    tts_path = text_to_speech(text, model_name, voice_name=srt_voice_name, speed=1.0, trim=1.0)

    tts_audio = AudioSegment.from_file(tts_path)
    tts_duration = len(tts_audio)

    # If the generated audio is too long for the subtitle's duration, speed it up
    if actual_duration > 0 and tts_duration > actual_duration:
        speedup_factor = tts_duration / actual_duration
        # Regenerate with the calculated speed factor
        tts_path = text_to_speech(text, model_name, voice_name=srt_voice_name, speed=speedup_factor, trim=1.0)

    shutil.copy(tts_path, audio_path)

class SRTDubbing:
    def __init__(self):
        self.cache_dir = os.path.join(config.BASE_PATH, "dummy", "cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def text_to_speech_srt(self, text, audio_path, language, actual_duration):
        temp_filename = os.path.join(self.cache_dir, f"{uuid.uuid4()}.wav")
        your_tts_for_srt(text, temp_filename, actual_duration)

        tts_audio = AudioSegment.from_file(temp_filename)
        tts_duration = len(tts_audio)

        if actual_duration <= 0: # If duration is 0 or negative, just use the file
            shutil.move(temp_filename, audio_path)
            return

        if tts_duration > actual_duration:
            speedup_factor = tts_duration / actual_duration
            speedup_filename = os.path.join(self.cache_dir, f"speedup_{uuid.uuid4()}.wav")
            change_speed(temp_filename, speedup_filename, speedup_factor)
            shutil.move(speedup_filename, audio_path)
        elif tts_duration < actual_duration:
            silence_gap = actual_duration - tts_duration
            silence = AudioSegment.silent(duration=int(silence_gap))
            new_audio = tts_audio + silence
            new_audio.export(audio_path, format="wav")
        else: # Durations match
            shutil.move(temp_filename, audio_path)

        if os.path.exists(temp_filename):
            os.remove(temp_filename)

    @staticmethod
    def make_silence(pause_time, pause_save_path):
        if pause_time > 0:
            silence = AudioSegment.silent(duration=pause_time)
            silence.export(pause_save_path, format="wav")

    @staticmethod
    def create_folder_for_srt(srt_file_path):
        srt_base_name = os.path.splitext(os.path.basename(srt_file_path))[0]
        random_uuid = str(uuid.uuid4())[:4]
        folder_path = os.path.join(config.BASE_PATH, "dummy", f"{srt_base_name}_{random_uuid}")
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    @staticmethod
    def concatenate_audio_files(audio_paths, output_path):
        concatenated_audio = AudioSegment.empty()
        for audio_path in audio_paths:
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                audio_segment = AudioSegment.from_file(audio_path)
                concatenated_audio += audio_segment
        concatenated_audio.export(output_path, format="wav")

    def srt_to_dub(self, srt_file_path, dub_save_path, language='en'):
        result = self.read_srt_file(srt_file_path)
        new_folder_path = self.create_folder_for_srt(srt_file_path)
        audio_segments_to_join = []

        for i in tqdm(result, desc="Processing SRT"):
            # Create silence before the segment
            pause_path = os.path.join(new_folder_path, i['previous_pause'])
            self.make_silence(i['pause_time'], pause_path)
            audio_segments_to_join.append(pause_path)

            # Create the TTS audio for the segment
            tts_path = os.path.join(new_folder_path, i['audio_name'])
            self.text_to_speech_srt(i['text'], tts_path, language, i['end_time'] - i['start_time'])
            audio_segments_to_join.append(tts_path)

        self.concatenate_audio_files(audio_segments_to_join, dub_save_path)
        shutil.rmtree(new_folder_path) # Clean up temp folder

    @staticmethod
    def read_srt_file(file_path):
        subs = pysrt.open(file_path, encoding='utf-8')
        entries = []
        previous_end_time_ms = 0

        for i, sub in enumerate(subs):
            start_time_ms = (sub.start.hours * 3600 * 1000) + (sub.start.minutes * 60 * 1000) + (sub.start.seconds * 1000) + sub.start.milliseconds
            end_time_ms = (sub.end.hours * 3600 * 1000) + (sub.end.minutes * 60 * 1000) + (sub.end.seconds * 1000) + sub.end.milliseconds

            entry = {
                'entry_number': i + 1,
                'start_time': start_time_ms,
                'end_time': end_time_ms,
                'text': sub.text_without_tags.replace('\n', ' ').strip(),
                'pause_time': start_time_ms - previous_end_time_ms,
                'audio_name': f"{i + 1}.wav",
                'previous_pause': f"{i + 1}_before_pause.wav",
            }
            entries.append(entry)
            previous_end_time_ms = end_time_ms
        return entries

def srt_process(srt_file, voice_name, custom_voicepack=None, dest_language="en"):
    """The main function called by the UI to start the SRT dubbing process."""
    global srt_voice_name
    if not srt_file or not srt_file.name.endswith(".srt"):
        gr.Error("Please upload a valid .srt file.")
        return None

    if USE_FFMPEG:
        gr.Info("Using FFmpeg for high-quality audio speed adjustments.")
    else:
        gr.Warning("FFmpeg not found. Using 'librosa' for audio speedup, which may impact quality.", duration=15)

    voicepack_path = custom_voicepack.name if custom_voicepack else None
    if voicepack_path and manage_files(voicepack_path):
        srt_voice_name = voicepack_path
    else:
        srt_voice_name = voice_name
        if voicepack_path:
            gr.Warning("Invalid custom voice pack. Using the selected voice instead.")

    srt_dubbing = SRTDubbing()
    dub_save_path = get_subtitle_dub_path(srt_file.name, dest_language)
    srt_dubbing.srt_to_dub(srt_file.name, dub_save_path, dest_language)
    return dub_save_path
