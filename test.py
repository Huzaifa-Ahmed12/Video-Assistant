import os
from utils.audio_processor import process_audio
from core.transcriber import transcribe_with_deepgram, transcribe_all, detect_audio_language
from core.translator import translate_urdu_to_english, translate_speaker_blocks
from core.summarize import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions


def run_pipeline(source: str):
    print("==================================================")
    print(" 🎙️  STARTING VIDEO ASSISTANT PROCESSING  ")
    print("==================================================")
    print(f"[+] Processing source: {source}")
    
    # 1. Extract / prepare audio file
    audio_path = process_audio(source, return_chunks=False)
    
    # 2. Detect audio language (Urdu vs English / others)
    detected_lang = detect_audio_language(audio_path)
    is_urdu = (detected_lang == "ur")
    
    urdu_raw = ""
    english_raw = ""
    translated_blocks = []
    
    # 3. Transcribe & Translate conditionally based on detected language
    if is_urdu:
        print("\n[+] Urdu audio detected! Processing with Deepgram (Urdu) + Translation pipeline...")
        if os.getenv("DEEPGRAM_API_KEY"):
            print("[+] Using Deepgram for Urdu transcription & Utterance Diarization...")
            result = transcribe_with_deepgram(
                audio_path=audio_path,
                language="ur",
                model="nova-3",
                diarize=True,
                smart_format=True
            )
            urdu_raw = result.get("text", "")
            diarized_blocks = result.get("diarized_blocks", [])

            print("\n[+] Translating Urdu transcript & speaker turns to English...")
            translated_blocks = translate_speaker_blocks(diarized_blocks)
            english_raw = translate_urdu_to_english(urdu_raw) if urdu_raw else ""
        else:
            print("\n[!] DEEPGRAM_API_KEY not found in environment. Falling back to local Whisper...")
            chunks = process_audio(source, return_chunks=True)
            urdu_raw = transcribe_all(chunks)
            print("\n[+] Translating Whisper transcript to English...")
            english_raw = translate_urdu_to_english(urdu_raw)
    else:
        print(f"\n[+] Audio detected as '{detected_lang}' (English / Non-Urdu). Skipping Deepgram & Urdu translation completely!")
        print("[+] Processing directly with local Whisper transcription...")
        chunks = process_audio(source, return_chunks=True)
        english_raw = transcribe_all(chunks)

    # 3. Print English Transcriptions to Console
    print("\n" + "="*50)
    print(" 🗣️ SPEAKER-ATTRIBUTED / FULL ENGLISH TRANSCRIPT")
    print("="*50)
    if translated_blocks:
        for block in translated_blocks:
            spk = block.get("speaker", "Speaker")
            eng_text = block.get("english_text", block.get("text", "")).strip()
            print(f"[{spk}]: {eng_text}\n")
    else:
        print(english_raw if english_raw else "No English transcript available.")


    # 4. Generate Title, Summary, and Extractions
    target_text = english_raw if english_raw.strip() else urdu_raw

    if not target_text.strip():
        print("\n[!] Error: Transcript is empty. Cannot perform summary or extraction.")
        return

    print("\n[+] Generating Meeting Title...")
    title = generate_title(target_text)

    print("[+] Generating Full Meeting Summary...")
    meeting_summary = summarize(target_text)

    print("[+] Extracting Action Items...")
    action_items = extract_action_items(target_text)

    print("[+] Extracting Key Decisions...")
    key_decisions = extract_key_decisions(target_text)

    print("[+] Extracting Unresolved Questions...")
    questions = extract_questions(target_text)

    # 5. Output Summary & Extractions to Console
    print("\n" + "="*60)
    print(f" 📌 MEETING TITLE: {title}")
    print("="*60)

    print("\n" + "="*60)
    print(" 📋 SUMMARY")
    print("="*60)
    print(meeting_summary)

    print("\n" + "="*60)
    print(" ✅ ACTION ITEMS")
    print("="*60)
    print(action_items)

    print("\n" + "="*60)
    print(" 🧠 KEY DECISIONS")
    print("="*60)
    print(key_decisions)

    print("\n" + "="*60)
    print(" ❓ UNRESOLVED QUESTIONS / FOLLOW-UPS")
    print("="*60)
    print(questions)

    print("\n==================================================")
    print(" 🎉 PROCESSING COMPLETE!")
    print("==================================================")


if __name__ == "__main__":
    source_link = "https://www.youtube.com/watch?v=rBlCOLfMYfw&t=16s"
    run_pipeline(source_link)
