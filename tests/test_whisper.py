import sys, wave
import numpy as np
from faster_whisper import WhisperModel

with wave.open(sys.argv[1], "rb") as w:
    print("Format:", w.getframerate(), "Hz,", w.getnchannels(), "ch,",
          w.getsampwidth() * 8, "bit,", round(w.getnframes() / w.getframerate(), 1), "detik")
    pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)

print("Amplitudo maks:", int(np.abs(pcm).max()), "(skala maksimum 32767)")
audio = pcm.astype(np.float32) / 32768.0

for nama in ["base", "small"]:
    m = WhisperModel(nama, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(audio, language="id", beam_size=5,
                           initial_prompt="Jadwal makan MPASI bayi.", vad_filter=True)
    print(nama, "->", " ".join(s.text for s in segs).strip())