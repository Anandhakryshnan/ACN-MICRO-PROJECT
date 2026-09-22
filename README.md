# Spectra Voice - VoIP Engine Dashboard

A Python-based, fully functional Symmetric Peer-to-Peer VoIP application featuring a modern graphical dashboard, adaptive jitter buffering, full-duplex communication, and network metric analysis.

## Features

- **Symmetric P2P Connection:** Seamlessly connect without needing to configure host/client roles. Just click **CONNECT** on both devices and the software will dynamically negotiate the handshake.
- **Full-Duplex Audio:** True bidirectional audio transmission over RTP using `sounddevice`.
- **4x Digital Audio Gain:** Automatically amplifies incoming audio packets to fix quiet laptop microphones while preventing digital clipping/distortion.
- **Hardware-Adaptive Buffering:** Negotiates the safest audio latency buffer dynamically with your OS to prevent driver crashes.
- **Adaptive Jitter Buffer:** Implementation of Ramjee's algorithm to dynamically manage playout delays based on network conditions.
- **Packet Loss Concealment (PLC):** Basic PLC to fade out audio seamlessly when packets are dropped or delayed, reducing jarring clicks.
- **Bi-directional Disconnects:** Click "End Call" on either device, and it will gracefully send a `BYE` command to tear down the connection symmetrically.
- **Live Diagnostics:** Track real-time network health with a live "Packets Received" counter.
- **Metrics Dashboard:** Generates beautiful Matplotlib graphs (Delay & Jitter Variance) after calls.

## Requirements

Ensure you have Python 3 installed. Install the dependencies using `pip`:

```bash
pip install -r requirements.txt
```

### Dependencies Include:
- `sounddevice` (Audio Capture & Playback)
- `matplotlib` (Graphing)
- `pandas` (Data manipulation)
- `numpy` (Audio manipulation)

## Usage

1. **Start the Application:**
   Run the dashboard:
   ```bash
   python app_ui.py
   ```

2. **Establish a Call:**
   - Both Person A and Person B type each other's IP address into the Target IP field.
   - Click **"🚀 CONNECT"**.
   - The application will automatically negotiate the roles, bypass the network firewall, and establish a high-quality two-way audio stream.

3. **Mute Microphone:**
   - Click **"🎤 MUTE"** to stop sending audio to the other party. Click **"🔇 UNMUTE"** to resume.

4. **End Call:**
   - Click **"🛑 END CALL"** on either laptop to terminate the connection gracefully for both parties.

5. **View Metrics:**
   - After ending a call, click **"📊 SHOW DELAY GRAPH"** or **"📉 SHOW JITTER VARIANCE"** to analyze the network performance during that call.

## Troubleshooting

- **Audio not working (No Packets):** Check the "Packets Received" counter. If it is 0, ensure your firewall isn't blocking UDP Port 5005.
- **Connection failing:** Make sure ports `5060`, `5061` (SIP Signaling), and `5005` (RTP Media) are not blocked.
