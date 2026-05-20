#!/usr/bin/env python3
"""
心海法律 AI · 律师板块 Phase7 — 用户端找律师模块
被 hermes_business_api.py 通过 subprocess 调用
"""
import sys
import json
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "/home/admin/xinhai_legal_api/data/xinhai_legal.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def json_response(code=200, message="success", data=None):
    return json.dumps({"code": code, "message": message, "data": data}, ensure_ascii=False)

def lawyer_list(query_str):
    """获取律师公开列表"""
    try:
        query = json.loads(query_str) if query_str else {}
    except:
        query = {}
    
    conn = get_connection()
    cursor = conn.cursor()
    
    region = query.get("region", "")
    specialty = query.get("specialty", "")
    keyword = query.get("keyword", "")
    sort = query.get("sort", "rating")
    page = int(query.get("page", 1))
    page_size = int(query.get("page_size", 20))
    offset = (page - 1) * page_size
    
    sql = "SELECT id, user_id, name, avatar, law_firm, specialties, years_exp, bio, rating, case_count, fee_rate FROM lawyer_profiles WHERE status = 'approved' AND available = 1"
    params = []
    
    if region:
        sql += " AND jurisdiction LIKE ?"
        params.append(f"%{region}%")
    if keyword:
        sql += " AND (name LIKE ? OR law_firm LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    
    # 按排序
    if sort == "cases":
        sql += " ORDER BY case_count DESC"
    elif sort == "price":
        sql += " ORDER BY fee_rate ASC"
    else:
        sql += " ORDER BY rating DESC"
    
    sql += f" LIMIT {page_size} OFFSET {offset}"
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    # 如果有专业领域筛选，过一遍
    result = []
    if specialty and rows:
        for row in rows:
            sp = row[5] or ""
            if specialty.lower() in sp.lower():
                result.append(row)
        rows = result
    
    # 总数
    count_sql = "SELECT COUNT(*) FROM lawyer_profiles WHERE status = 'approved' AND available = 1"
    cursor.execute(count_sql)
    total = cursor.fetchone()[0]
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "lawyer_id": row[0],
            "user_id": row[1],
            "name": row[2],
            "avatar": row[3],
            "law_firm": row[4],
            "specialties": row[5],
            "years_exp": row[6],
            "bio": row[7],
            "rating": row[8],
            "case_count": row[9],
            "fee_rate": row[10]
        })
    
    return json_response(data={"total": len(items) if specialty else total, "page": page, "page_size": page_size, "list": items})


def lawyer_recommend(body_str):
    """AI推荐律师（基于案件类型和描述模拟匹配）"""
    try:
        body = json.loads(body_str) if body_str else {}
    except:
        return json_response(400, "请求参数格式错误")
    
    case_type = body.get("case_type", "")
    description = body.get("description", "")
    region = body.get("region", "")
    
    if not case_type:
        return json_response(400, "缺少必填参数：case_type")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = "SELECT id, user_id, name, avatar, law_firm, specialties, years_exp, bio, rating, case_count, fee_rate FROM lawyer_profiles WHERE status = 'approved' AND available = 1"
    params = []
    
    # 按专业领域匹配
    if case_type:
        sql += " AND (specialties LIKE ? OR bio LIKE ?)"
        params.extend([f"%{case_type}%", f"%{case_type}%"])
    
    if region:
        sql += " AND jurisdiction LIKE ?"
        params.append(f"%{region}%")
    
    sql += " ORDER BY rating DESC, case_count DESC LIMIT 10"
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "lawyer_id": row[0],
            "user_id": row[1],
            "name": row[2],
            "avatar": row[3],
            "law_firm": row[4],
            "specialties": row[5],
            "years_exp": row[6],
            "bio": row[7],
            "rating": row[8],
            "case_count": row[9],
            "fee_rate": row[10],
            "match_reason": f"擅长{case_type}领域" if case_type else "资深律师推荐"
        })
    
    return json_response(data={"total": len(items), "list": items})


def lawyer_detail(query_str):
    """律师详情（公开信息）"""
    try:
        query = json.loads(query_str) if query_str else {}
    except:
        query = {}
    
    lawyer_id = query.get("lawyer_id")
    if not lawyer_id:
        return json_response(400, "缺少参数：lawyer_id")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, user_id, name, avatar, phone, email, law_firm, license_no, specialties, years_exp, jurisdiction, bio, rating, case_count, fee_rate, created_at FROM lawyer_profiles WHERE id = ? AND status = 'approved'",
        (lawyer_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return json_response(404, "律师不存在")
    
    # 获取专业标签
    cursor.execute("SELECT specialty_tag FROM lawyer_specialties WHERE lawyer_id = ?", (lawyer_id,))
    tags = [t[0] for t in cursor.fetchall()]
    
    # 获取评价统计
    cursor.execute("SELECT COUNT(*), AVG(rating) FROM lawyer_reviews r LEFT JOIN lawyer_cases c ON r.case_id = c.id WHERE c.lawyer_id = ?", (lawyer_id,))
    review_row = cursor.fetchone()
    review_count = review_row[0] or 0
    avg_rating = round(review_row[1], 1) if review_row[1] else 0
    
    # 获取成功案例
    cursor.execute("SELECT id, title, type, status, created_at FROM lawyer_cases WHERE lawyer_id = ? AND status = 'closed' ORDER BY created_at DESC LIMIT 5", (lawyer_id,))
    cases = [{"id": c[0], "title": c[1], "type": c[2], "status": c[3], "created_at": c[4]} for c in cursor.fetchall()]
    
    conn.close()
    
    data = {
        "lawyer_id": row[0],
        "user_id": row[1],
        "name": row[2],
        "avatar": row[3],
        "phone": row[4],
        "email": row[5],
        "law_firm": row[6],
        "license_no": row[7],
        "specialties": row[8],
        "specialty_tags": tags,
        "years_exp": row[9],
        "jurisdiction": row[10],
        "bio": row[11],
        "rating": row[12],
        "case_count": row[13],
        "fee_rate": row[14],
        "created_at": row[15],
        "review_count": review_count,
        "avg_rating": avg_rating,
        "success_cases": cases
    }
    
    return json_response(data=data)


def invite_create(body_str):
    """发起委托"""
    try:
        body = json.loads(body_str) if body_str else {}
    except:
        return json_response(400, "请求参数格式错误")
    
    user_id = body.get("user_id")
    lawyer_id = body.get("lawyer_id")
    case_title = body.get("case_title", "").strip()
    case_type = body.get("case_type", "").strip()
    description = body.get("description", "").strip()
    
    if not all([user_id, lawyer_id, case_title]):
        return json_response(400, "缺少必填参数：user_id, lawyer_id, case_title")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查律师是否存在且可用
    cursor.execute("SELECT id, status, available FROM lawyer_profiles WHERE id = ?", (lawyer_id,))
    lawyer = cursor.fetchone()
    if not lawyer:
        conn.close()
        return json_response(404, "律师不存在")
    if lawyer[1] != 'approved' or not lawyer[2]:
        conn.close()
        return json_response(400, "该律师当前不可接案")
    
    # 检查24小时内是否已发起过相同委托
    cursor.execute(
        "SELECT id FROM lawyer_invites WHERE user_id = ? AND lawyer_id = ? AND case_title = ? AND status = 'pending' AND datetime(created_at) > datetime('now', '-1 day')",
        (user_id, lawyer_id, case_title)
    )
    if cursor.fetchone():
        conn.close()
        return json_response(400, "已向该律师发起过相同委托，请等待回复")
    
    now = datetime.now()
    expired_at = (now + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        "INSERT INTO lawyer_invites (user_id, lawyer_id, case_title, case_type, description, status, expired_at) VALUES (?, ?, ?, ?, ?, 'pending', ?)",
        (user_id, lawyer_id, case_title, case_type, description, expired_at)
    )
    conn.commit()
    invite_id = cursor.lastrowid
    conn.close()
    
    return json_response(data={
        "invite_id": invite_id,
        "status": "pending",
        "expired_at": expired_at
    })


def invite_status(query_str):
    """委托状态查询"""
    try:
        query = json.loads(query_str) if query_str else {}
    except:
        query = {}
    
    invite_id = query.get("invite_id")
    if not invite_id:
        return json_response(400, "缺少参数：invite_id")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, user_id, lawyer_id, case_title, case_type, description, status, expired_at, created_at FROM lawyer_invites WHERE id = ?",
        (invite_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return json_response(404, "委托不存在")
    
    # 获取律师信息
    cursor.execute("SELECT name, avatar, law_firm FROM lawyer_profiles WHERE id = ?", (row[2],))
    lawyer = cursor.fetchone()
    
    conn.close()
    
    data = {
        "invite_id": row[0],
        "user_id": row[1],
        "lawyer_id": row[2],
        "case_title": row[3],
        "case_type": row[4],
        "description": row[5],
        "status": row[6],
        "expired_at": row[7],
        "created_at": row[8],
        "lawyer": {
            "name": lawyer[0] if lawyer else "",
            "avatar": lawyer[1] if lawyer else "",
            "law_firm": lawyer[2] if lawyer else ""
        } if lawyer else None
    }
    
    return json_response(data=data)


def lawyer_dashboard(data_str):
    """律师案件看板数据统计"""
    try:
        query = json.loads(data_str) if data_str else {}
    except:
        query = {}
    
    lawyer_id = query.get('lawyer_id')
    if not lawyer_id:
        # 尝试从user_id获取律师ID
        user_id = query.get('user_id')
        if not user_id:
            return json_response(400, "缺少 lawyer_id 或 user_id")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 如果传了user_id，先查对应的lawyer_id
        if not lawyer_id and user_id:
            cursor.execute("SELECT id FROM lawyer_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                lawyer_id = row[0]
            else:
                return json_response(404, "未找到律师信息")
        
        # 1. 案件统计
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END),
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END),
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END),
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END),
                COUNT(*)
            FROM lawyer_cases WHERE lawyer_id = ?
        """, (lawyer_id,))
        row = cursor.fetchone()
        stats = {
            'pending': row[0] or 0,
            'active': row[1] or 0,
            'completed': row[2] or 0,
            'closed': row[3] or 0,
            'total': row[4] or 0
        }
        
        # 2. 待开庭案件数（stage='trial' 且 status='active'）
        cursor.execute("""
            SELECT COUNT(*) FROM lawyer_cases 
            WHERE lawyer_id = ? AND stage = 'trial' AND status = 'active'
        """, (lawyer_id,))
        upcoming_trial = cursor.fetchone()[0]
        
        # 3. 最近5个案件
        cursor.execute("""
            SELECT id, title, type, status, stage, COALESCE(court, '') as court, created_at
            FROM lawyer_cases 
            WHERE lawyer_id = ?
            ORDER BY updated_at DESC LIMIT 5
        """, (lawyer_id,))
        recent_cases = []
        for r in cursor.fetchall():
            recent_cases.append({
                'id': r[0], 'title': r[1], 'type': r[2], 'status': r[3],
                'stage': r[4], 'court': r[5], 'created_at': r[6]
            })
        
        # 4. 近期日程（未来7天）
        today = datetime.now().strftime('%Y-%m-%d')
        seven_days = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT id, event_type, event_time, content, COALESCE(case_id, 0) as case_id
            FROM lawyer_schedules 
            WHERE lawyer_id = ? AND event_time >= ? AND event_time <= ?
            ORDER BY event_time ASC LIMIT 5
        """, (lawyer_id, today, seven_days))
        upcoming_schedules = []
        for r in cursor.fetchall():
            upcoming_schedules.append({
                'id': r[0], 'event_type': r[1], 'event_time': r[2],
                'content': r[3], 'case_id': r[4]
            })
        
        # 5. 钱包余额
        cursor.execute("""
            SELECT COALESCE(balance, 0), COALESCE(total_income, 0)
            FROM lawyer_wallet 
            WHERE lawyer_id = ?
        """, (lawyer_id,))
        wallet_row = cursor.fetchone()
        wallet_balance = wallet_row[0] if wallet_row else 0
        total_income = wallet_row[1] if wallet_row else 0
        
        return json_response(data={
            'case_stats': {
                'pending': stats['pending'] or 0,
                'active': stats['active'] or 0,
                'upcoming_trial': upcoming_trial,
                'completed': stats['completed'] or 0,
                'closed': stats['closed'] or 0,
                'total': stats['total'] or 0
            },
            'recent_cases': recent_cases,
            'upcoming_schedules': upcoming_schedules,
            'wallet': {
                'balance': wallet_balance,
                'total_income': total_income
            }
        })
    except Exception as e:
        return json_response(500, str(e))
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json_response(400, "参数不足"))
        sys.exit(0)
    
    action = sys.argv[1]
    data_str = sys.argv[2]
    
    if action == "lawyer_list":
        print(lawyer_list(data_str))
    elif action == "lawyer_recommend":
        print(lawyer_recommend(data_str))
    elif action == "lawyer_detail":
        print(lawyer_detail(data_str))
    elif action == "invite_create":
        print(invite_create(data_str))
    elif action == "invite_status":
        print(invite_status(data_str))
    elif action == "lawyer_dashboard":
        print(lawyer_dashboard(data_str))
    else:
        print(json_response(400, f"未知操作: {action}"))
