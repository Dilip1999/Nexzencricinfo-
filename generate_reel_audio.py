"""Create an original, royalty-free-style instrumental bed for Reel previews.

The tune is synthesized from simple tones and chord voicings; it does not sample
or reproduce a commercial recording. Uses only Python's standard library.
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

SAMPLE_RATE = 44100
DURATION_SECONDS = 28.0
OUTPUT = Path("assets/audio/nexzencricinfo_original.wav")
CHORDS = [
    (261.63, 329.63, 392.00),  # C major
    (196.00, 246.94, 392.00),  # G major
    (220.00, 261.63, 329.63),  # A minor
    (174.61, 220.00, 349.23),  # F major
]
BEAT_SECONDS = 0.6
CHORD_SECONDS = BEAT_SECONDS * 4


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    total_frames = int(SAMPLE_RATE * DURATION_SECONDS)
    with wave.open(str(OUTPUT), "wb") as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        frames = bytearray()

        for frame in range(total_frames):
            t = frame / SAMPLE_RATE
            chord_index = int(t / CHORD_SECONDS) % len(CHORDS)
            chord_start = int(t / CHORD_SECONDS) * CHORD_SECONDS
            local = t - chord_start
            chord = CHORDS[chord_index]

            # Warm, restrained chord pad and soft bass.
            pad = sum(
                math.sin(2 * math.pi * frequency * t) * 0.055
                + math.sin(2 * math.pi * frequency * 2 * t) * 0.008
                for frequency in chord
            )
            bass = math.sin(2 * math.pi * (chord[0] / 2) * t) * 0.045

            # A sparse pluck pattern using only notes from the current chord.
            beat_index = int(local / BEAT_SECONDS)
            beat_local = local - beat_index * BEAT_SECONDS
            note = chord[(beat_index * 2 + chord_index) % len(chord)] * 2
            pluck = math.sin(2 * math.pi * note * beat_local)
            pluck *= math.exp(-beat_local * 5.5) * 0.075

            fade_in = min(1.0, t / 1.0)
            fade_out = min(1.0, max(0.0, (DURATION_SECONDS - t) / 1.5))
            sample = max(-0.75, min(0.75, (pad + bass + pluck) * fade_in * fade_out))
            value = int(sample * 32767)
            frames.extend(value.to_bytes(2, "little", signed=True))
            frames.extend(value.to_bytes(2, "little", signed=True))

        audio.writeframes(frames)

    print(f"Created original background audio: {OUTPUT}")


if __name__ == "__main__":
    main()
