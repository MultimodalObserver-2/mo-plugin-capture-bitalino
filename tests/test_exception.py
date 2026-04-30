import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bitalino_recorder.bitalino_error_types import BitalinoErrorTypes
from bitalino_recorder.bitalino_exception import BitalinoException

class TestBitalinoException(unittest.TestCase):

    def test_exception_creation(self):
        error_type = BitalinoErrorTypes.LOST_COMMUNICATION
        exception = BitalinoException(error_type)
        self.assertEqual(exception.code, error_type.code)
        self.assertEqual(str(exception), error_type.description)

    def test_exception_inheritance(self):
        exception = BitalinoException(BitalinoErrorTypes.INVALID_PARAMETER)
        self.assertIsInstance(exception, Exception)

    def test_serial_version_uid(self):
        self.assertTrue(hasattr(BitalinoException, 'SERIAL_VERSION_UID'))
        self.assertEqual(BitalinoException.SERIAL_VERSION_UID, 3850110443125871497)

    def test_all_error_types_exception(self):
        for error_types in BitalinoErrorTypes:
            exception = BitalinoException(error_types)
            self.assertEqual(exception.code, error_types.code)
            self.assertEqual(str(exception), error_types.description)

if __name__ == '__main__':
    unittest.main()

