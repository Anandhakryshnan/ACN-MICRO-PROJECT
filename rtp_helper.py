import struct

def create_rtp_packet(seq_num, timestamp, payload, ssrc=12345):
    """
    Packs a 12-byte RTP header and appends the raw audio payload.
    RTP Header format:
    Byte 1: Version (2 bits), Padding (1 bit), Extension (1 bit), CSRC count (4 bits)
    Byte 2: Marker (1 bit), Payload Type (7 bits)
    Byte 3,4: Sequence Number (16 bits)
    Byte 5-8: Timestamp (32 bits)
    Byte 9-12: SSRC (32 bits)
    """
    version = 2
    padding = 0
    extension = 0
    cc = 0
    marker = 0
    payload_type = 0 # 0 for PCMU, though we are using raw PCM here
    
    # Byte 1: V, P, X, CC
    byte1 = (version << 6) | (padding << 5) | (extension << 4) | cc
    # Byte 2: M, PT
    byte2 = (marker << 7) | payload_type
    
    # Pack header: ! (network byte order), B (1 byte), B (1 byte), H (2 bytes), I (4 bytes), I (4 bytes)
    header = struct.pack('!BBHII', byte1, byte2, seq_num, timestamp, ssrc)
    return header + payload

def unpack_rtp_packet(packet):
    """
    Unpacks the 12-byte RTP header and returns (seq_num, timestamp, payload).
    """
    if len(packet) < 12:
        raise ValueError("Packet is too short to contain an RTP header")
        
    header = packet[:12]
    payload = packet[12:]
    
    # Unpack header
    byte1, byte2, seq_num, timestamp, ssrc = struct.unpack('!BBHII', header)
    
    return seq_num, timestamp, payload
