import mido
import os

def midi_to_guitar(midi_note):
    # Standard 6-string guitar open notes (midi numbers)
    # e(64), B(59), G(55), D(50), A(45), E(40)
    strings = [('e', 64), ('B', 59), ('G', 55), ('D', 50), ('A', 45), ('E', 40)]
    possible_positions = []
    
    for string_idx, (string_name, open_midi) in enumerate(strings):
        fret = midi_note - open_midi
        if 0 <= fret <= 15:  # Keep frets within a playable range
            possible_positions.append((string_idx, fret))
            
    # Return the position closest to the nut/playable area
    if possible_positions:
        return min(possible_positions, key=lambda x: x[1])
    return None

# Load the transcribed MIDI file
mid_path = './separated/htdemucs/test/bass_basic_pitch.mid' # Testing on our current MIDI first
if not os.path.exists(mid_path):
    print("Please make sure you have a transcribed MIDI file.")
    exit()

mid = mido.MidiFile(mid_path)

# Extract notes with timestamps to group them into chords
ticks_per_beat = mid.ticks_per_beat
current_time = 0
note_events = []

for track in mid.tracks:
    for msg in track:
        current_time += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            note_events.append((current_time, msg.note))

# Group notes that happen at the exact same time (chords)
grouped_chords = {}
for time, note in note_events:
    if time not in grouped_chords:
        grouped_chords[time] = []
    grouped_chords[time].append(note)

# Generate the 6-string visual tab
guitar_tab = {0: [], 1: [], 2: [], 3: [], 4: [], 5: []} # 0 is high 'e', 5 is low 'E'

# Sort times and process first 30 steps/chords
sorted_times = sorted(grouped_chords.keys())[:30]

for time in sorted_times:
    chord_notes = grouped_chords[time]
    active_strings_this_step = {}
    
    # Map each note in the chord to a guitar string
    for note in chord_notes:
        mapping = midi_to_guitar(note)
        if mapping:
            string_idx, fret = mapping
            # Ensure we don't try to play two notes on the same string simultaneously
            if string_idx not in active_strings_this_step:
                active_strings_this_step[string_idx] = fret

    # Append to tab notation
    max_len = 1
    for string_idx in range(6):
        if string_idx in active_strings_this_step:
            fret_str = str(active_strings_this_step[string_idx]) + "-"
            guitar_tab[string_idx].append(fret_str)
        else:
            guitar_tab[string_idx].append("--")

# Print the visual ASCII Guitar Tab
string_labels = ['e', 'B', 'G', 'D', 'A', 'E']
print("\n--- POLYPHONIC GUITAR TAB PREVIEW ---\n")
for idx, label in enumerate(string_labels):
    print(f"{label} |-{''.join(guitar_tab[idx])}")
print("\n-------------------------------------\n")