import os
import sys
import time
import threading
import serial
from typing import Callable, List, Any
import math

current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from mo.core import load_metadata_json
from mo.modules.capture.plugins.capture_plugin import CaptureData, CapturePlugin

from bitalino_recorder.bitalino_exception import BitalinoException
from bitalino_recorder.bitalino_error_types import BitalinoErrorTypes
from bitalino_recorder.bitalino_frame_decoder import BitalinoFrameDecoder

@load_metadata_json(rel_path="../..")
class BitalinoRecorderPlugin(CapturePlugin):

    def __init__(self):
        super().__init__()
        self.capture_event = threading.Event()
        self.paused_event = threading.Event()
        self.output_file = None
        self.get_timestamp_callback = None
        self.on_data_callback = None
        self.output_path = "" 
        self.file_name = ""
        self.file_writer = None
        self.pause_intervals: list = []
        self.last_pause_ts = None
        self.recording_start_ts = None
        self.paused_duration = 0.0
        self.analog_channels = []
        self.serial_port = None
        self.port_name = None 
        self.switch = 1
        self.resume_time = 0
        self.pause_time = 0
        self.prev_seq = 15
        self.sampling_rate = 100
        self.total_bytes = 0
        self.read_thread = None

    def load(self):
        self.capture_event.clear()
        self.paused_event.clear()
        self.file_writer = None
        self.pause_intervals = []
        self.last_pause_ts = None
        self.recording_start_ts = None
        self.paused_duration = 0.0
        self.analog_channels = []
        self.serial_port = None
        self.switch = 1
        self.prev_seq = 15
        self.get_timestamp_callback = None
        self.on_data_callback = None

    def unload(self):
        self.stop(time.time())
        if self.file_writer is not None:
            self.file_writer.close()
            self.file_writer = None
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

    def calculate_total_bytes(self, num_channels: int) -> int:
        if num_channels <= 4:
            total_bits = 12 + (10 * num_channels)
            return math.ceil(total_bits / 8)
        else:
            total_bits = 52 + (6 * (num_channels - 4))
            return math.ceil(total_bits / 8)
        
    def send_command(self, command: int):
        if self.serial_port and self.serial_port.is_open:
            try: 
                data = bytes([command])
                self.serial_port.write(data)
                time.sleep(0.1)
            except Exception as e:
                raise BitalinoException(BitalinoErrorTypes.LOST_COMMUNICATION)

    def set_sampling_rate(self, sampling_rate: int):
        command = 0
        if sampling_rate == 1000: command = 0x3
        elif sampling_rate == 100: command = 0x2
        elif sampling_rate == 10: command = 0x1
        elif sampling_rate == 1: command = 0x0
        else: command = 0x0
        
        command = (command << 6) | 0x03
        self.send_command(command)

    def start_acquisition(self):
        bit = 1
        for channel in self.analog_channels:
            bit = bit | (1 << (2 + channel))
        self.send_command(bit)

    def stop_acquisition(self):
        if self.serial_port and self.serial_port.is_open:
            self.send_command(0)
            time.sleep(0.1)

    def prepare(self, path: str, file_name: str):
        self.port_name = self.settings.get_setting("mac_address") 
        if not self.port_name:
             self.port_name = "COM10"

        self.output_path = os.path.join(path, f"{file_name}.txt")
        os.makedirs(path, exist_ok = True)
        self.file_name = file_name
        self.paused_event.set()
        sampling_rate_setting = self.settings.get_setting("sampling_rate")
        self.sampling_rate = sampling_rate_setting if sampling_rate_setting is not None else 100
        self.analog_channels = [0] 
        self.total_bytes = self.calculate_total_bytes(len(self.analog_channels))
        self.serial_port = serial.Serial(self.port_name, baudrate=115200, timeout=1)
        time.sleep(1.5)

        self.set_sampling_rate(self.sampling_rate) 
        self.file_writer = open(self.output_path, "w")

    def read_loop(self):
        while self.capture_event.is_set():
            if self.switch == 0: break
            
            if self.paused_event.is_set():
                try:
                    if self.serial_port and self.serial_port.in_waiting >= self.total_bytes:
                        data = self.serial_port.read(self.total_bytes)
                        valid = self.process_data(data)
                        if not valid and self.serial_port.in_waiting >= 1:
                            self.serial_port.read(1)
                    else:
                        time.sleep(0.001)
                except Exception:
                    break
            else:
                time.sleep(0.1)

    def process_data(self, data: bytes) -> bool:
        try:
            frame = BitalinoFrameDecoder.decode(data, self.analog_channels, self.total_bytes)

            if frame.get_seq() == -1:
                return False
            self.prev_seq = frame.get_seq()

            if not (self.on_data_callback and self.get_timestamp_callback):
                return True

            ts = self.get_timestamp_callback()
            ecg_value = frame.get_analog(self.analog_channels[0])
            sample_data = {
                "digital": [frame.get_digital(i) for i in range(4)],
                "analog": [ecg_value]
            }
            self.on_data_callback(CaptureData(timestamp=ts, data=sample_data))
            return True
        except Exception:
            return False

    def start(self, start_ts: float, get_timestamp: Callable[[], float], on_data: Callable[[CaptureData], None]):
        self.recording_start_ts = start_ts
        self.get_timestamp_callback = get_timestamp
        self.on_data_callback = on_data
        self.capture_event.set()
        self.paused_event.set()
        self.switch = 1
        self.resume_time = start_ts
        self.prev_seq = 15
        
        try:
            self.start_acquisition()
            self.read_thread = threading.Thread(target=self.read_loop)
            self.read_thread.start()
            
            while self.capture_event.is_set() and self.switch != 0:
                time.sleep(0.5)
                
        except Exception as e:
            self.stop(get_timestamp())

    def save(self, data: List[CaptureData], end_of_data: bool = False):
        if self.file_writer is None: return
        for item in data:
            ts = item.timestamp
            pause_duration_accumulated = 0
            for interval in self.pause_intervals:
                start_p, end_p = interval
                if ts > start_p:
                    duration = min(ts, end_p) - start_p
                    pause_duration_accumulated += duration
            relative_ts = (ts - self.recording_start_ts) - pause_duration_accumulated
            ecg_val = item.data["analog"][0]
            line = f"{relative_ts},{ecg_val}\n"
            
            self.file_writer.write(line)
        self.file_writer.flush()
        if end_of_data:
            self.file_writer.close()
            self.file_writer = None

    def pause(self, pause_ts: float):
        if not self.capture_event.is_set() or not self.paused_event.is_set(): return 
        self.paused_event.clear()
        self.last_pause_ts = pause_ts
        self.switch = 2
        self.pause_time = pause_ts - self.resume_time

    def resume(self, resume_ts: float):
        if not self.capture_event.is_set() or self.paused_event.is_set(): return
        self.paused_event.set()
        self.switch = 1
        if self.last_pause_ts is not None:
            self.pause_intervals.append((self.last_pause_ts, resume_ts))
            self.paused_duration += (resume_ts - self.last_pause_ts)
            self.last_pause_ts = None
        self.resume_time = resume_ts - self.pause_time

    def stop(self, stop_ts: float):
        self.capture_event.clear()
        self.paused_event.set()
        self.switch = 0
        
        try: 
            self.stop_acquisition()
        except Exception: 
            pass
            
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)
            
        if self.last_pause_ts is not None:
            self.pause_intervals.append((self.last_pause_ts, stop_ts))
            self.last_pause_ts = None
            
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

    def get_file_extension(self) -> str:
        return "txt"
    
    def get_output_descriptor(self) -> dict[str, Any] | None:
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ecg": {"type": "number"},
                    "seq": {"type": "number"},
                    "plugin_type": {"const": "bitalino_capture"},
                    "channels": {"const": [1]},
                    "sampling_rate": {"const": 100}
                }
            }
        }