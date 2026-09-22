import queue
import time
import threading
import numpy as np

class AdaptiveJitterBuffer:
    def __init__(self, alpha=0.125, beta=0.125, K=4):
        self.alpha = alpha
        self.beta = beta
        self.K = K
        
        # Jitter metrics
        self.d_i = 0.0 # moving average delay
        self.v_i = 0.0 # jitter
        self.p_i = 0.0 # dynamic playout window
        self.n_i = 0.0 # latest transit delay
        
        # Priority Queue for reordering (sorted by seq_num)
        # Elements are tuples: (seq_num, payload, send_time_ms, recv_time_ms)
        self.buffer = queue.PriorityQueue()
        self.lock = threading.Lock()
        
        self.current_jitter = 0.0
        self.total_packets = 0
        self.first_packet = True
        
        # Stats tracking for logging
        self.last_stats = None
        self.last_payload = b'\x00' * 320

        
    def push(self, seq_num, send_time_ms, payload):
        with self.lock:
            self.total_packets += 1
            recv_time_ms = int(time.time() * 1000)
            recv_time_32 = recv_time_ms & 0xFFFFFFFF
            
            # Calculate transit delay (n_i)
            # Handle 32-bit wraparound
            diff = (recv_time_32 - send_time_ms) & 0xFFFFFFFF
            if diff > 0x7FFFFFFF:
                diff -= 0x100000000
            self.n_i = diff
            
            # Ramjee's algorithm
            if self.first_packet:
                self.d_i = self.n_i
                self.v_i = 0.0
                self.first_packet = False
            else:
                self.d_i = self.alpha * self.d_i + (1 - self.alpha) * self.n_i
                self.v_i = self.beta * self.v_i + (1 - self.beta) * abs(self.n_i - self.d_i)
                
            self.p_i = self.d_i + self.K * self.v_i
            
            # Store packet in buffer
            self.buffer.put((seq_num, payload, send_time_ms, recv_time_ms))
            
            # Store stats for logging
            self.last_stats = {
                'seq_num': seq_num,
                'send_time': send_time_ms,
                'recv_time': recv_time_ms,
                'transit_delay': self.n_i,
                'moving_delay': self.d_i,
                'jitter': self.v_i,
                'playout_target': self.p_i
            }
            
    def pop(self):
        with self.lock:
            if self.buffer.empty():
                # Underflow: Apply PLC (repeat last payload with smooth 85% attenuation curve)
                if self.last_payload != b'\x00' * 320:
                    samples = np.frombuffer(self.last_payload, dtype=np.int16)
                    attenuated = (samples * 0.85).astype(np.int16)
                    self.last_payload = attenuated.tobytes()
                return self.last_payload
            
            # Catch up if buffer is too large (e.g., > 8 packets = 160ms delay) to prevent lag build-up
            while self.buffer.qsize() > 8:
                self.buffer.get() # Discard oldest packet
                
            # Retrieve the packet with the lowest sequence number
            packet = self.buffer.get()
            seq_num, payload, send_time_ms, recv_time_ms = packet
            self.last_payload = payload
            return payload

    def get_stats(self):
        with self.lock:
            return self.last_stats
