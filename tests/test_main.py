import sys
import os
import unittest
import threading
import tempfile
import math
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class MockSettings:
    def __init__(self, data=None):
        self._data = data or {}
    def get_setting(self, key):
        return self._data.get(key)

class CaptureData:
    def __init__(self, timestamp, data):
        self.timestamp = timestamp
        self.data = data

serial_mock = MagicMock()
serial_mock.SerialException = IOError
sys.modules['serial'] = serial_mock

from bitalino_recorder.main import BitalinoRecorderPlugin
from bitalino_recorder.bitalino_frame import BitalinoFrame
from bitalino_recorder.bitalino_frame_decoder import BitalinoFrameDecoder
from bitalino_recorder.bitalino_exception import BitalinoException
from bitalino_recorder.bitalino_error_types import BitalinoErrorTypes


def make(settings=None):
    p = BitalinoRecorderPlugin()
    p.settings = MockSettings(settings or {})
    p.load()
    return p


class TestMain(unittest.TestCase):

    def active(self):
        p = make()
        p.capture_event.set()
        p.paused_event.set()
        return p

    def mock_serial(self):
        sp = MagicMock()
        sp.is_open = True
        return sp

    def test_frame_default_values(self):
        f = BitalinoFrame()
        self.assertEqual(f.get_crc(), 0)
        self.assertEqual(f.get_seq(), 0)
        for i in range(6):
            self.assertEqual(f.get_analog(i), 0)
        for i in range(4):
            self.assertEqual(f.get_digital(i), 0)

    def test_frame_set_and_get(self):
        f = BitalinoFrame()
        f.set_crc(5)
        self.assertEqual(f.get_crc(), 5)
        f.set_seq(3)
        self.assertEqual(f.get_seq(), 3)
        f.set_analog(0, 512)
        self.assertEqual(f.get_analog(0), 512)
        f.set_analog(5, 1023)
        self.assertEqual(f.get_analog(5), 1023)
        f.set_digital(0, 1)
        self.assertEqual(f.get_digital(0), 1)
        f.set_digital(3, 1)
        self.assertEqual(f.get_digital(3), 1)

    def test_frame_seq_minus_one(self):
        f = BitalinoFrame()
        f.set_seq(-1)
        self.assertEqual(f.get_seq(), -1)

    def test_total_bytes_1_channel(self):
        p = make()
        self.assertEqual(p.calculate_total_bytes(1), 3)

    def test_total_bytes_2_channels(self):
        p = make()
        self.assertEqual(p.calculate_total_bytes(2), 4)

    def test_total_bytes_4_channels(self):
        p = make()
        expected = math.ceil((12 + 10 * 4) / 8)
        self.assertEqual(p.calculate_total_bytes(4), expected)

    def test_total_bytes_5_channels(self):
        p = make()
        expected = math.ceil((52 + 6 * 1) / 8)
        self.assertEqual(p.calculate_total_bytes(5), expected)

    def test_total_bytes_6_channels(self):
        p = make()
        expected = math.ceil((52 + 6 * 2) / 8)
        self.assertEqual(p.calculate_total_bytes(6), expected)

    def test_load_events_cleared(self):
        p = make()
        self.assertFalse(p.capture_event.is_set())
        self.assertFalse(p.paused_event.is_set())

    def test_load_defaults(self):
        p = make()
        self.assertEqual(p.analog_channels, [])
        self.assertIsNone(p.serial_port)
        self.assertEqual(p.switch, 1)
        self.assertEqual(p.prev_seq, 15)
        self.assertEqual(p.sampling_rate, 100)
        self.assertEqual(p.pause_intervals, [])
        self.assertIsNone(p.recording_start_ts)

    def test_send_command_writes_to_serial(self):
        p = make()
        mock_sp = MagicMock()
        mock_sp.is_open = True
        p.serial_port = mock_sp
        p.send_command(0x02)
        mock_sp.write.assert_called_once_with(bytes([0x02]))

    def test_send_command_no_serial(self):
        p = make()
        p.serial_port = None
        p.send_command(0x02)

    def test_send_command_not_open(self):
        p = make()
        mock_sp = MagicMock()
        mock_sp.is_open = False
        p.serial_port = mock_sp
        p.send_command(0x02)
        mock_sp.write.assert_not_called()

    def test_sampling_rate_1000hz(self):
        p = make()
        p.serial_port = MagicMock()
        p.serial_port.is_open = True
        p.set_sampling_rate(1000)
        cmd = p.serial_port.write.call_args[0][0][0]
        self.assertEqual(cmd, (0x3 << 6) | 0x03)

    def test_sampling_rate_100hz(self):
        p = make()
        p.serial_port = MagicMock()
        p.serial_port.is_open = True
        p.set_sampling_rate(100)
        cmd = p.serial_port.write.call_args[0][0][0]
        self.assertEqual(cmd, (0x2 << 6) | 0x03)

    def test_sampling_rate_10hz(self):
        p = make()
        p.serial_port = MagicMock()
        p.serial_port.is_open = True
        p.set_sampling_rate(10)
        cmd = p.serial_port.write.call_args[0][0][0]
        self.assertEqual(cmd, (0x1 << 6) | 0x03)

    def test_sampling_rate_1hz(self):
        p = make()
        p.serial_port = MagicMock()
        p.serial_port.is_open = True
        p.set_sampling_rate(1)
        cmd = p.serial_port.write.call_args[0][0][0]
        self.assertEqual(cmd, (0x0 << 6) | 0x03)

    def test_sampling_rate_unknown_defaults_to_0(self):
        p = make()
        p.serial_port = MagicMock()
        p.serial_port.is_open = True
        p.set_sampling_rate(999)
        cmd = p.serial_port.write.call_args[0][0][0]
        self.assertEqual(cmd, (0x0 << 6) | 0x03)

    def test_start_acquisition_correct_bits(self):
        p = make()
        p.serial_port = MagicMock()
        p.serial_port.is_open = True
        p.analog_channels = [1]
        p.start_acquisition()
        cmd = p.serial_port.write.call_args[0][0][0]
        self.assertEqual(cmd, 1 | (1 << 3))

    def test_stop_acquisition_sends_zero(self):
        p = make()
        p.serial_port = MagicMock()
        p.serial_port.is_open = True
        p.stop_acquisition()
        cmd = p.serial_port.write.call_args[0][0][0]
        self.assertEqual(cmd, 0)

    def test_pause_clears_event(self):
        p = self.active()
        p.resume_time = 100.0
        p.pause(120.0)
        self.assertFalse(p.paused_event.is_set())
        self.assertEqual(p.last_pause_ts, 120.0)

    def test_pause_not_capturing(self):
        p = self.active()
        p.capture_event.clear()
        p.pause(10.0)
        self.assertTrue(p.paused_event.is_set())

    def test_resume_sets_event_and_records(self):
        p = self.active()
        p.resume_time = 100.0
        p.pause(120.0)
        p.resume(150.0)
        self.assertTrue(p.paused_event.is_set())
        self.assertIn((120.0, 150.0), p.pause_intervals)
        self.assertIsNone(p.last_pause_ts)

    def test_resume_not_paused(self):
        p = self.active()
        p.resume(150.0)
        self.assertEqual(p.pause_intervals, [])

    def test_stop_clears_capture_event(self):
        p = make()
        p.capture_event.set()
        p.paused_event.set()
        p.serial_port = MagicMock()
        p.serial_port.is_open = True
        p.stop(200.0)
        self.assertFalse(p.capture_event.is_set())
        self.assertEqual(p.switch, 0)

    def test_stop_records_active_pause(self):
        p = make()
        p.capture_event.set()
        p.paused_event.set()
        p.serial_port = MagicMock()
        p.serial_port.is_open = True
        p.last_pause_ts = 100.0
        p.stop(200.0)
        self.assertIn((100.0, 200.0), p.pause_intervals)

    def test_stop_closes_serial(self):
        p = make()
        p.capture_event.set()
        p.paused_event.set()
        mock_sp = MagicMock()
        mock_sp.is_open = True
        p.serial_port = mock_sp
        p.stop(200.0)
        mock_sp.close.assert_called_once()

    def test_save_writes_csv_lines(self):
        p = make()
        p.recording_start_ts = 0.0
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            tmp = f.name
        try:
            p.output_path = tmp
            p.file_writer = open(tmp, 'w')
            cd = CaptureData(1.0, {'analog': [512], 'digital': [0, 0, 0, 0]})
            p.save([cd], end_of_data=False)
            p.file_writer.flush()
            p.file_writer.close()
            with open(tmp) as f:
                content = f.read()
            self.assertIn('1.0', content)
            self.assertIn('512', content)
        finally:
            os.unlink(tmp)

    def test_save_end_of_data_closes_writer(self):
        p = make()
        p.recording_start_ts = 0.0
        mock_writer = MagicMock()
        p.file_writer = mock_writer
        p.save([], end_of_data=True)
        mock_writer.close.assert_called_once()
        self.assertIsNone(p.file_writer)

    def test_save_no_writer(self):
        p = make()
        p.file_writer = None
        p.save([CaptureData(1.0, {'analog': [1]})], end_of_data=False)

    def test_extension(self):
        self.assertEqual(make().get_file_extension(), 'txt')

    def test_descriptor_type(self):
        d = make().get_output_descriptor()
        self.assertIsNotNone(d)
        self.assertEqual(d['type'], 'array')
        self.assertIn('items', d)

    def test_process_data_calls_callback(self):
        p = make()
        p.capture_event.set()
        p.paused_event.set()
        p.analog_channels = [1]
        p.total_bytes = 3
        mock_ts = MagicMock(return_value=1.0)
        mock_data = MagicMock()
        p.get_timestamp_callback = mock_ts
        p.on_data_callback = mock_data
        mock_frame = MagicMock()
        mock_frame.get_seq.return_value = 0
        mock_frame.get_analog.return_value = 512
        mock_frame.get_digital.side_effect = lambda i: 0
        with patch('bitalino_recorder.bitalino_frame_decoder.BitalinoFrameDecoder.decode', return_value=mock_frame):
            p.process_data(b'\x00\x00\x00')
        mock_data.assert_called_once()
        args = mock_data.call_args[0][0]
        self.assertIn('analog', args.data)
        self.assertIn('digital', args.data)

    def test_process_data_no_callback(self):
        p = make()
        p.analog_channels = [1]
        p.total_bytes = 3
        p.get_timestamp_callback = None
        p.on_data_callback = None
        mock_frame = MagicMock()
        mock_frame.get_seq.return_value = 0
        with patch('bitalino_recorder.bitalino_frame_decoder.BitalinoFrameDecoder.decode', return_value=mock_frame):
            p.process_data(b'\x00\x00\x00')

    def test_unload_closes_file_writer(self):
        p = make()
        mock_writer = MagicMock()
        p.file_writer = mock_writer
        p.unload()
        mock_writer.close.assert_called_once()
        self.assertIsNone(p.file_writer)

    def test_unload_no_file_writer(self):
        p = make()
        p.file_writer = None
        p.unload()

    def test_unload_closes_serial(self):
        p = make()
        mock_sp = MagicMock()
        mock_sp.is_open = True
        p.serial_port = mock_sp
        p.unload()
        mock_sp.close.assert_called()

    def test_unload_no_serial(self):
        p = make()
        p.serial_port = None
        p.unload()

    def test_send_command_write_error_raises(self):
        p = make()
        mock_sp = MagicMock()
        mock_sp.is_open = True
        mock_sp.write.side_effect = IOError("write failed")
        p.serial_port = mock_sp
        with self.assertRaises(BitalinoException):
            p.send_command(0x01)

    @patch('time.sleep')
    def test_prepare_sets_output_path(self, _sleep):
        p = make({'mac_address': 'COM5'})
        serial_mock.Serial.return_value = self.mock_serial()
        with tempfile.TemporaryDirectory() as d:
            p.prepare(d, 'rec')
            if p.file_writer:
                p.file_writer.close()
        self.assertTrue(p.output_path.endswith('rec.txt'))

    @patch('time.sleep')
    def test_prepare_mac_address_from_settings(self, _sleep):
        p = make({'mac_address': 'COM5'})
        serial_mock.Serial.return_value = self.mock_serial()
        with tempfile.TemporaryDirectory() as d:
            p.prepare(d, 'rec')
            if p.file_writer:
                p.file_writer.close()
        self.assertEqual(p.port_name, 'COM5')

    @patch('time.sleep')
    def test_prepare_default_port_com10(self, _sleep):
        p = make()
        serial_mock.Serial.return_value = self.mock_serial()
        with tempfile.TemporaryDirectory() as d:
            p.prepare(d, 'rec')
            if p.file_writer:
                p.file_writer.close()
        self.assertEqual(p.port_name, 'COM10')

    @patch('time.sleep')
    def test_prepare_paused_event_set(self, _sleep):
        p = make({'mac_address': 'COM5'})
        serial_mock.Serial.return_value = self.mock_serial()
        with tempfile.TemporaryDirectory() as d:
            p.prepare(d, 'rec')
            if p.file_writer:
                p.file_writer.close()
        self.assertTrue(p.paused_event.is_set())

    @patch('time.sleep')
    def test_prepare_analog_channels(self, _sleep):
        p = make({'mac_address': 'COM5'})
        serial_mock.Serial.return_value = self.mock_serial()
        with tempfile.TemporaryDirectory() as d:
            p.prepare(d, 'rec')
            if p.file_writer:
                p.file_writer.close()
        self.assertEqual(p.analog_channels, [0])

    @patch('time.sleep')
    def test_prepare_opens_file_writer(self, _sleep):
        p = make({'mac_address': 'COM5'})
        serial_mock.Serial.return_value = self.mock_serial()
        with tempfile.TemporaryDirectory() as d:
            p.prepare(d, 'rec')
            self.assertIsNotNone(p.file_writer)
            p.file_writer.close()

    def test_read_loop_exits_switch_zero(self):
        p = make()
        p.capture_event.set()
        p.switch = 0
        p.read_loop()

    def test_read_loop_exits_capture_not_set(self):
        p = make()
        p.capture_event.clear()
        p.read_loop()

    @patch('time.sleep')
    def test_read_loop_sleeps_paused(self, mock_sleep):
        p = make()
        p.capture_event.set()
        p.paused_event.clear()
        mock_sleep.side_effect = lambda _: p.capture_event.clear()
        p.read_loop()
        mock_sleep.assert_called()

    @patch('time.sleep')
    def test_read_loop_reads_and_calls_process(self, _sleep):
        p = make()
        p.capture_event.set()
        p.paused_event.set()
        p.analog_channels = [0]
        p.total_bytes = 3
        mock_sp = MagicMock()
        mock_sp.in_waiting = 3
        mock_sp.read.return_value = bytes([0, 0, 0])
        p.serial_port = mock_sp
        mock_process = MagicMock(side_effect=lambda _: (p.capture_event.clear(), True)[1])
        p.process_data = mock_process
        p.read_loop()
        mock_process.assert_called_once()

    @patch('time.sleep')
    def test_read_loop_discards_byte_invalid_crc(self, _sleep):
        p = make()
        p.capture_event.set()
        p.paused_event.set()
        p.analog_channels = [0]
        p.total_bytes = 3
        mock_sp = MagicMock()
        mock_sp.in_waiting = 3
        mock_sp.read.return_value = bytes([0, 0, 0])
        p.serial_port = mock_sp
        def _process(data):
            p.capture_event.clear()
            return False
        p.process_data = _process
        p.read_loop()
        self.assertEqual(mock_sp.read.call_count, 2)

    def test_read_loop_exception_breaks(self):
        p = make()
        p.capture_event.set()
        p.paused_event.set()
        p.analog_channels = [0]
        p.total_bytes = 3
        mock_sp = MagicMock()
        mock_sp.in_waiting = 3
        mock_sp.read.side_effect = IOError("read error")
        p.serial_port = mock_sp
        p.read_loop()

    def test_process_data_seq_minus_one(self):
        p = make()
        p.analog_channels = [0]
        p.total_bytes = 3
        mock_frame = MagicMock()
        mock_frame.get_seq.return_value = -1
        with patch('bitalino_recorder.bitalino_frame_decoder.BitalinoFrameDecoder.decode', return_value=mock_frame):
            result = p.process_data(b'\x00\x00\x00')
        self.assertFalse(result)

    def test_process_data_decode_exception(self):
        p = make()
        p.analog_channels = [0]
        p.total_bytes = 3
        with patch('bitalino_recorder.bitalino_frame_decoder.BitalinoFrameDecoder.decode',
                   side_effect=BitalinoException(BitalinoErrorTypes.DECODE_INVALID_DATA)):
            result = p.process_data(b'\x00\x00\x00')
        self.assertFalse(result)

    def test_save_pause_interval_adjusts_ts(self):
        p = make()
        p.recording_start_ts = 0.0
        p.pause_intervals = [(2.0, 3.0)]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            tmp = f.name
        try:
            p.file_writer = open(tmp, 'w')
            cd = CaptureData(5.0, {'analog': [100], 'digital': [0, 0, 0, 0]})
            p.save([cd], end_of_data=False)
            p.file_writer.flush()
            p.file_writer.close()
            p.file_writer = None
            with open(tmp) as f:
                content = f.read()
            self.assertIn('4.0', content)
        finally:
            os.unlink(tmp)

    def test_save_pause_interval_not_applied_before(self):
        p = make()
        p.recording_start_ts = 0.0
        p.pause_intervals = [(10.0, 20.0)]
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            tmp = f.name
        try:
            p.file_writer = open(tmp, 'w')
            cd = CaptureData(5.0, {'analog': [200], 'digital': [0, 0, 0, 0]})
            p.save([cd], end_of_data=False)
            p.file_writer.flush()
            p.file_writer.close()
            p.file_writer = None
            with open(tmp) as f:
                content = f.read()
            self.assertIn('5.0', content)
        finally:
            os.unlink(tmp)

    @patch('threading.Thread')
    @patch('time.sleep')
    def test_start_launches_read_thread(self, mock_sleep, mock_thread):
        p = make()
        mock_sp = MagicMock()
        mock_sp.is_open = True
        p.serial_port = mock_sp
        t_inst = MagicMock()
        mock_thread.return_value = t_inst
        p.start_acquisition = MagicMock()
        mock_sleep.side_effect = lambda t: p.capture_event.clear()
        p.start(0.0, MagicMock(return_value=0.0), MagicMock())
        mock_thread.assert_called_once()
        t_inst.start.assert_called_once()

    @patch('threading.Thread')
    @patch('time.sleep')
    def test_start_sets_recording_start_ts(self, mock_sleep, mock_thread):
        p = make()
        mock_sp = MagicMock()
        mock_sp.is_open = True
        p.serial_port = mock_sp
        t_inst = MagicMock()
        mock_thread.return_value = t_inst
        p.start_acquisition = MagicMock()
        mock_sleep.side_effect = lambda t: p.capture_event.clear()
        p.start(42.0, MagicMock(return_value=42.0), MagicMock())
        self.assertEqual(p.recording_start_ts, 42.0)

    def test_start_exception_calls_stop(self):
        p = make()
        p.start_acquisition = MagicMock(
            side_effect=BitalinoException(BitalinoErrorTypes.LOST_COMMUNICATION))
        with patch.object(p, 'stop') as mock_stop:
            p.start(0.0, MagicMock(return_value=0.0), MagicMock())
            mock_stop.assert_called_once()

    def test_stop_joins_alive_thread(self):
        p = make()
        p.capture_event.set()
        p.paused_event.set()
        p.serial_port = MagicMock()
        p.serial_port.is_open = True
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        p.read_thread = mock_thread
        p.stop(100.0)
        mock_thread.join.assert_called_once_with(timeout=1.0)

    def test_stop_acquisition_exception_swallowed(self):
        p = make()
        p.capture_event.set()
        p.paused_event.set()
        mock_sp = MagicMock()
        mock_sp.is_open = True
        mock_sp.write.side_effect = IOError("error")
        p.serial_port = mock_sp
        p.stop(100.0)
        self.assertFalse(p.capture_event.is_set())


if __name__ == '__main__':
    unittest.main()
