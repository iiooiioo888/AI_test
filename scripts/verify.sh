#!/bin/bash
# AVP Platform - 系統完整性檢查

set -e

echo "🔍 AVP Platform - System Verification"
echo "======================================"
echo ""

PASS=0
FAIL=0

# 檢查函數
check() {
    local name="$1"
    local command="$2"
    
    echo -n "Checking $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo "✅ PASS"
        ((PASS++))
        return 0
    else
        echo "❌ FAIL"
        ((FAIL++))
        return 1
    fi
}

# ============================================================================
# 1. 文件結構檢查
# ============================================================================
echo "📁 File Structure"
echo "-----------------"

check "app directory exists" "[ -d 'app' ]"
check "main.py exists" "[ -f 'app/main.py' ]"
check "config.py exists" "[ -f 'app/core/config.py' ]"
check "services directory" "[ -d 'app/services' ]"
check "narrative service" "[ -d 'app/services/narrative' ]"
check "prompt service" "[ -d 'app/services/prompt' ]"
check "auth service" "[ -d 'app/services/auth' ]"
check "tests directory" "[ -d 'tests' ]"
check "static files" "[ -d 'static' ]"
check "templates" "[ -d 'templates' ]"
check "scripts" "[ -d 'scripts' ]"

echo ""

# ============================================================================
# 2. Python 語法檢查
# ============================================================================
echo "🐍 Python Syntax Check"
echo "----------------------"

check "main.py syntax" "python3 -m py_compile app/main.py"
check "config syntax" "python3 -m py_compile app/core/config.py"
check "scene_state_machine syntax" "python3 -m py_compile app/services/narrative/scene_state_machine.py"
check "knowledge_graph syntax" "python3 -m py_compile app/services/narrative/knowledge_graph.py"
check "crdt_editor syntax" "python3 -m py_compile app/services/narrative/crdt_editor.py"
check "rbac syntax" "python3 -m py_compile app/services/auth/rbac.py"
check "narrative_engine syntax" "python3 -m py_compile app/services/narrative/narrative_engine.py"
check "prompt_optimizer syntax" "python3 -m py_compile app/services/prompt/prompt_optimizer.py"
check "rag_retriever syntax" "python3 -m py_compile app/services/prompt/rag_retriever.py"

echo ""

# ============================================================================
# 3. JavaScript 語法檢查
# ============================================================================
echo "📜 JavaScript Check"
echo "-------------------"

if command -v node &> /dev/null; then
    check "api.js syntax" "node --check static/js/api.js"
else
    echo "⚠️  Node.js not installed, skipping JS check"
fi

echo ""

# ============================================================================
# 4. 依賴檢查
# ============================================================================
echo "📦 Dependencies"
echo "---------------"

if [ -f "requirements.txt" ]; then
    check "requirements.txt exists" "[ -f 'requirements.txt' ]"
    
    # 檢查關鍵依賴
    if [ -d "venv" ]; then
        source venv/bin/activate
        check "fastapi installed" "python -c 'import fastapi'"
        check "pydantic installed" "python -c 'import pydantic'"
        check "structlog installed" "python -c 'import structlog'"
        check "neo4j installed" "python -c 'import neo4j'"
        check "pymilvus installed" "python -c 'import pymilvus'"
    else
        echo "⚠️  Virtual environment not found"
    fi
else
    echo "❌ requirements.txt not found"
    ((FAIL++))
fi

echo ""

# ============================================================================
# 5. 配置文件檢查
# ============================================================================
echo "⚙️  Configuration"
echo "-----------------"

check ".env.example exists" "[ -f '.env.example' ]"
check "docker-compose.yml" "[ -f 'docker-compose.yml' ]"
check "Dockerfile exists" "[ -f 'Dockerfile' ]"
check ".gitignore exists" "[ -f '.gitignore' ]"

echo ""

# ============================================================================
# 6. 文檔檢查
# ============================================================================
echo "📚 Documentation"
echo "----------------"

check "README.md exists" "[ -f 'README.md' ]"
check "QUICKSTART.md exists" "[ -f 'QUICKSTART.md' ]"
check "PHASE2_SUMMARY.md" "[ -f 'PHASE2_SUMMARY.md' ]"
check "TASKS.md exists" "[ -f 'TASKS.md' ]"

echo ""

# ============================================================================
# 7. 腳本檢查
# ============================================================================
echo "🔧 Scripts"
echo "----------"

check "start.sh exists" "[ -f 'scripts/start.sh' ]"
check "start.sh executable" "[ -x 'scripts/start.sh' ]"
check "test.sh exists" "[ -f 'scripts/test.sh' ]"
check "test.sh executable" "[ -x 'scripts/test.sh' ]"

echo ""

# ============================================================================
# 8. 測試檢查
# ============================================================================
echo "🧪 Tests"
echo "--------"

check "test_scene_state_machine.py" "[ -f 'tests/unit/test_scene_state_machine.py' ]"
check "test_crdt_editor.py" "[ -f 'tests/unit/test_crdt_editor.py' ]"
check "conftest.py" "[ -f 'tests/conftest.py' ]"

echo ""

# ============================================================================
# 總結
# ============================================================================
echo "======================================"
echo "📊 Verification Summary"
echo "======================================"
echo "✅ Passed: $PASS"
echo "❌ Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "🎉 All checks passed! System is ready."
    echo ""
    echo "Next steps:"
    echo "  1. Copy .env.example to .env and configure"
    echo "  2. Run: ./scripts/start.sh --dev"
    echo "  3. Open: http://localhost:8888"
    exit 0
else
    echo "⚠️  Some checks failed. Please fix the issues above."
    exit 1
fi
