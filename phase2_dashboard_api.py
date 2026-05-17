"""
心海法律 AI - Phase 2 数据看板 API
运营数据、财务数据统计
"""

from flask import Blueprint, request, jsonify
from models.db import get_db
from datetime import datetime, timedelta

phase2_dashboard_bp = Blueprint('phase2_dashboard', __name__, url_prefix='/api/v2/dashboard')


# ============== 核心指标 ==============

@phase2_dashboard_bp.route('/metrics/overview', methods=['GET'])
def get_overview_metrics():
    """
    获取核心运营指标
    GET /api/v2/dashboard/metrics/overview?days=7
    
    Response:
    {
        "code": 200,
        "data": {
            "period_days": 7,
            "revenue": 12580.00,
            "new_members": 156,
            "active_users": 890,
            "total_consultations": 2345,
            "conversion_rate": 0.175
        }
    }
    """
    try:
        days = request.args.get('days', 7, type=int)
        since = datetime.now() - timedelta(days=days)
        
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        
        # 总收入
        revenue = conn.execute("""
            SELECT COALESCE(SUM(price), 0)
            FROM membership_orders
            WHERE status='paid' AND paid_at >= ?
        """, (since.isoformat(),)).fetchone()[0]
        
        # 新会员数
        new_members = conn.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM membership_orders
            WHERE status='paid' AND paid_at >= ?
        """, (since.isoformat(),)).fetchone()[0]
        
        # 活跃用户数（有咨询记录）
        active_users = conn.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM chat_messages
            WHERE created_at >= ?
        """, (since.isoformat(),)).fetchone()[0]
        
        # 总咨询数
        total_consultations = conn.execute("""
            SELECT COUNT(*)
            FROM chat_messages
            WHERE role='user' AND created_at >= ?
        """, (since.isoformat(),)).fetchone()[0]
        
        # 转化率（新会员 / 活跃用户）
        conversion_rate = new_members / active_users if active_users > 0 else 0
        
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'period_days': days,
                'revenue': round(revenue, 2),
                'new_members': new_members,
                'active_users': active_users,
                'total_consultations': total_consultations,
                'conversion_rate': round(conversion_rate, 4)
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取指标失败：{str(e)}',
            'data': None
        }), 500


# ============== 收入趋势 ==============

@phase2_dashboard_bp.route('/metrics/revenue-trend', methods=['GET'])
def get_revenue_trend():
    """
    获取收入趋势数据
    GET /api/v2/dashboard/metrics/revenue-trend?days=30
    
    Response:
    {
        "code": 200,
        "data": {
            "days": 30,
            "trend": [
                {"date": "2026-04-17", "revenue": 450.00, "orders": 15},
                {"date": "2026-04-18", "revenue": 520.00, "orders": 18}
            ]
        }
    }
    """
    try:
        days = request.args.get('days', 30, type=int)
        since = datetime.now() - timedelta(days=days)
        
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        
        # 按日期统计收入
        trend = conn.execute("""
            SELECT 
                DATE(paid_at) as date,
                SUM(price) as revenue,
                COUNT(*) as orders
            FROM membership_orders
            WHERE status='paid' AND paid_at >= ?
            GROUP BY DATE(paid_at)
            ORDER BY date ASC
        """, (since.isoformat(),)).fetchall()
        
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'days': days,
                'trend': [dict(t) for t in trend]
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取收入趋势失败：{str(e)}',
            'data': None
        }), 500


# ============== 会员方案分布 ==============

@phase2_dashboard_bp.route('/metrics/membership-distribution', methods=['GET'])
def get_membership_distribution():
    """
    获取会员方案分布
    GET /api/v2/dashboard/metrics/membership-distribution
    
    Response:
    {
        "code": 200,
        "data": {
            "distribution": [
                {"plan": "monthly", "name": "月度会员", "count": 234, "percentage": 0.45},
                {"plan": "quarterly", "name": "季度会员", "count": 156, "percentage": 0.30},
                {"plan": "yearly", "name": "年度会员", "count": 130, "percentage": 0.25}
            ],
            "total": 520
        }
    }
    """
    try:
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        
        # 当前会员分布
        distribution = conn.execute("""
            SELECT membership, COUNT(*) as count
            FROM users
            WHERE membership != 'free' AND membership_end >= datetime('now')
            GROUP BY membership
        """).fetchall()
        
        total = sum(r['count'] for r in distribution)
        
        plan_names = {
            'monthly': '月度会员',
            'quarterly': '季度会员',
            'yearly': '年度会员'
        }
        
        result = []
        for r in distribution:
            result.append({
                'plan': r['membership'],
                'name': plan_names.get(r['membership'], r['membership']),
                'count': r['count'],
                'percentage': round(r['count'] / total, 4) if total > 0 else 0
            })
        
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'distribution': result,
                'total': total
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取会员分布失败：{str(e)}',
            'data': None
        }), 500


# ============== 订单统计 ==============

@phase2_dashboard_bp.route('/metrics/order-stats', methods=['GET'])
def get_order_stats():
    """
    获取订单统计
    GET /api/v2/dashboard/metrics/order-stats?days=7
    
    Response:
    {
        "code": 200,
        "data": {
            "total_orders": 234,
            "paid_orders": 198,
            "pending_orders": 36,
            "total_revenue": 8760.00,
            "average_order_value": 44.24
        }
    }
    """
    try:
        days = request.args.get('days', 7, type=int)
        since = datetime.now() - timedelta(days=days)
        
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        
        # 总订单数
        total = conn.execute("""
            SELECT COUNT(*) FROM membership_orders WHERE created_at >= ?
        """, (since.isoformat(),)).fetchone()[0]
        
        # 已支付订单数
        paid = conn.execute("""
            SELECT COUNT(*) FROM membership_orders 
            WHERE status='paid' AND paid_at >= ?
        """, (since.isoformat(),)).fetchone()[0]
        
        # 待支付订单数
        pending = conn.execute("""
            SELECT COUNT(*) FROM membership_orders 
            WHERE status IN ('pending', 'pending_payment') AND created_at >= ?
        """, (since.isoformat(),)).fetchone()[0]
        
        # 总收入
        revenue = conn.execute("""
            SELECT COALESCE(SUM(price), 0)
            FROM membership_orders
            WHERE status='paid' AND paid_at >= ?
        """, (since.isoformat(),)).fetchone()[0]
        
        # 平均订单价值
        avg_value = revenue / paid if paid > 0 else 0
        
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'period_days': days,
                'total_orders': total,
                'paid_orders': paid,
                'pending_orders': pending,
                'total_revenue': round(revenue, 2),
                'average_order_value': round(avg_value, 2)
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取订单统计失败：{str(e)}',
            'data': None
        }), 500


# ============== 用户增长趋势 ==============

@phase2_dashboard_bp.route('/metrics/user-growth', methods=['GET'])
def get_user_growth():
    """
    获取用户增长趋势
    GET /api/v2/dashboard/metrics/user-growth?days=30
    
    Response:
    {
        "code": 200,
        "data": {
            "days": 30,
            "trend": [
                {"date": "2026-04-17", "new_users": 23, "total_users": 1234},
                {"date": "2026-04-18", "new_users": 28, "total_users": 1262}
            ]
        }
    }
    """
    try:
        days = request.args.get('days', 30, type=int)
        since = datetime.now() - timedelta(days=days)
        
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        
        # 按日期统计新用户
        trend = conn.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as new_users
            FROM users
            WHERE created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """, (since.isoformat(),)).fetchall()
        
        # 计算累计用户数
        current_total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        
        # 反向计算每天的总用户数
        result = []
        running_total = current_total
        for row in reversed(trend):
            running_total -= row['new_users']
            result.insert(0, {
                'date': row['date'],
                'new_users': row['new_users'],
                'total_users': running_total + row['new_users']
            })
        
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'days': days,
                'trend': result
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取用户增长趋势失败：{str(e)}',
            'data': None
        }), 500


# ============== 健康检查 ==============

@phase2_dashboard_bp.route('/health', methods=['GET'])
def dashboard_health():
    """
    数据看板健康检查
    GET /api/v2/dashboard/health
    """
    try:
        import sqlite3
        conn = sqlite3.connect('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        conn.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'dashboard_router': 'available',
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'dashboard_router': 'unavailable',
            'error': str(e)
        }), 500
