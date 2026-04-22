#!/bin/bash
cd "$(dirname "$0")"
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
    python start.py
else
    python3 start.py
fi
