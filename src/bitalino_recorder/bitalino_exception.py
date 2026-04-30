from bitalino_recorder.bitalino_error_types import BitalinoErrorTypes
class BitalinoException(Exception):

    SERIAL_VERSION_UID = 3850110443125871497

    def __init__(self, error_type: BitalinoErrorTypes):
        super().__init__(error_type.description)
        self.code = error_type.code