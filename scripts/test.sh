#!/bin/bash
# AVP Platform - 測試腳本

set -e

echo "🧪 AVP Platform - Running Tests..."
echo ""

# 激活虛擬環境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 安裝測試依賴
pip install -q pytest pytest-async pytest-cov

# 運行測試
echo "📊 Running unit tests..."
python -m pytest tests/unit/ \
    -v \
    --tb=short \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    "$@"

echo ""
echo "✅ Tests completed!"
echo "📊 Coverage report: htmlcov/index.html"
