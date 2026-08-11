import streamlit as st
import os
import mido
import subprocess
import shutil
import sys

st.set_page_config(layout="wide")
st.title("🎵 AI Music Stem Splitter & Tab Generator")

# Create directories if they don't exist
os.makedirs("./uploads", exist_ok=True)
os.makedirs("./separated/htdemucs", exist_ok=True)

# ----------------------------------------------------
# 1. FILE UPLOAD & PROCESSING PIPELINE
# ----------------------------------------------------
uploaded_file = st.file_uploader("Upload an MP3 or MP4 song to split & transcribe", type=["mp3", "mp4", "wav"])

song_name = "test"  # Default fallback song

if uploaded_file is not None:
    # Get clean name without extension
    original_filename = uploaded_file.name
    song_name = os.path.splitext(original_filename)[0].replace(" ", "_")
    
    upload_path = os.path.join("./uploads", original_filename)
    output_dir = os.path.join("./separated/htdemucs", song_name)
    
    # Save the file locally
    with open(upload_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    # We now verify all three required MIDI files exist to check if a song is processed
    bass_mid = os.path.join(output_dir, "bass_basic_pitch.mid")
    drums_mid = os.path.join(output_dir, "drums_basic_pitch.mid")
    other_mid = os.path.join(output_dir, "other_basic_pitch.mid")
    
    if not os.path.exists(output_dir) or not os.path.exists(bass_mid) or not os.path.exists(drums_mid) or not os.path.exists(other_mid):
        # Self-heal: Wipe incomplete folders
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            
        st.info(f"Processing '{original_filename}'... This will take 2-4 minutes.")
        
        # Progress bar placeholder
        progress_bar = st.progress(0)
        
        # Prepare environment variables to bypass SSL inside the subprocess
        env = os.environ.copy()
        env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"
        env["PYTHONHTTPSVERIFY"] = "0"
        env["TO_DISABLE_SSL_VERIFICATION"] = "1"
        env["SSL_CERT_FILE"] = ""
        
        # Get the exact path to the virtual env's tools [1]
        bin_dir = os.path.dirname(sys.executable)
        basic_pitch_path = os.path.join(bin_dir, "basic-pitch")
        
        # Step A: Run Stem Separation (Demucs) [1]
        st.write("⏳ Running stem separation (Demucs)...")
        try:
            result_demucs = subprocess.run([
                sys.executable, "-m", "demucs", 
                "-n", "htdemucs", 
                "-o", "./separated", 
                upload_path
            ], env=env, capture_output=True, text=True)
            
            if result_demucs.returncode != 0:
                raise Exception(result_demucs.stderr)
                
            progress_bar.progress(30)
            
            # Step B: Run Transcription on Bass (Basic Pitch) [1]
            st.write("⏳ Transcribing bass line to MIDI...")
            result_bp = subprocess.run([
                basic_pitch_path, 
                output_dir, 
                os.path.join(output_dir, "bass.wav")
            ], env=env, capture_output=True, text=True)
            
            if result_bp.returncode != 0:
                raise Exception(result_bp.stderr)
            
            progress_bar.progress(60)
            
            # Step C: Run Transcription on Drums (Basic Pitch) [1]
            st.write("⏳ Transcribing drums to MIDI...")
            result_dp = subprocess.run([
                basic_pitch_path, 
                output_dir, 
                os.path.join(output_dir, "drums.wav")
            ], env=env, capture_output=True, text=True)
            
            if result_dp.returncode != 0:
                raise Exception(result_dp.stderr)
                
            progress_bar.progress(80)

            # Step D: Run Transcription on Guitar/Other (Basic Pitch) [1]
            st.write("⏳ Transcribing guitar (other) line to MIDI...")
            result_op = subprocess.run([
                basic_pitch_path, 
                output_dir, 
                os.path.join(output_dir, "other.wav")
            ], env=env, capture_output=True, text=True)
            
            if result_op.returncode != 0:
                raise Exception(result_op.stderr)
                
            progress_bar.progress(100)
            st.success("Processing complete! Loading player...")
            st.rerun()
            
        except Exception as e:
            st.error("❌ Processing failed with the following error:")
            st.code(str(e))
            st.stop()

# Set current song paths
song_dir = f"./separated/htdemucs/{song_name}"

# ----------------------------------------------------
# 2. BASS TAB GENERATOR (MONOPHONIC)
# ----------------------------------------------------
def generate_wrapped_bass_tabs(notes_per_line=32):
    mid_path = os.path.join(song_dir, 'bass_basic_pitch.mid')
    if not os.path.exists(mid_path):
        return "No Bass MIDI file found. Please process a song first."
        
    mid = mido.MidiFile(mid_path)
    notes = [msg.note for msg in mid if msg.type == 'note_on' and msg.velocity > 0]
    
    strings = [('G', 55), ('D', 50), ('A', 45), ('E', 40)]
    fret_mappings = []
    
    for note in notes:
        matched = False
        for string_name, open_midi in strings:
            fret = note - open_midi
            if 0 <= fret <= 15:
                fret_mappings.append((string_name, fret))
                matched = True
                break
        if not matched:
            fret_mappings.append(('E', 0))
    output = ""
    for i in range(0, len(fret_mappings), notes_per_line):
        chunk = fret_mappings[i : i + notes_per_line]
        tab = { 'G': [], 'D': [], 'A': [], 'E': [] }
        
        for string_name, fret in chunk:
            fret_str = str(fret)
            for s in tab.keys():
                if s == string_name:
                    tab[s].append(fret_str + "-")
                else:
                    tab[s].append("-" * len(fret_str) + "-")
                    
        output += f"--- Measures {i//notes_per_line + 1} ---\n"
        for s in ['G', 'D', 'A', 'E']:
            output += f"{s} |-{''.join(tab[s])}\n"
        output += "\n"
        
    return output

# ----------------------------------------------------
# 3. GUITAR TAB GENERATOR (POLYPHONIC CHORD-MAPPING)
# ----------------------------------------------------
def generate_wrapped_guitar_tabs(notes_per_line=24):
    # FIXED: Now pointing to other_basic_pitch.mid instead of bass_basic_pitch.mid!
    mid_path = os.path.join(song_dir, 'other_basic_pitch.mid')
    if not os.path.exists(mid_path):
        return "No Guitar MIDI file found. Please process a song first."

    def midi_to_guitar(midi_note):
        # e(64), B(59), G(55), D(50), A(45), E(40)
        strings = [('e', 64), ('B', 59), ('G', 55), ('D', 50), ('A', 45), ('E', 40)]
        possible_positions = []
        for string_idx, (string_name, open_midi) in enumerate(strings):
            fret = midi_note - open_midi
            if 0 <= fret <= 15:
                possible_positions.append((string_idx, fret))
        if possible_positions:
            return min(possible_positions, key=lambda x: x[1])
        return None

    mid = mido.MidiFile(mid_path)
    current_time = 0
    note_events = []
    for track in mid.tracks:
        for msg in track:
            current_time += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                note_events.append((current_time, msg.note))

    # Group notes that happen at the same time (chords)
    grouped_chords = {}
    for time, note in note_events:
        if time not in grouped_chords:
            grouped_chords[time] = []
        grouped_chords[time].append(note)
    sorted_times = sorted(grouped_chords.keys())
    
    output = ""
    for i in range(0, len(sorted_times), notes_per_line):
        chunk_times = sorted_times[i : i + notes_per_line]
        tab = {0: [], 1: [], 2: [], 3: [], 4: [], 5: []}
        
        for time in chunk_times:
            chord_notes = grouped_chords[time]
            active_strings_this_step = {}
            
            for note in chord_notes:
                mapping = midi_to_guitar(note)
                if mapping:
                    string_idx, fret = mapping
                    if string_idx not in active_strings_this_step:
                        active_strings_this_step[string_idx] = fret
            
            for string_idx in range(6):
                if string_idx in active_strings_this_step:
                    tab[string_idx].append(str(active_strings_this_step[string_idx]) + "-")
                else:
                    tab[string_idx].append("--")
                    
        output += f"--- Measures {i//notes_per_line + 1} ---\n"
        string_labels = ['e', 'B', 'G', 'D', 'A', 'E']
        for idx, label in enumerate(string_labels):
            output += f"{label} |-{''.join(tab[idx])}\n"
        output += "\n"
        
    return output

# ----------------------------------------------------
# 4. DRUM TAB GENERATOR (PATTERN GRID)
# ----------------------------------------------------
def generate_wrapped_drum_tabs(notes_per_line=32):
    mid_path = os.path.join(song_dir, 'drums_basic_pitch.mid')
    if not os.path.exists(mid_path):
        return "No Drum MIDI file found. Please process a song first."
        
    mid = mido.MidiFile(mid_path)
    
    drum_mapping = {
        'HH': [42, 44, 46],  # Hi-Hat (Closed, Pedal, Open)
        'SD': [38, 40],      # Snare Drum
        'BD': [35, 36]       # Bass Drum (Kick)
    }
    
    current_time = 0
    note_events = []
    for track in mid.tracks:
        for msg in track:
            current_time += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                note_events.append((current_time, msg.note))

    grouped_steps = {}
    for time, note in note_events:
        if time not in grouped_steps:
            grouped_steps[time] = []
        grouped_steps[time].append(note)
    sorted_times = sorted(grouped_steps.keys())
    
    output = ""
    for i in range(0, len(sorted_times), notes_per_line):
        chunk_times = sorted_times[i : i + notes_per_line]
        grid = { 'HH': [], 'SD': [], 'BD': [] }
        
        for time in chunk_times:
            step_notes = grouped_steps[time]
            active_elements = set()
            
            for note in step_notes:
                for instrument, midi_notes in drum_mapping.items():
                    if note in midi_notes:
                        active_elements.add(instrument)
            
            for inst in grid.keys():
                if inst in active_elements:
                    grid[inst].append("x-")
                else:
                    grid[inst].append("--")
                    
        output += f"--- Drum Measures {i//notes_per_line + 1} ---\n"
        for inst in ['HH', 'SD', 'BD']:
            output += f"{inst} |-{''.join(grid[inst])}\n"
        output += "\n"
        
    return output

# ----------------------------------------------------
# 5. GARAGEBAND-STYLE SYNCHRONIZED PLAYER
# ----------------------------------------------------
st.write("---")
st.subheader(f"Playing: {song_name.replace('_', ' ')}")
custom_player_html = """
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: transparent; color: white; }
    .mixer { background: #1e1e1e; padding: 20px; border-radius: 12px; border: 1px solid #333; }
    .master-controls { display: flex; align-items: center; gap: 15px; margin-bottom: 25px; background: #2a2a2a; padding: 10px; border-radius: 8px; }
    .track-row { display: flex; align-items: center; justify-content: space-between; background: #252525; padding: 12px 20px; border-radius: 6px; margin-bottom: 10px; }
    .track-info { width: 150px; font-weight: bold; }
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
        { id: "bass", name: "🎸 Bass", url: "/app/static/SONG_PLACEHOLDER/bass.wav" },
        { id: "drums", name: "🥁 Drums", url: "/app/static/SONG_PLACEHOLDER/drums.wav" },
        { id: "other", name: "🎹 Other (Guitar/Keys)", url: "/app/static/SONG_PLACEHOLDER/other.wav" },
        { id: "vocals", name: "🎤 Vocals", url: "/app/static/SONG_PLACEHOLDER/vocals.wav" }
    ];
    const audioElements = {};
    const tracksContainer = document.getElementById("track-list");
    let isPlaying = false;
    let masterDuration = 0;
    const trackStates = {
        bass: { muted: false, soloed: false },
        drums: { muted: false, soloed: false },
        other: { muted: false, soloed: false },
        vocals: { muted: false, soloed: false }
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
st.components.v1.html(custom_player_html, height=360)

# ----------------------------------------------------
# 6. DYNAMIC TAB VIEW WITH INSTRUMENT TOGGLE
# ----------------------------------------------------
st.write("---")
st.subheader("2. Interactive Tab Notation")
instrument_choice = st.radio(
    "Select transcription instrument notation:",
    ("🎸 Bass Guitar (4-String)", "🎸 Guitar (6-String Polyphonic)", "🥁 Drums (Pattern Grid)"),
    horizontal=True
)
if "4-String" in instrument_choice:
    st.code(generate_wrapped_bass_tabs(), language="text")
elif "6-String" in instrument_choice:
    st.code(generate_wrapped_guitar_tabs(), language="text")
else:
    st.code(generate_wrapped_drum_tabs(), language="text")