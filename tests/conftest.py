"""
Pytest 配置
"""
import pytest
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))


@pytest.fixture(scope="session")
def event_loop():
    """創建事件循環"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
