# 🎶 Kokoro-TTS Generator - Offline 🎙️

**Note:** This is not the official repository. Code is a mess.<br>
---

### Installation Tutorial

#### 1. Clone the GitHub Repository:
```bash
git clone https://github.com/NeuralFalconYT/Kokoro-82M-WebUI.git<br>

cd Kokoro-82M-WebUI
```

#### 2. Create a Python Virtual Environment:
```bash
python -m venv myenv
```
This command creates a new Python virtual environment named `myenv` for isolating dependencies.

#### 3. Activate the Virtual Environment:
- **For Windows:**
  ```bash
  myenv\Scripts\activate
  ```
- **For Linux:**
  ```bash
  source myenv/bin/activate
  ```
This activates the virtual environment, enabling you to install and run dependencies in an isolated environment.
Here’s the corrected version of point 4, with proper indentation for the subpoints:


#### 4. Install PyTorch:

- **For GPU (CUDA-enabled installation):**
  - Check CUDA Version (for GPU setup):
    ```bash
    nvcc --version
    ```
    Find your CUDA version example ```11.8```

  - Visit [PyTorch Get Started](https://pytorch.org/get-started/locally/) and install the version compatible with your CUDA setup.:<br>
    - For CUDA 11.8:
    ```
    pip install torch  --index-url https://download.pytorch.org/whl/cu118
    ```
    - For CUDA 12.1:
    ```
    pip install torch  --index-url https://download.pytorch.org/whl/cu121
    ```
    - For CUDA 12.4:
    ```
    pip install torch  --index-url https://download.pytorch.org/whl/cu124
    ```
- **For CPU (if not using GPU):**
  ```bash
  pip install torch
  ```
  This installs the CPU-only version of PyTorch.


#### 5. Install Required Dependencies:
```bash
pip install -r requirements.txt
```
This installs all the required Python libraries listed in the `requirements.txt` file.

#### 6. Download Model and Get Latest VoicePack:
```bash
python download_model.py
```

---

#### 7. Install eSpeak NG

- **For Windows:**
  1. Download the latest eSpeak NG release from the [eSpeak NG GitHub Releases](https://github.com/espeak-ng/espeak-ng/releases/tag/1.51).
  2. Locate and download the file named **`espeak-ng-X64.msi`**.
  3. Run the installer and follow the installation steps. Ensure that you install eSpeak NG in the default directory:
     ```
     C:\Program Files\eSpeak NG
     ```
     > **Note:** This default path is required for the application to locate eSpeak NG properly.

- **For Linux:**
  1. Open your terminal.
  2. Install eSpeak NG using the following command:
     ```bash
     sudo apt-get -qq -y install espeak-ng > /dev/null 2>&1
     ```
     > **Note:** This command suppresses unnecessary output for a cleaner installation process.

---
#### 8. Install ffmpeg [Only For Linux Users]
Skip this step if you are using Windows.
You only need FFmpeg if you plan to use it for subtitle dubbing feature. If you just want to use *Kokoro TTS*, you can *skip* this step too.
```
  apt-get update
  !apt-get install -y ffmpeg
```

#### 9. Run Gradio App

To run the Gradio app, follow these steps:

1. **Activate the Virtual Environment:**
   ```bash
   myenv\Scripts\activate
   ```

2. **Run the Application:**
   ```bash
   python app.py
   ```

   Alternatively, on Windows, double-click on `run_app.bat` to start the application.

---

![1](https://freeimage.host/i/3VovCVS)
![2](https://freeimage.host/i/3Vovni7)
![3](https://freeimage.host/i/3VovBx2)
![4](https://freeimage.host/i/3VovfDl)
![5](https://freeimage.host/i/3Vovxf9)

### License
[Kokoro model](https://huggingface.co/hexgrad/Kokoro-82M), is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)<br>
The inference code adapted from StyleTTS2 is MIT licensed.
### Credits
**Model:**<br>
[Kokoro HuggingFace](https://huggingface.co/hexgrad/Kokoro-82M)

**Voice Mix Feature:**<br>
[Make Custom Voices With KokoroTTS](https://huggingface.co/spaces/ysharma/Make_Custom_Voices_With_KokoroTTS)

**AI Assistance:** <br>
[ChatGPT](https://chatgpt.com/)<br>
[Google AI Studio](https://aistudio.google.com/)<br>
[Github Copilot](https://github.com/features/copilot)

**Sepcial Thanks:** <br>
[Falcon](https://github.com/NeuralFalconYT)
