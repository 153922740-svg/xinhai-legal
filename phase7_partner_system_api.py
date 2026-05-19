"""
Phase 7: 代理合伙人体系 API
- 合伙人等级管理
- 推荐关系绑定
- 佣金计算
- 收益提现
"""

import os
import uuid
import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

phase7_bp = Blueprint('phase7', __name__)

# 合伙人等级配置（PRD V1.1 终版）
# 5级：初级5%/铜牌8%/银牌12%/金牌15%/钻石20%
# 升级条件：直推人数
PARTNER_LEVELS = {
    1: {'name': '初级', 'commission_rate': 0.05, 'upgrade_threshold': 0, 'referrals_needed': 0},
    2: {'name': '铜牌', 'commission_rate': 0.08, 'upgrade_threshold': 0, 'referrals_needed': 5},
    3: {'name': '银牌', 'commission_rate': 0.12, 'upgrade_threshold': 0, 'referrals_needed': 20},
    4: {'name': '金牌', 'commission_rate': 0.15, 'upgrade_threshold': 0, 'referrals_needed': 50},
    5: {'name': '钻石', 'commission_rate': 0.20, 'upgrade_threshold': 0, 'referrals_needed': 100},
}

# 推荐奖励（PRD V1.1 终版）
# 好友注册：5,000 Token + 100积分
# 好友开会员：30,000 Token + 500积分
# 好友充值：5%返利
REFERRAL_REWARDS = {
    'register': {'tokens': 5000, 'points': 100, 'desc': '好友注册奖励'},
    'member': {'tokens': 30000, 'points': 500, 'desc': '好友开通会员奖励'},
    'recharge': {'rate': 0.05, 'desc': '好友充值5%返利'},
}

# 提现配置
MIN_WITHDRAWAL = 100  # 最低提现金额
WITHDRAWAL_FEE_RATE = 0.01  # 提现手续费 1%

def get_db():
    db = sqlite3.connect('/home/admin/xinhai_legal.db')
    db.row_factory = sqlite3.Row
    return db

# ============== 合伙人等级 ==============

@phase7_bp.route('/api/v1/partner/level', methods=['GET'])
def get_partner_level():
    """
    获取用户合伙人等级
    参数：user_id
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT * FROM partners WHERE user_id = ?', (user_id,))
        partner = cursor.fetchone()
        
        db.close()
        
        if partner:
            level_info = PARTNER_LEVELS.get(partner['level'], PARTNER_LEVELS[1])
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'is_partner': True,
                    'level': partner['level'],
                    'level_name': level_info['name'],
                    'commission_rate': level_info['commission_rate'],
                    'total_earnings': partner['total_earnings'],
                    'created_at': partner['created_at']
                }
            })
        else:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {'is_partner': False}
            })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


@phase7_bp.route('/api/v1/partner/upgrade', methods=['POST'])
def upgrade_partner_level():
    """
    升级合伙人等级（系统自动调用）
    参数：user_id
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # 查询当前合伙人信息
        cursor.execute('SELECT * FROM partners WHERE user_id = ?', (user_id,))
        partner = cursor.fetchone()
        
        if not partner:
            db.close()
            return jsonify({'code': 400, 'message': '用户还不是合伙人'}), 400
        
        # 计算直推人数（PRD升级条件基于直推而非累计收益）
        cursor.execute('SELECT COUNT(*) as total FROM referrals WHERE referrer_id = (SELECT id FROM partners WHERE user_id = ?)', (user_id,))
        result = cursor.fetchone()
        referrals_count = result['total'] or 0
        
        # 判断是否满足升级条件（PRD规则）
        current_level = partner['level']
        new_level = current_level
        
        # 从高到低检查
        for level in [5, 4, 3, 2]:
            if referrals_count >= PARTNER_LEVELS[level]['referrals_needed']:
                new_level = level
                break
        
        # 如果等级提升，更新
        if new_level > current_level:  # 数字越大等级越高
            cursor.execute('''
                UPDATE partners SET level = ?, updated_at = ?
                WHERE user_id = ?
            ''', (new_level, datetime.now().isoformat(), user_id))
            db.commit()
            
            level_info = PARTNER_LEVELS[new_level]
            result = {
                'upgraded': True,
                'new_level': new_level,
                'level_name': level_info['name'],
                'commission_rate': level_info['commission_rate']
            }
        else:
            # 更新累计收益
            cursor.execute('UPDATE partners SET total_earnings = ? WHERE user_id = ?', (total_earnings, user_id))
            db.commit()
            result = {'upgraded': False, 'current_level': current_level}
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '等级检查完成',
            'data': result
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'升级失败：{str(e)}'}), 500


# ============== 推荐关系 ==============

@phase7_bp.route('/api/v1/referral/bind', methods=['POST'])
def bind_referral():
    """
    绑定推荐关系
    参数：user_id, referrer_code (推荐码)
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        referrer_code = data.get('referrer_code')
        
        if not user_id or not referrer_code:
            return jsonify({'code': 400, 'message': '缺少参数'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # 检查用户是否已有推荐人
        cursor.execute('SELECT * FROM referrals WHERE user_id = ?', (user_id,))
        existing = cursor.fetchone()
        if existing:
            db.close()
            return jsonify({'code': 400, 'message': '已绑定推荐人，无法重复绑定'}), 400
        
        # 查找推荐人的用户 ID
        cursor.execute('SELECT user_id FROM partners WHERE referral_code = ?', (referrer_code,))
        referrer = cursor.fetchone()
        if not referrer:
            db.close()
            return jsonify({'code': 400, 'message': '推荐码无效'}), 400
        
        referrer_id = referrer['user_id']
        
        # 不能绑定自己
        if referrer_id == user_id:
            db.close()
            return jsonify({'code': 400, 'message': '不能绑定自己为推荐人'}), 400
        
        # 创建推荐关系
        cursor.execute('''
            INSERT INTO referrals (user_id, referrer_id, created_at)
            VALUES (?, ?, ?)
        ''', (user_id, referrer_id, datetime.now().isoformat()))
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '推荐关系绑定成功',
            'data': {'referrer_id': referrer_id}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'绑定失败：{str(e)}'}), 500


@phase7_bp.route('/api/v1/referral/code', methods=['POST'])
def generate_referral_code():
    """
    生成合伙人推荐码
    参数：user_id
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # 检查是否已是合伙人
        cursor.execute('SELECT * FROM partners WHERE user_id = ?', (user_id,))
        partner = cursor.fetchone()
        
        if not partner:
            # 自动成为普通合伙人
            referral_code = 'REF' + str(uuid.uuid4())[:8].upper()
            cursor.execute('''
                INSERT INTO partners (user_id, level, referral_code, created_at)
                VALUES (?, 1, ?, ?)
            ''', (user_id, referral_code, datetime.now().isoformat()))
            db.commit()
            partner = {'id': cursor.lastrowid, 'level': 1, 'referral_code': referral_code}
        
        db.close()
        
        level_info = PARTNER_LEVELS.get(partner['level'], PARTNER_LEVELS[1])
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'referral_code': partner['referral_code'],
                'level': partner['level'],
                'level_name': level_info['name'],
                'commission_rate': level_info['commission_rate'],
                'referral_link': f'https://xinclaw.com/register?ref={partner["referral_code"]}'
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'生成失败：{str(e)}'}), 500


@phase7_bp.route('/api/v1/referral/team', methods=['GET'])
def get_referral_team():
    """
    获取推荐团队
    参数：user_id
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # 查询直推用户
        cursor.execute('''
            SELECT r.*, u.username, u.created_at as join_date
            FROM referrals r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC
        ''', (user_id,))
        direct_referrals = [dict(row) for row in cursor.fetchall()]
        
        # 查询团队总人数（包括间接推荐）
        cursor.execute('''
            WITH RECURSIVE team AS (
                SELECT user_id FROM referrals WHERE referrer_id = ?
                UNION
                SELECT r.user_id FROM referrals r
                INNER JOIN team t ON r.referrer_id = t.user_id
            )
            SELECT COUNT(*) as count FROM team
        ''', (user_id,))
        team_size = cursor.fetchone()['count']
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'direct_referrals': len(direct_referrals),
                'team_size': team_size,
                'members': direct_referrals[:20]  # 只返回前 20 个
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


# ============== 佣金计算 ==============

@phase7_bp.route('/api/v1/commission/calculate', methods=['POST'])
def calculate_commission():
    """
    计算佣金（订单支付后调用）
    参数：order_id, user_id, amount, type (membership/token)
    """
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        user_id = data.get('user_id')
        amount = float(data.get('amount', 0))
        order_type = data.get('type', 'membership')
        
        if not order_id or not user_id:
            return jsonify({'code': 400, 'message': '缺少参数'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # 查找推荐人
        cursor.execute('SELECT referrer_id FROM referrals WHERE user_id = ?', (user_id,))
        referral = cursor.fetchone()
        
        if not referral:
            db.close()
            return jsonify({
                'code': 200,
                'message': '无推荐人，无需计算佣金',
                'data': {'commission': 0}
            })
        
        referrer_id = referral['referrer_id']
        
        # 获取推荐人等级和佣金比例
        cursor.execute('SELECT level FROM partners WHERE user_id = ?', (referrer_id,))
        partner = cursor.fetchone()
        
        if not partner:
            db.close()
            return jsonify({'code': 400, 'message': '推荐人不是合伙人'}), 400
        
        level_info = PARTNER_LEVELS.get(partner['level'], PARTNER_LEVELS[1])
        commission_rate = level_info['commission_rate']
        
        # 计算佣金
        commission = amount * commission_rate
        
        # 记录佣金
        cursor.execute('''
            INSERT INTO commissions (partner_id, order_id, order_type, amount, rate, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
        ''', (
            referrer_id,
            order_id,
            order_type,
            commission,
            commission_rate,
            datetime.now().isoformat()
        ))
        
        db.commit()
        commission_id = cursor.lastrowid
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '佣金计算成功',
            'data': {
                'commission_id': commission_id,
                'partner_id': referrer_id,
                'amount': commission,
                'rate': commission_rate,
                'status': 'pending'
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'计算失败：{str(e)}'}), 500


@phase7_bp.route('/api/v1/commission/list', methods=['GET'])
def get_commission_list():
    """
    获取佣金记录
    参数：user_id, status (pending/paid), page, limit
    """
    try:
        user_id = request.args.get('user_id')
        status = request.args.get('status', 'all')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # 获取合伙人 ID
        cursor.execute('SELECT id FROM partners WHERE user_id = ?', (user_id,))
        partner = cursor.fetchone()
        
        if not partner:
            db.close()
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {'total': 0, 'items': []}
            })
        
        partner_id = partner['id']
        
        # 查询佣金记录
        if status == 'all':
            cursor.execute('''
                SELECT c.*, o.order_no
                FROM commissions c
                LEFT JOIN member_orders o ON c.order_id = o.id
                WHERE c.partner_id = ?
                ORDER BY c.created_at DESC
                LIMIT ? OFFSET ?
            ''', (partner_id, limit, (page-1)*limit))
        else:
            cursor.execute('''
                SELECT c.*, o.order_no
                FROM commissions c
                LEFT JOIN member_orders o ON c.order_id = o.id
                WHERE c.partner_id = ? AND c.status = ?
                ORDER BY c.created_at DESC
                LIMIT ? OFFSET ?
            ''', (partner_id, status, limit, (page-1)*limit))
        
        commissions = [dict(row) for row in cursor.fetchall()]
        
        # 获取总数
        if status == 'all':
            cursor.execute('SELECT COUNT(*) as count FROM commissions WHERE partner_id = ?', (partner_id,))
        else:
            cursor.execute('SELECT COUNT(*) as count FROM commissions WHERE partner_id = ? AND status = ?', (partner_id, status))
        total = cursor.fetchone()['count']
        
        # 统计待结算和已结算金额
        cursor.execute('SELECT SUM(amount) as total FROM commissions WHERE partner_id = ? AND status = "pending"', (partner_id,))
        pending_amount = cursor.fetchone()['total'] or 0
        
        cursor.execute('SELECT SUM(amount) as total FROM commissions WHERE partner_id = ? AND status = "paid"', (partner_id,))
        paid_amount = cursor.fetchone()['total'] or 0
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': total,
                'page': page,
                'limit': limit,
                'pending_amount': pending_amount,
                'paid_amount': paid_amount,
                'items': commissions
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


# ============== 收益提现 ==============

@phase7_bp.route('/api/v1/withdrawal/apply', methods=['POST'])
def apply_withdrawal():
    """
    申请提现
    参数：user_id, amount, alipay_account, alipay_name
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        amount = float(data.get('amount', 0))
        alipay_account = data.get('alipay_account')
        alipay_name = data.get('alipay_name')
        
        if not user_id or not amount or not alipay_account:
            return jsonify({'code': 400, 'message': '缺少参数'}), 400
        
        # 检查最低提现金额
        if amount < MIN_WITHDRAWAL:
            return jsonify({'code': 400, 'message': f'最低提现金额为{MIN_WITHDRAWAL}元'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # 获取合伙人 ID
        cursor.execute('SELECT id FROM partners WHERE user_id = ?', (user_id,))
        partner = cursor.fetchone()
        
        if not partner:
            db.close()
            return jsonify({'code': 400, 'message': '用户不是合伙人'}), 400
        
        partner_id = partner['id']
        
        # 检查可提现余额
        cursor.execute('''
            SELECT SUM(amount) as total FROM commissions
            WHERE partner_id = ? AND status = 'paid'
        ''', (partner_id,))
        paid_total = cursor.fetchone()['total'] or 0
        
        cursor.execute('''
            SELECT SUM(amount) as total FROM withdrawals
            WHERE partner_id = ? AND status IN ('pending', 'processing')
        ''', (partner_id,))
        withdrawing_total = cursor.fetchone()['total'] or 0
        
        available_balance = paid_total - withdrawing_total
        
        if amount > available_balance:
            db.close()
            return jsonify({
                'code': 400,
                'message': f'可提现余额不足，当前可用：{available_balance:.2f}元',
                'data': {'available_balance': available_balance}
            }), 400
        
        # 计算手续费
        fee = amount * WITHDRAWAL_FEE_RATE
        actual_amount = amount - fee
        
        # 创建提现申请
        cursor.execute('''
            INSERT INTO withdrawals (partner_id, amount, fee, actual_amount, alipay_account, alipay_name, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        ''', (
            partner_id,
            amount,
            fee,
            actual_amount,
            alipay_account,
            alipay_name,
            datetime.now().isoformat()
        ))
        
        db.commit()
        withdrawal_id = cursor.lastrowid
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '提现申请提交成功',
            'data': {
                'withdrawal_id': withdrawal_id,
                'amount': amount,
                'fee': fee,
                'actual_amount': actual_amount,
                'status': 'pending'
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'申请失败：{str(e)}'}), 500


@phase7_bp.route('/api/v1/withdrawal/list', methods=['GET'])
def get_withdrawal_list():
    """
    获取提现记录
    参数：user_id, page, limit
    """
    try:
        user_id = request.args.get('user_id')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # 获取合伙人 ID
        cursor.execute('SELECT id FROM partners WHERE user_id = ?', (user_id,))
        partner = cursor.fetchone()
        
        if not partner:
            db.close()
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {'total': 0, 'items': []}
            })
        
        partner_id = partner['id']
        
        cursor.execute('''
            SELECT * FROM withdrawals
            WHERE partner_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (partner_id, limit, (page-1)*limit))
        
        withdrawals = [dict(row) for row in cursor.fetchall()]
        
        # 获取总数
        cursor.execute('SELECT COUNT(*) as count FROM withdrawals WHERE partner_id = ?', (partner_id,))
        total = cursor.fetchone()['count']
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': total,
                'page': page,
                'limit': limit,
                'items': withdrawals
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


@phase7_bp.route('/api/v1/withdrawal/approve', methods=['POST'])
def approve_withdrawal():
    """
    审核通过提现（管理员接口）
    参数：withdrawal_id, admin_id
    """
    try:
        data = request.get_json()
        withdrawal_id = data.get('withdrawal_id')
        admin_id = data.get('admin_id')
        
        if not withdrawal_id:
            return jsonify({'code': 400, 'message': '缺少 withdrawal_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            UPDATE withdrawals
            SET status = 'processing',
                admin_id = ?,
                approved_at = ?
            WHERE id = ?
        ''', (admin_id, datetime.now().isoformat(), withdrawal_id))
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '提现已批准，等待打款'
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'操作失败：{str(e)}'}), 500


@phase7_bp.route('/api/v1/withdrawal/complete', methods=['POST'])
def complete_withdrawal():
    """
    标记提现已完成打款（管理员接口）
    参数：withdrawal_id, admin_id, payment_proof
    """
    try:
        data = request.get_json()
        withdrawal_id = data.get('withdrawal_id')
        admin_id = data.get('admin_id')
        
        if not withdrawal_id:
            return jsonify({'code': 400, 'message': '缺少 withdrawal_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            UPDATE withdrawals
            SET status = 'completed',
                admin_id = ?,
                completed_at = ?,
                payment_proof = ?
            WHERE id = ?
        ''', (admin_id, datetime.now().isoformat(), data.get('payment_proof', ''), withdrawal_id))
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '提现已完成'
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'操作失败：{str(e)}'}), 500


# ============== 合伙人后台数据 ==============

@phase7_bp.route('/api/v1/partner/dashboard', methods=['GET'])
def get_partner_dashboard():
    """
    合伙人后台数据看板
    参数：user_id
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        # 获取合伙人信息
        cursor.execute('SELECT * FROM partners WHERE user_id = ?', (user_id,))
        partner = cursor.fetchone()
        
        if not partner:
            db.close()
            return jsonify({'code': 400, 'message': '用户不是合伙人'}), 400
        
        partner_id = partner['id']
        level_info = PARTNER_LEVELS.get(partner['level'], PARTNER_LEVELS[1])
        
        # 直推人数
        cursor.execute('SELECT COUNT(*) as count FROM referrals WHERE referrer_id = ?', (user_id,))
        direct_count = cursor.fetchone()['count']
        
        # 团队总人数
        cursor.execute('''
            WITH RECURSIVE team AS (
                SELECT user_id FROM referrals WHERE referrer_id = ?
                UNION
                SELECT r.user_id FROM referrals r
                INNER JOIN team t ON r.referrer_id = t.user_id
            )
            SELECT COUNT(*) as count FROM team
        ''', (user_id,))
        team_size = cursor.fetchone()['count']
        
        # 佣金统计
        cursor.execute('SELECT SUM(amount) as total FROM commissions WHERE partner_id = ? AND status = "pending"', (partner_id,))
        pending_commission = cursor.fetchone()['total'] or 0
        
        cursor.execute('SELECT SUM(amount) as total FROM commissions WHERE partner_id = ? AND status = "paid"', (partner_id,))
        paid_commission = cursor.fetchone()['total'] or 0
        
        # 可提现余额
        cursor.execute('SELECT SUM(amount) as total FROM withdrawals WHERE partner_id = ? AND status IN ("pending", "processing")', (partner_id,))
        withdrawing = cursor.fetchone()['total'] or 0
        available_balance = paid_commission - withdrawing
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'level': partner['level'],
                'level_name': level_info['name'],
                'commission_rate': level_info['commission_rate'],
                'referral_code': partner['referral_code'],
                'direct_referrals': direct_count,
                'team_size': team_size,
                'pending_commission': pending_commission,
                'paid_commission': paid_commission,
                'available_balance': available_balance,
                'referral_link': f'https://xinclaw.com/register?ref={partner["referral_code"]}'
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


# ============== 数据库初始化 ==============

def init_phase7_tables():
    """
    初始化 Phase 7 数据库表
    """
    db = get_db()
    cursor = db.cursor()
    
    # 合伙人表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL UNIQUE,
            level INTEGER DEFAULT 1,
            referral_code TEXT UNIQUE,
            total_earnings REAL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    
    # 推荐关系表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            referrer_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id)
        )
    ''')
    
    # 佣金表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_id INTEGER NOT NULL,
            order_id TEXT NOT NULL,
            order_type TEXT DEFAULT 'membership',
            amount REAL NOT NULL,
            rate REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            paid_at TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # 提现表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            fee REAL DEFAULT 0,
            actual_amount REAL,
            alipay_account TEXT,
            alipay_name TEXT,
            status TEXT DEFAULT 'pending',
            admin_id TEXT,
            approved_at TEXT,
            completed_at TEXT,
            payment_proof TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    db.commit()
    db.close()
    print("Phase 7 数据库表初始化完成")


if __name__ == '__main__':
    init_phase7_tables()
    print("Phase 7 代理合伙人体系 API 模块就绪")
