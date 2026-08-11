import streamlit as st
import os
import shutil
from audio_processor import run_separation_pipeline

st.set_page_config(layout="wide")
st.title("🎵 Pure AI 6-Stem Audio Isolator")
st.write("Upload any song to isolate Vocals, Guitar, Bass, Drums, Piano, and other background elements.")

# Ensure static directories exist
os.makedirs("./uploads", exist_ok=True)
os.makedirs("./separated/htdemucs_6s", exist_ok=True)

# File uploader [1]
uploaded_file = st.file_uploader("Upload an MP3, MP4, or WAV file", type=["mp3", "mp4", "wav"])
song_name = "test"  # Default fallback song

if uploaded_file is not None:
    song_name = os.path.splitext(uploaded_file.name)[0].replace(" ", "_")
    upload_path = os.path.join("./uploads", uploaded_file.name)
    output_dir = os.path.join("./separated/htdemucs_6s", song_name)
    
    # Save uploaded file
    with open(upload_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    # Check if isolated stems already exist
    required_stems = ["bass.wav", "drums.wav", "guitar.wav", "piano.wav", "vocals.wav", "other.wav"]
    is_processed = os.path.exists(output_dir) and all(
        os.path.exists(os.path.join(output_dir, stem)) for stem in required_stems
    )
    
    if not is_processed:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            
        st.info(f"Separating tracks for '{uploaded_file.name}' into 6 stems... Please wait.")
        
        with st.spinner("Processing audio through 6-stem AI splitter..."):
            try:
                run_separation_pipeline(upload_path, output_dir)
                st.success("Separation complete!")
                st.rerun()
            except Exception as e:
                st.error("❌ Separation failed with the following error:")
                st.code(str(e))
                st.stop()

# ----------------------------------------------------
# GARAGEBAND-STYLE SYNCHRONIZED PLAYER (6 TRACKS)
# ----------------------------------------------------
st.write("---")
st.subheader(f"Playing: {song_name.replace('_', ' ')}")

custom_player_html = """
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: transparent; color: white; }
    .mixer { background: #1e1e1e; padding: 20px; border-radius: 12px; border: 1px solid #333; }
    .master-controls { display: flex; align-items: center; gap: 15px; margin-bottom: 25px; background: #2a2a2a; padding: 10px; border-radius: 8px; }
    .track-row { display: flex; align-items: center; justify-content: space-between; background: #252525; padding: 12px 20px; border-radius: 6px; margin-bottom: 10px; }
    .track-info { width: 180px; font-weight: bold; }
    .track-controls { display: flex; align-items: center; gap: 10px; }
    .btn { background: #444; border: none; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: bold; transition: background 0.2s; }
    .btn.active-mute { background: #d9534f !important; color: white !important; }
    .btn.active-solo { background: #f0ad4e !important; color: black !important; }
    .slider { width: 100px; accent-color: #007aff; }
    .timeline { flex-grow: 1; accent-color: #34c759; }
    #time-display { font-family: monospace; font-size: 14px; }
</style>

<div class="mixer">
    <div class="master-controls">
        <button class="btn" id="master-play" style="background: #34c759; padding: 8px 16px;">Play</button>
        <input type="range" id="master-timeline" class="timeline" value="0" min="0" step="0.1">
        <span id="time-display">0:00 / 0:00</span>
    </div>
    <div class="track-list" id="track-list"></div>
</div>

<script>
    const stems = [
        { id: "vocals", name: "🎤 Vocals", url: "/app/static/SONG_PLACEHOLDER/vocals.wav" },
        { id: "guitar", name: "🎸 Guitar", url: "/app/static/SONG_PLACEHOLDER/guitar.wav" },
        { id: "bass", name: "🎸 Bass", url: "/app/static/SONG_PLACEHOLDER/bass.wav" },
        { id: "drums", name: "🥁 Drums", url: "/app/static/SONG_PLACEHOLDER/drums.wav" },
        { id: "piano", name: "🎹 Piano/Keys", url: "/app/static/SONG_PLACEHOLDER/piano.wav" },
        { id: "other", name: "🎹 Other", url: "/app/static/SONG_PLACEHOLDER/other.wav" }
    ];

    const audioElements = {};
    const tracksContainer = document.getElementById("track-list");
    let isPlaying = false;
    let masterDuration = 0;

    const trackStates = {
        vocals: { muted: false, soloed: false },
        guitar: { muted: false, soloed: false },
        bass: { muted: false, soloed: false },
        drums: { muted: false, soloed: false },
        piano: { muted: false, soloed: false },
        other: { muted: false, soloed: false }
    };

    stems.forEach(stem => {
        const audio = new Audio(stem.url);
        audio.preload = "auto";
        audioElements[stem.id] = audio;

        const row = document.createElement("div");
        row.className = "track-row";
        row.innerHTML = `
            <div class="track-info">${stem.name}</div>
            <div class="track-controls">
                <button class="btn" id="mute-${stem.id}">M</button>
                <button class="btn" id="solo-${stem.id}">S</button>
                <input type="range" class="slider" id="vol-${stem.id}" min="0" max="1" step="0.1" value="0.8">
            </div>
        `;
        tracksContainer.appendChild(row);

        const muteBtn = document.getElementById(`mute-${stem.id}`);
        const soloBtn = document.getElementById(`solo-${stem.id}`);
        const volSlider = document.getElementById(`vol-${stem.id}`);

        muteBtn.onclick = () => {
            trackStates[stem.id].muted = !trackStates[stem.id].muted;
            if (!trackStates[stem.id].muted) {
                stems.forEach(s => { trackStates[s.id].soloed = false; });
            } else {
                trackStates[stem.id].soloed = false;
            }
            syncMixer();
        };

        soloBtn.onclick = () => {
            trackStates[stem.id].soloed = !trackStates[stem.id].soloed;
            if (trackStates[stem.id].soloed) {
                trackStates[stem.id].muted = false;
                stems.forEach(s => {
                    if (s.id !== stem.id) {
                        trackStates[s.id].muted = true;
                        trackStates[s.id].soloed = false;
                    }
                });
            } else {
                stems.forEach(s => { trackStates[s.id].muted = false; });
            }
            syncMixer();
        };

        volSlider.oninput = (e) => {
            audio.volume = e.target.value;
        };
    });

    const audios = Object.values(audioElements);

    function syncMixer() {
        stems.forEach(stem => {
            const id = stem.id;
            const audio = audioElements[id];
            const state = trackStates[id];
            audio.muted = state.muted;
            const mBtn = document.getElementById(`mute-${id}`);
            const sBtn = document.getElementById(`solo-${id}`);
            if (state.muted) {
                mBtn.classList.add("active-mute");
            } else {
                mBtn.classList.remove("active-mute");
            }
            if (state.soloed) {
                sBtn.classList.add("active-solo");
            } else {
                sBtn.classList.remove("active-solo");
            }
        });
    }

    syncMixer();

    audios[0].addEventListener("loadedmetadata", () => {
        masterDuration = Math.max(...audios.map(a => a.duration || 0));
        document.getElementById("master-timeline").max = masterDuration;
    });

    const playBtn = document.getElementById("master-play");
    const timeline = document.getElementById("master-timeline");
    const timeDisplay = document.getElementById("time-display");

    playBtn.onclick = () => {
        isPlaying = !isPlaying;
        playBtn.innerText = isPlaying ? "Pause" : "Play";
        playBtn.style.background = isPlaying ? "#ff3b30" : "#34c759";
        audios.forEach(audio => {
            if (isPlaying) {
                audio.play().catch(e => console.log("Blocked: user interaction required"));
            } else {
                audio.pause();
            }
        });
    };

    timeline.oninput = (e) => {
        const targetTime = parseFloat(e.target.value);
        audios.forEach(audio => {
            audio.currentTime = targetTime;
        });
    };

    setInterval(() => {
        if (audios[0] && !audios[0].paused) {
            const currentTime = audios[0].currentTime;
            timeline.value = currentTime;
            
            const curMins = Math.floor(currentTime / 60);
            const curSecs = Math.floor(currentTime % 60).toString().padStart(2, '0');
            const durMins = Math.floor(masterDuration / 60) || 0;
            const durSecs = Math.floor(masterDuration % 60).toString().padStart(2, '0') || "00";
            
            timeDisplay.innerText = `${curMins}:${curSecs} / ${durMins}:${durSecs}`;
        }
    }, 250);
</script>
""".replace("SONG_PLACEHOLDER", song_name)

st.components.v1.html(custom_player_html, height=450)