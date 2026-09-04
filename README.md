# Microscope Vision Workbench

A lightweight, single-window Linux application for USB microscopy. Built with PyQt6 and OpenCV to replace bloated, legacy Java analysis tools. It provides low-latency V4L2 live streaming, hardware-accurate spatial calibration, and real-time point-to-point measurements natively on your desktop.

## Features

* **Native V4L2 Streaming:** Zero-latency live feed directly from `/dev/video*` devices.
* **Hardware-Based Calibration:** Automatically calculates $\mu$m/px scale based on your specific sensor pixel pitch, objective magnification, and C-mount adapter multiplier.
* **Live Spatial Measurement:** Measure distances by default, switch to angle mode for vertex-based angle readings, and remove a single measurement without clearing the whole frame.
* **One-Click Snapshots:** Save uncompressed, timestamped PNG captures to a persistent default directory.
* **Session Persistence:** Remembers your camera selection, calibration parameters, and save directories across restarts using `QSettings`.

## Development

Install system packages:

    sudo apt update
    sudo apt install python3 python3-pip python3-venv python-is-python3 pipx

Install the requirements:

    python -m venv .venv
    source .venv/bin/activate
    pip install .
    