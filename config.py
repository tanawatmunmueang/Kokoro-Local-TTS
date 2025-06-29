# config.py

import os
import shutil
import torch
import sys

# Add the project's root directory to the Python path to ensure imports work correctly
sys.path.append('.')

# --- Global Variables (to be initialized in app.py) ---
MODEL = None
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
CURRENT_MODEL = None
BASE_PATH = os.getcwd()

# --- Application Constants ---
MODEL_LIST = ["kokoro-v0_19.pth", "kokoro-v0_19-half.pth"]

# Dynamically get the list of voice names from the voices directory
try:
    VOICE_LIST = sorted(
        [
            os.path.splitext(filename)[0]
            for filename in os.listdir("./KOKORO/voices")
            if filename.endswith('.pt')
        ]
    )
except FileNotFoundError:
    print("Warning: './KOKORO/voices' directory not found. The voice list will be empty.")
    VOICE_LIST = []


# --- Startup Utility Function ---
def clean_folder_before_start():
    """Removes and recreates specified temporary folders to ensure a clean start."""
    folder_list = ["dummy", "TTS_DUB"]
    for folder in folder_list:
        folder_path = os.path.join(BASE_PATH, folder)
        if os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
            except OSError as e:
                print(f"Error removing folder {folder_path}: {e}")
        # Recreate the folder
        os.makedirs(folder_path, exist_ok=True)
