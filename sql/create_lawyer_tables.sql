-- ============================================================
-- 律师板块 - 16张数据库表
-- 创建于: 2026-05-20
-- ============================================================

-- 1. lawyer_profiles — 律师基本信息
CREATE TABLE IF NOT EXISTS lawyer_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    avatar TEXT,
    phone TEXT,
    email TEXT,
    law_firm TEXT,
    license_no TEXT,
    specialties TEXT,
    years_exp INTEGER,
    jurisdiction TEXT,
    bio TEXT,
    rating REAL DEFAULT 0,
    case_count INTEGER DEFAULT 0,
    fee_rate REAL,
    status TEXT DEFAULT 'pending',
    available INTEGER DEFAULT 1,
    fee_status TEXT DEFAULT 'unpaid',
    fee_expire_at TEXT,
    -- 合规改造：律所对公账户信息
    firm_bank_name TEXT DEFAULT '',
    firm_bank_account TEXT DEFAULT '',
    firm_license_url TEXT DEFAULT '',
    -- 实名认证信息
    real_name_verified INTEGER DEFAULT 0,
    real_name_idcard TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 2. lawyer_certifications — 资质认证
CREATE TABLE IF NOT EXISTS lawyer_certifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lawyer_id INTEGER NOT NULL,
    cert_type TEXT NOT NULL,
    file_url TEXT,
    status TEXT DEFAULT 'pending',
    remark TEXT,
    reviewed_by INTEGER,
    reviewed_at TEXT,
    expire_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 3. lawyer_specialties — 擅长领域标签
CREATE TABLE IF NOT EXISTS lawyer_specialties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lawyer_id INTEGER NOT NULL,
    specialty_tag TEXT NOT NULL,
    weight REAL DEFAULT 1.0
);

-- 4. lawyer_cases — 案件管理
CREATE TABLE IF NOT EXISTS lawyer_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lawyer_id INTEGER NOT NULL,
    user_id INTEGER,
    title TEXT NOT NULL,
    type TEXT,
    description TEXT,
    status TEXT DEFAULT 'pending',
    stage TEXT,
    fee REAL,
    court TEXT,
    case_no TEXT,
    opponent TEXT,
    urgency TEXT DEFAULT 'normal',
    started_at TEXT,
    closed_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 5. lawyer_case_documents — 案件材料
CREATE TABLE IF NOT EXISTS lawyer_case_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    doc_type TEXT,
    file_url TEXT,
    upload_by INTEGER,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 6. lawyer_case_timeline — 案件时间线
CREATE TABLE IF NOT EXISTS lawyer_case_timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    event_type TEXT,
    content TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 7. lawyer_reviews — 用户评价
CREATE TABLE IF NOT EXISTS lawyer_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER,
    reviewer_id INTEGER,
    rating INTEGER,
    dimension_ratings TEXT,
    content TEXT,
    reply TEXT,
    is_anonymous INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 8. lawyer_wallet — 律师钱包
CREATE TABLE IF NOT EXISTS lawyer_wallet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lawyer_id INTEGER UNIQUE NOT NULL,
    balance REAL DEFAULT 0,
    frozen REAL DEFAULT 0,
    pending REAL DEFAULT 0,
    total_income REAL DEFAULT 0,
    total_withdrawn REAL DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 9. lawyer_withdrawals — 提现记录
CREATE TABLE IF NOT EXISTS lawyer_withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lawyer_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    bank_account TEXT,
    status TEXT DEFAULT 'pending',
    remark TEXT,
    reviewed_by INTEGER,
    -- 合规改造：律所对公账户信息
    firm_bank_name TEXT DEFAULT '',
    firm_bank_account TEXT DEFAULT '',
    account_name TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 10. lawyer_commission_rules — 佣金配置
CREATE TABLE IF NOT EXISTS lawyer_commission_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lawyer_id INTEGER NOT NULL,
    platform_rate REAL DEFAULT 0.2,
    partner_rate REAL,
    agent_rate REAL,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 11. lawyer_settlements — 结算记录
CREATE TABLE IF NOT EXISTS lawyer_settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER,
    lawyer_id INTEGER NOT NULL,
    total_fee REAL,
    platform_commission REAL,
    lawyer_income REAL,
    status TEXT DEFAULT 'pending',
    settled_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 12. lawyer_schedules — 日程
CREATE TABLE IF NOT EXISTS lawyer_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lawyer_id INTEGER NOT NULL,
    event_type TEXT,
    event_time TEXT,
    content TEXT,
    case_id INTEGER,
    remind_before INTEGER,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 13. lawyer_ai_tool_logs — AI工具日志
CREATE TABLE IF NOT EXISTS lawyer_ai_tool_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lawyer_id INTEGER NOT NULL,
    tool_type TEXT,
    input_summary TEXT,
    output_summary TEXT,
    tokens_used INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 14. lawyer_complaints — 投诉
CREATE TABLE IF NOT EXISTS lawyer_complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER,
    complainant INTEGER,
    content TEXT,
    status TEXT DEFAULT 'pending',
    result TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 15. lawyer_collaboration — 协作空间
CREATE TABLE IF NOT EXISTS lawyer_collaboration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER,
    user_id INTEGER,
    msg_type TEXT,
    content TEXT,
    file_url TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

-- 16. lawyer_invites — 委托邀请
CREATE TABLE IF NOT EXISTS lawyer_invites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    lawyer_id INTEGER NOT NULL,
    case_title TEXT,
    case_type TEXT,
    description TEXT,
    status TEXT DEFAULT 'pending',
    expired_at TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
