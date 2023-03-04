#!/bin/bash
source linux-venv/bin/activate
pyinstaller --onefile --name='HenshouseChatServer' main.py
