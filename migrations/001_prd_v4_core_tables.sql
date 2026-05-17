-- ============================================================
-- 心海法律 AI - PRD v4.0 数据库迁移脚本
-- 创建 10 张核心表
-- 执行日期：2026-05-15
-- ============================================================

PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;

-- ============================================================
-- 1. 备份提示 (执行前请手动备份)
-- ============================================================
-- 在命令行执行：
-- cp /root/xinhai-legal/data/xinhai_legal.db /root/xinhai-legal/data/xinhai_legal.db.backup.$(date +%Y%m%d_%H%M%S)

-- ============================================================
-- 2. 扩展 users 表 - 添加心理画像和咨询相关字段
-- ============================================================

-- 添加心理画像 6 维度字段
ALTER TABLE users ADD COLUMN psych_openness REAL DEFAULT 5.0;
ALTER TABLE users ADD COLUMN psych_conscientiousness REAL DEFAULT 5.0;
ALTER TABLE users ADD COLUMN psych_extraversion REAL DEFAULT 5.0;
ALTER TABLE users ADD COLUMN psych_agreeableness REAL DEFAULT 5.0;
ALTER TABLE users ADD COLUMN psych_neuroticism REAL DEFAULT 5.0;
ALTER TABLE users ADD COLUMN psych_risk_tolerance REAL DEFAULT 5.0;

-- 添加咨询相关字段
ALTER TABLE users ADD COLUMN consultation_preference TEXT DEFAULT 'text' 
    CHECK(consultation_preference IN ('text', 'voice', 'video'));
ALTER TABLE users ADD COLUMN last_consultation_at TIMESTAMP;
ALTER TABLE users ADD COLUMN total_consultations INTEGER DEFAULT 0;

-- 为 users 表添加索引
CREATE INDEX IF NOT EXISTS idx_users_consultation_pref ON users(consultation_preference);
CREATE INDEX IF NOT EXISTS idx_users_last_consultation ON users(last_consultation_at);

-- ============================================================
-- 3. 创建 chat_logs 表 - 聊天记录
-- ============================================================

CREATE TABLE IF NOT EXISTS chat_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    message_type TEXT NOT NULL CHECK(message_type IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    content_embedding TEXT,  -- JSON array of floats
    model_used TEXT,
    tokens_used INTEGER DEFAULT 0,
    response_time_ms INTEGER DEFAULT 0,
    confidence_score REAL DEFAULT 0,
    is_helpful INTEGER,  -- 1=helpful, 0=not helpful, NULL=no feedback
    feedback_comment TEXT,
    metadata TEXT,  -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_logs_user ON chat_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_session ON chat_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_created ON chat_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_logs_type ON chat_logs(message_type);

-- ============================================================
-- 4. 创建 psych_profiles 表 - 心理画像 (6 维度)
-- ============================================================

CREATE TABLE IF NOT EXISTS psych_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    openness REAL DEFAULT 5.0 CHECK(openness >= 0 AND openness <= 10),
    conscientiousness REAL DEFAULT 5.0 CHECK(conscientiousness >= 0 AND conscientiousness <= 10),
    extraversion REAL DEFAULT 5.0 CHECK(extraversion >= 0 AND extraversion <= 10),
    agreeableness REAL DEFAULT 5.0 CHECK(agreeableness >= 0 AND agreeableness <= 10),
    neuroticism REAL DEFAULT 5.0 CHECK(neuroticism >= 0 AND neuroticism <= 10),
    risk_tolerance REAL DEFAULT 5.0 CHECK(risk_tolerance >= 0 AND risk_tolerance <= 10),
    assessment_source TEXT DEFAULT 'behavior' 
        CHECK(assessment_source IN ('questionnaire', 'behavior', 'ai_analysis', 'hybrid')),
    assessment_confidence REAL DEFAULT 0.5 CHECK(assessment_confidence >= 0 AND assessment_confidence <= 1),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_psych_profiles_user ON psych_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_psych_profiles_source ON psych_profiles(assessment_source);

-- ============================================================
-- 5. 创建 consultation_intents 表 - 咨询意向
-- ============================================================

CREATE TABLE IF NOT EXISTS consultation_intents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    intent_type TEXT NOT NULL DEFAULT 'initial'
        CHECK(intent_type IN ('initial', 'follow_up', 'urgent', 'referral')),
    legal_domain TEXT,
    case_type TEXT,
    urgency_level TEXT DEFAULT 'medium'
        CHECK(urgency_level IN ('low', 'medium', 'high', 'critical')),
    budget_range TEXT,
    preferred_contact TEXT,
    description TEXT,
    status TEXT DEFAULT 'new'
        CHECK(status IN ('new', 'contacted', 'qualified', 'converted', 'lost', 'archived')),
    assigned_agent_id INTEGER REFERENCES users(id),
    source TEXT DEFAULT 'web'
        CHECK(source IN ('web', 'app', 'referral', 'ad', 'social_media', 'offline')),
    converted_order_id INTEGER,
    priority_score REAL DEFAULT 0,
    notes TEXT,
    contacted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_consultation_intents_user ON consultation_intents(user_id);
CREATE INDEX IF NOT EXISTS idx_consultation_intents_status ON consultation_intents(status);
CREATE INDEX IF NOT EXISTS idx_consultation_intents_domain ON consultation_intents(legal_domain);
CREATE INDEX IF NOT EXISTS idx_consultation_intents_urgency ON consultation_intents(urgency_level);
CREATE INDEX IF NOT EXISTS idx_consultation_intents_created ON consultation_intents(created_at);

-- ============================================================
-- 6. 创建 orders 表 - 订单表 (动态价格)
-- ============================================================

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_type TEXT NOT NULL
        CHECK(order_type IN ('consultation', 'membership', 'token_package', 'legal_doc', 'custom_service')),
    product_id TEXT,
    product_name TEXT NOT NULL,
    original_price REAL NOT NULL DEFAULT 0,
    discount_rate REAL DEFAULT 1.0 CHECK(discount_rate >= 0 AND discount_rate <= 1),
    final_price REAL NOT NULL DEFAULT 0,
    pricing_strategy_id INTEGER REFERENCES pricing_strategies(id),
    quantity INTEGER DEFAULT 1,
    tokens_included INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending'
        CHECK(status IN ('pending', 'paid', 'processing', 'shipped', 'completed', 'refunded', 'cancelled', 'expired')),
    payment_id INTEGER,
    delivery_id INTEGER,
    agent_id INTEGER REFERENCES users(id),
    commission_amount REAL DEFAULT 0,
    commission_rate REAL DEFAULT 0,
    coupon_code TEXT,
    coupon_discount REAL DEFAULT 0,
    ip_address TEXT,
    user_agent TEXT,
    remarks TEXT,
    paid_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_type ON orders(order_type);
CREATE INDEX IF NOT EXISTS idx_orders_no ON orders(order_no);

-- ============================================================
-- 7. 创建 payments 表 - 支付记录
-- ============================================================

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_no TEXT UNIQUE NOT NULL,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount REAL NOT NULL DEFAULT 0,
    currency TEXT DEFAULT 'CNY' CHECK(currency IN ('CNY', 'USD', 'EUR')),
    payment_method TEXT NOT NULL
        CHECK(payment_method IN ('wechat', 'alipay', 'card', 'bank_transfer', 'token', 'balance', 'combo')),
    payment_channel TEXT,
    transaction_id TEXT,  -- 第三方交易 ID
    status TEXT DEFAULT 'pending'
        CHECK(status IN ('pending', 'processing', 'success', 'failed', 'refunded', 'partial_refunded')),
    error_code TEXT,
    error_message TEXT,
    paid_at TIMESTAMP,
    refunded_at TIMESTAMP,
    refund_amount REAL DEFAULT 0,
    refund_reason TEXT,
    metadata TEXT,  -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_method ON payments(payment_method);
CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at);

-- ============================================================
-- 8. 创建 deliveries 表 - 交付记录
-- ============================================================

CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    delivery_no TEXT UNIQUE NOT NULL,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delivery_type TEXT NOT NULL
        CHECK(delivery_type IN ('consultation_session', 'document', 'token_credit', 'service_access', 'membership_activation')),
    content TEXT,  -- 交付内容描述
    file_urls TEXT,  -- JSON array of file URLs
    tokens_credited INTEGER DEFAULT 0,
    service_duration_min INTEGER DEFAULT 0,
    consultant_id INTEGER REFERENCES users(id),
    consultation_time TIMESTAMP,
    consultation_platform TEXT,
    consultation_link TEXT,
    status TEXT DEFAULT 'pending'
        CHECK(status IN ('pending', 'delivered', 'confirmed', 'in_progress', 'expired', 'cancelled')),
    confirmed_at TIMESTAMP,
    expires_at TIMESTAMP,
    delivery_method TEXT,
    tracking_info TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_deliveries_user ON deliveries(user_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_order ON deliveries(order_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries(status);
CREATE INDEX IF NOT EXISTS idx_deliveries_type ON deliveries(delivery_type);

-- ============================================================
-- 9. 创建 system_prompts 表 - 提示词库
-- ============================================================

CREATE TABLE IF NOT EXISTS system_prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_name TEXT NOT NULL,
    prompt_category TEXT NOT NULL
        CHECK(prompt_category IN ('consultation', 'legal_analysis', 'doc_generation', 
                                   'customer_service', 'case_summary', 'risk_assessment', 'other')),
    prompt_template TEXT NOT NULL,
    variables TEXT,  -- JSON object: {"var_name": {"type": "string", "required": true}}
    model_compatibility TEXT,  -- JSON array of model names
    version TEXT DEFAULT '1.0.0',
    is_active INTEGER DEFAULT 1,
    is_default INTEGER DEFAULT 0,
    performance_score REAL DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    avg_response_quality REAL DEFAULT 0,
    test_results TEXT,  -- JSON object with A/B test results
    created_by INTEGER REFERENCES users(id),
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_prompts_category ON system_prompts(prompt_category);
CREATE INDEX IF NOT EXISTS idx_system_prompts_active ON system_prompts(is_active);
CREATE INDEX IF NOT EXISTS idx_system_prompts_default ON system_prompts(is_default);
CREATE UNIQUE INDEX IF NOT EXISTS idx_system_prompts_name_version ON system_prompts(prompt_name, version);

-- ============================================================
-- 10. 创建 pricing_strategies 表 - 定价策略
-- ============================================================

CREATE TABLE IF NOT EXISTS pricing_strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,
    strategy_type TEXT NOT NULL
        CHECK(strategy_type IN ('fixed', 'dynamic', 'tiered', 'time_based', 'user_segment', 'bundle')),
    product_type TEXT NOT NULL,
    description TEXT,
    base_price REAL NOT NULL DEFAULT 0,
    min_price REAL DEFAULT 0,
    max_price REAL,
    currency TEXT DEFAULT 'CNY',
    discount_rules TEXT,  -- JSON object with discount conditions
    user_segment TEXT,  -- new/vip/agent/regular/student/etc
    time_range TEXT,  -- JSON: {"start": "HH:MM", "end": "HH:MM", "days": [0,1,2,3,4,5,6]}
    conditions TEXT,  -- JSON object with application conditions
    priority INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    is_exclusive INTEGER DEFAULT 0,  -- 是否排他 (只应用此策略)
    test_group TEXT,  -- A/B 测试分组
    performance_metrics TEXT,  -- JSON: {"conversion_rate": 0.1, "avg_order_value": 100}
    created_by INTEGER REFERENCES users(id),
    approved_by INTEGER REFERENCES users(id),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pricing_strategies_type ON pricing_strategies(strategy_type);
CREATE INDEX IF NOT EXISTS idx_pricing_strategies_product ON pricing_strategies(product_type);
CREATE INDEX IF NOT EXISTS idx_pricing_strategies_active ON pricing_strategies(is_active);
CREATE INDEX IF NOT EXISTS idx_pricing_strategies_segment ON pricing_strategies(user_segment);

-- ============================================================
-- 11. 创建 optimization_logs 表 - 优化日志
-- ============================================================

CREATE TABLE IF NOT EXISTS optimization_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    optimization_type TEXT NOT NULL
        CHECK(optimization_type IN ('prompt', 'pricing', 'model', 'ux', 'conversion', 'retention', 'other')),
    experiment_id TEXT NOT NULL,
    experiment_name TEXT NOT NULL,
    variant TEXT NOT NULL CHECK(variant IN ('A', 'B', 'C', 'D', 'control')),
    hypothesis TEXT,  -- 实验假设
    target_metric TEXT NOT NULL,
    baseline_value REAL DEFAULT 0,
    current_value REAL DEFAULT 0,
    improvement_rate REAL DEFAULT 0,
    sample_size INTEGER DEFAULT 0,
    confidence_level REAL DEFAULT 0,
    p_value REAL,
    statistical_significance INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running'
        CHECK(status IN ('planning', 'running', 'paused', 'completed', 'failed', 'inconclusive')),
    conclusion TEXT,
    recommendations TEXT,
    implemented INTEGER DEFAULT 0,
    implementation_date TIMESTAMP,
    metadata TEXT,  -- JSON object with additional data
    created_by INTEGER REFERENCES users(id),
    reviewed_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_optimization_logs_type ON optimization_logs(optimization_type);
CREATE INDEX IF NOT EXISTS idx_optimization_logs_status ON optimization_logs(status);
CREATE INDEX IF NOT EXISTS idx_optimization_logs_experiment ON optimization_logs(experiment_id);
CREATE INDEX IF NOT EXISTS idx_optimization_logs_created ON optimization_logs(created_at);

-- ============================================================
-- 12. 创建关联视图 (可选)
-- ============================================================

-- 用户完整信息视图
CREATE VIEW IF NOT EXISTS v_user_full_profile AS
SELECT 
    u.id,
    u.username,
    u.real_name,
    u.phone,
    u.email,
    u.role,
    u.membership,
    u.membership_end,
    u.tokens_balance,
    u.consultation_preference,
    u.total_consultations,
    u.last_consultation_at,
    pp.openness,
    pp.conscientiousness,
    pp.extraversion,
    pp.agreeableness,
    pp.neuroticism,
    pp.risk_tolerance,
    pp.assessment_confidence,
    u.created_at
FROM users u
LEFT JOIN psych_profiles pp ON u.id = pp.user_id;

-- 订单完整信息视图
CREATE VIEW IF NOT EXISTS v_order_full AS
SELECT 
    o.*,
    p.payment_method,
    p.status as payment_status,
    p.paid_at,
    d.delivery_type,
    d.status as delivery_status,
    d.confirmed_at
FROM orders o
LEFT JOIN payments p ON o.payment_id = p.id
LEFT JOIN deliveries d ON o.delivery_id = d.id;

-- 咨询意向转化漏斗视图
CREATE VIEW IF NOT EXISTS v_consultation_funnel AS
SELECT 
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM consultation_intents), 2) as percentage
FROM consultation_intents
GROUP BY status;

-- ============================================================
-- 13. 插入默认数据
-- ============================================================

-- 默认系统提示词
INSERT OR IGNORE INTO system_prompts (prompt_name, prompt_category, prompt_template, is_default, is_active)
VALUES 
    ('legal_consultation_default', 'consultation', 
     '你是一位专业的法律咨询助手。请根据用户的问题，提供专业的法律分析和建议。
     
用户问题：{{question}}
法律领域：{{domain}}
紧急程度：{{urgency}}

请按照以下结构回答：
1. 问题定性
2. 相关法律依据
3. 建议行动方案
4. 风险提示', 
     1, 1),
    ('legal_doc_generation', 'doc_generation',
     '请根据以下信息生成法律文书：
     
文书类型：{{doc_type}}
当事人信息：{{parties}}
事实描述：{{facts}}
诉求：{{claims}}

请生成规范的法律文书。',
     0, 1),
    ('case_risk_assessment', 'risk_assessment',
     '请对以下案件进行风险评估：
     
案件类型：{{case_type}}
基本事实：{{facts}}
证据情况：{{evidence}}

请评估：
1. 胜诉概率
2. 主要风险点
3. 风险应对建议',
     0, 1);

-- 默认定价策略
INSERT OR IGNORE INTO pricing_strategies (strategy_name, strategy_type, product_type, base_price, is_active, is_default)
VALUES 
    ('consultation_standard', 'fixed', 'consultation', 99.0, 1, 1),
    ('consultation_vip', 'user_segment', 'consultation', 79.0, 1, 0),
    ('membership_monthly', 'fixed', 'membership', 29.9, 1, 1),
    ('membership_quarterly', 'fixed', 'membership', 79.9, 1, 1),
    ('membership_yearly', 'fixed', 'membership', 299.0, 1, 1),
    ('token_package_small', 'fixed', 'token_package', 9.9, 1, 1),
    ('token_package_medium', 'fixed', 'token_package', 49.9, 1, 1),
    ('token_package_large', 'fixed', 'token_package', 199.0, 1, 1),
    ('night_discount', 'time_based', 'consultation', 69.0, 0, 0);

-- ============================================================
-- 14. 验证查询
-- ============================================================

-- 检查所有表是否创建成功
SELECT name, type FROM sqlite_master 
WHERE type IN ('table', 'view') 
AND name IN ('users', 'chat_logs', 'psych_profiles', 'consultation_intents', 
             'orders', 'payments', 'deliveries', 'system_prompts', 
             'pricing_strategies', 'optimization_logs',
             'v_user_full_profile', 'v_order_full', 'v_consultation_funnel')
ORDER BY type, name;

-- 检查索引
SELECT name, tbl_name FROM sqlite_master 
WHERE type = 'index' 
AND tbl_name IN ('users', 'chat_logs', 'psych_profiles', 'consultation_intents', 
                 'orders', 'payments', 'deliveries', 'system_prompts', 
                 'pricing_strategies', 'optimization_logs')
ORDER BY tbl_name, name;

-- ============================================================
-- 迁移完成
-- ============================================================
