import yt_dlp
from pydub import AudioSegment
import os

DOWNLOAD_DIR='downloads'
os.makedirs(DOWNLOAD_DIR,exist_ok=True)

# To capture the audio from a video url and convert to wav
def download_youtube_audio(url:str)->str:
    output_path=os.path.join(DOWNLOAD_DIR,"%(title)s.%(ext)s")  #Output path with Directory
    ydl_opts={ 
        "format":"bestaudio/best",
        "outtmpl":output_path,
        "postprocessors":[
            {
                "key":"FFmpegExtractAudio",
                "preferredcodec":"wav",
                "preferredquality":"192",
            }
        ],
        "quiet":True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info=ydl.extract_info(url,download=True)
        filename=ydl.prepare_filename(info).replace(".webm",".wav").replace(".m4a",".wav")
    return filename


data=download_youtube_audio("https://www.youtube.com/watch?v=ggNHDf18R1E")

# capture the audio but this time convert to mono-audio and also the frequency to 16khz which is ideal for whisper AI

def convert_to_wav(input_path:str)->str:
    """Convert any audio/video into wav format using pydub. """
    output_path=os.path.splitext(input_path)[0]+"_converted.wav"
    audio=AudioSegment.from_file(input_path) # Check the type of audio automatically whether its mp4 or mp3 or any other
    audio=audio.set_channels(1).set_frame_rate(16000) #Convert to mono audio and set frame-rate to 16kHz
    audio.export(output_path,format="wav")
    return output_path

data_wav=(convert_to_wav(data))

# Create Chunking
def chunk_audio(wav_path:str,chunk_minutes:int=10)->str:
    audio=AudioSegment.from_wav(wav_path)
    chunk_ms=chunk_minutes*60*1000
    chunks=[]
    for i,start in enumerate(range(0,len(audio),chunk_ms)):
        chunk=audio[start:start+chunk_ms]
        chunk_path=f"{wav_path}_chunk{i}.wav"
        chunk.export(chunk_path)
        chunks.append(chunk_path)
    return chunks

# Final Function to call all
def process_audio(url:str)->list:
    if url.startswith("http://") or url.startswith("https://"): #If youtube video
        wav_path=download_youtube_audio(url)
    else:                                                       # If local audio file
        wav_path=convert_to_wav(url) 

    chunks=chunk_audio(wav_path)
    return chunks