#!/bin/bash
# AVP Platform - 啟動腳本

set -e

echo "🎬 AVP Platform - Starting..."
echo ""

# 檢查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python $PYTHON_VERSION"

# 檢查依賴
echo ""
echo "📦 Checking dependencies..."
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv venv
fi

source venv/bin/activate

# 安裝依賴
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
    echo "✅ Dependencies installed"
fi

# 檢查環境配置
echo ""
echo "🔧 Checking environment..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
fi

# 數據庫檢查 (可選)
echo ""
echo "💾 Database status (optional - skip if not configured)"
# TODO: 添加 PostgreSQL/Neo4j/Milvus 連接檢查

# 啟動應用
echo ""
echo "🚀 Starting AVP Platform..."
echo "   URL: http://localhost:8888"
echo "   Docs: http://localhost:8888/docs"
echo ""

# 設置環境變數
export PYTHONPATH=$(pwd):$PYTHONPATH

# 啟動
if [ "$1" == "--dev" ]; then
    echo "🔧 Development mode (auto-reload enabled)"
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8888
else
    echo "📦 Production mode (4 workers)"
    uvicorn app.main:app --host 0.0.0.0 --port 8888 --workers 4
fi
