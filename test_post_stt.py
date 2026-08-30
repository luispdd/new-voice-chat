import urllib.request
import urllib.error
import urllib.parse
from apps.backend.services.tts import text_to_wav_bytes

def run():
    wav = text_to_wav_bytes("Hello, this is a live test.")
    
    url = "http://localhost:8000/api/transcribe"
    import sys
    
    import mimetypes
    import uuid
    boundary = uuid.uuid4().hex
    headers = {'Content-type': f'multipart/form-data; boundary={boundary}'}
    
    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"audio\"; filename=\"mic.wav\"\r\n"
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode('utf-8') + wav + f"\r\n--{boundary}--\r\n".encode('utf-8')
    
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        response = urllib.request.urlopen(req)
        print("Response:", response.read().decode('utf-8'))
    except Exception as e:
        print("Error:", e)
        if hasattr(e, 'read'):
            print(e.read().decode('utf-8'))

run()
