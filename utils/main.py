import sys
import os
# Ensure the project root (parent of utils/) is always on sys.path,
# regardless of where Python is invoked from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from utils.audio_processor import process_audio
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
    # STEP 3 — Transcription (Primary: Cloud API Deepgram / OpenAI, Fallback: Local Whisper)
    # ------------------------------------------------------------------ #
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")

    if deepgram_key:
        print(f"\n[STEP 3] Transcribing with Deepgram API (Language: '{detected_lang}')...")
        dg_result = transcribe_with_deepgram(
            audio_path=audio_path,
            language=detected_lang if detected_lang in ["ur", "en", "es", "fr", "de", "hi"] else "en",
            model="nova-3",
            diarize=True,
            smart_format=True,
        )

        if is_urdu:
            urdu_transcript = dg_result.get("text", "")
            diarized_blocks = dg_result.get("diarized_blocks", [])

            print("\n[+] Translating Urdu speaker blocks to English...")
            translated_blocks = translate_speaker_blocks(diarized_blocks)

            print("[+] Translating full Urdu transcript to English...")
            english_transcript = (
                translate_urdu_to_english(urdu_transcript) if urdu_transcript else ""
            )

            if not english_transcript and translated_blocks:
                english_transcript = "\n\n".join(
                    f"{b['speaker']}: {b.get('english_text', b.get('text', ''))}"
                    for b in translated_blocks
                )
        else:
            english_transcript = dg_result.get("text", "")
            diarized_blocks = dg_result.get("diarized_blocks", [])
            translated_blocks = [
                {"speaker": b["speaker"], "text": b["text"], "english_text": b["text"]}
                for b in diarized_blocks
            ]
    else:
        # Fallback to local Whisper if no Deepgram key is set
        print(f"\n[STEP 3] No DEEPGRAM_API_KEY set. Falling back to local Whisper (Language: '{detected_lang}')...")
        chunks = process_audio(source, return_chunks=True)
        if is_urdu:
            urdu_transcript = transcribe_all(chunks)
            print("[+] Translating Whisper Urdu transcript to English...")
            english_transcript = translate_urdu_to_english(urdu_transcript)
        else:
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
    # STEP 7 — Build Vector Store & RAG Chain
    # ------------------------------------------------------------------ #
    print("\n[STEP 7] Building Vector Store & RAG Chain for Q&A...")
    rag_chain = None
    try:
        rag_chain = build_rag_chain(insight_text)
        print("[+] RAG Chain successfully initialized!")
    except Exception as e:
        print(f"[!] Error building RAG chain: {e}")

    # ------------------------------------------------------------------ #
    # STEP 8 — Print insights summary to console
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
    # STEP 9 — Return everything as a structured dictionary
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
        "rag_chain"         : rag_chain,
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
        rag_chain = result.get("rag_chain")

        if rag_chain:
            print("\n" + "=" * 60)
            print("  💬  INTERACTIVE RAG CHAT")
            print("  Ask any questions about the video! (Type 'exit' to quit)")
            print("=" * 60)
            while True:
                user_query = input("\n[Q]: ").strip()
                if not user_query or user_query.lower() in ["exit", "quit", "q"]:
                    print("\n[+] Exiting Interactive Chat. Goodbye!")
                    break
                print("\n[Searching transcript & generating answer...]")
                try:
                    get_question(rag_chain, user_query)
                except Exception as err:
                    print(f"[!] Error processing question: {err}")