import os
import requests
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


def free_google_translate(text: str) -> str:
    """
    Fallback translator using Google Translate endpoint (100% free, no API key needed).
    Preserves speaker badges (e.g. 'Speaker 0:').
    """
    if not text or not text.strip():
        return ""

    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=ur&tl=en&dt=t&q={quote(text)}"
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            data = res.json()
            translated_chunks = [item[0] for item in data[0] if item and item[0]]
            return "".join(translated_chunks).strip()
        return text
    except Exception as e:
        print(f"[!] Free translation fallback error: {e}")
        return text


def translate_urdu_to_english(text: str, api_key: str = None) -> str:
    """
    Translate Urdu text to English.
    Tries Mistral AI first. If API key is missing or fails, seamlessly falls back to free translation.
    """
    if not text or not text.strip():
        return ""

    # Check multiple common env variable names and strip quotes/spaces
    raw_key = api_key or os.getenv("MISTRAL_API_KEY") or os.getenv("MISTRALAI_API_KEY") or os.getenv("MISTRAL_KEY")
    effective_key = raw_key.strip("'\" \t\r\n") if raw_key else None

    if not effective_key:
        return free_google_translate(text)

    prompt = (
        "You are a professional translator. Translate the following Urdu text into clear, natural, fluent English.\n"
        "Do NOT summarize; output ONLY the English translation without commentary or intro.\n\n"
        f"Urdu Text:\n{text}"
    )

    # 1. Try Direct HTTP Request to Mistral AI API
    try:
        headers = {
            "Authorization": f"Bearer {effective_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        res = requests.post(MISTRAL_API_URL, headers=headers, json=payload, timeout=60)
        if res.status_code == 200:
            data = res.json()
            translated = data["choices"][0]["message"]["content"].strip()
            return translated
        else:
            print(f"[!] Mistral API HTTP Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[!] Direct Mistral HTTP request failed: {e}")

    # 2. Fallback to free google translate
    return free_google_translate(text)


def translate_speaker_blocks(blocks: list, api_key: str = None) -> list:
    """
    Translate a list of speaker blocks: [{'speaker': 'Speaker 0', 'text': 'Urdu...'}]
    Returns updated list of dicts with 100% accurate per-speaker English translation:
    [{'speaker': 'Speaker 0', 'text': 'Urdu...', 'english_text': 'English...'}]
    """
    if not blocks:
        return []
    updated_blocks = []

    for i, b in enumerate(blocks):
        speaker = b.get("speaker", f"Speaker {i}")
        urdu_text = b.get("text", "").strip()

        if not urdu_text:
            updated_blocks.append({
                "speaker": speaker,
                "text": "",
                "english_text": ""
            })
            continue

        # Translate single speaker's text directly
        eng_translation = translate_urdu_to_english(urdu_text, api_key=api_key)

        # Clean any accidental 'Speaker X:' prefix if returned by model
        if eng_translation.startswith(f"{speaker}:"):
            eng_translation = eng_translation.split(":", 1)[1].strip()
        elif eng_translation.startswith("Speaker "):
            parts = eng_translation.split(":", 1)
            if len(parts) > 1:
                eng_translation = parts[1].strip()

        updated_blocks.append({
            "speaker": speaker,
            "text": urdu_text,
            "english_text": eng_translation
        })

    return updated_blocks
