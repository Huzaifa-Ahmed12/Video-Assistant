import whisper
import os
import torch

WHISPER_MODEL=os.getenv("WHISPER_MODEL","small")
_model=None

def load_model():
    global _model
    if _model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[+] Loading Whisper Model ('{WHISPER_MODEL}') on {device.upper()}...")
        _model=whisper.load_model(WHISPER_MODEL, device=device)
        print(f"[+] Whisper '{WHISPER_MODEL}' model loaded successfully!")

    return _model

def transcribe_chunk(chunk_path:str,translate:bool=False)->str:
    model=load_model()
    task="Translate" if translate else "transcribe" #If translate value is True then Translate, else only transcribe
    use_fp16 = torch.cuda.is_available()
    result=model.transcribe(chunk_path,task=task,fp16=use_fp16)
    return result['text']

def transcribe_all(chunks,translate:bool=False)->str:
    full_transcript=""

    for i,chunk in enumerate(chunks):
        print(f"[+] Transcribing chunk {i+1} of {len(chunks)}...")
        text=transcribe_chunk(chunk,translate=translate)
        full_transcript+=text.strip() + " "
    print("[+] Transcription complete!")

    return full_transcript.strip()