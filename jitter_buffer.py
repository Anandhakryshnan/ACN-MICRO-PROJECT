import queue
import time
import threading
import struct

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
        
        self.first_packet = True
        
        # Statistics for logging
        self.last_stats = None
        self.last_payload = b'\x00' * 320

        
    def push(self, seq_num, send_time_ms, payload):
        recv_time_ms = time.time() * 1000
        
        with self.lock:
            # Calculate transit delay (n_i)
            self.n_i = recv_time_ms - send_time_ms
            
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
                # Underflow: Apply PLC (repeat last payload with 50% attenuation)
                if self.last_payload != b'\x00' * 320:
                    samples = struct.unpack(f'{len(self.last_payload)//2}h', self.last_payload)
                    attenuated = [int(s * 0.5) for s in samples]
                    self.last_payload = struct.pack(f'{len(attenuated)}h', *attenuated)
                return self.last_payload
            
            # Retrieve the packet with the lowest sequence number
            packet = self.buffer.get()
            seq_num, payload, send_time_ms, recv_time_ms = packet
            self.last_payload = payload
            return payload

    def get_stats(self):
        with self.lock:
            return self.last_stats
