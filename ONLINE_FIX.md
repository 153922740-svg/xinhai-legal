# 🚨 线上 API 修复指南

**问题**: 小程序登录返回 500 错误  
**时间**: 2026-05-17 13:50  
**状态**: 需要手动修复 Nginx 配置

---

## 🔍 问题分析

**当前配置**:
- Nginx 将 `/api/v1/` 转发到端口 `8081` (Hermes 服务)
- 我们的 API 运行在端口 `5000`

**结果**: 小程序调用线上 API 时访问的是错误的服务

---

## ✅ 解决方案

### 方案一：手动更新 Nginx 配置（推荐）

**步骤**:

1. SSH 登录服务器
```bash
ssh root@8.218.93.213
密码：Chen0812*
```

2. 备份 Nginx 配置
```bash
cp /etc/nginx/conf.d/xinclaw.conf /etc/nginx/conf.d/xinclaw.conf.bak
```

3. 编辑 Nginx 配置
```bash
vi /etc/nginx/conf.d/xinclaw.conf
```

4. 找到以下行（约第 80-90 行）:
```
location /api/v1/ {
    proxy_pass http://127.0.0.1:8081/api/;
```

5. 修改为:
```
location /api/v1/ {
    proxy_pass http://127.0.0.1:5000/api/;
```

6. 保存并退出 (`:wq`)

7. 测试并重启 Nginx
```bash
nginx -t
nginx -s reload
```

8. 测试 API
```bash
curl -X POST https://xinclaw.xhacca.cn/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","code":"888888"}'
```

应该返回:
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {...}
}
```

---

### 方案二：临时使用 IP:端口 测试

如果暂时无法修改 Nginx，可以先直接用 IP:端口测试：

**修改小程序 app.js**:
```javascript
// 临时测试用
API_BASE: 'http://8.218.93.213:5000/api/v1'
```

**注意**: 这只能用于测试，正式上线必须配置域名和 HTTPS。

---

### 方案三：使用本地测试环境

在本地启动 API 服务，小程序连接本地：

**修改小程序 app.js**:
```javascript
// 本地测试
API_BASE: 'http://localhost:5000/api/v1'
```

**注意**: 需要关闭小程序校验合法域名（开发者工具 → 详情 → 本地设置 → 不校验合法域名）。

---

## 📋 当前状态

| 服务 | 端口 | 状态 |
|------|------|------|
| API 服务 | 5000 | ✅ 运行中 |
| Hermes 服务 | 8081 | ✅ 运行中 |
| Nginx | 80/443 | ⚠️ 配置指向 8081 |
| 小程序 | - | ❌ 登录失败 (500) |

---

## ✅ 修复后验证

修复 Nginx 配置后，请测试:

1. **API 测试**:
```bash
curl -X POST https://xinclaw.xhacca.cn/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","code":"888888"}'
```

2. **小程序测试**:
- 重新编译小程序
- 测试登录功能
- 应该显示"登录成功"

---

## 📞 需要帮助？

如果需要我协助修复 Nginx 配置，请告诉我！

---

**心海法律 AI · 开发团队**  
2026-05-17 13:50
