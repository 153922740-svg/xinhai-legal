# 心海法律 AI - PRD v4.0 数据库迁移完成报告

## 执行摘要

**迁移日期**: 2026-05-15  
**数据库路径**: `/root/xinhai-legal/data/xinhai_legal.db`  
**迁移状态**: ✅ 完成

---

## 一、迁移内容

### 1.1 新建核心表 (10 张)

| 序号 | 表名 | 说明 | 关键字段数 |
|------|------|------|-----------|
| 1 | users (扩展) | 用户表，新增心理画像 6 维度字段 | +9 字段 |
| 2 | chat_logs | 聊天记录表 | 14 字段 |
| 3 | psych_profiles | 心理画像表 (6 维度) | 12 字段 |
| 4 | consultation_intents | 咨询意向表 | 15 字段 |
| 5 | orders | 订单表 (动态价格) | 20 字段 |
| 6 | payments | 支付记录表 | 16 字段 |
| 7 | deliveries | 交付记录表 | 15 字段 |
| 8 | system_prompts | 提示词库表 | 14 字段 |
| 9 | pricing_strategies | 定价策略表 | 17 字段 |
| 10 | optimization_logs | 优化日志表 | 16 字段 |

### 1.2 users 表扩展字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| psych_openness | REAL | 心理开放性 (0-10) |
| psych_conscientiousness | REAL | 心理尽责性 (0-10) |
| psych_extraversion | REAL | 心理外向性 (0-10) |
| psych_agreeableness | REAL | 心理宜人性 (0-10) |
| psych_neuroticism | REAL | 心理神经质 (0-10) |
| psych_risk_tolerance | REAL | 风险承受度 (0-10) |
| consultation_preference | TEXT | 咨询偏好 (text/voice/video) |
| last_consultation_at | TIMESTAMP | 最后咨询时间 |
| total_consultations | INTEGER | 总咨询次数 |

### 1.3 索引创建

共创建 **24+** 个索引，包括：
- 用户相关索引 (user_id 外键)
- 状态索引 (status 字段)
- 时间索引 (created_at 字段)
- 类型索引 (order_type, delivery_type 等)
- 唯一索引 (order_no, payment_no, delivery_no)

---

## 二、文件清单

### 2.1 创建的文件

| 文件路径 | 说明 |
|----------|------|
| `/root/xinhai-legal/docs/PRD_v4_Database_Design.md` | 数据库设计文档 (12KB) |
| `/root/xinhai-legal/migrations/001_prd_v4_core_tables.sql` | SQL 迁移脚本 (20KB) |
| `/root/xinhai-legal/migrations/migrate_prd_v4.py` | Python 迁移工具 (14KB) |
| `/root/xinhai-legal/migrations/verify_migration.py` | 验证脚本 (3KB) |
| `/root/xinhai-legal/models/db.py` | 模型定义 (已更新) |

### 2.2 修改的文件

| 文件路径 | 修改内容 |
|----------|----------|
| `/root/xinhai-legal/models/db.py` | 在 `init_db()` 函数中添加 10 张新表的创建逻辑 |

---

## 三、表结构详情

### 3.1 chat_logs (聊天记录)
- 支持 session 会话管理
- 记录消息类型 (user/assistant/system)
- 支持内容向量 embedding 存储
- 记录模型使用情况、token 消耗、响应时间
- 支持用户反馈 (is_helpful, feedback_comment)

### 3.2 psych_profiles (心理画像)
- 基于大五人格理论 + 风险承受度 (6 维度)
- 每个维度 0-10 分范围约束
- 支持多种评估来源 (questionnaire/behavior/ai_analysis)
- 记录评估置信度

### 3.3 consultation_intents (咨询意向)
- 意向类型：initial/follow_up/urgent/referral
- 紧急程度：low/medium/high/critical
- 状态流转：new → contacted → qualified → converted/lost
- 支持代理分配和来源追踪

### 3.4 orders (订单表)
- 支持动态定价 (pricing_strategy_id 外键)
- 订单类型：consultation/membership/token_package/legal_doc
- 状态机：pending → paid → processing → completed
- 支持优惠券、代理分佣

### 3.5 payments (支付记录)
- 多种支付方式：wechat/alipay/card/bank_transfer/token
- 支付状态：pending/processing/success/failed/refunded
- 记录第三方交易 ID
- 支持部分退款

### 3.6 deliveries (交付记录)
- 交付类型：consultation_session/document/token_credit/service_access
- 支持文件 URL 列表
- 记录咨询师、咨询时间、平台链接
- 支持过期时间管理

### 3.7 system_prompts (提示词库)
- 分类管理：consultation/legal_analysis/doc_generation 等
- 版本控制
- 支持变量定义 (JSON)
- 性能评分和使用统计

### 3.8 pricing_strategies (定价策略)
- 策略类型：fixed/dynamic/tiered/time_based/user_segment
- 支持价格区间约束 (min/max)
- 折扣规则 (JSON)
- A/B 测试分组支持

### 3.9 optimization_logs (优化日志)
- 优化类型：prompt/pricing/model/ux/conversion
- 实验管理 (experiment_id, variant)
- 统计显著性检验支持
- 结论和实施跟踪

---

## 四、数据完整性约束

### 4.1 CHECK 约束
- 心理画像维度：0-10 范围
- 消息类型：user/assistant/system
- 订单状态：pending/paid/processing/completed/refunded/cancelled
- 支付状态：pending/success/failed/refunded
- 交付状态：pending/delivered/confirmed/expired

### 4.2 UNIQUE 约束
- users.username
- orders.order_no
- payments.payment_no
- deliveries.delivery_no
- system_prompts (prompt_name, version) 组合唯一

### 4.3 外键约束
- 所有用户相关表都有 ON DELETE CASCADE
- orders → pricing_strategies
- payments → orders
- deliveries → orders

---

## 五、使用方法

### 5.1 执行迁移
```bash
# 方式 1: 使用 Python 迁移工具
python3 /root/xinhai-legal/migrations/migrate_prd_v4.py

# 方式 2: 使用 SQL 脚本
sqlite3 /root/xinhai-legal/data/xinhai_legal.db < /root/xinhai-legal/migrations/001_prd_v4_core_tables.sql

# 方式 3: 通过应用初始化 (自动创建)
python3 -c "from models.db import init_db; init_db('/root/xinhai-legal/data/xinhai_legal.db')"
```

### 5.2 验证迁移
```bash
python3 /root/xinhai-legal/migrations/verify_migration.py
```

### 5.3 数据库备份
```bash
cp /root/xinhai-legal/data/xinhai_legal.db \
   /root/xinhai-legal/data/xinhai_legal.db.backup.$(date +%Y%m%d_%H%M%S)
```

---

## 六、后续工作建议

1. **数据迁移**: 如有现有数据，需要编写数据迁移脚本
2. **API 更新**: 更新相关 API 接口以支持新表
3. **前端适配**: 更新前端界面以展示新功能
4. **测试**: 编写单元测试和集成测试
5. **文档**: 更新 API 文档和用户手册

---

## 七、联系信息

如有疑问，请参考:
- 数据库设计文档：`/root/xinhai-legal/docs/PRD_v4_Database_Design.md`
- 迁移脚本：`/root/xinhai-legal/migrations/`

---

*报告生成时间：2026-05-15*
