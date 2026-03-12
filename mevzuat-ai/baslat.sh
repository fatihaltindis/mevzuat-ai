#!/bin/bash
set -e

echo ""
echo "  ⚖️  Mevzuat AI Başlatılıyor..."
echo "  ──────────────────────────────"
echo ""

# Go to script directory
cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "  ❌ Python3 bulunamadı!"
    echo "  macOS: brew install python3"
    echo "  Ubuntu: sudo apt install python3 python3-venv"
    exit 1
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "  📦 İlk kurulum yapılıyor..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt --quiet
else
    source .venv/bin/activate
fi

echo "  ✅ Tarayıcınızda açılıyor..."
echo "  Kapatmak için Ctrl+C basın."
echo ""

streamlit run app.py --server.headless true --browser.gatherUsageStats false
