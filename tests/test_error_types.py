import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bitalino_recorder.bitalino_error_types import BitalinoErrorTypes

class TestBitalinoErrorTypes(unittest.TestCase):

    def test_error_types_values(self):
        self.assertEqual(BitalinoErrorTypes.BT_DEVICE_NOT_CONNECTED.code, 0)
        self.assertEqual(BitalinoErrorTypes.BT_DEVICE_NOT_CONNECTED.description, "Bluetooth Device not connected")
        self.assertEqual(BitalinoErrorTypes.LOST_COMMUNICATION.code, 5)
        self.assertEqual(BitalinoErrorTypes.LOST_COMMUNICATION.description, "The Computer lost communication")
        self.assertEqual(BitalinoErrorTypes.UNDEFINED.code, 12)
        self.assertEqual(BitalinoErrorTypes.UNDEFINED.description, "UNDEFINED ERROR")

    def test_error_types_iteration(self):
        error_count = 0
        for error in BitalinoErrorTypes:
            error_count += 1
            self.assertTrue(hasattr(error, 'code'))
            self.assertTrue(hasattr(error, 'description'))
        self.assertGreater(error_count, 0)

    def test_all_error_codes(self):
        codes = []
        for error_types in BitalinoErrorTypes:
            codes.append(error_types.code)
        self.assertEqual(len(codes), len(set(codes)))

if __name__ == '__main__':
    unittest.main()

