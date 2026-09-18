# VoIP Engine Dashboard

A Python-based, fully functional VoIP application featuring an interactive Tkinter dashboard, adaptive jitter buffering, full-duplex communication, and network metric analysis.

## Features

- **Full-Duplex (Two-Way) Calling:** True bidirectional audio transmission over RTP.
- **Adaptive Jitter Buffer:** Implementation of Ramjee's algorithm to dynamically manage playout delays based on network conditions.
- **Packet Loss Concealment (PLC):** Basic PLC to fade out audio seamlessly when packets are dropped or delayed, reducing jarring clicks.
- **Mute Functionality:** Toggle your microphone mid-call without interrupting the RTP stream (sends silent packets to keep the connection alive).
- **SIP-style Signaling:** Handshake and tear-down logic using UDP over port 5060/5061.
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

## Usage

1. **Start the Application:**
   Run the dashboard:
   ```bash
   python app_ui.py
   ```

2. **Establish a Call:**
   - **Person A (Listener):** Clicks **"🎧 LISTEN (RECEIVER)"**. The application will wait for an incoming call.
   - **Person B (Caller):** Enters Person A's IP address into the Target IP field and clicks **"📞 CALL TARGET (SENDER)"**.
   
   Once established, both parties will be able to speak and hear each other simultaneously (Full-Duplex).

3. **Mute Microphone:**
   - Click **"🎤 MUTE"** to stop sending audio to the other party. Click **"🔇 UNMUTE"** to resume.

4. **End Call:**
   - Click **"🛑 END CALL"** to terminate the connection gracefully.

5. **View Metrics:**
   - After ending a call, click **"📊 SHOW DELAY GRAPH"** or **"📉 SHOW JITTER VARIANCE"** to analyze the network performance during that call.

## Troubleshooting

- **Audio not working:** Ensure your default microphone and speakers are properly set in your OS settings.
- **Connection failing:** Make sure ports `5060`, `5061` (SIP Signaling), and `5005` (RTP Media) are not blocked by your firewall.
