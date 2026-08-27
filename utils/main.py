import sys
import os
# Ensure the project root (parent of utils/) is always on sys.path,
# regardless of where Python is invoked from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from audio_processor import process_audio
from core.transcriber import transcribe_all, detect_audio_language, transcribe_with_deepgram
from core.summarize import summarize, generate_title
from core.translator import translate_urdu_to_english, translate_speaker_blocks
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, load_rag_chain, get_question


load_dotenv()


def run_pipeline(source: str) -> dict:
    """
    Full end-to-end Video Assistant pipeline.

    Args:
        source: YouTube URL or local audio/video file path.

    Returns:
        A dictionary containing:
            - language         : Detected language code ('ur', 'en', etc.)
            - is_urdu          : Boolean flag
            - urdu_transcript  : Raw Urdu transcript (if Urdu audio)
            - english_transcript: Final English transcript text
            - diarized_blocks  : List of speaker-attributed blocks (Deepgram, Urdu path only)
            - translated_blocks: Translated speaker blocks with 'english_text' key (Urdu path only)
            - title            : Auto-generated meeting title
            - summary          : Full professional meeting summary
            - action_items     : Extracted action items
            - key_decisions    : Extracted key decisions
            - questions        : Extracted unresolved questions / follow-ups
            - rag_chain        : A ready-to-use RAG chain for Q&A on the transcript
    """

    print("=" * 52)
    print("  🎙️  VIDEO ASSISTANT — STARTING PIPELINE  ")
    print("=" * 52)
    print(f"[+] Source: {source}\n")

    # ------------------------------------------------------------------ #
    # STEP 1 — Download / prepare audio (single full file for language
    #           detection and Deepgram; chunks for local Whisper fallback)
    # ------------------------------------------------------------------ #
    print("[STEP 1] Preparing audio...")
    audio_path = process_audio(source, return_chunks=False)

    # ------------------------------------------------------------------ #
    # STEP 2 — Detect spoken language using Whisper's language detector
    # ------------------------------------------------------------------ #
    print("\n[STEP 2] Detecting audio language...")
    detected_lang = detect_audio_language(audio_path)
    is_urdu = detected_lang == "ur"

    # Initialise result containers
    urdu_transcript   = ""
    english_transcript = ""
    diarized_blocks   = []
    translated_blocks = []

    # ------------------------------------------------------------------ #
    # STEP 3 — Transcription  (two paths: Urdu  vs  English/other)
    # ------------------------------------------------------------------ #
    if is_urdu:
        # ── Urdu Path ──────────────────────────────────────────────────
        print("\n[STEP 3] Urdu audio detected.")

        deepgram_key = os.getenv("DEEPGRAM_API_KEY")

        if deepgram_key:
            # ── 3a. Deepgram (primary — full diarization in Urdu) ───────
            print("[+] Using Deepgram for Urdu transcription & speaker diarization...")
            dg_result = transcribe_with_deepgram(
                audio_path=audio_path,
                language="ur",
                model="nova-3",
                diarize=True,
                smart_format=True,
            )
            urdu_transcript = dg_result.get("text", "")
            diarized_blocks = dg_result.get("diarized_blocks", [])

            # ── 3b. Translate speaker blocks + full transcript to English ─
            print("\n[+] Translating speaker blocks to English...")
            translated_blocks = translate_speaker_blocks(diarized_blocks)

            print("[+] Translating full Urdu transcript to English...")
            english_transcript = (
                translate_urdu_to_english(urdu_transcript) if urdu_transcript else ""
            )

            # Build a clean English text from translated blocks as fallback
            if not english_transcript and translated_blocks:
                english_transcript = "\n\n".join(
                    f"{b['speaker']}: {b.get('english_text', b.get('text', ''))}"
                    for b in translated_blocks
                )

        else:
            # ── 3c. No Deepgram key — fallback to local Whisper ─────────
            print("[!] DEEPGRAM_API_KEY not found. Falling back to local Whisper...")
            chunks = process_audio(source, return_chunks=True)
            urdu_transcript = transcribe_all(chunks)

            print("[+] Translating Whisper Urdu transcript to English...")
            english_transcript = translate_urdu_to_english(urdu_transcript)

    else:
        # ── English / other language path ──────────────────────────────
        print(f"\n[STEP 3] Audio detected as '{detected_lang}' (non-Urdu).")
        print("[+] Transcribing with local Whisper (English mode)...")
        chunks = process_audio(source, return_chunks=True)
        english_transcript = transcribe_all(chunks)

    # ------------------------------------------------------------------ #
    # STEP 4 — Print transcript to console
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 52)
    print("  🗣️  TRANSCRIPT")
    print("=" * 52)

    if translated_blocks:
        for block in translated_blocks:
            spk      = block.get("speaker", "Speaker")
            eng_text = block.get("english_text", block.get("text", "")).strip()
            print(f"[{spk}]: {eng_text}\n")
    else:
        print(english_transcript or "No transcript available.")

    # ------------------------------------------------------------------ #
    # STEP 5 — Choose the best text for insight extraction
    # ------------------------------------------------------------------ #
    # Use the rich diarized English text when available so that the LLMs
    # get speaker context; fall back to raw Urdu if nothing else exists.
    if translated_blocks:
        insight_text = "\n\n".join(
            f"{b['speaker']}: {b.get('english_text', b.get('text', ''))}"
            for b in translated_blocks
        )
    elif english_transcript.strip():
        insight_text = english_transcript
    else:
        insight_text = urdu_transcript  # last resort

    if not insight_text.strip():
        print("\n[!] Transcript is empty — cannot extract insights.")
        return {
            "language": detected_lang,
            "is_urdu": is_urdu,
            "urdu_transcript": urdu_transcript,
            "english_transcript": english_transcript,
            "diarized_blocks": diarized_blocks,
            "translated_blocks": translated_blocks,
            "title": "",
            "summary": "",
            "action_items": "",
            "key_decisions": "",
            "questions": "",
            "rag_chain": None,
        }

    # ------------------------------------------------------------------ #
    # STEP 6 — Extract meaningful insights
    # ------------------------------------------------------------------ #
    print("\n[STEP 6] Extracting insights from transcript...")

    print("[+] Generating meeting title...")
    title = generate_title(insight_text)

    print("[+] Generating full meeting summary...")
    meeting_summary = summarize(insight_text)

    print("[+] Extracting action items...")
    action_items = extract_action_items(insight_text)

    print("[+] Extracting key decisions...")
    key_decisions = extract_key_decisions(insight_text)

    print("[+] Extracting unresolved questions / follow-ups...")
    questions = extract_questions(insight_text)

    # ------------------------------------------------------------------ #
    # STEP 7 — Print insights summary to console
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print(f"  📌  TITLE: {title}")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("  📋  SUMMARY")
    print("=" * 60)
    print(meeting_summary)

    print("\n" + "=" * 60)
    print("  ✅  ACTION ITEMS")
    print("=" * 60)
    print(action_items)

    print("\n" + "=" * 60)
    print("  🧠  KEY DECISIONS")
    print("=" * 60)
    print(key_decisions)

    print("\n" + "=" * 60)
    print("  ❓  UNRESOLVED QUESTIONS / FOLLOW-UPS")
    print("=" * 60)
    print(questions)

    print("\n" + "=" * 52)
    print("  🎉  PIPELINE COMPLETE!")
    print("=" * 52)

    # ------------------------------------------------------------------ #
    # STEP 8 — Return everything as a structured dictionary
    # ------------------------------------------------------------------ #
    return {
        # ── Raw transcripts ───────────────────────────────────────────
        "language"          : detected_lang,
        "is_urdu"           : is_urdu,
        "urdu_transcript"   : urdu_transcript,
        "english_transcript": english_transcript,

        # ── Speaker diarization (Urdu + Deepgram path only) ───────────
        "diarized_blocks"   : diarized_blocks,    # [{speaker, text}]
        "translated_blocks" : translated_blocks,  # [{speaker, text, english_text}]

        # ── AI-generated insights ─────────────────────────────────────
        "title"             : title,
        "summary"           : meeting_summary,
        "action_items"      : action_items,
        "key_decisions"     : key_decisions,
        "questions"         : questions,
    }


if __name__ == "__main__":
    print("=" * 52)
    print("  🎙️  VIDEO ASSISTANT — INTERACTIVE MODE  ")
    print("=" * 52)
    source = input("\nEnter YouTube URL or local file path: ").strip()
    if not source:
        print("[!] No input provided. Exiting.")
    else:
        result = run_pipeline(source)