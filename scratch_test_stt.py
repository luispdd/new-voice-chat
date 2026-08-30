import asyncio
from apps.backend.services.stt import get_stt_model, transcribe_audio, audio_bytes_to_float32
import urllib.request
import os

print("Downloading sample audio...")
url = "https://www.wavsource.com/snds_2018-01-14_510641579458/test/test.wav"
urllib.request.urlretrieve(url, "test.wav")

with open("test.wav", "rb") as f:
    audio_bytes = f.read()

print("Transcribing...")
text = transcribe_audio(audio_bytes)
print(f"Result: {text}")
