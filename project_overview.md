# ACN Micro Project: P2P VoIP Application Overview

This document provides a clear, high-level overview of how the Spectra Voice P2P VoIP application works under the hood. It is designed to help team members quickly understand the project's architecture, the flow of a call, and what each file is responsible for.

---

## 1. High-Level Architecture

At its core, this application is a **Peer-to-Peer (P2P)** network program. Instead of routing audio through a central server (like Discord or Skype do), the two computers talk directly to each other over the local Wi-Fi or LAN.

A phone call in this application consists of two distinct phases:
1. **The Handshake (SIP):** Negotiating the connection before the call starts.
2. **The Audio Stream (RTP):** Continuously sending and receiving microphone data in real-time.

---

## 2. File-by-File Breakdown

Here is exactly what each file in the project does:

### 🖥️ User Interface & Controller
*   **[`app_ui.py`](file:///d:/ACN%20MICRO%20PROJECT/app_ui.py)**: The entry point of the application. It runs the Tkinter graphical dashboard, handles user inputs (like IP addresses), and visualizes the call status.
*   **[`p2p_session.py`](file:///d:/ACN%20MICRO%20PROJECT/p2p_session.py)**: The master controller. When you click "Connect" in the UI, this script wires everything together. It starts the SIP handshake and, once successful, launches the audio sending and receiving threads.

### 🤝 The Handshake (SIP)
*   **[`sip_signaling.py`](file:///d:/ACN%20MICRO%20PROJECT/sip_signaling.py)**: Implements a lightweight, custom version of the **Session Initiation Protocol (SIP)**. 
    *   It uses **TCP/UDP ports 5060 & 5061** to send `INVITE`, `200 OK`, and `ACK` messages.
    *   It also contains logic to handle "collisions" (when both users click connect at the exact same time) by deterministically assigning one user as the Caller and the other as the Receiver.

### 🎙️ The Audio Stream (RTP)
Once the SIP handshake is successful, the application transitions to the **Real-time Transport Protocol (RTP)** phase. Three independent threads spin up on both computers simultaneously:

*   **[`sender.py`](file:///d:/ACN%20MICRO%20PROJECT/sender.py)**: 
    1.  Records audio from your physical microphone using the `sounddevice` library.
    2.  Chops the continuous audio into tiny 20-millisecond chunks.
    3.  Compresses the audio using `zlib` to save bandwidth.
    4.  Passes it to `rtp_helper.py` to wrap it in an RTP header (adding a sequence number and timestamp).
    5.  Fires the packet across the network via **UDP port 5005**.
*   **[`receiver.py`](file:///d:/ACN%20MICRO%20PROJECT/receiver.py)**: 
    1.  Continuously listens on **UDP port 5005** for incoming packets from the other person.
    2.  Decompresses the payload and hands the raw audio packet over to the **Jitter Buffer**.
    3.  Runs a separate "Playout" thread that constantly reads smoothed-out audio from the Jitter Buffer and plays it through your speakers.

### 🧠 Network Intelligence
*   **[`jitter_buffer.py`](file:///d:/ACN%20MICRO%20PROJECT/jitter_buffer.py)**: The brains of the receiver. Because Wi-Fi networks are unreliable, packets might arrive out of order, delayed, or clumped together (network jitter).
    *   It uses **Ramjee's Algorithm** to dynamically calculate the network delay.
    *   It holds packets in a priority queue (sorted by sequence number) to reorder them chronologically.
    *   If a packet is lost, it uses Packet Loss Concealment (PLC) to artificially play a fading sound, preventing the audio from abruptly popping or clicking.

### ⚙️ Utilities
*   **[`audio_config.py`](file:///d:/ACN%20MICRO%20PROJECT/audio_config.py)**: A centralized configuration file that holds audio constants (e.g., 8000 Hz Sample Rate, 1 channel, Int16 format). Ensuring both sender and receiver use the exact same audio settings is critical.
*   **[`rtp_helper.py`](file:///d:/ACN%20MICRO%20PROJECT/rtp_helper.py)**: Contains helper functions to pack and unpack raw bytes into RTP headers, allowing the application to attach sequence numbers and timestamps to the raw audio.
*   **`plot_metrics.py`** & **`plot_jitter.py`**: Helper scripts that read from `jitter_metrics.csv` to generate matplotlib graphs of network latency and buffer performance after a call ends.

---

## 3. The Lifecycle of a Call

To summarize the flow from scratch:

1.  **Start:** Both users open `app_ui.py`.
2.  **Dialing:** User A enters User B's IP address and clicks "Connect".
3.  **SIP Phase:** `p2p_session.py` tells `sip_signaling.py` to send an `INVITE` packet to User B. User B responds with `200 OK`. User A acknowledges with `ACK`.
4.  **RTP Phase:** 
    *   User A's `sender.py` starts recording and throwing UDP packets at User B.
    *   User A's `receiver.py` starts listening for UDP packets from User B.
    *   (User B is doing the exact same thing simultaneously).
5.  **Playout:** Incoming packets hit the `jitter_buffer.py` to be sorted, then get played through the speakers.
6.  **End:** When a user clicks "End Call", a SIP `BYE` message is sent, and all audio threads gracefully shut down.
