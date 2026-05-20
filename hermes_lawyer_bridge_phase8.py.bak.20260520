#!/usr/bin/env python3
"""
心海法律 AI · 律师板块 Phase8 — COO后台管理模块
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

def admin_pending_list(query_str):
    """待审核律师列表"""
    try:
        query = json.loads(query_str) if query_str else {}
    except:
        query = {}
    
    page = int(query.get("page", 1))
    page_size = int(query.get("page_size", 20))
    offset = (page - 1) * page_size
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 从两张表查 pending 状态的律师
    sql = """
        SELECT p.id, p.user_id, p.name, p.avatar, p.phone, p.law_firm,
               p.specialties, p.years_exp, p.bio, p.created_at,
               r.id as reg_id, r.bar_number, r.practice_license, r.practice_area,
               r.experience_years, r.education, r.school,
               p.firm_bank_name, p.firm_bank_account,
               r.firm_bank_name as reg_firm_bank_name, r.firm_bank_account as reg_firm_bank_account,
               r.firm_license_url, p.firm_license_url as profile_firm_license
        FROM lawyer_profiles p
        LEFT JOIN lawyer_registrations r ON p.user_id = r.user_id
        WHERE p.status = 'pending'
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
    """
    cursor.execute(sql, (page_size, offset))
    rows = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM lawyer_profiles WHERE status = 'pending'")
    total = cursor.fetchone()[0]
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "lawyer_id": row[0],
            "user_id": row[1],
            "name": row[2],
            "avatar": row[3],
            "phone": row[4],
            "law_firm": row[5],
            "specialties": row[6],
            "years_exp": row[7],
            "bio": row[8],
            "created_at": row[9],
            "registration": {
                "id": row[10],
                "bar_number": row[11],
                "practice_license": row[12],
                "practice_area": row[13],
                "experience_years": row[14],
                "education": row[15],
                "school": row[16]
            },
            "firm_bank_info": {
                "bank_name": row[17] or row[19] or "",
                "bank_account": row[18] or row[20] or "",
                "firm_license_url": row[22] or row[21] or ""
            }
        })
    
    return json_response(data={"total": total, "page": page, "page_size": page_size, "list": items})


def admin_audit(body_str):
    """审核律师"""
    try:
        body = json.loads(body_str) if body_str else {}
    except:
        return json_response(400, "请求参数格式错误")
    
    lawyer_id = body.get("lawyer_id")
    action = body.get("action", "").strip()
    remark = body.get("remark", "").strip()
    
    if not lawyer_id or not action:
        return json_response(400, "缺少必填参数：lawyer_id, action")
    if action not in ("approve", "reject"):
        return json_response(400, "action 必须为 approve 或 reject")
    if action == "reject" and not remark:
        return json_response(400, "拒绝时必须填写审核备注")
    
    new_status = "approved" if action == "approve" else "rejected"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE lawyer_profiles SET status = ?, available = ?, updated_at = ? WHERE id = ?",
        (new_status, 1 if action == "approve" else 0, now, lawyer_id)
    )
    if cursor.rowcount == 0:
        conn.close()
        return json_response(404, "律师不存在")
    
    # 也更新 registration 表
    cursor.execute(
        "UPDATE lawyer_registrations SET status = ?, admin_remark = ?, reviewed_at = ?, updated_at = ? WHERE user_id = (SELECT user_id FROM lawyer_profiles WHERE id = ?)",
        (new_status, remark, now, now, lawyer_id)
    )
    
    conn.commit()
    conn.close()
    
    return json_response(data={
        "lawyer_id": lawyer_id,
        "status": new_status,
        "remark": remark,
        "reviewed_at": now
    })


def admin_list(query_str):
    """律师管理列表（全部律师）"""
    try:
        query = json.loads(query_str) if query_str else {}
    except:
        query = {}
    
    status_filter = query.get("status", "")
    keyword = query.get("keyword", "")
    page = int(query.get("page", 1))
    page_size = int(query.get("page_size", 20))
    offset = (page - 1) * page_size
    
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = "SELECT id, user_id, name, avatar, phone, law_firm, specialties, years_exp, rating, case_count, fee_rate, status, available, fee_status, fee_expire_at, created_at FROM lawyer_profiles WHERE 1=1"
    params = []
    
    if status_filter:
        sql += " AND status = ?"
        params.append(status_filter)
    if keyword:
        sql += " AND (name LIKE ? OR law_firm LIKE ? OR phone LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
    
    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    # 总数
    count_sql = "SELECT COUNT(*) FROM lawyer_profiles WHERE 1=1"
    count_params = []
    if status_filter:
        count_sql += " AND status = ?"
        count_params.append(status_filter)
    if keyword:
        count_sql += " AND (name LIKE ? OR law_firm LIKE ? OR phone LIKE ?)"
        count_params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
    cursor.execute(count_sql, count_params)
    total = cursor.fetchone()[0]
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "lawyer_id": row[0],
            "user_id": row[1],
            "name": row[2],
            "avatar": row[3],
            "phone": row[4],
            "law_firm": row[5],
            "specialties": row[6],
            "years_exp": row[7],
            "rating": row[8],
            "case_count": row[9],
            "fee_rate": row[10],
            "status": row[11],
            "available": bool(row[12]),
            "fee_status": row[13],
            "fee_expire_at": row[14],
            "created_at": row[15]
        })
    
    return json_response(data={"total": total, "page": page, "page_size": page_size, "list": items})


def admin_status(body_str):
    """冻结/解封律师"""
    try:
        body = json.loads(body_str) if body_str else {}
    except:
        return json_response(400, "请求参数格式错误")
    
    lawyer_id = body.get("lawyer_id")
    status = body.get("status", "").strip()
    reason = body.get("reason", "").strip()
    
    if not lawyer_id or not status:
        return json_response(400, "缺少必填参数：lawyer_id, status")
    if status not in ("frozen", "active"):
        return json_response(400, "status 必须为 frozen 或 active")
    if not reason:
        return json_response(400, "必须填写原因说明")
    
    is_available = 0 if status == "frozen" else 1
    new_status = "frozen" if status == "frozen" else "approved"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE lawyer_profiles SET status = ?, available = ?, updated_at = ? WHERE id = ?",
        (new_status, is_available, now, lawyer_id)
    )
    if cursor.rowcount == 0:
        conn.close()
        return json_response(404, "律师不存在")
    
    conn.commit()
    conn.close()
    
    return json_response(data={
        "lawyer_id": lawyer_id,
        "status": new_status,
        "available": bool(is_available),
        "reason": reason,
        "updated_at": now
    })


def admin_complaints_list(query_str):
    """投诉列表"""
    try:
        query = json.loads(query_str) if query_str else {}
    except:
        query = {}
    
    page = int(query.get("page", 1))
    page_size = int(query.get("page_size", 20))
    offset = (page - 1) * page_size
    status_filter = query.get("status", "")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = """
        SELECT c.id, c.case_id, c.complainant, c.content, c.status, c.result, c.created_at,
               p.name as lawyer_name
        FROM lawyer_complaints c
        LEFT JOIN lawyer_cases cs ON c.case_id = cs.id
        LEFT JOIN lawyer_profiles p ON cs.lawyer_id = p.id
        WHERE 1=1
    """
    params = []
    if status_filter:
        sql += " AND c.status = ?"
        params.append(status_filter)
    
    sql += " ORDER BY c.created_at DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    
    count_sql = "SELECT COUNT(*) FROM lawyer_complaints WHERE 1=1"
    count_params = []
    if status_filter:
        count_sql += " AND status = ?"
        count_params.append(status_filter)
    cursor.execute(count_sql, count_params)
    total = cursor.fetchone()[0]
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            "id": row[0],
            "case_id": row[1],
            "complainant": row[2],
            "content": row[3],
            "status": row[4],
            "result": row[5],
            "created_at": row[6],
            "lawyer_name": row[7] or "未知"
        })
    
    return json_response(data={"total": total, "page": page, "page_size": page_size, "list": items})


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json_response(400, "参数不足"))
        sys.exit(0)
    
    action = sys.argv[1]
    data_str = sys.argv[2]
    
    if action == "admin_pending_list":
        print(admin_pending_list(data_str))
    elif action == "admin_audit":
        print(admin_audit(data_str))
    elif action == "admin_list":
        print(admin_list(data_str))
    elif action == "admin_status":
        print(admin_status(data_str))
    elif action == "admin_complaints_list":
        print(admin_complaints_list(data_str))
    else:
        print(json_response(400, f"未知操作: {action}"))
