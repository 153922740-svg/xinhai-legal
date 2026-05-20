#!/usr/bin/env python3
"""
心海法律 AI · 律师消息通知模块 (Phase5 Extension)
被 hermes_business_api.py 通过 subprocess 调用
提供消息表创建、通知列表、标记已读、未读数等接口
"""
import sys
import json
import sqlite3
from datetime import datetime

DB_PATH = "/home/admin/xinhai_legal_api/data/xinhai_legal.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def json_response(code=200, message="success", data=None):
    return json.dumps({"code": code, "message": message, "data": data}, ensure_ascii=False)


# ==================== 建表 ====================

def ensure_table():
    """确保 lawyer_notifications 表存在"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lawyer_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            related_id INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()
    return True


# ==================== 通知发送辅助函数 ====================

def send_notification(user_id, type_, title, content, related_id=None):
    """
    插入一条律师通知（供其他模块调用）
    参数:
        user_id: 律师用户ID
        type_: 通知类型 (audit_pass/audit_reject/new_委托/withdraw_done/system)
        title: 通知标题
        content: 通知内容
        related_id: 关联ID (可选)
    返回: (success, error_msg)
    """
    try:
        ensure_table()
        conn = get_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO lawyer_notifications (user_id, type, title, content, is_read, related_id, created_at) VALUES (?, ?, ?, ?, 0, ?, ?)",
            (user_id, type_, title, content, related_id, now)
        )
        conn.commit()
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)


# ==================== 通知列表接口 ====================

def notification_list(body_str):
    """查询律师通知列表（分页）"""
    try:
        body = json.loads(body_str) if body_str else {}
    except:
        return json_response(400, "请求参数格式错误")
    
    ensure_table()
    
    user_id = body.get("user_id")
    page = int(body.get("page", 1))
    page_size = int(body.get("page_size", 20))
    type_filter = body.get("type", "")
    is_read_filter = body.get("is_read")  # None=全部, 0=未读, 1=已读
    
    if not user_id:
        return json_response(400, "缺少必填参数: user_id")
    
    offset = (page - 1) * page_size
    
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = "SELECT id, user_id, type, title, content, is_read, related_id, created_at FROM lawyer_notifications WHERE user_id = ?"
    params = [user_id]
    
    if type_filter:
        sql += " AND type = ?"
        params.append(type_filter)
    
    if is_read_filter is not None:
        sql += " AND is_read = ?"
        params.append(int(is_read_filter))
    
    # 统计总数
    count_sql = sql.replace(
        "SELECT id, user_id, type, title, content, is_read, related_id, created_at",
        "SELECT COUNT(*)"
    )
    cursor.execute(count_sql, params)
    total = cursor.fetchone()[0]
    
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "id": row[0],
            "user_id": row[1],
            "type": row[2],
            "title": row[3],
            "content": row[4],
            "is_read": bool(row[5]),
            "related_id": row[6],
            "created_at": row[7]
        })
    
    return json_response(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "list": items
    })


# ==================== 标记已读 ====================

def notification_read(body_str):
    """标记通知为已读（单条或全部）"""
    try:
        body = json.loads(body_str) if body_str else {}
    except:
        return json_response(400, "请求参数格式错误")
    
    ensure_table()
    
    user_id = body.get("user_id")
    notification_id = body.get("notification_id")  # 可选，不传则标记全部已读
    
    if not user_id:
        return json_response(400, "缺少必填参数: user_id")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if notification_id:
        cursor.execute(
            "UPDATE lawyer_notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
            (notification_id, user_id)
        )
    else:
        cursor.execute(
            "UPDATE lawyer_notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
            (user_id,)
        )
    
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    
    return json_response(data={
        "affected": affected,
        "message": "全部已读" if not notification_id else "已标记已读"
    })


# ==================== 未读数统计 ====================

def notification_unread_count(body_str):
    """查询律师未读通知数"""
    try:
        body = json.loads(body_str) if body_str else {}
    except:
        return json_response(400, "请求参数格式错误")
    
    ensure_table()
    
    user_id = body.get("user_id")
    if not user_id:
        return json_response(400, "缺少必填参数: user_id")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT COUNT(*) FROM lawyer_notifications WHERE user_id = ? AND is_read = 0",
        (user_id,)
    )
    count = cursor.fetchone()[0]
    
    # 按类型分组统计
    cursor.execute(
        "SELECT type, COUNT(*) FROM lawyer_notifications WHERE user_id = ? AND is_read = 0 GROUP BY type",
        (user_id,)
    )
    type_counts = {}
    for row in cursor.fetchall():
        type_counts[row[0]] = row[1]
    
    conn.close()
    
    return json_response(data={
        "total_unread": count,
        "type_counts": type_counts
    })


# ==================== 测试插入 ====================

def notification_test_insert(body_str):
    """测试用：插入一条示例通知"""
    try:
        body = json.loads(body_str) if body_str else {}
    except:
        return json_response(400, "请求参数格式错误")
    
    user_id = body.get("user_id", 1)
    type_ = body.get("type", "system")
    title = body.get("title", "测试通知")
    content = body.get("content", "这是一条测试通知内容")
    related_id = body.get("related_id")
    
    success, error = send_notification(user_id, type_, title, content, related_id)
    if success:
        return json_response(data={"message": "通知已插入"})
    else:
        return json_response(500, f"插入失败: {error}")


# ==================== 主入口 ====================

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json_response(400, "参数不足"))
        sys.exit(0)
    
    action = sys.argv[1]
    data_str = sys.argv[2]
    
    # 每次调用确保表存在
    ensure_table()
    
    if action == "notification_list":
        print(notification_list(data_str))
    elif action == "notification_read":
        print(notification_read(data_str))
    elif action == "notification_unread_count":
        print(notification_unread_count(data_str))
    elif action == "notification_test_insert":
        print(notification_test_insert(data_str))
    else:
        print(json_response(400, f"未知操作: {action}"))
