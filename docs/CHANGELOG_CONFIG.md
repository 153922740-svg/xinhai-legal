# 心海法律 AI - 配置更新日志

**文档路径**: `/home/admin/xinhai_legal_api/docs/CHANGELOG_CONFIG.md`

---

## 2026-05-18 15:45 - 阿里云短信 SDK 集成

**更新人**: COO  
**更新类型**: 功能集成  
**影响范围**: 短信验证码发送

### 变更内容

| 项目 | 变更 | 说明 |
|------|------|------|
| SDK 安装 | ✅ 新增 | `aliyun-python-sdk-core 2.16.0` + `dysmsapi 2.1.2` |
| requirements.txt | ✅ 更新 | 添加阿里云短信 SDK 依赖 |
| phase8_user_auth_api.py | ✅ 更新 | 集成短信发送函数 |
| 发送模式 | ✅ 新增 | 支持开发模式（固定验证码）和生产模式（真实发送） |

### 新增功能

1. **开发模式** (`DEV_MODE = True`)
   - 使用固定验证码 `888888`
   - 不真实发送短信
   - 不产生费用
   - 适合测试

2. **生产模式** (`DEV_MODE = False`)
   - 调用阿里云短信 API
   - 真实发送短信
   - 产生费用（约 0.045 元/条）
   - 适合正式环境

### 更新文件
- [x] `/home/admin/xinhai_legal_api/requirements.txt`
- [x] `/home/admin/xinhai_legal_api/phase8_user_auth_api.py`
- [x] `/home/admin/xinhai_legal_api/SENSITIVE_INFO.md`
- [x] `/home/admin/xinhai_legal_api/docs/CHANGELOG_CONFIG.md` (本文档)
- [x] `/home/admin/xinhai_legal_api/docs/阿里云短信 SDK 集成报告.md` (新建)

### 测试建议
1. 开发模式测试（不扣费）
2. 登录流程验证
3. 生产模式测试（需审批）

### 状态
✅ SDK 已集成  
✅ 代码已更新  
⏳ 待测试验证

---

## 2026-05-18 15:00 - 支付回调地址修正

**更新人**: COO  
**更新原因**: 发现原回调地址域名无法访问，修正为实际可用域名

### 变更内容

| 配置项 | 原值 | 新值 | 说明 |
|--------|------|------|------|
| WECHAT_NOTIFY_URL | `https://www.xinclaw.com.cn/api/callback/pay/wechat` | `https://xinclaw.xhacca.cn/api/callback/pay/wechat` | 域名修正 |

### 验证结果

**域名可用性测试**:
```bash
# www.xinclaw.com.cn - 无法访问 ❌
curl -sI https://www.xinclaw.com.cn/
# 返回：空

# xinclaw.xhacca.cn - 可访问 ✅
curl -sI https://xinclaw.xhacca.cn/
# 返回：HTTP/1.1 200 OK
```

**API 健康检查**:
```bash
curl -s https://xinclaw.xhacca.cn/api/v1/health
# 返回：{"status":"ok","message":"心海法律 AI API 服务运行中","version":"1.1.0"}
```

### 更新文件
- [x] `/home/admin/xinhai_legal_api/.env`
- [x] `/home/admin/xinhai_legal_api/SENSITIVE_INFO.md`
- [x] `/home/admin/xinhai_legal_api/MINIPROGRAM_API_CONFIG.md`
- [x] `/home/admin/xinhai_legal_api/docs/CHANGELOG_CONFIG.md` (本文档)

### 影响范围
- 微信支付回调通知
- 会员购买支付结果
- Token 充值支付结果

### 状态
✅ 配置已修正  
✅ 域名已验证可用  
⏳ 待支付测试验证

---

## 2026-05-18 14:45 - 微信支付配置更新（小程序）

**更新人**: COO  
**更新原因**: 用户提供真实微信支付配置 (wechat_pay.txt)  
**支付类型**: 微信小程序支付

### 变更内容

| 配置项 | 原值 | 新值 | 来源 |
|--------|------|------|------|
| WECHAT_APPID | wxdfc6a1991d0b3bec | wx73612d8efb98658d | wechat_pay.txt |
| WECHAT_MCHID | 1111669879 | 1745164408 | wechat_pay.txt |
| WECHAT_APIKEY | wxdfc6...3bec (示例) | Xinclaw2026xinhaifalvzixunxincla | wechat_pay.txt |

### 更新文件
- [x] `/home/admin/xinhai_legal_api/.env`
- [x] `/home/admin/xinhai_legal_api/SENSITIVE_INFO.md`
- [x] `/home/admin/xinhai_legal_api/docs/CHANGELOG_CONFIG.md` (本文档)

### 影响范围
- 小程序微信支付接口：`POST /api/v2/pay/wechat`
- 支付回调接口：`POST /api/v2/pay/callback/wechat`
- 小程序会员购买流程
- 小程序 Token 充值流程

### 验证步骤
1. 重启 API 服务
2. 小程序创建测试订单
3. 调用微信支付接口
4. 验证返回参数是否正确
5. 小程序调起支付
6. 测试支付回调

### 状态
✅ 配置已更新  
⏳ 待小程序测试验证

---

## 2026-05-18 14:30 - 初始敏感信息文档创建

**更新人**: COO  
**更新原因**: 项目配置整理，防止信息丢失

### 创建文档
- [x] `SENSITIVE_INFO.md` - 敏感信息配置
- [x] `API_DOCUMENTATION.md` - 完整接口文档
- [x] `DEV_PROGRESS_20260518.md` - 开发进度报告
- [x] `TEST_CHECKLIST.md` - 完整测试清单

### 包含信息
- 服务器信息
- 微信小程序配置
- API 密钥（大模型/支付/短信）
- 数据库配置
- 服务端口
- 目录结构

---

**维护人**: COO  
**最后更新**: 2026-05-18 15:00

---

*心海法律 AI · 配置更新日志 | 版本：1.1 | 2026-05-18*
