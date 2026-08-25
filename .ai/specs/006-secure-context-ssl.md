# Spec 006: Secure Context & SSL Configuration for Web Audio

## Status: Implemented & Verified

## Overview
Web browsers mandate a Secure Context (`https://` or `localhost`) to grant microphone access (`navigator.mediaDevices.getUserMedia`). This spec defines local SSL certificate generation and HTTPS configuration across backend and frontend dev servers.

## Requirements
1. **Certificate Generation**:
   - Generate local RSA 2048-bit self-signed certificate pair: `cert.pem` and `key.pem` valid for `localhost` and local IP addresses.
   - Command: `openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"`.
2. **Backend Server SSL**:
   - Uvicorn server configured with `--ssl-certfile cert.pem --ssl-keyfile key.pem` on port 8000.
3. **Frontend Server SSL**:
   - Angular dev server in `apps/frontend/project.json` configured with `ssl: true`, `sslCert: "cert.pem"`, `sslKey: "key.pem"` on port 4200.
4. **LAN Mobile / Tablet Access**:
   - Allows phones, tablets, and other computers on the local network to open `https://<LAN_IP>:4200` and speak through the microphone.
