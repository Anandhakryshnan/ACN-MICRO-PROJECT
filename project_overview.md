# ACN Micro Project: Spectra Voice - Zero-Latency P2P Matrix

This document provides a highly detailed, comprehensive overview of the Spectra Voice P2P VoIP application. It is designed to be the definitive technical guide for campus presentations, explaining the exact logic, algorithms, and engineering decisions implemented in every module of the project.

---

## 1. System Architecture: The Peer-to-Peer Model

Unlike traditional VoIP applications (like Discord or Skype) that act as a middleman by routing audio through a centralized server, this application uses a pure **Peer-to-Peer (P2P)** architecture. 

In this model, two endpoints (computers) communicate directly with each other over the Local Area Network (LAN) or Wi-Fi. This completely eliminates server processing latency, resulting in true zero-latency audio transmission.

The system is logically split into two completely separate sub-systems that run sequentially:
1. **The Signaling Plane (SIP over UDP):** Responsible for locating the peer, ringing them, resolving call collisions, and establishing the session parameters before any audio is sent.
2. **The Media Plane (RTP over UDP):** Responsible for the real-time capture, compression, packetization, and transmission of raw audio data, as well as handling network unreliability via Jitter Buffering.

---

## 2. In-Depth Module Breakdown

Below is a detailed explanation of every file and how it operates in the ecosystem.

### 2.1. User Interface (`app_ui.py`)
The application starts here. The UI is built using Python's standard `tkinter` library, but heavily customized for a modern aesthetic.
* **Animated Canvas:** It uses an infinite recursive loop (`animate_bg()`) updating canvas coordinates to create a floating particle effect in the background, making the UI feel alive.
* **Thread Safety:** The Tkinter `mainloop()` must run on the main thread and blocks it. Therefore, all networking and audio logic are spawned on background `daemon=True` threads. To prevent the background threads from crashing the UI when they need to update the screen (e.g., changing status to "In-Call"), we use thread-safe lambda functions scheduled via `root.after(0, ...)`.
* **State Management:** It uses `threading.Event()` objects (`stop_event` and `mute_event`) to communicate state changes (like hanging up or muting the mic) instantly to the deeply nested audio threads.

### 2.2. Master Controller (`p2p_session.py`)
When a user clicks "Connect", `p2p_session.py` takes over to establish the call.
* **Symmetric Negotiation:** To solve the classic P2P problem of "who is the server and who is the client?", this module starts both simultaneously. 
  * It spawns a `SIPServer` thread listening on port 5060.
  * It spawns a `SIPClient` thread that repeatedly tries to call the target IP on port 5060 (from its own port 5061).
* **Collision Resolution:** If both users click connect at the exact same millisecond, both clients fire packets at both servers. Whichever server processes the packet first becomes the active receiver, and the other side acts as the active caller, preventing a deadlock.
* **Early Socket Binding:** To prevent OS-level `WinError 10054 (ICMP Port Unreachable)` crashes, the UDP media socket (port 5005) is bound *before* the call is even established, guaranteeing the socket is ready to receive data the microsecond the call starts.

### 2.3. The Signaling Protocol (`sip_signaling.py`)
We implemented a lightweight, custom version of the **Session Initiation Protocol (SIP)** over UDP.
* It operates as a deterministic State Machine: `IDLE` -> `CALLING` -> `IN_CALL` -> `ENDED`.
* **The Handshake:** 
  1. **Client** sends `INVITE`.
  2. **Server** receives `INVITE`, transitions to `CALLING`, and replies with `200 OK`.
  3. **Client** receives `200 OK`, transitions to `IN_CALL`, and replies with `ACK`.
  4. **Server** receives `ACK` and transitions to `IN_CALL`. 
* **Teardown:** When a user ends the call, a `BYE` message is sent, forcing both state machines into `ENDED` and terminating all audio loops.

### 2.4. Audio Configuration (`audio_config.py`)
Defines the strict mathematical constants required for the VoIP stream:
* **`RATE = 8000` Hz**: The industry standard for human voice (telephone quality). It limits bandwidth while preserving speech intelligibility.
* **`CHANNELS = 1`**: Mono audio.
* **`FORMAT = 'int16'`**: 16-bit PCM audio depth.
* **`CHUNK = 160`**: Exactly 20 milliseconds of audio (8000 Hz / 50 frames per second = 160 samples per chunk).

### 2.5. Audio Sender & Compression (`sender.py`)
This thread is responsible for pushing your voice onto the network.
* **Hardware Interface:** Uses `sounddevice.RawInputStream` to pull 20ms blocks of raw electrical signals from the physical microphone.
* **Privacy Failsafe:** If Windows blocks microphone access for privacy reasons, `sounddevice` will throw an exception. Instead of crashing, the exception is caught, and the program seamlessly substitutes the missing data with empty `\x00` bytes (silence), keeping the call alive (one-way audio) instead of dropping the connection.
* **Bandwidth Optimization:** The raw 20ms PCM audio chunk is heavily compressed in real-time using `zlib.compress()`, significantly reducing the payload size before it hits the network.
* **RTP Header Construction:** Before sending, the compressed audio is passed to `rtp_helper.py`.

### 2.6. Packet Formatting (`rtp_helper.py`)
Since UDP does not guarantee packet delivery or order, we must wrap our audio in the **Real-time Transport Protocol (RTP)**. 
* It uses Python's `struct.pack('!BBHII', ...)` to construct a 12-byte binary header.
* **Sequence Number (16-bit):** Increments by 1 for every packet. Used by the receiver to detect missing packets and reorder them chronologically.
* **Timestamp (32-bit):** A millisecond-precision wall-clock timestamp attached to every packet, used mathematically by the Jitter Buffer to calculate network transit delay.

### 2.7. Audio Receiver & Playout (`receiver.py`)
Handles incoming network data and pushes it to the speakers.
* **The Receiver Thread:** Listens on UDP port 5005. It strips the 12-byte RTP header, decompresses the payload using `zlib.decompress`, and immediately pushes the raw audio into the Jitter Buffer. Corrupted packets that fail decompression are silently discarded.
* **The Playout Thread:** A strictly timed loop using `sounddevice.RawOutputStream`. It pulls a 20ms frame from the Jitter Buffer. Before playing, it casts the bytes to a `numpy` array, applies a **4x digital gain** (to boost quiet laptop microphones), mathematically clips the values between `-32768 and 32767` to prevent integer overflow distortion, casts back to bytes, and plays it.

### 2.8. Network Intelligence (`jitter_buffer.py`)
The most complex and critical module. Wi-Fi networks suffer from "Jitter" (packets arriving out of order, or clumped together due to router queuing).
* **Ramjee's Algorithm:** We implemented Ramjee's adaptive delay algorithm. For every packet, it calculates:
  * Transit Delay ($n_i$): Current time minus packet send time.
  * Moving Average Delay ($d_i$): $d_i = 0.125 * d_{i-1} + 0.875 * n_i$
  * Network Jitter ($v_i$): $v_i = 0.125 * v_{i-1} + 0.875 * |n_i - d_i|$
  * Target Playout Window ($p_i$): $d_i + 4 * v_i$
* **Priority Queue:** Incoming packets are shoved into a `queue.PriorityQueue`, which automatically sorts them by their RTP Sequence Number, fixing out-of-order delivery.
* **Packet Loss Concealment (PLC):** If the network lags and the buffer underflows (no audio is ready to play), it doesn't just output silence (which causes an audible "pop" or "click"). Instead, it repeats the *previous* 20ms audio frame, but artificially attenuates it by 85% (`samples * 0.85`). This creates a smooth fade-out effect.
* **Buffer Catch-up:** If a massive lag spike resolves, a huge burst of packets arrives at once. If the queue size exceeds 8 packets (160ms of audio), it intentionally drops the oldest packets to resynchronize the audio with real-time, prioritizing low latency over perfect quality.

### 2.9. Metrics & Data Visualization
* **`jitter_metrics.csv`:** Every time a packet hits the buffer, its sequence number, send time, receive time, delay, and jitter calculations are written to this CSV in real-time.
* **`plot_metrics.py` & `plot_jitter.py`:** Standalone Matplotlib scripts that can be triggered from the UI dashboard. They read the CSV and generate interactive graphs, mathematically proving to the user how the network is behaving and how the Adaptive Jitter Buffer is successfully smoothing out the lag.

---
