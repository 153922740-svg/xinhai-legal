# 📱 心海法律 AI - 小程序 API 配置指南

**更新时间**: 2026-05-17 11:45  
**适用环境**: 微信小程序

---

## 🔧 服务器域名配置

### 登录小程序后台
1. 访问 https://mp.weixin.qq.com
2. 进入 开发 → 开发管理 → 开发设置
3. 服务器域名 配置

### request 合法域名
```
https://xinclaw.xhacca.cn
https://www.xinclaw.com.cn
```

### socket 合法域名（流式对话）
```
wss://xinclaw.xhacca.cn
```

### uploadFile 合法域名
```
https://xinclaw.xhacca.cn
```

### downloadFile 合法域名
```
https://xinclaw.xhacca.cn
```

---

## 📋 核心 API 接口清单

### 用户认证
| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/auth/login | POST | 手机号登录 |
| /api/v1/auth/wechat | POST | 微信授权登录 |
| /api/v1/user/profile | GET | 获取用户信息 |
| /api/v1/user/update | POST | 更新用户信息 |

### AI 对话
| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/chat/send | POST | 发送消息 |
| /api/v1/chat/stream | WebSocket | 流式响应 |
| /api/v1/conversations | GET | 会话列表 |
| /api/v1/conversations/{id} | GET | 会话详情 |

### 会员服务
| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/member/info | GET | 会员信息 |
| /api/v1/member/packages | GET | 套餐列表 |
| /api/v1/order/create | POST | 创建订单 |
| /api/v1/order/query | GET | 订单查询 |

### 支付接口
| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/pay/wechat | POST | 微信支付预下单 |
| /api/v1/pay/callback | POST | 支付回调 |
| /api/v1/pay/refund | POST | 申请退款 |

### 文书生成
| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/document/templates | GET | 模板列表 |
| /api/v1/document/generate | POST | 生成文书 |
| /api/v1/document/list | GET | 文书列表 |
| /api/v1/document/{id} | GET | 文书详情 |

### 数据看板
| 接口 | 方法 | 说明 |
|------|------|------|
| /api/v1/dashboard/stats | GET | 统计数据 |
| /api/v1/dashboard/trend | GET | 趋势数据 |
| /api/v1/dashboard/ranking | GET | 排行榜单 |

---

## 🔐 微信支付配置

### 已配置信息
```
APPID: wxdfc6a1991d0b3bec
MCHID: 1111669879
APIKEY: wxdfc6a1991d0b3becwxdfc6a1991d0b3bec (待更新为 32 位真密钥)
证书路径：/www/wwwroot/xinclaw-law/backend/cert/
回调地址：https://www.xinclaw.com.cn/api/callback/pay/wechat
```

### ⚠️ 待办事项
1. 登录 https://pay.weixin.qq.com 获取真正的 32 位 APIKEY
2. 替换当前配置中的 APIKEY
3. 测试支付流程

---

## 📱 新增页面路由

### 已创建页面
| 页面 | 路径 | 功能 |
|------|------|------|
| chat | pages/chat/chat | AI 法律咨询 |
| dashboard | pages/dashboard/dashboard | 数据看板 |

### 待创建页面
| 页面 | 路径 | 功能 | 优先级 |
|------|------|------|--------|
| verification | pages/verification/verification | 实名认证 | P1 |
| assistant | pages/assistant/assistant | 专属助手 | P1 |

---

## 🧪 测试步骤

### 1. 开发工具测试
1. 打开微信开发者工具
2. 导入小程序项目 (/home/admin/xinclaw-backup/miniprogram)
3. 配置 AppID: wxdfc6a1991d0b3bec
4. 编译并测试 chat 和 dashboard 页面

### 2. 真机测试
1. 在开发者工具中点击"预览"
2. 扫码在真机上测试
3. 验证 API 调用是否正常

### 3. 支付测试
1. 创建测试订单（金额 0.01 元）
2. 调用微信支付
3. 验证回调处理

---

## ⚠️ 注意事项

### iOS 虚拟支付限制
- 小程序内不能直接购买虚拟物品（会员、Token）
- 解决方案：
  - 方案 A: 引导至公众号 H5 支付
  - 方案 B: 使用"客服消息"引导
  - 方案 C: 线下扫码支付

### 内容安全
- 用户生成内容需调用微信内容安全 API
- 接口：/api/v1/security/check
- 检测类型：文本、图片

### 性能优化
- 首屏加载时间 < 3 秒
- 图片使用 webp 格式
- 合理使用缓存

---

**心海法律 AI · 开发团队**  
2026-05-17
