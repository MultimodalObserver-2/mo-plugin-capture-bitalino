# BITalino Capture Plugin

A plugin for [**Multimodal Observer**](https://github.com/MultimodalObserver-2/mo) that records ECG signals from a BITalino biosignal device over a serial connection and saves them as a timestamped CSV file.

---

## Features

- Captures ECG data from a BITalino device via serial (Bluetooth COM port)
- Configurable sampling rate (100 Hz or 1000 Hz)
- Supports pause and resume during a recording session
- Saves data as a plain-text CSV with relative timestamps

---

## Configuration Options

| Property | Description | Default |
|----------|-------------|---------|
| `mac_address` | COM port of the BITalino device | `COM10` |
| `sampling_rate` | Sampling frequency in Hz (`100` or `1000`) | `1000` |

---

## Output Format

The plugin produces a `.txt` file with one sample per line:

```
<relative_timestamp_seconds>,<ecg_value>
```

Pause intervals are subtracted from the timestamp so the timeline is continuous.

---

## How It Works

- Opens a serial connection to the BITalino device at 115200 baud
- Sends the sampling rate and acquisition start commands using the BITalino binary protocol
- Reads frames in a background thread, decodes them with CRC validation, and passes ECG values to the data callback
- On pause, frame reading stops without closing the serial port; on resume it continues from where it left off
- On stop, sends the stop acquisition command, closes the serial port, and flushes the output file

---

## Installation

1. Download the latest plugin release from [here](https://github.com/MultimodalObserver-2/mo-plugin-capture-bitalino/releases/latest).
2. Extract the downloaded `.zip` file.
3. Register the plugin using the plugin interface within Multimodal Observer.
