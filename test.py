from utils.audio_processor import process_audio
from core.transcriber import transcribe_all

if __name__ == "__main__":
    source="https://www.youtube.com/watch?v=XATu16PmlEk"
    print("=== Starting Video Assistant Processing ===")
    chunks=process_audio(source)
    
    print("\n=== Starting Audio Transcription ===")
    transcript = transcribe_all(chunks)
    
    print("\n=== FINAL TRANSCRIPT ===")
    print(transcript)