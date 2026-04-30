import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bitalino_recorder.bitalino_frame import BitalinoFrame


class TestBitalinoFrame(unittest.TestCase):

    def test_frame_init(self):
        frame = BitalinoFrame()
        self.assertEqual(frame.get_crc(), 0)
        self.assertEqual(frame.get_seq(), 0)
        self.assertEqual(frame.get_analog(0), 0)
        self.assertEqual(frame.get_digital(0), 0)

    def test_frame_setters(self):
        frame = BitalinoFrame()
        frame.set_crc(10)
        self.assertEqual(frame.get_crc(), 10)

        frame.set_seq(10)
        self.assertEqual(frame.get_seq(), 10)

        frame.set_analog(0, 100)
        frame.set_analog(1, 200)
        frame.set_analog(5, 300)
        self.assertEqual(frame.get_analog(0), 100)
        self.assertEqual(frame.get_analog(1), 200)
        self.assertEqual(frame.get_analog(5), 300)

        frame.set_digital(0, 1)
        frame.set_digital(3, 1)
        self.assertEqual(frame.get_digital(0), 1)
        self.assertEqual(frame.get_digital(3), 1)

    def test_frame_equality(self):
        frame1 = BitalinoFrame()
        frame2 = BitalinoFrame()
        frame3 = BitalinoFrame()

        frame1.set_crc(5)
        frame1.set_seq(10)

        frame2.set_crc(5)
        frame2.set_seq(10)

        frame3.set_crc(6)
        frame3.set_seq(10)

        self.assertTrue(frame1.equal(frame2))
        self.assertFalse(frame1.equal(frame3))
        self.assertFalse(frame1.equal("not_a_frame"))

    def test_frame_string(self):
        frame = BitalinoFrame()
        frame.set_crc(1)
        frame.set_seq(2)
        frame.set_analog(0, 100)
        frame.set_digital(0, 1)
        frame_str = frame.to_string()
        self.assertIn("BitalinoFrame", frame_str)
        self.assertIn("crc=1", frame_str)
        self.assertIn("seq=2", frame_str)
        self.assertIn("analog=[100, 0, 0, 0, 0, 0]", frame_str)

    def test_analog_channels(self):
        frame = BitalinoFrame()
        for i in range(6):
            frame.set_analog(i, i * 100)
            self.assertEqual(frame.get_analog(i), i * 100)

    def test_digital_channels(self):
        frame = BitalinoFrame()
        for i in range(4):
            frame.set_digital(i, i % 2)
            self.assertEqual(frame.get_digital(i), i % 2)


if __name__ == '__main__':
    unittest.main()
