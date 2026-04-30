import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bitalino_recorder.bitalino_frame_decoder import BitalinoFrameDecoder
from bitalino_recorder.bitalino_exception import BitalinoException
from bitalino_recorder.bitalino_frame import BitalinoFrame
from bitalino_recorder.bitalino_error_types import BitalinoErrorTypes


class TestFrameDecoder(unittest.TestCase):

    def decode_1ch(self):
        return BitalinoFrameDecoder.decode(bytes([0, 0, 0]), [0], 3)

    def test_decode_returns_frame(self):
        frame = self.decode_1ch()
        self.assertIsInstance(frame, BitalinoFrame)

    def test_valid_seq_not_minus_one(self):
        frame = self.decode_1ch()
        self.assertNotEqual(frame.get_seq(), -1)

    def test_valid_seq_zero(self):
        frame = self.decode_1ch()
        self.assertEqual(frame.get_seq(), 0)

    def test_valid_analog_ch0_zero(self):
        frame = self.decode_1ch()
        self.assertEqual(frame.get_analog(0), 0)

    def test_valid_digital_zero(self):
        frame = self.decode_1ch()
        for i in range(4):
            self.assertEqual(frame.get_digital(i), 0)

    def test_two_channels(self):
        frame = BitalinoFrameDecoder.decode(bytes([0, 0, 0, 0]), [0, 1], 4)
        self.assertNotEqual(frame.get_seq(), -1)

    def test_valid_seq_nonnegative(self):
        frame = self.decode_1ch()
        self.assertGreaterEqual(frame.get_seq(), 0)

    def test_invalid_seq_minus_one(self):
        frame = BitalinoFrameDecoder.decode(bytes([0, 0, 1]), [0], 3)
        self.assertEqual(frame.get_seq(), -1)

    def test_invalid_returns_frame(self):
        frame = BitalinoFrameDecoder.decode(bytes([0, 0, 1]), [0], 3)
        self.assertIsInstance(frame, BitalinoFrame)

    def test_invalid_buffers(self):
        for bad_byte in [1, 2, 3, 5, 7, 15]:
            frame = BitalinoFrameDecoder.decode(bytes([0, 0, bad_byte]), [0], 3)
            self.assertEqual(frame.get_seq(), -1, msg=f"Expected seq=-1 for bad_byte={bad_byte}")

    def test_empty_buffer_raises(self):
        with self.assertRaises(BitalinoException):
            BitalinoFrameDecoder.decode(bytes([]), [0], 3)

    def test_short_buffer_raises(self):
        with self.assertRaises(BitalinoException):
            BitalinoFrameDecoder.decode(bytes([0]), [0], 3)

    def test_decode_exception_code(self):
        try:
            BitalinoFrameDecoder.decode(bytes([]), [0], 3)
            self.fail("Should have raised BitalinoException")
        except BitalinoException as e:
            self.assertEqual(e.code, BitalinoErrorTypes.DECODE_INVALID_DATA.code)

    def test_exception_description(self):
        exc = BitalinoException(BitalinoErrorTypes.LOST_COMMUNICATION)
        self.assertIn("lost communication", str(exc).lower())

    def test_exception_code(self):
        exc = BitalinoException(BitalinoErrorTypes.UNDEFINED)
        self.assertEqual(exc.code, 12)

    def test_exception_is_exception(self):
        exc = BitalinoException(BitalinoErrorTypes.BT_DEVICE_NOT_CONNECTED)
        self.assertIsInstance(exc, Exception)

    def test_exception_error_type(self):
        exc = BitalinoException(BitalinoErrorTypes.BT_DEVICE_NOT_CONNECTED)
        self.assertEqual(exc.code, BitalinoErrorTypes.BT_DEVICE_NOT_CONNECTED.code)


if __name__ == '__main__':
    unittest.main()
