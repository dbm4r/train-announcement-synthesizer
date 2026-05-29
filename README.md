# Train Announcement Concatenative Speech Synthesizer

## Overview
This program implements a concatenative speech synthesizer that generates spoken English train announcements for Warszawa Centralna railway station. It combines pre-recorded audio files to create complete announcements for train departures and arrivals.

## Features
- Handles Polish characters in station names (ą, ć, ę, ł, ń, ó, ś, ź, ż)
- Supports both digit and word forms for track numbers (e.g., "2" or "two")
- Automatically parses announcement text into components
- Concatenates audio segments with natural pauses
- Saves generated announcements as WAV files
- Falls back gracefully when some audio files are missing (adds pauses)

## Requirements

### Software
- Python 3.11 or lower (Python 3.13 has known issues with pydub)

### Python Packages
```bash
pip install pydub