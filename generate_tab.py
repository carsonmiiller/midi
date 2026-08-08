import mido

def note_to_bass(midi_note):
    # Standard bass tuning open notes: G(55), D(50), A(45), E(40)
    strings = [('G', 55), ('D', 50), ('A', 45), ('E', 40)]
    for string_name, open_midi in strings:
        fret = midi_note - open_midi
        if 0 <= fret <= 15:  # Keep frets in a playable 0-15 range
            return string_name, fret
    return 'E', 0  # Fallback

# Load MIDI file
mid = mido.MidiFile('./separated/htdemucs/test/bass_basic_pitch.mid')

# Extract unique chronological note-on events
notes = []
for msg in mid:
    if msg.type == 'note_on' and msg.velocity > 0:
        notes.append(msg.note)

# Limit to first 40 notes for a clean terminal preview
notes = notes[:40]

# Initialize tab lines
tab = { 'G': [], 'D': [], 'A': [], 'E': [] }

# Populate tab lines
for note in notes:
    string, fret = note_to_bass(note)
    fret_str = str(fret)
    
    # Add fret to the active string, and dashes to inactive strings
    for s in tab.keys():
        if s == string:
            tab[s].append(fret_str + "-")
        else:
            tab[s].append("-" * len(fret_str) + "-")

# Print the visual ASCII tab
print("\n--- BASS TAB PREVIEW (First 40 Notes) ---\n")
for s in ['G', 'D', 'A', 'E']:
    print(f"{s} |-{''.join(tab[s])}")
print("\n-----------------------------------------\n")