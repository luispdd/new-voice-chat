# ADR 004: Secure Context & Local SSL Certificates for Web Audio

## Context
Browser security specifications require a Secure Context (`https://` or `localhost`) for `navigator.mediaDevices.getUserMedia` to access the microphone. Accessing the voice companion from mobile devices or LAN computers over plain `http://` results in microphone permission errors.

## Decision
- Generate local self-signed RSA certificates (`cert.pem`, `key.pem`) for `localhost` and local network addresses.
- Configure both FastAPI (port 8000) and Angular dev server (port 4200) to serve over HTTPS using these certificates.

## Consequences
- Unlocks microphone and Web Audio recording across all devices on the local network (phones, tablets, laptops).
