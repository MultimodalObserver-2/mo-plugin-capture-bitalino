class BitalinoFrame:

    def __init__(self):
        self.crc = 0
        self.seq = 0
        self.analog = [0] * 6
        self.digital = [0] * 4

    def get_crc(self) -> int:
        return self.crc
    
    def set_crc(self, crc: int):
        self.crc = crc

    def get_seq(self) -> int:
        return self.seq
    
    def set_seq(self, seq: int):
        self.seq = seq

    def get_analog(self, pos: int) -> int:
        return self.analog[pos]
    
    def set_analog(self, pos: int, value: int):
        self.analog[pos] = value

    def get_digital(self, pos: int) -> int:
        return self.digital[pos]
    
    def set_digital(self, pos: int, value: int):
        self.digital[pos] = value

    def equal(self, object) -> bool:
        if isinstance(object, BitalinoFrame):
            return self.crc == object.crc and self.seq == object.seq
        return False
    
    def to_string(self) -> str:
        return f"BitalinoFrame(crc={self.crc}, seq={self.seq}, analog={self.analog}, digital={self.digital})"