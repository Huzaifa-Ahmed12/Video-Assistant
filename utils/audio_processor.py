import yt_dlp
from pydub import AudioSegment
import os

DOWNLOAD_DIR='downloads'
os.makedirs(DOWNLOAD_DIR,exist_ok=True)

# To capture the audio from a video url and convert to lightweight mp3
def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
        "quiet": True,
        "nocheckcertificate": True,
        "noplaylist": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "mweb", "web"]
            }
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        base_filename = ydl.prepare_filename(info)
        filename = os.path.splitext(base_filename)[0] + ".mp3"
    return filename


# Convert any audio/video into clean mono mp3 audio format
def convert_to_mp3(input_path: str) -> str:
    """Convert any audio/video into lightweight mp3 format using pydub."""
    output_path = os.path.splitext(input_path)[0] + "_converted.mp3"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format="mp3", bitrate="128k")
    return output_path


# Create Chunking
def chunk_audio(audio_path: str, chunk_minutes: int = 10) -> list:
    audio = AudioSegment.from_file(audio_path)
    chunk_ms = chunk_minutes * 60 * 1000
    chunks = []
    base, _ = os.path.splitext(audio_path)
    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start:start + chunk_ms]
        chunk_path = f"{base}_chunk{i}.mp3"
        chunk.export(chunk_path, format="mp3")
        chunks.append(chunk_path)
    return chunks

# Final Function to prepare audio from YouTube URL or local file path
def prepare_audio_source(source: str) -> str:
    """Download or convert media input to clean WAV format."""
    if source.startswith("http://") or source.startswith("https://"): # If video/audio URL
        print(f"[+] Downloading audio from URL: {source}")
        wav_path = download_youtube_audio(source)
        print(f"[+] Audio saved to: {wav_path}")
    else:                                                        # If local audio/video file
        print(f"[+] Processing local file: {source}")
        wav_path = convert_to_mp3(source)
    return wav_path

def process_audio(source: str, return_chunks: bool = False, chunk_minutes: int = 10):
    """
    Process audio source (URL or local file).
    If return_chunks is True, returns a list of chunk file paths.
    Otherwise, returns the single converted WAV file path (ideal for Deepgram diarization).
    """
    wav_path = prepare_audio_source(source)

    if return_chunks:
        chunks = chunk_audio(wav_path, chunk_minutes=chunk_minutes)
        print(f"[+] Created {len(chunks)} chunk(s).")
        return chunks

    return wav_path