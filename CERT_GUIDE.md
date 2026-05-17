# 🔐 微信支付证书配置指南

**更新时间**: 2026-05-17  
**状态**: 等待证书上传

---

## 📁 证书文件说明

### 需要的证书文件

| 文件名 | 说明 | 用途 |
|--------|------|------|
| apiclient_cert.pem | API 证书 | 身份验证 |
| apiclient_key.pem | API 证书私钥 | 签名请求 |

### 证书存放路径

**服务器路径**: `/home/admin/xinhai-legal/cert/`

```
/home/admin/xinhai-legal/cert/
├── apiclient_cert.pem
└── apiclient_key.pem
```

---

## 📥 获取证书步骤

### 步骤 1: 登录微信支付商户平台

访问：https://pay.weixin.qq.com

### 步骤 2: 进入 API 安全设置

```
账户中心 → API 安全 → 申请 API 证书
```

### 步骤 3: 下载证书

1. 点击"申请证书"
2. 填写申请信息
3. 下载证书文件（通常是压缩包）
4. 解压得到：
   - apiclient_cert.pem
   - apiclient_key.pem

### 步骤 4: 上传到服务器

**Mac 上传命令**:
```bash
# 假设证书在桌面
scp ~/Desktop/apiclient_cert.pem root@8.218.93.213:/home/admin/xinhai-legal/cert/
scp ~/Desktop/apiclient_key.pem root@8.218.93.213:/home/admin/xinhai-legal/cert/
```

**密码**: `Chen0812*`

**Windows 上传**:
使用 SCP 工具（如 WinSCP、FileZilla）上传到上述路径

---

## ✅ 验证证书

上传完成后，在服务器上验证:

```bash
# 检查证书文件
ls -la /home/admin/xinhai-legal/cert/

# 查看证书信息
openssl x509 -in /home/admin/xinhai-legal/cert/apiclient_cert.pem -text -noout
```

---

## 🔧 配置 API 调用

证书上传后，API 会自动使用证书进行微信支付调用。

**配置路径**: `/home/admin/xinhai_legal_api/.env`

```
WECHAT_CERT_PATH=/home/admin/xinhai-legal/cert/apiclient_cert.pem
WECHAT_KEY_PATH=/home/admin/xinhai-legal/cert/apiclient_key.pem
```

---

## ⚠️ 注意事项

1. **证书有效期**: 证书有效期为 1 年，到期需重新申请
2. **证书安全**: 不要泄露私钥文件 (apiclient_key.pem)
3. **备份证书**: 建议本地备份证书文件
4. **权限设置**: 证书文件权限应设置为 600

```bash
chmod 600 /home/admin/xinhai-legal/cert/*.pem
```

---

## 📞 上传完成后告诉我

证书上传完成后，请告诉我，我会：
1. 验证证书文件
2. 更新 API 配置
3. 测试支付接口
4. 生成测试报告

---

**心海法律 AI · 开发团队**  
2026-05-17
