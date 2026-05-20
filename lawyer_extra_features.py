#!/usr/bin/env python3
"""心海法律 AI · 律师板块 — 新增功能：费率设置 + 消息通知 + 实名认证增强"""
import sqlite3, json, sys
from datetime import datetime

DB_PATH = "/home/admin/xinhai_legal_api/data/xinhai_legal.db"

def get_db():
    return sqlite3.connect(DB_PATH)

def json_ok(data=None):
    return json.dumps({"code": 200, "message": "success", "data": data}, ensure_ascii=False)

def json_err(msg, code=400):
    return json.dumps({"code": code, "message": msg, "data": None}, ensure_ascii=False)

# ==================== 建表 ====================
def create_extra_tables():
    """创建新增功能所需的表和字段"""
    conn = get_db()
    c = conn.cursor()
    
    # 消息通知表
    c.execute("""
        CREATE TABLE IF NOT EXISTS lawyer_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            is_read INTEGER DEFAULT 0,
            related_id INTEGER,
            related_type TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_notif_user ON lawyer_notifications(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_notif_unread ON lawyer_notifications(user_id, is_read)")
    
    # 律师费率表（独立的费率配置表）
    c.execute("""
        CREATE TABLE IF NOT EXISTS lawyer_rate_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            fee_rate REAL DEFAULT 10.0,
            is_accepting INTEGER DEFAULT 1,
            min_fee REAL DEFAULT 0,
            max_fee REAL DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    
    # 兼容旧字段
    try:
        c.execute("ALTER TABLE lawyer_profiles ADD COLUMN is_accepting INTEGER DEFAULT 1")
    except Exception:
        pass
    
    conn.commit()
    conn.close()
    return json_ok({"message": "额外表初始化完成"})

# ==================== 辅助：发送通知 ====================
def add_notification(user_id, ntype, title, content="", related_id=None, related_type=None):
    """供其他模块调用的发送通知函数"""
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO lawyer_notifications (user_id, type, title, content, related_id, related_type) VALUES (?,?,?,?,?,?)",
        (user_id, ntype, title, content, related_id, related_type)
    )
    conn.commit()
    nid = c.lastrowid
    conn.close()
    return nid

# ==================== 费率设置 ====================
def handle_rate_set(params):
    """POST /api/lawyer/rate/set — 设置费率"""
    user_id = params.get("user_id")
    fee_rate = params.get("fee_rate")
    is_accepting = params.get("is_accepting")
    
    if not user_id:
        return json_err("缺少 user_id")
    
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 检查是否存在
    c.execute("SELECT id FROM lawyer_rate_config WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    if row:
        updates = []
        vals = []
        if fee_rate is not None:
            updates.append("fee_rate = ?")
            vals.append(float(fee_rate))
        if is_accepting is not None:
            updates.append("is_accepting = ?")
            vals.append(1 if is_accepting else 0)
        updates.append("updated_at = ?")
        vals.append(now)
        vals.append(user_id)
        c.execute(f"UPDATE lawyer_rate_config SET {', '.join(updates)} WHERE user_id = ?", vals)
    else:
        c.execute(
            "INSERT INTO lawyer_rate_config (user_id, fee_rate, is_accepting, updated_at) VALUES (?,?,?,?)",
            (user_id, float(fee_rate or 10.0), 1 if is_accepting is None or is_accepting else 0, now)
        )
    
    # 同步更新 lawyer_profiles
    if fee_rate is not None:
        c.execute("UPDATE lawyer_profiles SET fee_rate = ?, updated_at = ? WHERE user_id = ?", (float(fee_rate), now, user_id))
    
    conn.commit()
    conn.close()
    return json_ok({"message": "费率设置成功", "fee_rate": fee_rate, "is_accepting": is_accepting})

def handle_rate_info(params):
    """GET /api/lawyer/rate/info — 查询费率"""
    user_id = params.get("user_id")
    if not user_id:
        return json_err("缺少 user_id")
    
    conn = get_db()
    c = conn.cursor()
    
    # 从rate_config查
    c.execute("SELECT fee_rate, is_accepting, min_fee, max_fee FROM lawyer_rate_config WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    if not row:
        # 从profiles查
        c.execute("SELECT fee_rate, is_accepting FROM lawyer_profiles WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return json_ok({"user_id": user_id, "fee_rate": None, "is_accepting": True, "configured": False})
    
    conn.close()
    return json_ok({
        "user_id": user_id,
        "fee_rate": row[0] if row else None,
        "is_accepting": bool(row[1]) if row and len(row) > 1 else True,
        "configured": True
    })

# ==================== 消息通知 ====================
def handle_notification_list(params):
    """GET /api/lawyer/notification/list — 通知列表"""
    user_id = params.get("user_id")
    page = int(params.get("page", 1))
    page_size = int(params.get("page_size", 20))
    offset = (page - 1) * page_size
    
    if not user_id:
        return json_err("缺少 user_id")
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM lawyer_notifications WHERE user_id = ?", (user_id,))
    total = c.fetchone()[0]
    
    c.execute(
        "SELECT id, type, title, content, is_read, related_id, related_type, created_at FROM lawyer_notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, page_size, offset)
    )
    items = []
    for row in c.fetchall():
        items.append({
            "id": row[0], "type": row[1], "title": row[2], "content": row[3],
            "is_read": bool(row[4]), "related_id": row[5], "related_type": row[6],
            "created_at": row[7]
        })
    conn.close()
    return json_ok({"total": total, "page": page, "page_size": page_size, "list": items})

def handle_notification_read(params):
    """POST /api/lawyer/notification/read — 标记已读"""
    user_id = params.get("user_id")
    notification_id = params.get("notification_id")
    
    if not user_id:
        return json_err("缺少 user_id")
    
    conn = get_db()
    c = conn.cursor()
    
    if notification_id:
        c.execute("UPDATE lawyer_notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notification_id, user_id))
    else:
        c.execute("UPDATE lawyer_notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0", (user_id,))
    
    conn.commit()
    affected = c.rowcount
    conn.close()
    return json_ok({"affected": affected, "message": "标记已读成功"})

def handle_notification_unread(params):
    """GET /api/lawyer/notification/unread_count — 未读数"""
    user_id = params.get("user_id")
    if not user_id:
        return json_err("缺少 user_id")
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM lawyer_notifications WHERE user_id = ? AND is_read = 0", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return json_ok({"unread_count": count})

# ==================== 路由调度 ====================
EXTRA_ACTION_MAP = {
    "create_extra_tables": lambda p: create_extra_tables(),
    "rate_set": handle_rate_set,
    "rate_info": handle_rate_info,
    "notification_list": handle_notification_list,
    "notification_read": handle_notification_read,
    "notification_unread": handle_notification_unread,
    "send_notification": lambda p: json_ok({"id": add_notification(
        p.get("user_id"), p.get("type", ""), p.get("title", ""),
        p.get("content", ""), p.get("related_id"), p.get("related_type")
    )}),
}

def main():
    if len(sys.argv) < 2:
        print(json_err("缺少参数 action"))
        sys.exit(1)
    action = sys.argv[1]
    body_str = sys.argv[2] if len(sys.argv) > 2 else "{}"
    try:
        params = json.loads(body_str) if body_str else {}
    except json.JSONDecodeError:
        print(json_err("JSON解析失败"))
        sys.exit(1)
    handler = EXTRA_ACTION_MAP.get(action)
    if handler:
        result = handler(params)
    else:
        result = json_err(f"未知操作: {action}")
    print(result, flush=True)

if __name__ == "__main__":
    main()
