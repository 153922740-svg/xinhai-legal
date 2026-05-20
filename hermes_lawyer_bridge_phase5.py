#!/usr/bin/env python3
"""
心海法律 AI · 律师板块 Phase5 — 日程管理模块
被 hermes_business_api.py 通过 subprocess 调用
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

def schedules_list(query_str):
    """获取日程列表"""
    try:
        query = json.loads(query_str) if query_str else {}
    except:
        query = {}
    
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = "SELECT id, lawyer_id, event_type, event_time, content, case_id, remind_before, created_at FROM lawyer_schedules WHERE 1=1"
    params = []
    
    lawyer_id = query.get("lawyer_id")
    if lawyer_id:
        sql += " AND lawyer_id = ?"
        params.append(lawyer_id)
    
    date = query.get("date", "")
    if date:
        sql += " AND date(event_time) = ?"
        params.append(date)
    
    month = query.get("month", "")
    if month:
        sql += " AND substr(event_time, 1, 7) = ?"
        params.append(month)
    
    sql += " ORDER BY event_time ASC"
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "id": row[0],
            "lawyer_id": row[1],
            "event_type": row[2],
            "event_time": row[3],
            "content": row[4],
            "case_id": row[5],
            "remind_before": row[6],
            "created_at": row[7]
        })
    
    return json_response(data={"total": len(items), "list": items})

def schedules_create(body_str):
    """创建日程"""
    try:
        body = json.loads(body_str) if body_str else {}
    except:
        return json_response(400, "请求参数格式错误")
    
    lawyer_id = body.get("lawyer_id")
    event_type = body.get("event_type", "")
    event_time = body.get("event_time", "")
    content = body.get("content", "")
    case_id = body.get("case_id")
    remind_before = body.get("remind_before")
    
    if not all([lawyer_id, event_type, event_time, content]):
        return json_response(400, "缺少必填参数：lawyer_id, event_type, event_time, content")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO lawyer_schedules (lawyer_id, event_type, event_time, content, case_id, remind_before, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (lawyer_id, event_type, event_time, content, case_id, remind_before, now)
    )
    
    conn.commit()
    schedule_id = cursor.lastrowid
    conn.close()
    
    return json_response(data={"schedule_id": schedule_id, "created_at": now})


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json_response(400, "参数不足"))
        sys.exit(0)
    
    action = sys.argv[1]
    data_str = sys.argv[2]
    
    if action == "schedules_list":
        print(schedules_list(data_str))
    elif action == "schedules_create":
        print(schedules_create(data_str))
    else:
        print(json_response(400, f"未知操作: {action}"))
