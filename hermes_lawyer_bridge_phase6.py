#!/usr/bin/env python3
"""
心海法律 AI · 律师板块 Phase6 — 评价管理模块
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

def reviews_list(query_str):
    """获取评价列表"""
    try:
        query = json.loads(query_str) if query_str else {}
    except:
        query = {}
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 支持按律师维度查询（根据 case_id 关联到律师）
    lawyer_id = query.get("lawyer_id")
    case_id = query.get("case_id")
    page = int(query.get("page", 1))
    page_size = int(query.get("page_size", 20))
    offset = (page - 1) * page_size
    
    if lawyer_id:
        # 通过案件关联查询律师的评价
        sql = """
            SELECT r.id, r.case_id, r.reviewer_id, r.rating, r.dimension_ratings,
                   r.content, r.reply, r.is_anonymous, r.created_at,
                   COALESCE(u.full_name, '匿名用户') as reviewer_name,
                   COALESCE(c.title, '') as case_title
            FROM lawyer_reviews r
            LEFT JOIN lawyer_cases c ON r.case_id = c.id
            LEFT JOIN users u ON r.reviewer_id = u.id
            WHERE c.lawyer_id = ?
            ORDER BY r.created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(sql, (lawyer_id, page_size, offset))
    elif case_id:
        sql = """
            SELECT r.id, r.case_id, r.reviewer_id, r.rating, r.dimension_ratings,
                   r.content, r.reply, r.is_anonymous, r.created_at,
                   COALESCE(u.full_name, '匿名用户') as reviewer_name,
                   COALESCE(c.title, '') as case_title
            FROM lawyer_reviews r
            LEFT JOIN lawyer_cases c ON r.case_id = c.id
            LEFT JOIN users u ON r.reviewer_id = u.id
            WHERE r.case_id = ?
            ORDER BY r.created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(sql, (case_id, page_size, offset))
    else:
        sql = """
            SELECT r.id, r.case_id, r.reviewer_id, r.rating, r.dimension_ratings,
                   r.content, r.reply, r.is_anonymous, r.created_at,
                   COALESCE(u.full_name, '匿名用户') as reviewer_name,
                   COALESCE(c.title, '') as case_title
            FROM lawyer_reviews r
            LEFT JOIN lawyer_cases c ON r.case_id = c.id
            LEFT JOIN users u ON r.reviewer_id = u.id
            ORDER BY r.created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(sql, (page_size, offset))
    
    rows = cursor.fetchall()
    
    # 统计总数
    if lawyer_id:
        cursor.execute(
            "SELECT COUNT(*) FROM lawyer_reviews r LEFT JOIN lawyer_cases c ON r.case_id = c.id WHERE c.lawyer_id = ?",
            (lawyer_id,)
        )
    elif case_id:
        cursor.execute("SELECT COUNT(*) FROM lawyer_reviews WHERE case_id = ?", (case_id,))
    else:
        cursor.execute("SELECT COUNT(*) FROM lawyer_reviews")
    
    total = cursor.fetchone()[0]
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "id": row[0],
            "case_id": row[1],
            "reviewer_id": row[2],
            "rating": row[3],
            "dimension_ratings": json.loads(row[4]) if row[4] else None,
            "content": row[5],
            "reply": row[6] if row[6] else "",
            "is_anonymous": bool(row[7]),
            "created_at": row[8],
            "reviewer_name": row[9],
            "case_title": row[10]
        })
    
    return json_response(data={"total": total, "page": page, "page_size": page_size, "list": items})


def reviews_reply(body_str):
    """回复评价"""
    try:
        body = json.loads(body_str) if body_str else {}
    except:
        return json_response(400, "请求参数格式错误")
    
    review_id = body.get("review_id")
    reply = body.get("reply", "").strip()
    
    if not review_id:
        return json_response(400, "缺少必填参数：review_id")
    if not reply:
        return json_response(400, "回复内容不能为空")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查评价是否存在
    cursor.execute("SELECT id, reply FROM lawyer_reviews WHERE id = ?", (review_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return json_response(404, "评价不存在")
    
    if row[1] and row[1].strip():
        conn.close()
        return json_response(400, "该评价已回复，不可重复回复")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE lawyer_reviews SET reply = ?, created_at = ? WHERE id = ?", (reply, now, review_id))
    conn.commit()
    conn.close()
    
    return json_response(data={"review_id": review_id, "reply": reply, "replied_at": now})


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json_response(400, "参数不足"))
        sys.exit(0)
    
    action = sys.argv[1]
    data_str = sys.argv[2]
    
    if action == "reviews_list":
        print(reviews_list(data_str))
    elif action == "reviews_reply":
        print(reviews_reply(data_str))
    else:
        print(json_response(400, f"未知操作: {action}"))
