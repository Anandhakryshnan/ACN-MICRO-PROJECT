# ACN Micro Project: P2P VoIP Application

Welcome to the **ACN Micro Project**, a fully functional, peer-to-peer VoIP (Voice over IP) application written entirely in Python. 

This application allows two computers on the same Local Area Network (LAN) or Wi-Fi to establish a direct, full-duplex audio call. It is designed to act exactly like a traditional phone call, where both parties can speak and listen simultaneously with low latency.

---

## 🚀 What Is Working (Features)

* **Full-Duplex Bidirectional Audio**: Both users can talk and listen at the exact same time without waiting for the other person to finish.
* **SIP Signaling (Session Initiation Protocol)**: The app uses a custom, lightweight SIP implementation to "ring" the other device and negotiate the connection before opening the audio streams.
* **Symmetric Call Negotiation**: If both users attempt to call each other at the exact same time, the application acts as a referee. It automatically resolves the collision, forcing one device to act as the "Caller" and the other as the "Receiver" so the call connects instantly.
* **RTP Streaming (Real-time Transport Protocol)**: Audio is captured in real-time, compressed, and streamed over UDP port 5005 for maximum speed and minimal latency.
* **Adaptive Jitter Buffer**: A custom jitter buffer dynamically handles network lag. If packets arrive out of order or are delayed by the Wi-Fi, the buffer reorders them and smooths out the playback to ensure clear, uninterrupted audio.
* **Anti-Crash Microphone Failsafe**: If a user's microphone is suddenly unplugged or blocked by Windows Privacy Settings, the application gracefully intercepts the hardware error and transmits "silent" packets instead of crashing.
* **Tkinter GUI Dashboard**: A clean, user-friendly graphical interface to view the connection status and input the target IP address.

---

## 🧠 How It Works Behind the Scenes

A standard phone call in this application operates in two distinct phases running simultaneously:

### 1. The "Dialing" Phase (SIP Signaling)
When you click "Connect", your device spins up a **SIP Client** on port 5061 and sends an `INVITE` message to the other device's IP address on port 5060. 
* The other device's **SIP Server** receives the `INVITE` and responds with a `200 OK` message.
* Your device acknowledges this with an `ACK` message. 
* Once the handshake is complete, the SIP signaling stops, and the application transitions into the "In-Call" state.

### 2. The "Talking" Phase (RTP Audio Streaming)
Immediately after the SIP handshake, the application spins up three separate background threads on **both** computers:
1. **The Sender Thread (`sender.py`)**: Continuously records your microphone, chops the raw audio into tiny 20-millisecond chunks, compresses them using `zlib`, wraps them in an RTP header (containing a sequence number and timestamp), and fires them across the Wi-Fi via UDP.
2. **The Receiver Thread (`receiver.py`)**: Constantly listens on UDP port 5005. As RTP packets arrive from the network, it decompresses them and pushes them into the Adaptive Jitter Buffer.
3. **The Playout Thread (`receiver.py`)**: Pulls the smoothed-out, chronologically ordered audio chunks from the jitter buffer and feeds them directly into your speakers.

Because these threads run entirely independently of each other on both computers, you get a seamless, full-duplex phone call.

---

## 🛠️ Prerequisites & Setup (Before Running)

Before you can run this project on two devices, you must ensure the following requirements are met:

1. **Python Installation**: Both computers must have Python 3.8+ installed.
2. **Required Libraries**: You must install the external audio processing libraries. Open your terminal or command prompt and run:
   ```bash
   pip install sounddevice numpy
   ```
3. **Network Connection**: Both computers must be connected to the **exact same Wi-Fi network** or LAN. (Note: Highly restrictive "Guest" networks at hotels or universities often block peer-to-peer traffic).
4. **IP Addresses**: You need to know the IPv4 address of both computers. 
   * On Windows, open Command Prompt and type `ipconfig`. Look for the "IPv4 Address" under your Wi-Fi adapter (e.g., `10.203.43.99`).

---

## 🏃 How to Run the Project

1. Clone or copy this entire project folder onto **Device A** and **Device B**.
2. On **Device A**, open a terminal in the project folder and run:
   ```bash
   python app_ui.py
   ```
3. On **Device B**, open a terminal in the project folder and run:
   ```bash
   python app_ui.py
   ```
4. On **Device A's** dashboard, type the IP address of Device B and click "Connect".
5. On **Device B's** dashboard, type the IP address of Device A and click "Connect".
6. The UI will update to say "In-Call", and you can begin talking!

---

## 🏗️ Project Structure

The codebase is highly optimized, modular, and DRY (Don't Repeat Yourself):
* `app_ui.py`: The main entry point. Renders the Tkinter graphical user interface. 
* `p2p_session.py`: The master controller. Wires the SIP signaling and RTP threads together.
* `sip_signaling.py`: Handles the SIP handshakes (`INVITE`, `200 OK`, `ACK`, `BYE`).
* `sender.py`: A single-purpose module that manages the microphone recording and UDP transmission threads.
* `receiver.py`: A single-purpose module that manages incoming UDP packets, the Adaptive Jitter Buffer, and the audio playout thread.
* `audio_config.py`: Centralized audio configuration (Sample Rate, Chunk Size, Channels).
* `rtp_helper.py`: Utilities for packing and unpacking raw RTP byte headers.
* `jitter_buffer.py`: The mathematical logic for sorting delayed packets.

---

## 🚨 Complete Troubleshooting Guide

If the call connects but you experience issues, the Python code is functioning correctly, but your operating system is blocking the audio hardware or network traffic. Run through this definitive checklist to solve any issue:

### 1. One-Way Audio (or Dead Silence)
**Symptom**: The call connects (the UI says "In-Call"), but you can only hear one person (or neither). The terminal shows packets are being sent/received, but there is no sound coming out.
**Cause**: The Windows Operating System is aggressively blocking Python from accessing your microphone for "Privacy" reasons. Because of our anti-crash failsafe, Python will send "silent" packets instead of crashing, resulting in one-way audio.
**The Fix**: 
1. On the computer whose voice *cannot* be heard, open Windows **Settings**.
2. Go to **Privacy & Security** > **Microphone**.
3. Ensure **"Microphone access"** is toggled **ON**.
4. Scroll to the very bottom of the page and ensure **"Let desktop apps access your microphone"** is toggled **ON**. (Python runs as a desktop app and is blocked by default!).
5. Finally, go to **Settings > System > Sound**, check that the correct physical microphone is selected as your default Input device, and ensure it is not physically muted on your headset.

### 2. Stuck on "Initiating Call..." (Does Not Connect)
**Symptom**: You click connect, but the SIP handshake never finishes, and the UI never switches to "In-Call".
**Cause**: The Windows Defender Firewall is aggressively blocking the inbound UDP SIP packets on ports 5060/5061.
**The Fix**:
1. Click the Windows Start Menu, type "Allow an app through Windows Firewall", and hit Enter.
2. Click the "Change Settings" button at the top (requires administrator privileges).
3. Scroll down the list until you find `python.exe` (and/or `py.exe`). 
4. Ensure the checkboxes for **both "Private" and "Public"** networks are checked next to Python. Click OK and restart the app.

### 3. Immediate "WinError 10054" Crash
**Symptom**: As soon as the call connects, the terminal crashes with `[WinError 10054] An existing connection was forcibly closed by the remote host`.
**Cause**: A Router, NAT, or VPN is actively inspecting your network packets and forcibly rejecting the UDP connection.
**The Fix**:
1. Turn off any VPNs (like NordVPN, ExpressVPN, or corporate work VPNs) on both computers.
2. Ensure you are not on a highly restrictive "Guest" network (like a hotel, airport, or university Wi-Fi) that is configured to block peer-to-peer device communication. You may need to use a personal mobile hotspot to test it.

### 4. Audio is Choppy or Distorted
**Symptom**: You can hear the other person, but they sound like a robot or the audio cuts in and out.
**Cause**: Your Wi-Fi network is experiencing heavy packet loss or extreme latency spikes, causing the jitter buffer to drop frames.
**The Fix**: Move closer to your Wi-Fi router, disconnect other devices that might be downloading large files, or switch to a wired Ethernet connection.
