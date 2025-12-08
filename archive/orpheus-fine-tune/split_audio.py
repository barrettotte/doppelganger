import csv
import os
import shutil
from pathlib import Path

from faster_whisper import WhisperModel
from pydub import AudioSegment
from tqdm import tqdm

TRAINING_DIR = Path(__file__).parent.parent / "training"
CHARACTER = "test_character"

INPUT_AUDIO_FILE =  TRAINING_DIR / CHARACTER / "sample.wav"
OUTPUT_CLIPS_DIR = TRAINING_DIR / CHARACTER / "train"
OUTPUT_METADATA_FILE = OUTPUT_CLIPS_DIR / "metadata.csv"

WHISPER_MODEL = "medium.en" 

TARGET_CHUNK_SEC = 10.0
MIN_CHUNK_SEC = 2.0 
MAX_CHUNK_SEC = 15.0
SILENCE_BETWEEN_SEGMENTS_MS = 150 

VAD_PARAMS = dict(
    min_silence_duration_ms=500,
    min_speech_duration_ms=250,
    speech_pad_ms=400,
)

def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.{ms:03}"

def main():
    OUTPUT_CLIPS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading Whisper model '{WHISPER_MODEL}'...")
    model = WhisperModel(WHISPER_MODEL, device="auto", compute_type="float16")

    if not INPUT_AUDIO_FILE.exists():
        print(f"ERROR: Input file not found at: {INPUT_AUDIO_FILE.absolute()}")
        exit(1)

    if OUTPUT_CLIPS_DIR.exists() and OUTPUT_CLIPS_DIR.is_dir():
        shutil.rmtree(OUTPUT_CLIPS_DIR)
        print(f"Cleared existing dataset at {OUTPUT_CLIPS_DIR}")
    
    os.makedirs(OUTPUT_CLIPS_DIR, exist_ok=True)

    print(f"Loading audio file: {INPUT_AUDIO_FILE}")
    try:
        original_audio = AudioSegment.from_file(INPUT_AUDIO_FILE)
    
        original_frame_rate = original_audio.frame_rate
        print(f"Original Sample Rate: {original_frame_rate}Hz. Keeping this for export.")

    except Exception as e:
        print(f"Error loading audio file: {e}")
        exit(2)

    print("Transcribing and segmenting...")
    segments, info = model.transcribe(
        str(INPUT_AUDIO_FILE),
        beam_size=5,
        vad_filter=True,
        vad_parameters=VAD_PARAMS,
        word_timestamps=True,
    )

    clip_count = 0
    total_duration = 0

    with open(OUTPUT_METADATA_FILE, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["audio_file", "text"])

        all_segments = list(segments)
        print(f"Found {len(all_segments)} total segments.")

        current_chunk_segments = []
        
        spacer_silence = AudioSegment.silent(duration=SILENCE_BETWEEN_SEGMENTS_MS, frame_rate=original_frame_rate)

        for i, segment in enumerate(tqdm(all_segments, unit="segment")):
            text = segment.text.strip()
            if not text or text.startswith("[") or text == "...":
                continue

            current_chunk_segments.append(segment)
            
            current_duration_sec = sum([(s.end - s.start) for s in current_chunk_segments])
            is_last_segment = (i == len(all_segments) - 1)

            if (current_duration_sec >= TARGET_CHUNK_SEC) or is_last_segment:
                
                if current_duration_sec < MIN_CHUNK_SEC and not is_last_segment:
                    continue 

                full_text = " ".join([s.text.strip() for s in current_chunk_segments])
                
                combined_audio = AudioSegment.empty()
                for seg in current_chunk_segments:
                    start_ms = int(seg.start * 1000)
                    end_ms = int(seg.end * 1000)
                    seg_audio = original_audio[start_ms:end_ms]
                    combined_audio += seg_audio + spacer_silence

                try:
                    clip_count += 1
                    clip_name = f"sample_{clip_count:06d}.wav"
                    
                    combined_audio.set_frame_rate(original_frame_rate).set_channels(1).export(
                        OUTPUT_CLIPS_DIR / clip_name, 
                        format="wav"
                    )
                    csv_writer.writerow([clip_name, full_text])
                    total_duration += (len(combined_audio) / 1000.0)

                except Exception as e:
                    print(f"Error exporting clip: {e}")

                current_chunk_segments = []

    print(f"Successfully exported {clip_count} clips at {original_frame_rate}Hz")

if __name__ == '__main__': 
    main()
