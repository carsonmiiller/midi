# AI Music Stem Splitter & Tab Generator

An interactive web app built with Streamlit that separates music audio files (MP3, MP4, WAV) into individual instrument stems (vocals, drums, bass, other) and transcribes the bass stem into playable tab notation.

## Prerequisites

- **Python 3.10** (Machine learning dependencies such as TensorFlow and Basic Pitch are not yet fully supported on newer Python versions).
- **FFmpeg** (Required for audio processing and stem separation).

## Local Installation

1. **Install FFmpeg** on your system:
   - **Mac (via Homebrew):** `brew install ffmpeg`
   - **Linux (Debian/Ubuntu):** `sudo apt-get install ffmpeg`

2. **Clone the repository**:
```
git clone https://github.com/carsonmiiller/midi.git
cd midi
```

3. **Set up a virtual environment** and activate it:
```
python3 -m venv music-env
source music-env/bin/activate
```

4. **Install Python dependencies**:
```
pip install -r requirements.txt
```

5. **Create the static directory link** (Required for serving the synchronized audio stems to the browser player):
```
ln -s ./separated/htdemucs static
```
6. **Run the application**:
```
streamlit run app.py
```

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request or open an issue to suggest new features (such as guitar tab transcription or sheet music visualizers).