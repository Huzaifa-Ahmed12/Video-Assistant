import os
import torch
from dotenv import load_dotenv

# Load environment variables (e.g. DEEPGRAM_API_KEY)
load_dotenv()

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
_whisper_model = None

# --- Deepgram Transcription Engine ---

def format_speaker_diarization(alternative, results_obj=None):
    """
    Format speaker utterances into clean speaker-attributed text ('who said what').
    Prioritizes Utterance-level diarization (highest accuracy for speaker turns).
    Returns tuple: (diarized_text_string, list_of_speaker_blocks)
    """
    def get_val(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    # 1. Check Utterances level diarization FIRST (Best for natural sentence-level speaker boundaries)
    utterances_list = get_val(results_obj, "utterances") if results_obj else None
    if not utterances_list:
        utterances_list = get_val(alternative, "utterances")

    if utterances_list:
        blocks = []
        current_speaker = None
        current_sentences = []

        for u in utterances_list:
            spk = get_val(u, "speaker", 0)
            text = get_val(u, "transcript", "").strip()
            if not text:
                continue

            if spk != current_speaker:
                if current_sentences and current_speaker is not None:
                    blocks.append({
                        "speaker": f"Speaker {current_speaker}",
                        "text": " ".join(current_sentences)
                    })
                current_speaker = spk
                current_sentences = [text]
            else:
                current_sentences.append(text)

        if current_sentences and current_speaker is not None:
            blocks.append({
                "speaker": f"Speaker {current_speaker}",
                "text": " ".join(current_sentences)
            })

        if blocks:
            text_str = "\n\n".join([f"{b['speaker']}: {b['text']}" for b in blocks])
            return text_str, blocks

    # 2. Check Word level speaker grouping SECOND
    words_list = get_val(alternative, "words")
    if words_list:
        blocks = []
        current_speaker = None
        current_words = []

        for w in words_list:
            spk = get_val(w, "speaker", 0)
            word_text = get_val(w, "punctuated_word") or get_val(w, "word", "")
            if not word_text:
                continue

            if spk != current_speaker:
                if current_words and current_speaker is not None:
                    blocks.append({
                        "speaker": f"Speaker {current_speaker}",
                        "text": " ".join(current_words)
                    })
                current_speaker = spk
                current_words = [word_text]
            else:
                current_words.append(word_text)

        if current_words and current_speaker is not None:
            blocks.append({
                "speaker": f"Speaker {current_speaker}",
                "text": " ".join(current_words)
            })

        if blocks:
            text_str = "\n\n".join([f"{b['speaker']}: {b['text']}" for b in blocks])
            return text_str, blocks

    # 3. Check Paragraph level fallback THIRD
    paragraphs_obj = get_val(alternative, "paragraphs")
    if paragraphs_obj:
        paragraphs_list = get_val(paragraphs_obj, "paragraphs")
        if paragraphs_list:
            blocks = []
            current_speaker = None
            current_texts = []

            for p in paragraphs_list:
                spk = get_val(p, "speaker", 0)
                sentences = get_val(p, "sentences", [])
                if sentences:
                    sentence_texts = [get_val(s, "text", "") for s in sentences]
                    p_text = " ".join([t for t in sentence_texts if t])
                else:
                    p_text = get_val(p, "text", "")

                if not p_text.strip():
                    continue

                if spk != current_speaker:
                    if current_texts and current_speaker is not None:
                        blocks.append({
                            "speaker": f"Speaker {current_speaker}",
                            "text": " ".join(current_texts)
                        })
                    current_speaker = spk
                    current_texts = [p_text.strip()]
                else:
                    current_texts.append(p_text.strip())

            if current_texts and current_speaker is not None:
                blocks.append({
                    "speaker": f"Speaker {current_speaker}",
                    "text": " ".join(current_texts)
                })

            if blocks:
                text_str = "\n\n".join([f"{b['speaker']}: {b['text']}" for b in blocks])
                return text_str, blocks

    # 4. Fallback to raw transcript text
    raw_text = get_val(alternative, "transcript", "")
    fallback_blocks = [{"speaker": "Transcript", "text": raw_text}] if raw_text else []
    return raw_text, fallback_blocks


def transcribe_with_deepgram(
    audio_path: str,
    language: str = "ur",
    model: str = "nova-3",
    diarize: bool = True,
    smart_format: bool = True,
    api_key: str = None
) -> dict:
    """
    Transcribe audio file using Deepgram API with speaker diarization ('who said what').
    Supports Urdu ('ur') and other languages with extended timeout for large files.
    """
    import httpx
    import requests
    from deepgram import DeepgramClient

    effective_key = api_key or os.getenv("DEEPGRAM_API_KEY")
    if not effective_key:
        raise ValueError("DEEPGRAM_API_KEY is not set. Please set it in your .env file.")

    # Configure 10-minute timeout for large audio file uploads
    custom_timeout = httpx.Timeout(600.0, connect=60.0, read=600.0, write=600.0)

    try:
        from deepgram import DeepgramClientOptions
        config = DeepgramClientOptions(options={"timeout": custom_timeout})
        client = DeepgramClient(api_key=effective_key, config=config)
    except Exception:
        client = DeepgramClient(api_key=effective_key)

    with open(audio_path, "rb") as audio_file:
        file_data = audio_file.read()

    print(f"[+] Transcribing audio with Deepgram (Model: '{model}', Language: '{language}', Diarize: {diarize})...")
    print(f"[+] Uploading audio file ({len(file_data) / (1024*1024):.2f} MB)...")

    response = None
    try:
        response = client.listen.v1.media.transcribe_file(
            request=file_data,
            model=model,
            language=language,
            diarize=diarize,
            smart_format=smart_format,
            punctuate=True,
            paragraphs=True,
            utterances=True
        )
    except Exception as e:
        print(f"[!] Deepgram SDK upload timed out or failed ({e}). Trying Direct REST request with extended 10-min timeout...")
        url = (
            f"https://api.deepgram.com/v1/listen?"
            f"model={model}&language={language}&diarize={'true' if diarize else 'false'}&"
            f"smart_format={'true' if smart_format else 'false'}&punctuate=true&paragraphs=true&utterances=true"
        )
        headers = {
            "Authorization": f"Token {effective_key}",
            "Content-Type": "application/octet-stream"
        }
        res = requests.post(url, headers=headers, data=file_data, timeout=(60, 600))
        res.raise_for_status()
        response = res.json()

    # Helper for attribute/dict access
    def get_val(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    results = get_val(response, "results")
    channels = get_val(results, "channels", [])
    first_channel = channels[0] if channels else {}
    alternatives = get_val(first_channel, "alternatives", [])
    alt = alternatives[0] if alternatives else {}

    raw_transcript = get_val(alt, "transcript", "")
    diarized_transcript, diarized_blocks = format_speaker_diarization(alt, results_obj=results)

    print("[+] Deepgram transcription successful!")
    return {
        "text": raw_transcript,
        "diarized_text": diarized_transcript,
        "diarized_blocks": diarized_blocks,
        "response": response
    }


class DeepgramProvider:
    """Modular Deepgram Transcription Provider."""
    def __init__(self, api_key: str = None, model: str = "nova-3"):
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        self.model = model

    def transcribe(
        self,
        audio_path: str,
        language: str = "ur",
        diarize: bool = True,
        smart_format: bool = True
    ) -> dict:
        return transcribe_with_deepgram(
            audio_path=audio_path,
            language=language,
            model=self.model,
            diarize=diarize,
            smart_format=smart_format,
            api_key=self.api_key
        )


# --- Whisper Local Fallback Engine ---

def load_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[+] Loading Whisper Model ('{WHISPER_MODEL}') on {device.upper()}...")
        _whisper_model = whisper.load_model(WHISPER_MODEL, device=device)
        print(f"[+] Whisper '{WHISPER_MODEL}' model loaded successfully!")
    return _whisper_model


def detect_audio_language(audio_path: str) -> str:
    """
    Detect spoken language of audio file using Whisper.
    Returns language code e.g. 'ur' (Urdu), 'en' (English).
    """
    import whisper
    model = load_whisper_model()
    print(f"[+] Detecting spoken language for audio: {os.path.basename(audio_path)}...")
    audio = whisper.load_audio(audio_path)
    audio = whisper.pad_or_trim(audio)
    n_mels = getattr(model.dims, "n_mels", 80)
    mel = whisper.log_mel_spectrogram(audio, n_mels=n_mels).to(model.device)
    _, probs = model.detect_language(mel)
    detected_lang = max(probs, key=probs.get)
    confidence = probs[detected_lang]
    print(f"[+] Detected audio language: '{detected_lang}' (Confidence: {confidence:.2%})")
    return detected_lang


def transcribe_chunk(chunk_path: str, translate: bool = False) -> str:
    model = load_whisper_model()
    task = "Translate" if translate else "transcribe"
    use_fp16 = torch.cuda.is_available()
    result = model.transcribe(chunk_path, task=task, fp16=use_fp16)
    return result['text']


def transcribe_all(chunks, translate: bool = False) -> str:
    full_transcript = ""
    for i, chunk in enumerate(chunks):
        print(f"[+] Transcribing chunk {i+1} of {len(chunks)}...")
        text = transcribe_chunk(chunk, translate=translate)
        full_transcript += text.strip() + " "
    print("[+] Local Whisper transcription complete!")
    return full_transcript.strip()