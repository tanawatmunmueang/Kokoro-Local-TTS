from huggingface_hub import list_repo_files, hf_hub_download
import os
import shutil
import torch
from itertools import combinations
import platform
import hashlib

# Repository ID
repo_id = "hexgrad/Kokoro-82M"
repo_id2="Remsky/kokoro-82m-mirror"
# Set up the cache directory
cache_dir = "./cache"
os.makedirs(cache_dir, exist_ok=True)

# Set up the base model paths
KOKORO_DIR = "./KOKORO"
VOICES_DIR = os.path.join(KOKORO_DIR, "voices")
FP16_DIR = os.path.join(KOKORO_DIR, "fp16")
KOKORO_FILE = "kokoro-v0_19.pth"
FP16_FILE = "fp16/kokoro-v0_19-half.pth"

def get_file_hash(path):
    """Calculates the SHA256 hash of a file to check for updates."""
    if not os.path.exists(path):
        return None
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def download_files(repo_id, filenames, destination_dir, cache_dir):
    """
    Downloads files from Hugging Face and only copies them to the destination
    if they are new or have been updated (by checking file hashes).
    """
    os.makedirs(destination_dir, exist_ok=True)

    for filename in filenames:
        destination_path = os.path.join(destination_dir, os.path.basename(filename))

        try:
            # This is fast if the file is already in the cache. It ensures we have the latest version locally.
            cached_path = hf_hub_download(repo_id=repo_id, filename=filename, cache_dir=cache_dir)

            # Compare the hash of the latest cached file with the local destination file.
            cached_hash = get_file_hash(cached_path)
            local_hash = get_file_hash(destination_path)

            # If hashes are different or the local file doesn't exist, it's an update.
            if cached_hash != local_hash:
                shutil.copy(cached_path, destination_path)
                print(f"UPDATED/DOWNLOADED: {os.path.basename(destination_path)}")
            else:
                print(f"ALREADY UP-TO-DATE: {os.path.basename(destination_path)}")

        except Exception as e:
            print(f"ERROR downloading or processing {filename}: {e}")

def get_voice_models():
    """
    Downloads official voice models from Hugging Face if they are missing or outdated,
    without deleting existing custom voices.
    """
    # Ensure the target directory exists, but DO NOT delete it.
    os.makedirs(VOICES_DIR, exist_ok=True)
    print(f"Checking for voice models in: {VOICES_DIR}")

    try:
        repo_files = list_repo_files(repo_id)
    except Exception as e:
        print(f"Could not list repo files. Are you offline? Error: {e}")
        return

    # Get the list of official voice files from the repository.
    official_voice_files = [f.replace("voices/", "") for f in repo_files if f.startswith("voices/")]
    official_eng_voices = [f for f in official_voice_files if f.startswith("a") or f.startswith("b")]

    print(f"Verifying all {len(official_eng_voices)} official English voices...")
    # Call our new smart download function for all official voices.
    # It will handle skipping, downloading, or updating each one automatically.
    download_files(repo_id, [f"voices/{file}" for file in official_eng_voices], VOICES_DIR, cache_dir)

def download_base_models():
    """Downloads Kokoro base model and fp16 version if missing or outdated."""
    download_files(repo_id2, [KOKORO_FILE], KOKORO_DIR, cache_dir)
    os.makedirs(FP16_DIR, exist_ok=True) # Ensure fp16 dir exists before download
    download_files(repo_id2, [FP16_FILE], FP16_DIR, cache_dir)

def setup_batch_file():
    """Creates a 'run_app.bat' file for Windows if it doesn't exist."""
    if platform.system() == "Windows":
        bat_file_name = 'run_app.bat'
        if not os.path.exists(bat_file_name):
            bat_content_app = '''@echo off
call myenv\\Scripts\\activate
@python.exe app.py %*
@pause
'''
            with open(bat_file_name, 'w') as bat_file:
                bat_file.write(bat_content_app)
            print(f"Created '{bat_file_name}'.")
        else:
            print(f"'{bat_file_name}' already exists.")
    else:
        print("Not a Windows system, skipping batch file creation.")

def download_ffmpeg():
    """Downloads ffmpeg and ffprobe executables from Hugging Face."""
    print("For Kokoro TTS we don't need ffmpeg, But for Subtitle Dubbing we need ffmpeg")
    os_name=platform.system()
    if os_name == "Windows":
        repo_id = "fishaudio/fish-speech-1"
        filenames = ["ffmpeg.exe", "ffprobe.exe"]
        ffmpeg_dir = "./ffmpeg"
        download_files(repo_id, filenames, ffmpeg_dir, cache_dir)
    elif os_name == "Linux":
         print("Please install ffmpeg using the package manager for your system.")
         print("'sudo apt install ffmpeg' on Debian/Ubuntu")
    else:
        print(f"Manually install ffmpeg for {os_name} from https://ffmpeg.org/download.html")

def mix_all_voices(folder_path=VOICES_DIR):
     """Mix all pairs of voice models and save the new models."""
     available_voice_pack = [
        os.path.splitext(filename)[0]
        for filename in os.listdir(folder_path)
        if filename.endswith('.pt')
    ]
     voice_combinations = combinations(available_voice_pack, 2)
     def mix_model(voice_1, voice_2):
          new_name = f"{voice_1}_mix_{voice_2}"
          voice_id_1 = torch.load(f'{folder_path}/{voice_1}.pt', weights_only=True)
          voice_id_2 = torch.load(f'{folder_path}/{voice_2}.pt', weights_only=True)
          mixed_voice = torch.mean(torch.stack([voice_id_1, voice_id_2]), dim=0)
          torch.save(mixed_voice, f'{folder_path}/{new_name}.pt')
          print(f"Created new voice model: {new_name}")
     for voice_1, voice_2 in voice_combinations:
          print(f"Mixing {voice_1} ❤️ {voice_2}")
          mix_model(voice_1, voice_2)

def save_voice_names(directory=VOICES_DIR, output_file="./voice_names.txt"):
    """
    Retrieves voice names from a directory, sorts them by length, and saves to a file.
    """
    voice_list = [
        os.path.splitext(filename)[0]
        for filename in os.listdir(directory)
        if filename.endswith('.pt')
    ]
    voice_list = sorted(voice_list, key=len)
    with open(output_file, "w") as f:
        for voice_name in voice_list:
            f.write(f"{voice_name}\n")
    print(f"Voice names saved to {output_file}")

# --- Main Execution ---
if __name__ == "__main__":
    get_voice_models()
    download_base_models()
    setup_batch_file()
    # mix_all_voices()
    save_voice_names()
    download_ffmpeg()
    print("Setup complete!")
