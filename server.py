import asyncio, json, os, subprocess, tempfile
import numpy as np
from fastapi import FastAPI, WebSocket
from faster_whisper import WhisperModel
from google import genai
from google.genai import types

app = FastAPI()

stt = WhisperModel("small", device="cpu", compute_type="int8")
ai = genai.Client(http_options=types.HttpOptions(timeout=20000))  # 20 detik; key dari GEMINI_API_KEY
PIPER_MODEL = "id_ID-news_tts-medium.onnx"

# Model dicoba berurutan. Sesuaikan dengan hasil tes_gemini.py dan halaman rate-limit.
GEMINI_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash"]

with open("pengetahuan_konsul.txt", encoding="utf-8") as f:
    PENGETAHUAN = f.read()

# Jadwal makan anak. Samakan dengan REMINDER_HOURS di firmware ESP.
JADWAL = "07.00 makan pagi; 12.00 makan siang; 17.00 makan sore"


SYSTEM_PROMPT = f"""Kamu adalah PocketMind, asisten suara pintar untuk membantu
pelajar dan mahasiswa di Indonesia dalam menghadapi permasalahan
kehidupan sekolah, perkuliahan, dan lingkungan sosial.

ATURAN:
1. Jawab menggunakan bahasa Indonesia yang sederhana, ramah,
   empatik, dan mudah dipahami pelajar.
2. Dasarkan jawaban pada PENGETAHUAN yang tersedia di bawah.
3. Kamu boleh membantu membahas permasalahan seperti bullying,
   pertemanan, tekanan akademik, motivasi belajar, stres sekolah,
   konflik sosial, dan permasalahan pelajar lainnya.
4. Jika pengguna mengalami bullying, berikan respons yang empatik,
   jangan menyalahkan korban, dan sarankan mencari bantuan dari
   guru BK, orang tua, wali kelas, atau pihak tepercaya.
5. Jika terdapat ancaman keselamatan, kekerasan, atau kondisi
   darurat, sarankan segera mencari bantuan orang dewasa tepercaya
   atau pihak berwenang.
6. Jangan mengarang informasi yang tidak terdapat dalam PENGETAHUAN.
   Jika informasi tidak tersedia, sampaikan bahwa kamu belum memiliki
   informasi yang cukup.
7. Jika pertanyaan berkaitan dengan MPASI, makanan bayi, atau
   pemberian nutrisi anak, tolak dengan sopan karena saat ini kamu
   sedang berada dalam mode Konsultasi Pelajar.
8. Jika pertanyaan tidak berkaitan dengan konsultasi pelajar,
   tolak dengan sopan.
9. Jika ucapan tidak jelas atau salah dikenali, minta pengguna
   mengulangi pertanyaannya.

FORMAT:
Balas HANYA dengan satu objek JSON, tanpa teks lain dan tanpa markdown:
{{"suara": "...", "layar": "..."}}

- "suara": maksimal 2 kalimat pendek, gunakan bahasa alami,
  tanpa emoji dan tanpa tanda baca aneh.
- "layar": ringkasan maksimal 60 karakter, boleh menggunakan angka,
  tanpa emoji dan tanpa baris baru.

PENGETAHUAN:
{PENGETAHUAN}
"""


AI_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    response_mime_type="application/json",
)


def panggil_gemini(isi):
    gagal = None
    for nama in GEMINI_MODELS:
        try:
            r = ai.models.generate_content(model=nama, contents=isi, config=AI_CONFIG)
            if r.text:
                print("Model dipakai:", nama)
                return r.text.strip()
        except Exception as e:
            gagal = e
            print(f"Model {nama} gagal: {e!r}")
    raise RuntimeError(f"Semua model gagal: {gagal!r}")


def ask_ai(pertanyaan: str, riwayat: list):
    pesan = riwayat[-6:] + [types.Content(role="user", parts=[types.Part(text=pertanyaan)])]
    try:
        mentah = panggil_gemini(pesan)
        bersih = mentah.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(bersih)
            suara, layar = data["suara"], data["layar"]
        except (json.JSONDecodeError, KeyError, TypeError):
            suara, layar = bersih, bersih[:60]
        riwayat.append(types.Content(role="user", parts=[types.Part(text=pertanyaan)]))
        riwayat.append(types.Content(role="model", parts=[types.Part(text=mentah)]))
        return suara, layar[:60]
    except Exception as e:
        print("Error API:", repr(e))
        return "Maaf, koneksi ke AI sedang bermasalah.", "AI error"


def transcribe(pcm: np.ndarray) -> str:
    audio = pcm.astype(np.float32) / 32768.0
    segs, _ = stt.transcribe(
        audio, language="id", beam_size=5, vad_filter=True,
        initial_prompt="Jadwal makan MPASI bayi usia 6 bulan, 9 bulan, 12 bulan.")
    return " ".join(s.text for s in segs).strip()


def tts_pcm(text: str) -> bytes:
    # Hasil: PCM 16-bit, 16 kHz, mono (sesuai firmware ESP)
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "out.wav")
        subprocess.run(["piper", "--model", PIPER_MODEL, "--output_file", wav],
                       input=text.encode(), check=True)
        out = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", wav,
                              "-f", "s16le", "-ar", "16000", "-ac", "1", "-"],
                             capture_output=True, check=True)
    return out.stdout


@app.get("/")
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    buf = bytearray()
    riwayat = []   # ingatan percakapan singkat selama koneksi ini
    while True:
        msg = await ws.receive()
        if msg["type"] == "websocket.disconnect":
            break
        if msg.get("bytes"):
            buf.extend(msg["bytes"])
        elif msg.get("text") == "END":
            pcm = np.frombuffer(bytes(buf), dtype=np.int16)
            buf.clear()
            amp = int(np.abs(pcm).max()) if len(pcm) else 0
            print(f"Audio: {len(pcm)/16000:.1f} detik, amplitudo maks {amp}")
            teks = "" if len(pcm) < 8000 else await asyncio.to_thread(transcribe, pcm)
            print("Terdengar:", teks)
            suara, layar = await asyncio.to_thread(
                ask_ai, teks or "(suara tidak terdengar jelas)", riwayat)
            print("Jawaban AI:", suara, "|", layar)
            await ws.send_text("OLED:" + layar)
            audio = await asyncio.to_thread(tts_pcm, suara)
            for i in range(0, len(audio), 1024):
                await ws.send_bytes(audio[i:i + 1024])
            await ws.send_text("DONE")