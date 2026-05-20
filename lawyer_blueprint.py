"""心海法律 AI · 律师模块统一蓝图
整合8个bridge_phase + 新增功能（费率设置、消息通知）
"""
from flask import Blueprint, request, jsonify
import sqlite3, os, json, sys
from datetime import datetime, timedelta

DB_PATH = "/home/admin/xinhai_legal_api/data/xinhai_legal.db"

lawyer_bp = Blueprint("lawyer", __name__, url_prefix="/api/lawyer")

def get_db():
    return sqlite3.connect(DB_PATH)

# ==================== 导入bridge_phase函数 ====================
sys.path.insert(0, "/home/admin/xinhai_legal_api")

def call_bridge(action, params=None):
    """通过subprocess调用bridge_phase（兼容旧模式）"""
    if params is None:
        params = {}
    # 优先使用new内置实现（如果已实现）
    fn = BUILTIN_HANDLERS.get(action)
    if fn:
        return fn(params)
    # 回退到subprocess（旧bridge文件仍然可用）
    import subprocess
    # 找哪个phase有对应action
    for phase_file in ["hermes_lawyer_bridge_phase1.py", "hermes_lawyer_bridge_phase2.py",
                        "hermes_lawyer_bridge_phase4.py", "hermes_lawyer_bridge_phase5.py",
                        "hermes_lawyer_bridge_phase6.py", "hermes_lawyer_bridge_phase7.py",
                        "hermes_lawyer_bridge_phase8.py"]:
        fpath = f"/home/admin/xinhai_legal_api/{phase_file}"
        if os.path.exists(fpath):
            try:
                p = subprocess.run(
                    ["python3", fpath, action, json.dumps(params, ensure_ascii=False)],
                    capture_output=True, text=True, timeout=10
                )
                if p.returncode == 0 and p.stdout:
                    return json.loads(p.stdout)
            except:
                pass
    return {"code": 500, "message": f"未知操作: {action}", "data": None}

# ==================== 内置实现 ====================
# 将常用接口内置到蓝图中，提升性能

def _get_user_id():
    """从请求参数提取user_id（先header后body）"""
    data = request.get_json(silent=True) or {}
    uid = request.headers.get("X-User-Id") or request.args.get("user_id") or data.get("user_id")
    if uid:
        try:
            return int(uid)
        except:
            return uid
    return None

# --- 健康检查 ---
@lawyer_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"code": 200, "message": "pong", "data": {"service": "lawyer"}})

# --- 入驻认证（9个） ---
from hermes_lawyer_bridge_phase1 import (
    handle_realname, handle_realname_status, handle_register,
    handle_cert_upload, handle_status, handle_pay_fee,
    handle_fee_status, handle_get_profile, handle_update_profile,
    create_tables as phase1_create_tables
)

@lawyer_bp.route("/realname", methods=["POST"])
def realname():
    data = request.get_json(silent=True) or {}
    data["user_id"] = data.get("user_id") or _get_user_id()
    r = handle_realname(data)
    return jsonify({"code": 200 if r.get("success") else 400, "message": r.get("error") or "success", "data": r.get("data")})

@lawyer_bp.route("/realname/status", methods=["POST"])
def realname_status():
    data = request.get_json(silent=True) or {}
    data["user_id"] = data.get("user_id") or _get_user_id()
    r = handle_realname_status(data)
    return jsonify({"code": 200 if r.get("success") else 400, "message": r.get("error") or "success", "data": r.get("data")})

@lawyer_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    data["user_id"] = data.get("user_id") or _get_user_id()
    r = handle_register(data)
    return jsonify({"code": 200 if r.get("success") else 400, "message": r.get("error") or "success", "data": r.get("data")})

@lawyer_bp.route("/cert/upload", methods=["POST"])
def cert_upload():
    data = request.get_json(silent=True) or {}
    r = handle_cert_upload(data)
    return jsonify({"code": 200 if r.get("success") else 400, "message": r.get("error") or "success", "data": r.get("data")})

@lawyer_bp.route("/status", methods=["GET"])
def status():
    data = {"user_id": _get_user_id()}
    r = handle_status(data)
    return jsonify({"code": 200 if r.get("success") else 400, "message": r.get("error") or "success", "data": r.get("data")})

@lawyer_bp.route("/pay-fee", methods=["POST"])
def pay_fee():
    data = request.get_json(silent=True) or {}
    r = handle_pay_fee(data)
    return jsonify({"code": 200 if r.get("success") else 400, "message": r.get("error") or "success", "data": r.get("data")})

@lawyer_bp.route("/fee-status", methods=["GET"])
def fee_status():
    data = {"user_id": _get_user_id()}
    r = handle_fee_status(data)
    return jsonify({"code": 200 if r.get("success") else 400, "message": r.get("error") or "success", "data": r.get("data")})

@lawyer_bp.route("/profile", methods=["GET"])
def get_profile():
    data = {"user_id": _get_user_id()}
    r = handle_get_profile(data)
    return jsonify({"code": 200 if r.get("success") else 400, "message": r.get("error") or "success", "data": r.get("data")})

@lawyer_bp.route("/profile", methods=["PUT"])
def update_profile():
    data = request.get_json(silent=True) or {}
    data["user_id"] = data.get("user_id") or _get_user_id()
    r = handle_update_profile(data)
    return jsonify({"code": 200 if r.get("success") else 400, "message": r.get("error") or "success", "data": r.get("data")})

# --- 案件管理（6个） ---
@lawyer_bp.route("/cases", methods=["GET"])
def cases_list():
    r = call_bridge("cases_list", {"lawyer_id": _get_user_id(), "page": request.args.get("page", 1), "page_size": request.args.get("page_size", 20)})
    return jsonify(r)

@lawyer_bp.route("/cases/<int:case_id>", methods=["GET"])
def case_detail(case_id):
    r = call_bridge("case_detail", {"case_id": case_id})
    return jsonify(r)

@lawyer_bp.route("/cases/<int:case_id>/status", methods=["PUT"])
def case_status(case_id):
    data = request.get_json(silent=True) or {}
    data["case_id"] = case_id
    r = call_bridge("case_update_status", data)
    return jsonify(r)

@lawyer_bp.route("/cases/<int:case_id>/timeline", methods=["GET"])
def case_timeline(case_id):
    r = call_bridge("case_timeline", {"case_id": case_id})
    return jsonify(r)

@lawyer_bp.route("/cases/<int:case_id>/documents", methods=["GET"])
def case_documents(case_id):
    r = call_bridge("case_documents", {"case_id": case_id})
    return jsonify(r)

@lawyer_bp.route("/cases/<int:case_id>/documents", methods=["POST"])
def case_upload_doc(case_id):
    data = request.get_json(silent=True) or {}
    data["case_id"] = case_id
    r = call_bridge("case_upload_document", data)
    return jsonify(r)

# --- AI工具（8个） ---
@lawyer_bp.route("/ai/analyze", methods=["POST"])
def ai_analyze():
    data = request.get_json(silent=True) or {}
    r = call_bridge("ai_analyze", data)
    return jsonify(r)

@lawyer_bp.route("/ai/generate-doc", methods=["POST"])
def ai_generate_doc():
    data = request.get_json(silent=True) or {}
    r = call_bridge("ai_generate_doc", data)
    return jsonify(r)

@lawyer_bp.route("/ai/review-doc", methods=["POST"])
def ai_review_doc():
    data = request.get_json(silent=True) or {}
    r = call_bridge("ai_review_doc", data)
    return jsonify(r)

@lawyer_bp.route("/ai/summary", methods=["POST"])
def ai_summary():
    data = request.get_json(silent=True) or {}
    r = call_bridge("ai_summary", data)
    return jsonify(r)

@lawyer_bp.route("/ai/evidence", methods=["POST"])
def ai_evidence():
    data = request.get_json(silent=True) or {}
    r = call_bridge("ai_evidence", data)
    return jsonify(r)

@lawyer_bp.route("/ai/legal-search", methods=["POST"])
def ai_legal_search():
    data = request.get_json(silent=True) or {}
    r = call_bridge("ai_legal_search", data)
    return jsonify(r)

@lawyer_bp.route("/ai/class-case", methods=["POST"])
def ai_class_case():
    data = request.get_json(silent=True) or {}
    r = call_bridge("ai_class_case", data)
    return jsonify(r)

@lawyer_bp.route("/ai/trial-outline", methods=["POST"])
def ai_trial_outline():
    data = request.get_json(silent=True) or {}
    r = call_bridge("ai_trial_outline", data)
    return jsonify(r)

# --- 钱包（5个） ---
@lawyer_bp.route("/wallet", methods=["GET"])
def wallet():
    r = call_bridge("wallet_info", {"lawyer_id": _get_user_id()})
    return jsonify(r)

@lawyer_bp.route("/wallet/withdraw", methods=["POST"])
def wallet_withdraw():
    data = request.get_json(silent=True) or {}
    r = call_bridge("wallet_withdraw", data)
    return jsonify(r)

@lawyer_bp.route("/wallet/withdrawals", methods=["GET"])
def wallet_withdrawals():
    r = call_bridge("wallet_withdrawals", {"lawyer_id": _get_user_id()})
    return jsonify(r)

@lawyer_bp.route("/wallet/income", methods=["GET"])
def wallet_income():
    r = call_bridge("wallet_income", {"lawyer_id": _get_user_id()})
    return jsonify(r)

@lawyer_bp.route("/wallet/settlements", methods=["GET"])
def wallet_settlements():
    r = call_bridge("wallet_settlements", {"lawyer_id": _get_user_id()})
    return jsonify(r)

# --- 日程（2个） ---
@lawyer_bp.route("/schedules", methods=["GET"])
def schedules_list():
    data = {"lawyer_id": _get_user_id(), "date": request.args.get("date", ""), "month": request.args.get("month", "")}
    r = call_bridge("schedules_list", data)
    return jsonify(r)

@lawyer_bp.route("/schedules", methods=["POST"])
def schedules_create():
    data = request.get_json(silent=True) or {}
    r = call_bridge("schedules_create", data)
    return jsonify(r)

# --- 评价（2个） ---
@lawyer_bp.route("/reviews", methods=["GET"])
def reviews_list():
    r = call_bridge("reviews_list", {"lawyer_id": _get_user_id()})
    return jsonify(r)

@lawyer_bp.route("/reviews/<int:review_id>/reply", methods=["POST"])
def reviews_reply(review_id):
    data = request.get_json(silent=True) or {}
    data["review_id"] = review_id
    r = call_bridge("reviews_reply", data)
    return jsonify(r)

# --- 用户端（5个） ---
@lawyer_bp.route("/list", methods=["GET"])
@lawyer_bp.route("/lawyers", methods=["GET"])
def lawyer_list():
    """律师公开列表，直接查询数据库不走subprocess"""
    region = request.args.get("region", "")
    specialty = request.args.get("specialty", "")
    keyword = request.args.get("keyword", "")
    sort = request.args.get("sort", "rating")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    offset = (page - 1) * page_size
    
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    
    sql = "SELECT id, user_id, name, avatar, law_firm, specialties, years_exp, bio, rating, case_count, fee_rate FROM lawyer_profiles WHERE status = 'approved' AND available = 1"
    params = []
    if region:
        sql += " AND jurisdiction LIKE ?"
        params.append(f"%{region}%")
    if keyword:
        sql += " AND (name LIKE ? OR law_firm LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    sort_col = {"cases": "case_count DESC", "price": "fee_rate ASC"}.get(sort, "rating DESC")
    sql += f" ORDER BY {sort_col} LIMIT ? OFFSET ?"
    params.extend([page_size, offset])
    
    items = []
    try:
        c = db.cursor()
        c.execute(sql, params)
        for row in c.fetchall():
            sp = row["specialties"] or ""
            if specialty and specialty.lower() not in sp.lower():
                continue
            items.append(dict(
                lawyer_id=row["id"], user_id=row["user_id"], name=row["name"],
                avatar=row["avatar"], law_firm=row["law_firm"],
                specialties=sp.split(",") if sp else [],
                years_exp=row["years_exp"], bio=row["bio"],
                rating=row["rating"], case_count=row["case_count"],
                fee_rate=row["fee_rate"]
            ))
        c.execute("SELECT COUNT(*) FROM lawyer_profiles WHERE status='approved' AND available=1")
        total = c.fetchone()[0]
    finally:
        db.close()
    return jsonify({"code": 200, "message": "success", "data": {"total": total, "page": page, "page_size": page_size, "list": items}})

@lawyer_bp.route("/recommend", methods=["POST"])
def recommend():
    """AI推荐律师"""
    data = request.get_json(silent=True) or {}
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        c = db.cursor()
        c.execute("SELECT id, user_id, name, avatar, law_firm, specialties, years_exp, bio, rating, case_count, fee_rate FROM lawyer_profiles WHERE status='approved' AND available=1 ORDER BY rating DESC LIMIT 10")
        rows = [dict(r) for r in c.fetchall()]
        for r in rows:
            r["specialties"] = r.get("specialties","").split(",") if r.get("specialties") else []
    finally:
        db.close()
    return jsonify({"code": 200, "message": "success", "data": {"total": len(rows), "list": rows}})

@lawyer_bp.route("/<int:lawyer_id>", methods=["GET"])
def lawyer_detail(lawyer_id):
    """律师详情"""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        c = db.cursor()
        c.execute("SELECT id, user_id, name, avatar, phone, email, law_firm, license_no, specialties, years_exp, jurisdiction, bio, rating, case_count, fee_rate, fee_status, created_at FROM lawyer_profiles WHERE id = ? AND status='approved'", (lawyer_id,))
        row = c.fetchone()
        if not row:
            return jsonify({"code": 404, "message": "律师不存在", "data": None})
        profile = dict(row)
        profile["specialties"] = profile.get("specialties","").split(",") if profile.get("specialties") else []
        # 查评价数（兼容reviewer_id或lawyer_id）
        try:
            c.execute("SELECT COUNT(*) FROM lawyer_reviews WHERE reviewer_id = ?", (lawyer_id,))
            profile["review_count"] = c.fetchone()[0]
        except:
            profile["review_count"] = 0
    finally:
        db.close()
    return jsonify({"code": 200, "message": "success", "data": profile})

@lawyer_bp.route("/invite", methods=["POST"])
def invite():
    """发起委托"""
    data = request.get_json(silent=True) or {}
    lawyer_id = data.get("lawyer_id")
    user_id = data.get("user_id")
    case_title = data.get("case_title", "")
    case_type = data.get("case_type", "")
    desc = data.get("description", "")
    
    if not all([lawyer_id, user_id, case_title]):
        return jsonify({"code": 400, "message": "缺少必填参数：lawyer_id, user_id, case_title", "data": None})
    
    expires = (datetime.now() + timedelta(hours=24)).isoformat()
    now = datetime.now().isoformat()
    
    db = sqlite3.connect(DB_PATH)
    try:
        c = db.cursor()
        c.execute("INSERT INTO lawyer_invites (user_id, lawyer_id, case_title, case_type, description, status, expired_at, created_at) VALUES (?,?,?,?,?,'pending',?,?)",
               (user_id, lawyer_id, case_title, case_type, desc, expires, now))
        db.commit()
        invite_id = c.lastrowid
    finally:
        db.close()
    return jsonify({"code": 200, "message": "success", "data": {"invite_id": invite_id, "status": "pending", "expired_at": expires}})

@lawyer_bp.route("/invite/status", methods=["GET"])
def invite_status():
    """委托状态查询"""
    invite_id = request.args.get("invite_id")
    if not invite_id:
        return jsonify({"code": 400, "message": "缺少 invite_id", "data": None})
    
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        c = db.cursor()
        c.execute("SELECT id, user_id, lawyer_id, case_title, case_type, description, status, expired_at, created_at FROM lawyer_invites WHERE id = ?", (invite_id,))
        row = c.fetchone()
        if not row:
            return jsonify({"code": 404, "message": "委托不存在", "data": None})
        d = dict(row)
        c.execute("SELECT name, avatar, law_firm FROM lawyer_profiles WHERE id = ?", (row["lawyer_id"],))
        lawyer = c.fetchone()
        d["lawyer"] = dict(lawyer) if lawyer else None
    finally:
        db.close()
    return jsonify({"code": 200, "message": "success", "data": d})

# --- 费率设置（新增） ---
from lawyer_extra_features import handle_rate_set, handle_rate_info

@lawyer_bp.route("/rate/set", methods=["POST"])
def rate_set():
    data = request.get_json(silent=True) or {}
    r = handle_rate_set(data)
    return jsonify(json.loads(r))

@lawyer_bp.route("/rate/info", methods=["GET"])
def rate_info():
    data = {"user_id": _get_user_id()}
    r = handle_rate_info(data)
    return jsonify(json.loads(r))

# --- 消息通知（新增） ---
from lawyer_extra_features import handle_notification_list, handle_notification_read, handle_notification_unread

@lawyer_bp.route("/notification/list", methods=["GET"])
def notif_list():
    data = {"user_id": _get_user_id(), "page": request.args.get("page", 1), "page_size": request.args.get("page_size", 20)}
    r = handle_notification_list(data)
    return jsonify(json.loads(r))

@lawyer_bp.route("/notification/read", methods=["POST"])
def notif_read():
    data = request.get_json(silent=True) or {}
    data["user_id"] = data.get("user_id") or _get_user_id()
    r = handle_notification_read(data)
    return jsonify(json.loads(r))

@lawyer_bp.route("/notification/unread_count", methods=["GET"])
def notif_unread():
    data = {"user_id": _get_user_id()}
    r = handle_notification_unread(data)
    return jsonify(json.loads(r))

# --- COO后台管理（5个，通过subprocess调用bridge_phase8） ---
@lawyer_bp.route("/admin/pending", methods=["GET"])
def admin_pending():
    r = call_bridge("admin_pending_list", dict(request.args))
    return jsonify(r)

@lawyer_bp.route("/admin/audit", methods=["POST"])
def admin_audit():
    data = request.get_json(silent=True) or {}
    r = call_bridge("admin_audit", data)
    return jsonify(r)

@lawyer_bp.route("/admin/list", methods=["GET"])
def admin_list():
    r = call_bridge("admin_list", dict(request.args))
    return jsonify(r)

@lawyer_bp.route("/admin/<int:lawyer_id>/status", methods=["PUT"])
def admin_status(lawyer_id):
    data = request.get_json(silent=True) or {}
    data["lawyer_id"] = lawyer_id
    r = call_bridge("admin_status", data)
    return jsonify(r)

@lawyer_bp.route("/admin/complaints", methods=["GET"])
def admin_complaints():
    r = call_bridge("admin_complaints_list", dict(request.args))
    return jsonify(r)

# ==================== 初始化 ====================
def init_lawyer_module():
    """初始化律师模块（建表等）"""
    try:
        phase1_create_tables()
    except Exception as e:
        print(f"⚠️ Phase1表初始化: {e}")
    try:
        from lawyer_extra_features import create_extra_tables
        create_extra_tables()
    except Exception as e:
        print(f"⚠️ 额外表初始化: {e}")
    print("✅ 律师模块初始化完成")

# 内置处理函数映射（新代码优先）
BUILTIN_HANDLERS = {
    "create_tables": lambda p: phase1_create_tables(),
    "realname": handle_realname,
    "realname_status": handle_realname_status,
    "register": handle_register,
    "cert_upload": handle_cert_upload,
    "status": handle_status,
    "pay_fee": handle_pay_fee,
    "fee_status": handle_fee_status,
    "get_profile": handle_get_profile,
    "update_profile": handle_update_profile,
    "rate_set": handle_rate_set,
    "rate_info": handle_rate_info,
    "notification_list": handle_notification_list,
    "notification_read": handle_notification_read,
    "notification_unread": handle_notification_unread,
}
