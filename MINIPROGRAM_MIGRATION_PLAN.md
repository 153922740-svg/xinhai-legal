# 📱 心海法律 AI - 小程序迁移计划

**制定时间**: 2026-05-17 11:30  
**制定人**: COO(心海)  
**目标**: 将 29 个 H5 页面迁移至微信小程序

---

## 📊 现状分析

| 类别 | 数量 | 状态 |
|------|------|------|
| H5 页面总数 | 29 个 | ✅ 已完成 |
| 小程序已有页面 | 25 个 | ✅ 可复用 |
| 需新增页面 | 4 个 | ⏳ 待开发 |
| 需优化页面 | 6 个 | ⏳ 待优化 |

---

## 📋 页面对比清单

### ✅ 已匹配页面（25 个）

| H5 页面 | 小程序页面 | 状态 | 操作 |
|--------|-----------|------|------|
| index | index | ✅ | 直接复用 |
| document | document | ✅ | 直接复用 |
| doc-detail | doc-detail | ✅ | 直接复用 |
| member | member | ✅ | 直接复用 |
| recharge | recharge | ✅ | 直接复用 |
| partner | partner | ✅ | 直接复用 |
| agent-team | agent-team | ✅ | 直接复用 |
| login | login | ✅ | 直接复用 |
| profile | profile | ✅ | 优化更新 |
| signin | signin | ✅ | 优化更新 |
| mall | mall | ✅ | 直接复用 |
| integral | integral | ✅ | 直接复用 |
| history | history | ✅ | 直接复用 |
| review | review | ✅ | 直接复用 |
| order | order | ✅ | 直接复用 |
| help | help | ✅ | 直接复用 |
| feedback | feedback | ✅ | 直接复用 |
| about | about | ✅ | 直接复用 |
| activity | activity | ✅ | 优化更新 |
| archive | archive | ✅ | 优化更新 |
| evolution | evolution | ✅ | 优化更新 |
| notification | notifications | ✅ | 重命名 |
| payment-result | payment-result | ✅ | 直接复用 |
| webview | webview | ✅ | 直接复用 |
| promotion | promotion | ✅ | 直接复用 |

### ⏳ 缺失页面（4 个）

| 页面 | 功能 | 优先级 | 预计工时 |
|------|------|--------|---------|
| chat | AI 法律咨询 | P0 | 4h |
| dashboard | 数据看板 | P0 | 3h |
| verification | 实名认证 | P1 | 2h |
| assistant | 专属 AI 助手 | P1 | 3h |

---

## 🚀 迁移步骤

### 阶段 1：核心功能（P0）

**目标**: 确保小程序核心功能可用

1. **创建 chat 页面** (4h)
   - 复制 H5 chat.html 逻辑
   - 适配小程序 API 调用
   - 流式响应处理
   - 测试 AI 对话功能

2. **创建 dashboard 页面** (3h)
   - 数据看板 UI 实现
   - 图表组件集成
   - API 数据对接

3. **API 接口适配** (2h)
   - 配置小程序服务器域名
   - 测试所有 API 调用
   - 处理跨域问题

**小计**: 9 小时

### 阶段 2：增强功能（P1）

**目标**: 完善用户体验

1. **创建 verification 页面** (2h)
   - 实名认证表单
   - 身份证上传
   - 状态展示

2. **创建 assistant 页面** (3h)
   - 专属助手 UI
   - 对话入口
   - 能力展示

3. **优化现有页面** (3h)
   - profile 更新
   - signin 更新
   - activity 更新
   - archive 更新
   - evolution 更新
   - notification 重命名

**小计**: 8 小时

### 阶段 3：测试与上线（P2）

**目标**: 确保小程序稳定运行

1. **功能测试** (4h)
   - 所有页面跳转测试
   - API 调用测试
   - 支付流程测试

2. **性能优化** (2h)
   - 首屏加载优化
   - 图片资源压缩
   - 缓存策略

3. **微信审核准备** (2h)
   - 准备审核材料
   - 隐私政策更新
   - 用户协议更新

4. **提交审核** (1h)
   - 上传代码
   - 填写审核信息
   - 跟踪审核进度

**小计**: 9 小时

---

## ⏱️ 时间估算

| 阶段 | 工时 | 日历时间 |
|------|------|---------|
| 阶段 1: 核心功能 | 9h | 1-2 天 |
| 阶段 2: 增强功能 | 8h | 1-2 天 |
| 阶段 3: 测试上线 | 9h | 1-2 天 |
| **总计** | **26h** | **3-6 天** |

---

## 🔧 技术要点

### 1. API 调用适配

```javascript
// H5 fetch → 小程序 wx.request
// H5:
fetch('/api/v1/chat', { method: 'POST', body: JSON.stringify(data) })

// 小程序:
wx.request({
  url: 'https://xinclaw.xhacca.cn/api/v1/chat',
  method: 'POST',
  data: data,
  success: (res) => { ... }
})
```

### 2. 流式响应处理

```javascript
// 使用 WebSocket 或轮询实现流式效果
const socket = new WebSocket('wss://xinclaw.xhacca.cn/api/v1/chat/stream');
socket.onmessage = (event) => {
  // 更新聊天内容
};
```

### 3. 支付集成

```javascript
// 调用微信支付
wx.requestPayment({
  timeStamp: '',
  nonceStr: '',
  package: '',
  signType: 'MD5',
  paySign: '',
  success: (res) => { ... }
})
```

---

## ⚠️ 注意事项

### 微信小程序限制

1. **域名要求**
   - 必须备案
   - 必须 HTTPS
   - 需在后台配置白名单

2. **虚拟支付限制**
   - iOS 小程序禁止虚拟物品支付
   - 需使用 H5 支付或引导至公众号

3. **内容审核**
   - 用户生成内容需审核
   - 敏感词过滤
   - 图片内容安全检测

### 解决方案

1. **支付问题**: iOS 端引导至公众号或 H5 完成支付
2. **内容审核**: 集成微信内容安全 API
3. **域名配置**: 提前在小程序后台配置

---

## 📞 需要总裁决策

1. **小程序主体**: 使用哪个公司主体注册？
2. **支付配置**: 微信支付商户号是否已申请？
3. **上线时间**: 期望何时提交审核？
4. **iOS 支付**: 是否接受 H5 支付方案？

---

**下一步**: 等待总裁确认后，开始阶段 1 开发

**心海法律 AI · 开发团队**  
2026-05-17 11:30
