# 心海法律 AI - 端到端测试用例

**版本**: V1.0  
**创建日期**: 2026-05-18  
**负责人**: 铁壁（测试官）  
**执行频率**: 每次部署前必须执行

---

## 一、测试环境

| 项目 | 配置 |
|------|------|
| 测试环境 | http://localhost:8081 |
| 生产环境 | https://xinclaw.xhacca.cn |
| 测试账号 | 13800138000 |
| 测试验证码 | 888888（固定） |
| 数据库 | /home/admin/xinhai_legal_api/data/xinhai_legal.db |

---

## 二、核心业务流程测试

### 2.1 登录流程测试 🔴 P0

**测试目标**: 验证用户可以正常登录

**前置条件**: 
- 后端服务运行正常
- 数据库连接正常

**测试步骤**:

```python
def test_login_flow():
    """完整的登录流程测试"""
    
    # 步骤 1: 发送验证码
    print("步骤 1: 发送验证码")
    resp = requests.post(
        "http://localhost:8081/api/v1/auth/send_sms",
        json={"phone": "13800138000"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['code'] == 200, f"发送验证码失败：{data}"
    print(f"✅ 验证码发送成功")
    
    # 步骤 2: 登录
    print("步骤 2: 登录")
    code = data['data']['code']  # 测试环境返回验证码
    resp = requests.post(
        "http://localhost:8081/api/v1/auth/login",
        json={"phone": "13800138000", "code": code}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['code'] == 200, f"登录失败：{data}"
    assert 'token' in data['data'], "登录未返回 token"
    token = data['data']['token']
    print(f"✅ 登录成功，Token: {token[:20]}...")
    
    # 步骤 3: 验证 Token 可用
    print("步骤 3: 验证 Token")
    resp = requests.get(
        "http://localhost:8081/api/v1/member/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    print(f"✅ Token 验证成功")
    
    print("\n🎉 登录流程测试通过！")
```

**验收标准**:
- [ ] 验证码发送成功
- [ ] 登录成功并返回 Token
- [ ] Token 可以用于后续请求

---

### 2.2 会员购买流程测试 🔴 P0

**测试目标**: 验证用户可以查看套餐并购买

**前置条件**: 用户已登录

**测试步骤**:

```python
def test_member_purchase_flow(token):
    """会员购买流程测试"""
    
    # 步骤 1: 获取会员套餐列表
    print("步骤 1: 获取会员套餐")
    resp = requests.get("http://localhost:8081/api/v1/member/packages")
    assert resp.status_code == 200
    data = resp.json()
    assert data['code'] == 200, f"获取套餐失败：{data}"
    assert 'plans' in data['data'], "套餐列表为空"
    print(f"✅ 获取到 {len(data['data']['plans'])} 个套餐")
    
    # 步骤 2: 获取会员状态
    print("步骤 2: 获取会员状态")
    resp = requests.get(
        "http://localhost:8081/api/v1/member/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    print(f"✅ 会员状态获取成功")
    
    print("\n🎉 会员流程测试通过！")
```

**验收标准**:
- [ ] 套餐列表返回正确
- [ ] 会员状态查询正常
- [ ] 价格、天数等信息准确

---

### 2.3 文书生成流程测试 🔴 P0

**测试目标**: 验证用户可以生成法律文书

**前置条件**: 用户已登录

**测试步骤**:

```python
def test_document_generation(token):
    """文书生成流程测试"""
    
    # 步骤 1: 获取文书模板列表
    print("步骤 1: 获取文书模板")
    resp = requests.get("http://localhost:8081/api/v1/document/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert data['success'] == True, f"获取模板失败：{data}"
    print(f"✅ 获取到 {len(data['data']['templates'])} 个模板")
    
    # 步骤 2: 生成文书
    print("步骤 2: 生成文书")
    resp = requests.post(
        "http://localhost:8081/api/v1/document/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "template_id": "civil_complaint",
            "fields": {
                "plaintiff_name": "张三",
                "defendant_name": "李四",
                "claim": "请求判决离婚",
                "facts": "双方感情破裂，分居满两年"
            }
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['success'] == True, f"生成文书失败：{data}"
    print(f"✅ 文书生成成功")
    
    # 步骤 3: 获取文书列表
    print("步骤 3: 获取文书列表")
    resp = requests.get(
        "http://localhost:8081/api/v1/document/list",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    print(f"✅ 文书列表获取成功")
    
    print("\n🎉 文书生成流程测试通过！")
```

**验收标准**:
- [ ] 模板列表返回正确
- [ ] 文书生成成功
- [ ] 文书内容完整
- [ ] 文书列表可查询

---

### 2.4 AI 对话流程测试 🔴 P0

**测试目标**: 验证用户可以与 AI 进行法律咨询

**前置条件**: 用户已登录

**测试步骤**:

```python
def test_ai_chat(token):
    """AI 对话流程测试"""
    
    # 步骤 1: 发送对话消息
    print("步骤 1: 发送对话")
    resp = requests.post(
        "http://localhost:8081/api/v1/chat/send",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "我想咨询离婚流程",
            "conversation_id": "test_conv_001"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data['success'] == True, f"对话失败：{data}"
    print(f"✅ AI 回复：{data['data']['response'][:50]}...")
    
    # 步骤 2: 获取会话列表
    print("步骤 2: 获取会话列表")
    resp = requests.get(
        "http://localhost:8081/api/v1/chat/sessions",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    print(f"✅ 会话列表获取成功")
    
    # 步骤 3: 获取历史对话
    print("步骤 3: 获取历史对话")
    resp = requests.get(
        "http://localhost:8081/api/v1/chat/history",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    print(f"✅ 历史对话获取成功")
    
    print("\n🎉 AI 对话流程测试通过！")
```

**验收标准**:
- [ ] AI 回复正常
- [ ] 会话记录保存
- [ ] 历史对话可查询

---

## 三、接口兼容性测试

### 3.1 v1 兼容路由测试

**测试目标**: 验证所有 v1 兼容路由正常工作

**测试用例**:

```python
def test_v1_compat_routes():
    """v1 兼容路由测试"""
    
    # Phase 4: 用户认证
    assert test_endpoint("POST", "/api/v1/auth/send_sms", {"phone": "13800138000"})
    assert test_endpoint("POST", "/api/v1/auth/login", {"phone": "13800138000", "code": "888888"})
    
    # Phase 2: 会员系统
    assert test_endpoint("GET", "/api/v1/member/packages")
    
    # Phase 3: 文书生成
    assert test_endpoint("GET", "/api/v1/document/templates")
    
    # Phase 3: AI 对话
    assert test_endpoint("POST", "/api/v1/chat/send", {"message": "测试"})
    
    print("\n🎉 所有 v1 兼容路由测试通过！")

def test_endpoint(method, path, data=None):
    """通用接口测试函数"""
    url = f"http://localhost:8081{path}"
    if method == "GET":
        resp = requests.get(url)
    else:
        resp = requests.post(url, json=data)
    
    assert resp.status_code == 200, f"{path} 返回 {resp.status_code}"
    print(f"✅ {method} {path} 正常")
    return True
```

---

## 四、异常场景测试

### 4.1 错误处理测试

```python
def test_error_handling():
    """错误处理测试"""
    
    # 测试 401: 未认证
    resp = requests.get("http://localhost:8081/api/v1/member/status")
    assert resp.status_code == 401, "未认证应返回 401"
    print("✅ 401 错误处理正确")
    
    # 测试 400: 参数错误
    resp = requests.post(
        "http://localhost:8081/api/v1/auth/send_sms",
        json={"phone": "123"}  # 无效手机号
    )
    assert resp.status_code in [400, 500], "参数错误应返回 400 或 500"
    print("✅ 400 错误处理正确")
    
    # 测试 404: 接口不存在
    resp = requests.get("http://localhost:8081/api/v1/nonexistent")
    assert resp.status_code == 404, "接口不存在应返回 404"
    print("✅ 404 错误处理正确")
    
    print("\n🎉 错误处理测试通过！")
```

---

## 五、性能测试

### 5.1 响应时间测试

```python
def test_response_time():
    """响应时间测试"""
    
    endpoints = [
        ("GET", "/api/v1/health"),
        ("POST", "/api/v1/auth/send_sms", {"phone": "13800138000"}),
        ("GET", "/api/v1/member/packages"),
    ]
    
    for ep in endpoints:
        method = ep[0]
        path = ep[1]
        data = ep[2] if len(ep) > 2 else None
        
        start = time.time()
        if method == "GET":
            requests.get(f"http://localhost:8081{path}")
        else:
            requests.post(f"http://localhost:8081{path}", json=data)
        elapsed = time.time() - start
        
        assert elapsed < 2.0, f"{path} 响应时间过长：{elapsed}s"
        print(f"✅ {path} 响应时间：{elapsed*1000:.0f}ms")
    
    print("\n🎉 性能测试通过！")
```

---

## 六、测试执行

### 6.1 本地测试

```bash
# 安装依赖
pip install requests pytest

# 运行测试
pytest tests/e2e_test.py -v

# 生成报告
pytest tests/e2e_test.py --html=report.html
```

### 6.2 CI/CD集成

```yaml
# .github/workflows/e2e-test.yml
name: E2E Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run E2E Tests
        run: pytest tests/e2e_test.py -v
```

### 6.3 测试报告模板

```markdown
# E2E 测试报告

**日期**: 2026-05-18
**执行人**: 铁壁
**环境**: 测试环境

## 测试结果
- 总用例数：20
- 通过：18
- 失败：2
- 通过率：90%

## 失败用例
1. 文书生成流程 - Token 过期处理
2. AI 对话流程 - 长文本响应

## 问题汇总
1. 部分接口未处理 Token 过期
2. 长文本响应超时

## 改进建议
1. 添加 Token 刷新机制
2. 优化长文本处理
```

---

## 七、验收标准

### 7.1 上线标准

- [ ] 所有 P0 测试用例通过
- [ ] 测试通过率 ≥ 95%
- [ ] 无严重 Bug
- [ ] 性能达标（响应时间 < 2s）

### 7.2 回归测试

每次代码提交后必须执行：
- [ ] 登录流程测试
- [ ] 核心业务测试
- [ ] 错误处理测试

---

**心海法律 AI · 测试团队**  
2026-05-18
