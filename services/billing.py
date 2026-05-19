"""
心海法律AI - 用户会员与 Token 计费系统
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from models.db import get_db, UserModel


class BillingService:
    """Token计费与会员服务"""
    
    def __init__(self, config: Dict):
        self.config = config
        billing_cfg = config.get('billing') or config.get('pricing', {})
        
        # Token价格 (元/1000 tokens)
        self.token_prices = billing_cfg['token_prices']
        self.default_free_tokens = billing_cfg['default_free_tokens']
        
        # 会员方案
        self.membership_plans = {
            'monthly': {
                'price': billing_cfg['membership']['monthly'],
                'duration_days': 30,
                'tokens': billing_cfg['membership']['monthly_tokens'],
                'name': '月度会员'
            },
            'quarterly': {
                'price': billing_cfg['membership']['quarterly'],
                'duration_days': 90,
                'tokens': billing_cfg['membership']['quarterly_tokens'],
                'name': '季度会员'
            },
            'yearly': {
                'price': billing_cfg['membership']['yearly'],
                'duration_days': 365,
                'tokens': billing_cfg['membership']['yearly_tokens'],
                'name': '年度会员'
            }
        }
    
    def get_token_price(self, user_id: int) -> float:
        """获取用户的token单价 (会员有折扣)"""
        user = UserModel.get_by_id(user_id)
        if user and user['membership'] != 'free':
            return self.token_prices['premium']
        return self.token_prices['basic']
    
    def can_use(self, user_id: int, tokens_needed: int) -> bool:
        """检查用户是否有足够token"""
        user = UserModel.get_by_id(user_id)
        if not user:
            return False
        return user['tokens_balance'] >= tokens_needed
    
    def consume(self, user_id: int, tokens: int, description: str = "") -> bool:
        """消耗用户token"""
        return UserModel.deduct_tokens(user_id, tokens, description)
    
    def create_membership_order(self, user_id: int, plan: str) -> Optional[Dict]:
        """创建会员订单"""
        plan_info = self.membership_plans.get(plan)
        if not plan_info:
            return None
        
        db_path = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'
        conn = get_db(db_path)
        try:
            cursor = conn.execute("""
                INSERT INTO membership_orders (user_id, plan, price, duration_days, tokens_granted, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            """, (user_id, plan, plan_info['price'], plan_info['duration_days'], plan_info['tokens']))
            conn.commit()
            
            order = conn.execute(
                "SELECT * FROM membership_orders WHERE id=?", (cursor.lastrowid,)
            ).fetchone()
            return dict(order)
        finally:
            conn.close()
    
    def activate_membership(self, order_id: int) -> bool:
        """激活会员 (支付成功后调用)"""
        db_path = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'
        conn = get_db(db_path)
        try:
            order = conn.execute(
                "SELECT * FROM membership_orders WHERE id=? AND status='pending'",
                (order_id,)
            ).fetchone()
            if not order:
                return False
            
            order = dict(order)
            user_id = order['user_id']
            plan = order['plan']
            plan_info = self.membership_plans[plan]
            
            # 检查当前会员，在现有基础上延长
            user = UserModel.get_by_id(user_id)
            now = datetime.now()
            
            if user['membership_end']:
                try:
                    current_end = datetime.fromisoformat(user['membership_end'])
                    if current_end > now:
                        new_end = current_end + timedelta(days=plan_info['duration_days'])
                    else:
                        new_end = now + timedelta(days=plan_info['duration_days'])
                except:
                    new_end = now + timedelta(days=plan_info['duration_days'])
            else:
                new_end = now + timedelta(days=plan_info['duration_days'])
            
            # 更新用户会员状态
            conn.execute("""
                UPDATE users SET membership=?, membership_start=?, membership_end=?, 
                    tokens_balance = tokens_balance + ?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (plan, now.isoformat(), new_end.isoformat(), plan_info['tokens'], user_id))
            
            # 记录token发放
            conn.execute("""
                INSERT INTO token_transactions (user_id, amount, balance_after, 
                    transaction_type, description, reference_id)
                VALUES (?, ?, (SELECT tokens_balance FROM users WHERE id=?), 
                    'membership_bonus', ?, ?)
            """, (user_id, plan_info['tokens'], user_id, f"会员{plan_info['name']}赠送", str(order_id)))
            
            # 更新订单状态
            conn.execute("""
                UPDATE membership_orders SET status='paid', paid_at=CURRENT_TIMESTAMP WHERE id=?
            """, (order_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"[Billing] activate_membership error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def purchase_tokens(self, user_id: int, amount_rmb: float) -> Optional[Dict]:
        """购买 Token（按PRD定价：2元=10,000 Token）"""
        user = UserModel.get_by_id(user_id)
        if not user:
            return None
        
        # PRD定价: 2元=10,000 Token → 0.2元/千Token
        price_per_1k = self.get_token_price(user_id)
        tokens = int(amount_rmb / price_per_1k * 1000)
        
        # PRD固定充值档位（含优惠bonus）
        package_map = {
            10: 50000,
            30: 160000,
            50: 270000,
            100: 600000,
            500: 3200000
        }
        if int(amount_rmb) in package_map:
            tokens = package_map[int(amount_rmb)]
        
        if tokens <= 0:
            return None
        
        # 创建购买记录
        db_path = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'
        conn = get_db(db_path)
        try:
            success = UserModel.add_tokens(
                user_id, tokens, 'purchase',
                f"购买{amount_rmb}元 = {tokens} tokens"
            )
            if success:
                return {
                    'tokens': tokens,
                    'amount': amount_rmb,
                    'price_per_1k': price_per_1k,
                    'balance_after': UserModel.get_by_id(user_id)['tokens_balance']
                }
            return None
        finally:
            conn.close()
    
    def get_usage_stats(self, user_id: int) -> Dict:
        """获取用户使用统计"""
        db_path = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'
        conn = get_db(db_path)
        try:
            # 本月使用
            first_of_month = datetime.now().replace(day=1).isoformat()
            monthly_usage = conn.execute("""
                SELECT COALESCE(SUM(ABS(amount)), 0) as total
                FROM token_transactions 
                WHERE user_id=? AND transaction_type='usage' AND created_at >= ?
            """, (user_id, first_of_month)).fetchone()
            
            # 总统计
            user = UserModel.get_by_id(user_id)
            if not user:
                return {}
            
            return {
                'tokens_balance': user['tokens_balance'],
                'total_tokens_used': user['total_tokens_used'],
                'total_tokens_bought': user['total_tokens_bought'],
                'membership': user['membership'],
                'membership_end': user.get('membership_end'),
                'monthly_usage': monthly_usage['total'] if monthly_usage else 0
            }
        finally:
            conn.close()
    
    def check_membership_status(self, user_id: int) -> Dict:
        """检查会员状态"""
        user = UserModel.get_by_id(user_id)
        if not user:
            return {'is_valid': False, 'membership': 'none'}
        
        membership = user['membership']
        end_str = user.get('membership_end')
        
        if membership == 'free':
            return {'is_valid': False, 'membership': 'free', 'level': 'free'}
        
        if end_str:
            try:
                end = datetime.fromisoformat(end_str)
                if end < datetime.now():
                    # 会员已过期
                    UserModel.update(user_id, membership='free', membership_end=None)
                    return {'is_valid': False, 'membership': 'expired', 'level': 'free'}
                
                days_left = (end - datetime.now()).days
                return {
                    'is_valid': True,
                    'membership': membership,
                    'level': self.membership_plans.get(membership, {}).get('name', membership),
                    'days_left': days_left,
                    'end_date': end_str
                }
            except:
                pass
        
        return {'is_valid': False, 'membership': 'unknown'}
