import asyncio
from pathlib import Path
import re
import sys
import wave
import websockets


def buat_nama_balasan(input_path: str) -> str:
    stem = Path(input_path).stem
    # Cari angka di nama file input, prioritaskan angka di akhir nama file
    match = re.search(r"(\d+)$", stem) or re.search(r"(\d+)", stem)
    if match:
        return f"balasan{match.group(1)}.wav"
    return f"balasan_{stem}.wav"


async def main(path, host):
    output_path = buat_nama_balasan(path)

    with wave.open(path, "rb") as w:
        assert (
            w.getframerate() == 16000
            and w.getnchannels() == 1
            and w.getsampwidth() == 2
        ), "File harus WAV 16 kHz, mono, 16-bit"
        data = w.readframes(w.getnframes())

    async with websockets.connect(f"ws://{host}:8000/ws", max_size=None) as ws:
        for i in range(0, len(data), 512):
            await ws.send(data[i : i + 512])
        await ws.send("END")
        audio = bytearray()
        while True:
            msg = await ws.recv()
            if isinstance(msg, bytes):
                audio += msg
            elif msg == "DONE":
                break
            else:
                print("Pesan:", msg)

    with wave.open(output_path, "wb") as o:
        o.setnchannels(1)
        o.setsampwidth(2)
        o.setframerate(16000)
        o.writeframes(bytes(audio))

    print(f"Balasan tersimpan di {output_path}")


asyncio.run(
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "localhost")
)