#!/bin/bash
# QQ Group Daily Briefing — Linux/macOS launcher
set -e
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true
python daily_briefing.py
