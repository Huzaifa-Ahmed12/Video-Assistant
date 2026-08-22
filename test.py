import os
from utils.audio_processor import process_audio
from core.transcriber import transcribe_with_deepgram, DeepgramProvider, transcribe_all
from core.translator import translate_urdu_to_english, translate_speaker_blocks


def save_transcript_html(
    speaker_blocks: list,
    raw_english: str = "",
    output_file: str = "transcription.html"
):
    """Save transcript output into a beautifully styled HTML page containing ONLY English transcripts."""
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"[+] Cleared previous '{output_file}'.")

    if os.path.exists("transcription.txt"):
        os.remove("transcription.txt")

    cards_html = ""
    if speaker_blocks:
        for block in speaker_blocks:
            spk = block.get("speaker", "Speaker")
            e_text = block.get("english_text", "").strip()

            if not e_text:
                continue

            cards_html += f"""
            <div class="speaker-card">
                <div class="speaker-badge">🗣️ {spk}</div>
                <div class="transcript-text-english" dir="ltr">{e_text}</div>
            </div>
            """
    else:
        cards_html = f"""
        <div class="speaker-card">
            <div class="speaker-badge">🗣️ Transcript</div>
            <div class="transcript-text-english" dir="ltr">{raw_english}</div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Assistant - English Transcript</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --primary-gradient: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --speaker-badge-bg: rgba(99, 102, 241, 0.15);
            --speaker-badge-border: rgba(99, 102, 241, 0.3);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(at 20% 20%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 80% 80%, rgba(168, 85, 247, 0.15) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            min-height: 100vh;
            padding: 2.5rem 1rem;
            line-height: 1.8;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--card-border);
        }}

        .header-title {{
            font-size: 2.2rem;
            font-weight: 700;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        .header-subtitle {{
            color: var(--text-muted);
            font-size: 0.95rem;
        }}

        .section-header {{
            font-size: 1.3rem;
            font-weight: 600;
            margin: 2rem 0 1rem 0;
            color: #cbd5e1;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .speaker-card {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }}

        .speaker-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(99, 102, 241, 0.4);
        }}

        .speaker-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            background: var(--speaker-badge-bg);
            border: 1px solid var(--speaker-badge-border);
            color: #a5b4fc;
            padding: 0.3rem 0.85rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 0.85rem;
        }}

        .transcript-text-english {{
            font-size: 1.1rem;
            color: #f1f5f9;
            white-space: pre-wrap;
            word-wrap: break-word;
            text-align: left;
            direction: ltr;
            line-height: 1.8;
        }}

        .raw-box {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.5rem;
            font-size: 1.05rem;
            color: #cbd5e1;
            white-space: pre-wrap;
            line-height: 2.0;
            direction: ltr;
            text-align: left;
        }}

        footer {{
            text-align: center;
            margin-top: 3rem;
            color: var(--text-muted);
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1 class="header-title">🎙️ Video Assistant Transcript</h1>
            <p class="header-subtitle">English Speaker Diarization & Audio Processing Output</p>
        </header>

        <h2 class="section-header">🗣️ Speaker-Attributed English Transcript</h2>
        <div class="diarized-section">
            {cards_html}
        </div>

        <h2 class="section-header">📝 Full Raw English Transcript</h2>
        <div class="raw-box" dir="ltr">
            {raw_english if raw_english else "Translation unavailable."}
        </div>

        <footer>
            Generated automatically by Video Assistant
        </footer>
    </div>
</body>
</html>"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"\n[+] Output successfully saved to HTML file: '{output_file}'!")


if __name__ == "__main__":
    # Supports YouTube URL or local file path (e.g., 'downloads/meeting.wav')
    source = "https://www.youtube.com/watch?v=6yQ-l5iBitQ"
    
    print("=== Starting Video Assistant Audio Processing ===")
    audio_path = process_audio(source, return_chunks=False)
    
    print("\n=== Starting Deepgram Transcription (Urdu + Utterance Diarization) ===")
    
    if os.getenv("DEEPGRAM_API_KEY"):
        result = transcribe_with_deepgram(
            audio_path=audio_path,
            language="ur",
            model="nova-3",
            diarize=True,
            smart_format=True
        )
        
        urdu_raw = result.get("text", "")
        diarized_blocks = result.get("diarized_blocks", [])

        # --- English Translation Step (1-to-1 Per Speaker) ---
        print("\n=== Starting English Translation (Per Speaker Turn) ===")
        translated_blocks = translate_speaker_blocks(diarized_blocks)
        english_raw = translate_urdu_to_english(urdu_raw) if urdu_raw else ""
        
        # Save output to transcription.html with ONLY English transcripts
        save_transcript_html(
            speaker_blocks=translated_blocks,
            raw_english=english_raw,
            output_file="transcription.html"
        )

    else:
        print("[!] DEEPGRAM_API_KEY not found in environment. Falling back to local Whisper...")
        chunks = process_audio(source, return_chunks=True)
        transcript = transcribe_all(chunks)        
        
        english_raw = translate_urdu_to_english(transcript)

        save_transcript_html(
            speaker_blocks=[],
            raw_english=english_raw,
            output_file="transcription.html"
        )
