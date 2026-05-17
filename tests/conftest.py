"""
心海法律 AI - 测试共享 Fixtures
提供测试用的临时数据库、FastAPI TestClient 等

注意：这是 pytest 风格的 conftest，仅适用于 test_api_fastapi.py 等 pytest 测试。
Unittest 风格的 test_chat_router.py 自行处理临时数据库，不受影响。
"""

import sys
import os
import json
import tempfile
import pytest
from typing import Generator, Dict

# 确保项目路径在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def db_path() -> Generator[str, None, None]:
    """创建临时数据库文件，测试会话结束后自动清理"""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    tmp.close()
    # 初始化数据库
    from models.db import init_db
    init_db(tmp.name)
    yield tmp.name
    os.unlink(tmp.name)


@pytest.fixture(scope="function")
def client(db_path: str) -> Generator[TestClient, None, None]:
    """
    提供 FastAPI TestClient，使用临时数据库
    """
    import yaml
    
    # 读取配置并临时修改数据库路径
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config.yaml'
    )
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 保存原始路径
    orig_path = config['database']['path']
    config['database']['path'] = db_path
    
    # 由于 main.py 在 import 时已初始化 db，我们直接在测试中操作
    # 注意：临时数据库已由 init_db 建表
    from app.main import app as fastapi_app
    with TestClient(fastapi_app) as c:
        yield c


@pytest.fixture(scope="function")
def sample_user(client: TestClient) -> Dict:
    """创建一个测试用户"""
    import os as _os
    response = client.post("/api/register", json={
        "username": f"testuser_{_os.urandom(4).hex()}",
        "password": "test123456",
        "phone": "13800138000"
    })
    return response.json()


@pytest.fixture(scope="function")
def auth_headers(sample_user: Dict) -> Dict:
    """提供认证 header（X-User-Id）"""
    return {"X-User-Id": str(sample_user["user"]["id"])}
