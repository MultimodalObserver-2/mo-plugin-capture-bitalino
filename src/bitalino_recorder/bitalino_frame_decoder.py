import sys
import os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
from bitalino_recorder.bitalino_error_types import BitalinoErrorTypes
from bitalino_recorder.bitalino_exception import BitalinoException
from bitalino_recorder.bitalino_frame import BitalinoFrame


class BitalinoFrameDecoder:

    @staticmethod
    def decode(buffer: bytes, analog_channels: list, total_bytes: int) -> BitalinoFrame:
        try:
            frame = BitalinoFrame()
            j = total_bytes - 1
            x0, x1, x2, x3, out, inp = 0, 0, 0, 0, 0, 0
            crc = (buffer[j] & 0x0F) & 0xFF
            for i in range(total_bytes):
                for bit in range(7, -1, -1):
                    if i == (total_bytes - 1) and bit < 4:
                        inp = 0
                    else:
                        inp = (buffer[i] >> bit) & 1
                    out = x3
                    x3 = x2
                    x2 = x1
                    x1 = out ^ x0
                    x0 = inp ^ out
            if crc == ((x3 << 3) | (x2 << 2) | (x1 << 1) | x0): 
                frame.set_seq(((buffer[j] & 0xF0) >> 4) & 0xF)
                frame.set_digital(0, (buffer[j-1] >> 7) & 0x01) 
                frame.set_digital(1, (buffer[j-1] >> 6) & 0x01)
                frame.set_digital(2, (buffer[j-1] >> 5) & 0x01)
                frame.set_digital(3, (buffer[j-1] >> 4) & 0x01)

                if len(analog_channels) >= 1:
                    frame.set_analog(
                        analog_channels[0],
                        (((buffer[j-1] & 0xF) << 6) | ((buffer[j-2] & 0xFC) >> 2)) & 0x3FF
                    )
                if len(analog_channels) >= 2:
                    frame.set_analog(
                        analog_channels[1],
                        (((buffer[j-2] & 0x3) << 8) | (buffer[j-3] & 0xFF)) & 0x3FF
                    )
                if len(analog_channels) >= 3:
                    frame.set_analog(
                        analog_channels[2],
                        (((buffer[j-4] & 0xFF) << 2) | ((buffer[j-5] & 0xC0) >> 6)) & 0x3FF
                    )
                if len(analog_channels) >= 4:
                    frame.set_analog(
                        analog_channels[3],
                        (((buffer[j-1] & 0x3F) << 4) | ((buffer[j-6] & 0xF0) >> 4)) & 0x3FF
                    )    
                if len(analog_channels) >= 5:
                    frame.set_analog(
                        analog_channels[4],
                        (((buffer[j-1] & 0x0F) << 2) | ((buffer[j-7] & 0xC0) >> 6)) & 0x3FF
                    )
                if len(analog_channels) >= 6:
                    frame.set_analog(
                        analog_channels[5],
                        (buffer[j-7] & 0x3F)
                    )
            else:
                frame.set_seq(-1)

            return frame
        except Exception as e:
            raise BitalinoException(BitalinoErrorTypes.DECODE_INVALID_DATA)