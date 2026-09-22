# ACN Micro Project: P2P VoIP Application

A fully functional, peer-to-peer VoIP (Voice over IP) application written in Python. This application allows two computers on the same network to establish a direct, full-duplex audio call using SIP for signaling and RTP over UDP for audio transmission.

## Features & Architecture

* **Full-Duplex Audio**: Both devices can talk and listen simultaneously, exactly like a real phone call.
* **SIP Signaling**: Uses a custom implementation of the Session Initiation Protocol (SIP) on ports 5060 and 5061 to "ring" the other device and negotiate the connection.
* **Symmetric Connection Logic**: Both devices aggressively call each other simultaneously. The application acts as a referee to seamlessly elect one as the "Caller" and one as the "Receiver" to establish the connection instantly without conflicts.
* **RTP Streaming**: Audio is captured, chunked into 20ms frames, compressed using `zlib`, and streamed over UDP port 5005 using the Real-time Transport Protocol (RTP).
* **Adaptive Jitter Buffer**: A custom jitter buffer dynamically handles packet delays, reorders out-of-order packets, and smooths out internet latency for clear audio playback.
* **Failsafe Audio Driver**: Includes robust error handling to gracefully send silent packets if the microphone is abruptly disconnected or blocked by the operating system, preventing catastrophic application crashes.

## Project Structure

The codebase is highly optimized, modular, and DRY (Don't Repeat Yourself):
* `app_ui.py`: The Tkinter graphical user interface. 
* `p2p_session.py`: The master controller. Wires the SIP signaling and RTP threads together.
* `sip_signaling.py`: Handles the SIP handshakes (`INVITE`, `200 OK`, `ACK`, `BYE`).
* `sender.py`: A single-purpose module that manages the microphone recording and UDP transmission threads.
* `receiver.py`: A single-purpose module that manages incoming UDP packets, the Adaptive Jitter Buffer, and the audio playout thread.
* `audio_config.py`: Centralized audio configuration (Sample Rate, Chunk Size, Channels).
* `rtp_helper.py`: Utilities for packing and unpacking raw RTP byte headers.

---

## How to Use It

1. **Install Dependencies**: Ensure you have Python installed, then install the required libraries:
   ```bash
   pip install sounddevice numpy
   ```
2. **Launch the Application**: Run the application on **both** computers (Device A and Device B):
   ```bash
   python app_ui.py
   ```
3. **Connect**:
   - On **Device A**, type the IP address of Device B into the UI and click "Connect".
   - On **Device B**, type the IP address of Device A into the UI and click "Connect".
   - The application will instantly negotiate the collision, establish the SIP session, and begin streaming bidirectional RTP audio!

---

## Recent Fixes & Optimizations

This project recently underwent a major overhaul to make it production-ready and highly resilient:

1. **Microphone Failsafe (Anti-Crash)**: 
   Previously, if Windows blocked microphone access (or if the microphone was unplugged mid-call), the PortAudio driver would crash the entire application. The `sender.py` now wraps the microphone stream in a robust `try/except` block. If the microphone fails, it gracefully intercepts the crash and sends "silent" audio packets instead, keeping the connection alive.
2. **Early Socket Binding (NAT/Firewall Resilience)**: 
   Previously, the RTP UDP socket wasn't opened until *after* the SIP handshake finished. Because both computers process the handshake at slightly different speeds, one computer would often send audio before the other had opened its port, resulting in an `ICMP Port Unreachable` (WinError 10054) crash. The socket binding was moved to the very start of the session to guarantee the port is always open and ready for early packets.
3. **Dead Code & Duplication Removal**: 
   Over 130 lines of dead boilerplate code (`start_sender` and `start_receiver`) were completely removed. All hardcoded audio constants were extracted into a single, centralized `audio_config.py` file.
4. **Jitter Buffer Timestamp Overflow Fix**: 
   Fixed a critical bug in `jitter_buffer.py` where 32-bit millisecond timestamps would cause the application to crash or drop packets when the system uptime wrapped around the 32-bit integer limit.

---

## Troubleshooting Guide

If the call connects but you experience issues, the Python code is functioning correctly, but your operating system is blocking the data. Run through this checklist:

### 1. One-Way Audio (or Dead Silence)
**Symptom**: The call connects, but you can only hear one person (or neither). The terminal shows packets are being sent/received, but there is no sound.
**Cause**: The Windows Operating System is aggressively blocking Python from accessing your microphone for "Privacy" reasons.
**The Fix**: 
1. On the computer whose voice cannot be heard, open Windows **Settings**.
2. Go to **Privacy & Security** > **Microphone**.
3. Ensure **"Microphone access"** is toggled ON.
4. Scroll to the very bottom and ensure **"Let desktop apps access your microphone"** is toggled ON (Python runs as a desktop app).

### 2. Stuck on "Initiating Call..." (Does not connect)
**Symptom**: You click connect, but the SIP handshake never finishes. 
**Cause**: The Windows Defender Firewall is blocking the inbound UDP packets on ports 5060/5061.
**The Fix**:
1. Click the Windows Start Menu, type "Allow an app through Windows Firewall", and hit Enter.
2. Click "Change Settings".
3. Scroll down the list, find `python.exe` (and/or `py.exe`), and ensure the checkboxes for **both "Private" and "Public"** networks are checked. Click OK.

### 3. Immediate "WinError 10054" Crash
**Symptom**: As soon as the call connects, the terminal crashes with "An existing connection was forcibly closed by the remote host".
**Cause**: A Router, NAT, or VPN is rewriting your network packets and refusing the connection.
**The Fix**:
1. Turn off any VPNs on both computers.
2. Ensure both computers are connected to the exact same Wi-Fi network.
3. Ensure you are not on a highly restrictive "Guest" network (like a hotel or university) that actively blocks peer-to-peer device communication.
