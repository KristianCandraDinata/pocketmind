import argparse
from pathlib import Path
import re
import subprocess

# Ekstensi file audio yang didukung
AUDIO_EXTENSIONS = {
    ".wav", ".mp3", ".mpeg", ".mpg", ".m4a", ".aac",
    ".ogg", ".opus", ".flac", ".wma", ".webm", ".3gp"
}

# Pola nama file: input<angka>.<ekstensi> (case-insensitive)
INPUT_PATTERN = re.compile(r"^input(\d+)$", re.IGNORECASE)


def convert_audio_files(input_dir: Path, output_dir: Path, sample_rate: int = 16000, channels: int = 1) -> None:
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"[ERROR] Folder input tidak ditemukan: {input_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Ambil file yang cocok dengan pola input<angka>.<ext> dan urutkan berdasarkan angka
    matched_files = []
    for file_path in input_dir.iterdir():
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in AUDIO_EXTENSIONS:
            continue

        match = INPUT_PATTERN.match(file_path.stem)
        if match:
            number = int(match.group(1))
            matched_files.append((number, file_path))

    matched_files.sort(key=lambda item: item[0])

    if not matched_files:
        print(f"[INFO] Tidak ada file dengan format 'input<angka>.<ekstensi>' di '{input_dir}'.")
        return

    for number, src_file in matched_files:
        dst_file = output_dir / f"output{number}.wav"

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(src_file),
            "-ar", str(sample_rate),
            "-ac", str(channels),
            "-c:a", "pcm_s16le",
            str(dst_file),
        ]

        print(f"[PROSES] {src_file.name} -> {dst_file.name}")
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            print(f"[SUKSES] Tersimpan di: {dst_file}")
        except FileNotFoundError:
            print("[ERROR] 'ffmpeg' tidak ditemukan. Pastikan ffmpeg sudah terpasang dan masuk ke PATH Windows.")
            break
        except subprocess.CalledProcessError as e:
            print(f"[GAGAL] Error saat mengonversi {src_file.name}:")
            print(e.stderr.strip())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Konversi file input<angka>.<ext> menjadi output<angka>.wav (16kHz, mono, pcm_s16le)."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("."),
        help="Folder sumber file input (default: folder saat ini)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Folder tujuan file output (default: folder saat ini)",
    )
    parser.add_argument(
        "--ar",
        type=int,
        default=16000,
        help="Sample rate audio dalam Hz (default: 16000)",
    )
    parser.add_argument(
        "--ac",
        type=int,
        default=1,
        help="Jumlah channel audio: 1=mono, 2=stereo (default: 1)",
    )

    args = parser.parse_args()
    convert_audio_files(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        sample_rate=args.ar,
        channels=args.ac,
    )


if __name__ == "__main__":
    main()