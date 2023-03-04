#!/bin/bash
source linux-venv/bin/activate
pyinstaller --onefile --name='HenshouseChatServer' server.py
