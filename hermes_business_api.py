#!/usr/bin/env python3
"""
Hermes Business API v1 — 通过 bridge subprocess 处理所有业务请求
提供认证、支付、用户管理等业务 API
端口：8647
"""
import json, subprocess, uuid, os, urllib.parse, time, logging, sys
from http.server import HTTPServer, BaseHTTPRequestHandler

# 加载 .env 文件
_env_path = '/home/admin/xinhai_legal_api/.env'
if os.path.exists(_env_path):
    with open(_env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

PORT = 8647
BRIDGE = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge.py'
BRIDGE_P0 = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_p0.py'
BRIDGE_P1_DOC = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_p1_doc.py'
BRIDGE_P1_INTEGRAL = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_p1_integral.py'
BRIDGE_P1_PARTNER = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_p1_partner.py'
BRIDGE_P1_PAYMENT = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_p1_payment.py'
BRIDGE_P2_MEMORY = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_p2_memory.py'
BRIDGE_P2_HISTORY = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_p2_history.py'
BRIDGE_P2_EVOLUTION = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_p2_evolution.py'
BRIDGE_P2_DASHBOARD = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_p2_dashboard.py'
BRIDGE_P2_RECOMMEND = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_p2_recommend.py'
BRIDGE_P3_VALIDATION = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_validation.py'
BRIDGE_AGENT = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_agent.py'
BRIDGE_LAWYER = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/xinhai_legal_api/hermes_lawyer_bridge_phase1.py'
BRIDGE_LAWYER_AI = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/xinhai_legal_api/hermes_lawyer_bridge_phase2.py'
BRIDGE_LAWYER_WALLET = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/xinhai_legal_api/hermes_lawyer_bridge_phase4.py'
BRIDGE_LAWYER_SCHEDULE = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/xinhai_legal_api/hermes_lawyer_bridge_phase5.py'
BRIDGE_LAWYER_REVIEW = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/xinhai_legal_api/hermes_lawyer_bridge_phase6.py'
BRIDGE_LAWYER_USER = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/xinhai_legal_api/hermes_lawyer_bridge_phase7.py'
BRIDGE_LAWYER_ADMIN = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/xinhai_legal_api/hermes_lawyer_bridge_phase8.py'
BRIDGE_LAWYER_NOTIFICATION = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/xinhai_legal_api/p5_lawyer_notification.py'
BRIDGE_ENTRUST = '/home/admin/.hermes/hermes-agent/venv/bin/python3 /home/admin/hermes_business_bridge_entrust.py'
LOG_FILE = '/home/admin/hermes_business_api.log'

# 设置数据库路径环境变量
os.environ['DB_PATH'] = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'
os.environ['PYTHONUNBUFFERED'] = '1'

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('HermesBusinessAPI')


class BusinessAPIHandler(BaseHTTPRequestHandler):
    """Hermes Business API HTTP Handler"""

    # ==================== 辅助方法 ====================

    def _get_token(self):
        """从请求头获取 token"""
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            return auth[7:]
        return None

    def _json(self, data, status=200):
        """返回 JSON 响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _read_body(self):
        """读取并解析请求体 JSON（优先使用缓存的 raw_body）"""
        try:
            raw = getattr(self, '_raw_body_raw', '')
            if not raw:
                length = int(self.headers.get('Content-Length', 0))
                if length > 0:
                    raw = self.rfile.read(length).decode('utf-8')
                else:
                    return {}
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return {}
        except Exception as e:
            logger.error(f"读取请求体失败: {e}")
            return {}

    def _run_bridge(self, *args, timeout=30):
        """运行bridge脚本并返回JSON结果"""
        cmd = [BRIDGE.split()[0]] + BRIDGE.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.returncode != 0:
                if r.stdout.strip():
                    return json.loads(r.stdout.strip())
                raise Exception(r.stderr[:500] or 'Bridge returned error')
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception('Bridge returned empty')
        except subprocess.TimeoutExpired:
            logger.error(f"[Bridge] 超时 ({timeout}s)")
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            logger.error(f"[Bridge] JSON解析失败: {e}, output: {r.stdout[:500] if 'r' in dir() else ''}")
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            logger.error(f"[Bridge] 执行失败: {e}")
            return {'success': False, 'error': str(e)}

    def _parse_path(self):
        """解析 URL 路径，返回 (path, query_dict)"""
        parsed = urllib.parse.urlparse(self.path)
        p = parsed.path
        q = urllib.parse.parse_qs(parsed.query)
        return p, q

    # ==================== 路由装饰器风格 ====================

    _routes_get = {}
    _routes_post = {}

    @classmethod
    def register_route(cls, method, path, handler_name):
        """注册路由"""
        if method == 'GET':
            cls._routes_get[path] = handler_name
        elif method == 'POST':
            cls._routes_post[path] = handler_name

    # ==================== HTTP 方法 ====================

    def do_OPTIONS(self):
        """CORS 预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_PUT(self):
        """处理 PUT 请求 — 委托给 do_POST"""
        self.do_POST()

    def do_GET(self):
        """处理 GET 请求"""
        p, q = self._parse_path()
        logger.info(f"GET {p}")

        try:
            # 路由分发
            if p in ('/health', '/api/v1/health', '/app/info', '/api/v1/app/info'):
                self._json({'status': 'ok', 'app': 'hermes-business-api', 'version': '1.0'})
            elif p == '/':
                self._json({'status': 'ok', 'app': 'hermes-business-api', 'version': '1.0'})
            # ========== P0 Token计费 GET 路由 ==========
            elif p in ('/token/packages', '/api/v1/token/packages', '/p0/token/packages'):
                body = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
                self._handle_bridge_p0('token_get_packages', body)
            elif p in ('/token/balance', '/api/v1/token/balance', '/p0/token/balance'):
                body = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
                self._handle_bridge_p0('token_get_balance', body)
            # ========== P0 会员系统 GET 路由 ==========
            elif p in ('/member/status', '/api/v1/member/status', '/p0/member/status', '/auth/me', '/api/v1/auth/me'):
                body = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
                self._handle_bridge_p0('member_get_status', body)
            elif p in ('/user/verify-status', '/api/v1/user/verify-status'):
                body = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
                self._handle_bridge_p0('user_verify_status', body)
            # P0 活动 GET 路由
            elif p in ('/activity/list', '/api/v1/activity/list'):
                body = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
                self._handle_bridge_p0('activity_list', body)
            elif p in ('/activity/my-participations', '/api/v1/activity/my-participations'):
                body = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
                self._handle_bridge_p0('activity_my_participations', body)
            # P0 通知 GET 路由
            elif p in ('/notification/list', '/api/v1/notification/list'):
                body = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
                self._handle_bridge_p0('notification_list', body)
            # P0 推广 GET 路由
            elif p in ('/promotion/stats', '/api/v1/promotion/stats'):
                body = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
                self._handle_bridge_p0('promotion_stats', body)
            elif p in ('/member/packages', '/api/v1/member/packages', '/p0/member/packages', '/order/list', '/api/v1/order/list'):
                body = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
                self._handle_bridge_p0('member_get_plans', body)
            # P0 档案管理 GET 路由
            elif p in ('/archive/list', '/api/v1/archive/list'):
                body = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
                self._handle_bridge_p0('archive_list', body)
            # P0 用户认证 GET 路由
            elif p in ('/auth/profile', '/api/v1/auth/profile'):
                body = {k: v[0] if isinstance(v, list) else v for k, v in q.items()}
                self._handle_bridge_p0('user_get_profile', body)
            # P1 文书生成 GET 路由
            elif p in ('/document/templates', '/api/v1/document/templates', '/p1/document/templates'):
                self._handle_bridge_p1_doc_get('document_templates', q)
            elif p in ('/document/template/detail', '/api/v1/document/template/detail', '/p1/document/template/detail'):
                self._handle_bridge_p1_doc_get('document_template_detail', q)
            elif p in ('/document/history', '/api/v1/document/history', '/p1/document/history', '/document/list', '/api/v1/document/list'):
                self._handle_bridge_p1_doc_get('document_history', q)
            # P1 积分系统 GET 路由
            elif p in ('/integral/balance', '/api/v1/integral/balance', '/p1/integral/balance', '/user/points', '/api/v1/user/points'):
                self._handle_bridge_p1_integral('balance', q)
            elif p in ('/integral/records', '/api/v1/integral/records', '/p1/integral/records'):
                self._handle_bridge_p1_integral('records', q)
            elif p in ('/integral/tasks', '/api/v1/integral/tasks', '/p1/integral/tasks'):
                self._handle_bridge_p1_integral('tasks', q)
            elif p in ('/integral/sign/status', '/api/v1/integral/sign/status', '/p1/integral/sign/status', '/integral/signin', '/api/v1/integral/signin', '/user/sign/status', '/api/v1/user/sign/status', '/user/sign/data', '/api/v1/user/sign/data'):
                self._handle_bridge_p1_integral('sign_status', q)
            elif p in ('/integral/shop', '/api/v1/integral/shop', '/p1/integral/shop', '/mall/goods', '/api/v1/mall/goods'):
                self._handle_bridge_p1_integral('shop_items', q)
            elif p in ('/integral/orders', '/api/v1/integral/orders', '/p1/integral/orders'):
                self._handle_bridge_p1_integral('exchange_orders', q)
            # P1 合伙人系统 GET 路由
            elif p in ('/partner/level', '/api/v1/partner/level', '/p1/partner/level', '/partner/info', '/api/v1/partner/info', '/partner/status', '/api/v1/partner/status'):
                self._handle_bridge_p1_partner('partner_level', q)
            elif p in ('/referral/team', '/api/v1/referral/team', '/p1/referral/team', '/partner/team-members', '/api/v1/partner/team-members'):
                self._handle_bridge_p1_partner('referral_team', q)
            elif p in ('/commission/list', '/api/v1/commission/list', '/p1/commission/list', '/partner/commissions', '/api/v1/partner/commissions', '/partner/profit-records', '/api/v1/partner/profit-records', '/commission/records', '/api/v1/commission/records'):
                self._handle_bridge_p1_partner('commission_list', q)
            elif p in ('/withdrawal/list', '/api/v1/withdrawal/list', '/p1/withdrawal/list', '/commission/withdraw/list', '/api/v1/commission/withdraw/list'):
                self._handle_bridge_p1_partner('withdrawal_list', q)
            elif p in ('/partner/dashboard', '/api/v1/partner/dashboard', '/p1/partner/dashboard'):
                self._handle_bridge_p1_partner('partner_dashboard', q)
            # P1 支付系统 GET 路由
            elif p in ('/payment/wechat/status', '/api/v1/payment/wechat/status', '/p1/payment/wechat/status'):
                self._handle_bridge_p1_payment('payment_status', q)
            elif p in ('/payment/health', '/api/v1/payment/health', '/p1/payment/health'):
                self._handle_bridge_p1_payment('payment_health', q)
            # P2 用户记忆 GET 路由
            elif p in ('/user/memory', '/api/v1/user/memory', '/memory/info', '/api/v1/memory/info'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_p2_memory('get_memory', q_flat)
            # P2 对话历史 GET 路由
            elif p in ('/chat/sessions', '/api/v1/chat/sessions', '/history/list', '/api/v1/history/list'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_p2_history('sessions', q_flat)
            # P2 自进化 GET 路由
            elif p in ('/badcases/list', '/api/v1/badcases/list', '/ai/evolution-stats', '/api/v1/ai/evolution-stats', '/evolution/stats', '/api/v1/evolution/stats'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_p2_evolution('list_badcases', q_flat)
            # P2 数据看板 GET 路由
            elif p in ('/dashboard/overview', '/api/v1/dashboard/overview'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_p2_dashboard('overview', q_flat)
            elif p in ('/dashboard/revenue-trend', '/api/v1/dashboard/revenue-trend'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_p2_dashboard('revenue_trend', q_flat)
            elif p in ('/dashboard/membership-distribution', '/api/v1/dashboard/membership-distribution'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_p2_dashboard('membership_distribution', q_flat)
            elif p in ('/dashboard/order-stats', '/api/v1/dashboard/order-stats'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_p2_dashboard('order_stats', q_flat)
            elif p in ('/dashboard/user-growth', '/api/v1/dashboard/user-growth'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_p2_dashboard('user_growth', q_flat)
            # 文书下载路由（/document/download/<doc_id>）
            elif p.startswith('/document/download/') or p.startswith('/api/v1/document/download/'):
                # 提取文档ID
                if p.startswith('/api/v1/document/download/'):
                    doc_id = p[len('/api/v1/document/download/'):]
                else:
                    doc_id = p[len('/document/download/'):]
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                q_flat['document_id'] = doc_id
                self._handle_bridge_p1_doc_get('document_download', q_flat)
            # 历史记录列表路由（/history/list）
            elif p in ('/history/list', '/api/v1/history/list'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_p2_history('sessions', q_flat)
            # P3 三模型交叉验证 GET 路由
            elif p in ('/model/stats', '/api/v1/model/stats'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_p3_validation('model_stats', q_flat)
            # ========== 代理商系统 GET 路由 ==========
            elif p in ('/agent/list', '/api/v1/agent/list'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_bridge_agent('agent_list', q_flat)
            elif p in ('/agent/detail', '/api/v1/agent/detail'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_bridge_agent('agent_detail', q_flat)
            elif p in ('/agent/stats', '/api/v1/agent/stats'):
                self._handle_bridge_agent('agent_stats', {})
            elif p in ('/agent/commissions', '/api/v1/agent/commissions'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_bridge_agent('agent_commissions', q_flat)
            elif p in ('/agent/regions', '/api/v1/agent/regions'):
                self._handle_bridge_agent('agent_regions', {})
            # ========== 律师板块 GET 路由 ==========
            # 简单路径匹配
            elif p in ('/lawyer/status', '/api/v1/lawyer/status', '/api/lawyer/status'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_bridge_lawyer_get('status', q)
            elif p in ('/lawyer/fee-status', '/api/v1/lawyer/fee-status', '/api/lawyer/fee-status'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_bridge_lawyer_get('fee_status', q)
            elif p in ('/lawyer/profile', '/api/v1/lawyer/profile', '/api/lawyer/profile'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_bridge_lawyer_get('get_profile', q)
            elif p in ('/lawyer/cases', '/api/v1/lawyer/cases', '/api/lawyer/cases'):
                q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in q.items()}
                self._handle_bridge_lawyer_get('cases_list', q)
            # 带 case_id 的动态路径
            elif p.startswith('/lawyer/cases/') or p.startswith('/api/v1/lawyer/cases/') or p.startswith('/api/lawyer/cases/'):
                self._match_lawyer_case_path_get(p, q)
            # ========== 律师钱包模块 GET 路由 ==========
            elif p in ('/api/lawyer/wallet', '/api/v1/lawyer/wallet'):
                self._handle_bridge_lawyer_wallet_get('wallet', q)
            elif p in ('/api/lawyer/wallet/withdrawals', '/api/v1/lawyer/wallet/withdrawals'):
                self._handle_bridge_lawyer_wallet_get('withdrawals', q)
            elif p in ('/api/lawyer/wallet/income', '/api/v1/lawyer/wallet/income'):
                self._handle_bridge_lawyer_wallet_get('income', q)
            elif p in ('/api/lawyer/wallet/settlements', '/api/v1/lawyer/wallet/settlements'):
                self._handle_bridge_lawyer_wallet_get('settlements', q)
            # ========== 律师日程模块 GET 路由 ==========
            elif p in ('/api/lawyer/schedules', '/api/v1/lawyer/schedules'):
                self._handle_bridge_lawyer_schedule_get('schedules_list', q)
            # ========== 律师评价模块 GET 路由 ==========
            elif p in ('/api/lawyer/reviews', '/api/v1/lawyer/reviews'):
                self._handle_bridge_lawyer_review_get('reviews_list', q)
            # ========== 用户端找律师模块 GET 路由 ==========
            elif p in ('/api/lawyer/list', '/api/v1/lawyer/list'):
                self._handle_bridge_lawyer_user_get('lawyer_list', q)
            elif p.startswith('/api/lawyer/') and p.split('/')[-1].isdigit():
                # 律师详情: /api/lawyer/{lawyer_id}
                lawyer_id = p.split('/')[-1]
                self._handle_bridge_lawyer_user_get('lawyer_detail', {**q, 'lawyer_id': lawyer_id})
            elif p in ('/api/lawyer/invite/status', '/api/v1/lawyer/invite/status'):
                self._handle_bridge_lawyer_user_get('invite_status', q)
            elif p.startswith('/api/v1/lawyer/') and p.split('/')[-1].isdigit():
                # v1兼容
                lawyer_id = p.split('/')[-1]
                self._handle_bridge_lawyer_user_get('lawyer_detail', {**q, 'lawyer_id': lawyer_id})
            # ========== COO管理模块 GET 路由 ==========
            elif p in ('/api/admin/lawyer/pending', '/api/v1/admin/lawyer/pending'):
                self._handle_bridge_lawyer_admin_get('admin_pending_list', q)
            elif p in ('/api/admin/lawyer/list', '/api/v1/admin/lawyer/list'):
                self._handle_bridge_lawyer_admin_get('admin_list', q)
            elif p in ('/api/admin/lawyer/complaints', '/api/v1/admin/lawyer/complaints'):
                self._handle_bridge_lawyer_admin_get('admin_complaints_list', q)
            else:
                # 检查是否匹配已注册的 GET 路由
                handler_name = self._routes_get.get(p)
                if handler_name and hasattr(self, handler_name):
                    getattr(self, handler_name)(p, q)
                else:
                    self._json({'success': False, 'error': 'Not Found'}, 404)
        except Exception as e:
            logger.error(f"GET {p} 异常: {e}")
            self._json({'success': False, 'error': f'服务器内部错误: {str(e)}'}, 500)

    def do_POST(self):
        """处理 POST 请求"""
        p, q = self._parse_path()
        # 先保存原始body（微信回调是XML，_read_body无法解析）
        try:
            length = int(self.headers.get('Content-Length', 0))
            self._raw_body_raw = self.rfile.read(length).decode('utf-8') if length > 0 else ''
        except Exception:
            self._raw_body_raw = ''
        body = self._read_body()
        logger.info(f"POST {p}")

        try:
            # 认证模块路由
            if p in ('/auth/send_sms', '/api/v1/auth/send_sms'):
                self._handle_bridge('send_sms', body)
            elif p in ('/auth/login', '/api/v1/auth/login'):
                self._handle_bridge('login', body)
            elif p in ('/auth/wx_login', '/api/v1/auth/wx_login'):
                self._handle_bridge('wx_login', body)
            elif p in ('/user/profile', '/api/v1/user/profile'):
                self._handle_bridge('get_user', body)
            # ========== P0 业务模块路由 ==========
            # AI对话
            elif p in ('/chat/send', '/api/v1/chat/send', '/p0/chat/send', '/chat/new_session', '/api/v1/chat/new_session'):
                self._handle_bridge_p0('chat_send_message', body)
            elif p in ('/chat/history', '/api/v1/chat/history', '/p0/chat/history'):
                self._handle_bridge_p0('chat_get_history', body)
            # Token计费
            elif p in ('/token/balance', '/api/v1/token/balance', '/p0/token/balance'):
                self._handle_bridge_p0('token_get_balance', body)
            elif p in ('/token/consume', '/api/v1/token/consume', '/p0/token/consume'):
                self._handle_bridge_p0('token_consume', body)
            elif p in ('/token/recharge', '/api/v1/token/recharge', '/p0/token/recharge'):
                self._handle_bridge_p0('token_recharge', body)
            elif p in ('/token/packages', '/api/v1/token/packages', '/p0/token/packages'):
                self._handle_bridge_p0('token_get_packages', body)
            # 会员系统
            elif p in ('/member/status', '/api/v1/member/status', '/p0/member/status'):
                self._handle_bridge_p0('member_get_status', body)
            elif p in ('/member/plans', '/api/v1/member/plans', '/p0/member/plans', '/member/packages', '/api/v1/member/packages'):
                self._handle_bridge_p0('member_get_plans', body)
            elif p in ('/member/order', '/api/v1/member/order', '/p0/member/order'):
                self._handle_bridge_p0('member_create_order', body)
            # ========== P0 用户认证 POST 路由 ==========
            elif p in ('/user/verify', '/api/v1/user/verify'):
                self._handle_bridge_p0('user_verify', body)
            elif p in ('/user/upload-avatar', '/api/v1/user/upload-avatar'):
                self._handle_bridge_p0('user_update_avatar', body)
            # ========== P0 档案管理 POST 路由 ==========
            elif p in ('/archive/create', '/api/v1/archive/create'):
                self._handle_bridge_p0('archive_create', body)
            # ========== P0 活动 POST 路由 ==========
            elif p in ('/activity/join', '/api/v1/activity/join'):
                self._handle_bridge_p0('activity_join', body)
            # ========== P0 通知 POST 路由 ==========
            elif p in ('/notification/read', '/api/v1/notification/read'):
                self._handle_bridge_p0('notification_read', body)
            elif p in ('/notification/read-all', '/api/v1/notification/read-all'):
                self._handle_bridge_p0('notification_read_all', body)
            elif p in ('/notification/clear', '/api/v1/notification/clear'):
                self._handle_bridge_p0('notification_clear', body)
            # ========== P0 推广 POST 路由 ==========
            elif p in ('/promotion/generate-link', '/api/v1/promotion/generate-link'):
                self._handle_bridge_p0('promotion_generate_link', body)
            # ========== P1 文书生成路由 ==========
            elif p in ('/document/generate', '/api/v1/document/generate', '/p1/document/generate'):
                self._handle_bridge_p1_doc('document_generate', body)
            # ========== P1 积分系统路由 ==========
            elif p in ('/integral/sign', '/api/v1/integral/sign', '/p1/integral/sign', '/integral/signin', '/api/v1/integral/signin', '/user/sign', '/api/v1/user/sign'):
                self._handle_bridge_p1_integral('sign', body)
            elif p in ('/integral/sign/makeup', '/api/v1/integral/sign/makeup', '/p1/integral/sign/makeup', '/user/sign/makeup', '/api/v1/user/sign/makeup'):
                self._handle_bridge_p1_integral('sign_makeup', body)
            elif p in ('/integral/task/complete', '/api/v1/integral/task/complete', '/p1/integral/task/complete'):
                self._handle_bridge_p1_integral('task_complete', body)
            elif p in ('/integral/exchange', '/api/v1/integral/exchange', '/p1/integral/exchange', '/mall/exchange', '/api/v1/mall/exchange'):
                self._handle_bridge_p1_integral('exchange', body)
            # ========== P1 合伙人系统路由 ==========
            elif p in ('/partner/upgrade', '/api/v1/partner/upgrade', '/p1/partner/upgrade'):
                self._handle_bridge_p1_partner('partner_upgrade', body)
            elif p in ('/referral/bind', '/api/v1/referral/bind', '/p1/referral/bind'):
                self._handle_bridge_p1_partner('referral_bind', body)
            elif p in ('/referral/code', '/api/v1/referral/code', '/p1/referral/code'):
                self._handle_bridge_p1_partner('referral_code', body)
            elif p in ('/commission/calculate', '/api/v1/commission/calculate', '/p1/commission/calculate'):
                self._handle_bridge_p1_partner('commission_calculate', body)
            elif p in ('/withdrawal/apply', '/api/v1/withdrawal/apply', '/p1/withdrawal/apply', '/commission/withdraw', '/api/v1/commission/withdraw'):
                self._handle_bridge_p1_partner('withdrawal_apply', body)
            elif p in ('/withdrawal/approve', '/api/v1/withdrawal/approve', '/p1/withdrawal/approve'):
                self._handle_bridge_p1_partner('withdrawal_approve', body)
            elif p in ('/withdrawal/complete', '/api/v1/withdrawal/complete', '/p1/withdrawal/complete'):
                self._handle_bridge_p1_partner('withdrawal_complete', body)
            # ========== P1 微信支付路由 ==========
            elif p in ('/payment/wechat/create', '/api/v1/payment/wechat/create', '/p1/payment/wechat/create', '/payment/wechat', '/api/v1/payment/wechat'):
                self._handle_bridge_p1_payment('create_payment', body)
            elif p in ('/payment/wechat/notify', '/api/v1/payment/wechat/notify', '/p1/payment/wechat/notify'):
                # 微信回调是XML格式，需要特殊处理
                raw_body = getattr(self, '_raw_body_raw', '') or ''
                import re
                out_trade_no = ''
                transaction_id = ''
                total_fee = ''
                result_code = ''
                if raw_body:
                    m = re.search(r'<out_trade_no><!\[CDATA\[(.*?)\]\]></out_trade_no>', raw_body)
                    if m: out_trade_no = m.group(1)
                    m = re.search(r'<transaction_id><!\[CDATA\[(.*?)\]\]></transaction_id>', raw_body)
                    if m: transaction_id = m.group(1)
                    m = re.search(r'<total_fee>(.*?)</total_fee>', raw_body)
                    if m: total_fee = m.group(1)
                    m = re.search(r'<result_code><!\[CDATA\[(.*?)\]\]></result_code>', raw_body)
                    if m: result_code = m.group(1)
                xml_body = {
                    'out_trade_no': out_trade_no,
                    'transaction_id': transaction_id,
                    'total_amount': total_fee,
                    'trade_state': result_code or 'SUCCESS'
                }
                self._handle_bridge_p1_payment('payment_notify', xml_body)
            elif p in ('/payment/wechat/refund', '/api/v1/payment/wechat/refund', '/p1/payment/wechat/refund'):
                self._handle_bridge_p1_payment('apply_refund', body)
            # ========== P0 微信OpenID路由 ==========
            elif p in ('/payment/get_openid', '/api/v1/payment/get_openid'):
                self._handle_bridge_p0('payment_get_openid', body)
            # ========== P2 用户记忆 POST 路由 ==========
            elif p in ('/user/memory', '/api/v1/user/memory'):
                self._handle_p2_memory('save_memory', body)
            # ========== P2 对话历史 POST 路由 ==========
            elif p.startswith('/chat/sessions/') and p.endswith('/rename'):
                session_id = p.split('/')[3]
                body['session_id'] = session_id
                self._handle_p2_history('rename_session', body)
            elif p.startswith('/chat/sessions/'):
                session_id = p.split('/')[3]
                self._handle_p2_history('delete_session', {'session_id': session_id, 'user_id': body.get('user_id')})
            # ========== P2 自进化 POST 路由 ==========
            elif p in ('/feedback/submit', '/api/v1/feedback/submit'):
                self._handle_p2_evolution('submit_feedback', body)
            elif p in ('/feedback/quick', '/api/v1/feedback/quick'):
                self._handle_p2_evolution('quick_feedback', body)
            elif p in ('/badcases/review', '/api/v1/badcases/review'):
                self._handle_p2_evolution('review_badcase', body)
            # ========== P2 推荐系统 POST 路由 ==========
            elif p in ('/recommend/user', '/api/v1/recommend/user'):
                self._handle_p2_recommend('recommend', body)
            elif p in ('/recommend/cases', '/api/v1/recommend/cases', '/case/evaluate', '/api/v1/case/evaluate'):
                self._handle_p2_recommend('similar_cases', body)
            # ========== P3 三模型交叉验证 POST 路由 ==========
            elif p in ('/ai/chat/validated', '/api/v1/ai/chat/validated', '/p3/ai/chat/validated'):
                self._handle_p3_validation('validated_chat', body)
            elif p in ('/ai/cache', '/api/v1/ai/cache'):
                self._handle_p3_validation('validated_cache', body)
            elif p in ('/model/stats', '/api/v1/model/stats'):
                self._handle_p3_validation('model_stats', body)
            # ========== 代理商系统 POST 路由 ==========
            elif p in ('/agent/approve', '/api/v1/agent/approve'):
                self._handle_bridge_agent('agent_approve', body)
            elif p in ('/agent/reject', '/api/v1/agent/reject'):
                self._handle_bridge_agent('agent_reject', body)
            # ========== 律师板块 POST/PUT 路由 ==========
            elif p in ('/lawyer/register', '/api/v1/lawyer/register', '/api/lawyer/register'):
                self._handle_bridge_lawyer('register', body)
            elif p in ('/lawyer/realname', '/api/v1/lawyer/realname', '/api/lawyer/realname'):
                self._handle_bridge_lawyer('realname', body)
            elif p in ('/lawyer/realname/status', '/api/v1/lawyer/realname/status', '/api/lawyer/realname/status'):
                self._handle_bridge_lawyer('realname_status', body)
            elif p in ('/lawyer/cert/upload', '/api/v1/lawyer/cert/upload', '/api/lawyer/cert/upload'):
                self._handle_bridge_lawyer('cert_upload', body)
            elif p in ('/lawyer/pay-fee', '/api/v1/lawyer/pay-fee', '/api/lawyer/pay-fee'):
                self._handle_bridge_lawyer('pay_fee', body)
            elif p in ('/lawyer/profile', '/api/v1/lawyer/profile', '/api/lawyer/profile'):
                # POST 注册/更新，PUT 也有
                self._handle_bridge_lawyer('update_profile', body)
            # 案件状态更新 PUT （同POST处理）
            elif self._match_lawyer_case_path_post(p, body, 'status', 'case_update_status'):
                pass
            # 材料上传 POST
            elif self._match_lawyer_case_path_post(p, body, 'documents', 'case_upload_document'):
                pass
            # ========== 委托付费 POST 路由（PRD接口文档一致） ==========
            elif p in ('/api/lawyer/invite', '/api/v1/lawyer/invite'):
                self._handle_bridge_entrust('create_entrust', body)
            elif p in ('/api/lawyer/invite/cancel', '/api/v1/lawyer/invite/cancel'):
                self._handle_bridge_entrust('cancel_entrust', body)
            elif p in ('/api/lawyer/invite/complete', '/api/v1/lawyer/invite/complete'):
                self._handle_bridge_entrust('complete_entrust', body)
            # ========== 律师AI工具 Phase2 POST 路由 ==========
            elif p in ('/api/lawyer/ai/analyze',):
                self._handle_bridge_lawyer_ai('analyze', body)
            elif p in ('/api/lawyer/ai/generate-doc',):
                self._handle_bridge_lawyer_ai('generate_doc', body)
            elif p in ('/api/lawyer/ai/review-doc',):
                self._handle_bridge_lawyer_ai('review_doc', body)
            elif p in ('/api/lawyer/ai/summary',):
                self._handle_bridge_lawyer_ai('summary', body)
            elif p in ('/api/lawyer/ai/evidence',):
                self._handle_bridge_lawyer_ai('evidence', body)
            elif p in ('/api/lawyer/ai/legal-search',):
                self._handle_bridge_lawyer_ai('legal_search', body)
            elif p in ('/api/lawyer/ai/class-case',):
                self._handle_bridge_lawyer_ai('class_case', body)
            elif p in ('/api/lawyer/ai/trial-outline',):
                self._handle_bridge_lawyer_ai('trial_outline', body)
            # ========== 律师钱包模块 POST 路由 ==========
            elif p in ('/api/lawyer/wallet/withdraw', '/api/v1/lawyer/wallet/withdraw'):
                self._handle_bridge_lawyer_wallet('withdraw', body)
            # ========== 律师日程模块 POST 路由 ==========
            elif p in ('/api/lawyer/schedules', '/api/v1/lawyer/schedules'):
                self._handle_bridge_lawyer_schedule('schedules_create', body)
            # ========== 律师评价模块 POST 路由 ==========
            elif p.startswith('/api/lawyer/reviews/') and p.endswith('/reply'):
                # 提取 review_id: /api/lawyer/reviews/{id}/reply
                parts = p.rstrip('/').split('/')
                review_id = parts[-2] if len(parts) >= 5 else None
                if review_id and review_id.isdigit():
                    body['review_id'] = int(review_id)
                self._handle_bridge_lawyer_review('reviews_reply', body)
            elif p in ('/api/lawyer/reviews/{id}/reply',):
                # 兼容 API 文档路径
                self._handle_bridge_lawyer_review('reviews_reply', body)
            # ========== 用户端找律师模块 POST 路由 ==========
            elif p in ('/api/lawyer/recommend', '/api/v1/lawyer/recommend'):
                self._handle_bridge_lawyer_user('lawyer_recommend', body)
            elif p in ('/api/lawyer/invite', '/api/v1/lawyer/invite'):
                self._handle_bridge_lawyer_user('invite_create', body)
            # ========== COO管理模块 POST+PUT 路由 ==========
            elif p in ('/api/admin/lawyer/audit', '/api/v1/admin/lawyer/audit'):
                self._handle_bridge_lawyer_admin('admin_audit', body)
            elif p.startswith('/api/admin/lawyer/') and p.endswith('/status'):
                parts = p.rstrip('/').split('/')
                lawyer_id = parts[-2] if len(parts) >= 6 else None
                if lawyer_id and lawyer_id.isdigit():
                    body['lawyer_id'] = int(lawyer_id)
                self._handle_bridge_lawyer_admin('admin_status', body)
            elif p.startswith('/api/v1/admin/lawyer/') and p.endswith('/status'):
                parts = p.rstrip('/').split('/')
                lawyer_id = parts[-2] if len(parts) >= 7 else None
                if lawyer_id and lawyer_id.isdigit():
                    body['lawyer_id'] = int(lawyer_id)
                self._handle_bridge_lawyer_admin('admin_status', body)
            else:
                # 检查是否匹配已注册的 POST 路由
                handler_name = self._routes_post.get(p)
                if handler_name and hasattr(self, handler_name):
                    getattr(self, handler_name)(body, p, q)
                else:
                    self._json({'success': False, 'error': 'Not Found'}, 404)
        except Exception as e:
            logger.error(f"POST {p} 异常: {e}")
            self._json({'success': False, 'error': f'服务器内部错误: {str(e)}'}, 500)

    # ==================== Bridge 通用处理 ====================

    def _handle_bridge(self, action, body):
        """调用 bridge 处理业务逻辑"""
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge(action, body_str)
        self._json(result)

    def _run_bridge_p0(self, *args, timeout=60):
        """运行P0 bridge脚本（AI对话/Token/会员），超时更长"""
        cmd = [BRIDGE_P0.split()[0]] + BRIDGE_P0.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-P0] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.returncode != 0:
                if r.stdout.strip():
                    return json.loads(r.stdout.strip())
                raise Exception(r.stderr[:500] or 'Bridge-P0 returned error')
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception('Bridge-P0 returned empty')
        except subprocess.TimeoutExpired:
            logger.error(f"[Bridge-P0] 超时 ({timeout}s)")
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            logger.error(f"[Bridge-P0] JSON解析失败: {e}, output: {r.stdout[:500] if 'r' in dir() else ''}")
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            logger.error(f"[Bridge-P0] 执行失败: {e}")
            return {'success': False, 'error': str(e)}

    def _handle_bridge_p0(self, action, body):
        """调用P0 bridge 处理业务逻辑"""
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_p0(action, body_str)
        self._json(result)

    # ==================== P1 Bridge 文书生成模块 ====================

    def _run_bridge_p1_doc(self, *args, timeout=60):
        """运行P1 文书生成 bridge"""
        cmd = [BRIDGE_P1_DOC.split()[0]] + BRIDGE_P1_DOC.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-P1-Doc] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.returncode != 0:
                if r.stdout.strip():
                    return json.loads(r.stdout.strip())
                raise Exception(r.stderr[:500] or 'Bridge-P1-Doc returned error')
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception('Bridge-P1-Doc returned empty')
        except subprocess.TimeoutExpired:
            logger.error(f"[Bridge-P1-Doc] 超时 ({timeout}s)")
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            logger.error(f"[Bridge-P1-Doc] JSON解析失败: {e}, output: {r.stdout[:500] if 'r' in dir() else ''}")
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            logger.error(f"[Bridge-P1-Doc] 执行失败: {e}")
            return {'success': False, 'error': str(e)}

    def _handle_bridge_p1_doc(self, action, body):
        """调用P1 文书生成 bridge 处理业务逻辑"""
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_p1_doc(action, body_str)
        self._json(result)

    def _handle_bridge_p1_doc_get(self, action, query_dict):
        """处理P1 文书生成 GET 请求（将 query params 转为普通 dict 传给 bridge）"""
        params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in query_dict.items()}
        body_str = json.dumps(params, ensure_ascii=False)
        result = self._run_bridge_p1_doc(action, body_str)
        self._json(result)

    # ==================== P1 Bridge 积分系统 ====================

    def _run_bridge_p1_integral(self, *args, timeout=30):
        """运行P1 积分系统 bridge"""
        cmd = [BRIDGE_P1_INTEGRAL.split()[0]] + BRIDGE_P1_INTEGRAL.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-P1-Integral] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_bridge_p1_integral(self, action, body):
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_p1_integral(action, body_str)
        self._json(result)

    # ==================== P1 Bridge 合伙人系统 ====================

    def _run_bridge_p1_partner(self, *args, timeout=30):
        """运行P1 合伙人系统 bridge"""
        cmd = [BRIDGE_P1_PARTNER.split()[0]] + BRIDGE_P1_PARTNER.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-P1-Partner] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_bridge_p1_partner(self, action, body):
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_p1_partner(action, body_str)
        self._json(result)

    # ==================== P1 Bridge 微信支付 ====================

    def _run_bridge_p1_payment(self, *args, timeout=30):
        """运行P1 微信支付 bridge"""
        cmd = [BRIDGE_P1_PAYMENT.split()[0]] + BRIDGE_P1_PAYMENT.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-P1-Payment] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_bridge_p1_payment(self, action, body):
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_p1_payment(action, body_str)
        self._json(result)

    # ==================== P2 Bridge 用户记忆 ====================

    def _run_bridge_p2_memory(self, *args, timeout=30):
        cmd = [BRIDGE_P2_MEMORY.split()[0]] + BRIDGE_P2_MEMORY.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-P2-Memory] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip(): return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired: return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError: return {'success': False, 'error': '内部处理错误'}
        except Exception as e: return {'success': False, 'error': str(e)}

    def _handle_p2_memory(self, action, body):
        self._json(self._run_bridge_p2_memory(action, json.dumps(body, ensure_ascii=False)))

    # ==================== P2 Bridge 对话历史 ====================

    def _run_bridge_p2_history(self, *args, timeout=30):
        cmd = [BRIDGE_P2_HISTORY.split()[0]] + BRIDGE_P2_HISTORY.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-P2-History] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip(): return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired: return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError: return {'success': False, 'error': '内部处理错误'}
        except Exception as e: return {'success': False, 'error': str(e)}

    def _handle_p2_history(self, action, body):
        self._json(self._run_bridge_p2_history(action, json.dumps(body, ensure_ascii=False)))

    # ==================== P2 Bridge 自进化 ====================

    def _run_bridge_p2_evolution(self, *args, timeout=30):
        cmd = [BRIDGE_P2_EVOLUTION.split()[0]] + BRIDGE_P2_EVOLUTION.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-P2-Evolution] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip(): return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired: return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError: return {'success': False, 'error': '内部处理错误'}
        except Exception as e: return {'success': False, 'error': str(e)}

    def _handle_p2_evolution(self, action, body):
        self._json(self._run_bridge_p2_evolution(action, json.dumps(body, ensure_ascii=False)))

    # ==================== P2 Bridge 数据看板 ====================

    def _run_bridge_p2_dashboard(self, *args, timeout=30):
        cmd = [BRIDGE_P2_DASHBOARD.split()[0]] + BRIDGE_P2_DASHBOARD.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-P2-Dashboard] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip(): return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired: return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError: return {'success': False, 'error': '内部处理错误'}
        except Exception as e: return {'success': False, 'error': str(e)}

    def _handle_p2_dashboard(self, action, body):
        self._json(self._run_bridge_p2_dashboard(action, json.dumps(body, ensure_ascii=False)))

    # ==================== P2 Bridge 推荐系统 ====================

    def _run_bridge_p2_recommend(self, *args, timeout=30):
        cmd = [BRIDGE_P2_RECOMMEND.split()[0]] + BRIDGE_P2_RECOMMEND.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-P2-Recommend] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip(): return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired: return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError: return {'success': False, 'error': '内部处理错误'}
        except Exception as e: return {'success': False, 'error': str(e)}

    def _handle_p2_recommend(self, action, body):
        self._json(self._run_bridge_p2_recommend(action, json.dumps(body, ensure_ascii=False)))

    # ==================== 委托付费 Bridge ====================

    def _run_bridge_entrust(self, *args, timeout=30):
        cmd = [BRIDGE_ENTRUST.split()[0]] + BRIDGE_ENTRUST.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-Entrust] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip(): return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired: return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError: return {'success': False, 'error': '内部处理错误'}
        except Exception as e: return {'success': False, 'error': str(e)}

    def _handle_bridge_entrust(self, action, body):
        self._json(self._run_bridge_entrust(action, json.dumps(body, ensure_ascii=False)))

    # ==================== P3 Bridge 三模型交叉验证 ====================

    def _run_bridge_p3_validation(self, *args, timeout=60):
        cmd = [BRIDGE_P3_VALIDATION.split()[0]] + BRIDGE_P3_VALIDATION.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-P3-Validation] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip(): return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired: return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError: return {'success': False, 'error': '内部处理错误'}
        except Exception as e: return {'success': False, 'error': str(e)}

    def _handle_p3_validation(self, action, body):
        self._json(self._run_bridge_p3_validation(action, json.dumps(body, ensure_ascii=False)))

    # ==================== 代理商系统 Bridge ====================

    def _run_bridge_agent(self, *args, timeout=30):
        """运行代理商 bridge"""
        cmd = [BRIDGE_AGENT.split()[0]] + BRIDGE_AGENT.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-Agent] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_bridge_agent(self, action, body):
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_agent(action, body_str)
        self._json(result)

    # ==================== 律师板块 Bridge ====================

    def _run_bridge_lawyer(self, *args, timeout=30):
        """运行律师板块 bridge"""
        cmd = [BRIDGE_LAWYER.split()[0]] + BRIDGE_LAWYER.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-Lawyer] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_bridge_lawyer(self, action, body):
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_lawyer(action, body_str)
        self._json(result)

    def _handle_bridge_lawyer_get(self, action, query_dict):
        """处理律师板块 GET 请求"""
        params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in query_dict.items()}
        body_str = json.dumps(params, ensure_ascii=False)
        result = self._run_bridge_lawyer(action, body_str)
        self._json(result)

    def _handle_bridge_lawyer_put(self, action, body):
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_lawyer(action, body_str)
        self._json(result)

    # ==================== 律师AI工具 Bridge (Phase2) ====================

    def _run_bridge_lawyer_ai(self, *args, timeout=60):
        """运行律师AI工具 bridge"""
        cmd = [BRIDGE_LAWYER_AI.split()[0]] + BRIDGE_LAWYER_AI.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-Lawyer-AI] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired:
            return {'code': 500, 'message': '请求超时', 'data': {}}
        except json.JSONDecodeError as e:
            return {'code': 500, 'message': '内部处理错误', 'data': {}}
        except Exception as e:
            return {'code': 500, 'message': str(e), 'data': {}}

    # ==================== 律师钱包模块 Bridge (Phase4) ====================

    def _run_bridge_lawyer_wallet(self, *args, timeout=30):
        """运行律师钱包模块 bridge"""
        cmd = [BRIDGE_LAWYER_WALLET.split()[0]] + BRIDGE_LAWYER_WALLET.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-Lawyer-Wallet] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_bridge_lawyer_wallet(self, action, body):
        """调用律师钱包 bridge 处理业务逻辑"""
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_lawyer_wallet(action, body_str)
        self._json(result)

    def _handle_bridge_lawyer_wallet_get(self, action, query_dict):
        """处理律师钱包模块 GET 请求"""
        params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in query_dict.items()}
        body_str = json.dumps(params, ensure_ascii=False)
        result = self._run_bridge_lawyer_wallet(action, body_str)
        self._json(result)

    # ==================== 律师日程模块 Bridge (Phase5) ====================

    def _run_bridge_lawyer_schedule(self, *args, timeout=30):
        """运行律师日程模块 bridge"""
        cmd = [BRIDGE_LAWYER_SCHEDULE.split()[0]] + BRIDGE_LAWYER_SCHEDULE.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-Lawyer-Schedule] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_bridge_lawyer_schedule(self, action, body):
        """调用律师日程 bridge 处理业务逻辑"""
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_lawyer_schedule(action, body_str)
        self._json(result)

    def _handle_bridge_lawyer_schedule_get(self, action, query_dict):
        """处理律师日程模块 GET 请求"""
        params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in query_dict.items()}
        body_str = json.dumps(params, ensure_ascii=False)
        result = self._run_bridge_lawyer_schedule(action, body_str)
        self._json(result)

    # ==================== 律师评价模块 Bridge (Phase6) ====================

    def _run_bridge_lawyer_review(self, *args, timeout=30):
        """运行律师评价模块 bridge"""
        cmd = [BRIDGE_LAWYER_REVIEW.split()[0]] + BRIDGE_LAWYER_REVIEW.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-Lawyer-Review] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_bridge_lawyer_review(self, action, body):
        """调用律师评价 bridge 处理业务逻辑"""
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_lawyer_review(action, body_str)
        self._json(result)

    def _handle_bridge_lawyer_review_get(self, action, query_dict):
        """处理律师评价模块 GET 请求"""
        params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in query_dict.items()}
        body_str = json.dumps(params, ensure_ascii=False)
        result = self._run_bridge_lawyer_review(action, body_str)
        self._json(result)

    # ==================== 用户端找律师模块 Bridge (Phase7) ====================

    def _run_bridge_lawyer_user(self, *args, timeout=30):
        """运行用户端找律师模块 bridge"""
        cmd = [BRIDGE_LAWYER_USER.split()[0]] + BRIDGE_LAWYER_USER.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-Lawyer-User] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_bridge_lawyer_user(self, action, body):
        """调用用户端找律师 bridge 处理业务逻辑"""
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_lawyer_user(action, body_str)
        self._json(result)

    def _handle_bridge_lawyer_user_get(self, action, query_dict):
        """处理用户端找律师模块 GET 请求"""
        params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in query_dict.items()}
        body_str = json.dumps(params, ensure_ascii=False)
        result = self._run_bridge_lawyer_user(action, body_str)
        self._json(result)

    # ==================== COO管理模块 Bridge (Phase8) ====================

    def _run_bridge_lawyer_admin(self, *args, timeout=30):
        """运行COO管理模块 bridge"""
        cmd = [BRIDGE_LAWYER_ADMIN.split()[0]] + BRIDGE_LAWYER_ADMIN.split()[1:] + list(args)
        env = os.environ.copy()
        logger.info(f"[Bridge-Lawyer-Admin] 执行: {' '.join(cmd)}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            if r.stdout.strip():
                return json.loads(r.stdout.strip())
            raise Exception(r.stderr[:500] or 'Bridge returned empty')
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': '请求超时'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': '内部处理错误'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _handle_bridge_lawyer_admin(self, action, body):
        """调用COO管理 bridge 处理业务逻辑"""
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_lawyer_admin(action, body_str)
        self._json(result)

    def _handle_bridge_lawyer_admin_get(self, action, query_dict):
        """处理COO管理模块 GET 请求"""
        params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in query_dict.items()}
        body_str = json.dumps(params, ensure_ascii=False)
        result = self._run_bridge_lawyer_admin(action, body_str)
        self._json(result)

    def _handle_bridge_lawyer_ai(self, action, body, extract_token=True):
        """调用律师AI工具 bridge 处理业务逻辑
        
        如果 extract_token=True，自动从请求头的 Authorization 中提取 Bearer Token 注入 body
        """
        if extract_token:
            token = self._get_token()
            if token:
                body['_token'] = token
        body_str = json.dumps(body, ensure_ascii=False)
        result = self._run_bridge_lawyer_ai(action, body_str)
        self._json(result)

    def _match_lawyer_case_path_get(self, path, query_dict):
        """解析律师案件动态路径（GET用），支持 /lawyer/cases/<id>/timeline, /status, /documents 等"""
        # 去掉前缀
        for prefix in ['/api/lawyer/cases/', '/api/v1/lawyer/cases/', '/lawyer/cases/']:
            if path.startswith(prefix):
                remainder = path[len(prefix):].rstrip('/')
                break
        else:
            return False

        parts = remainder.split('/')
        case_id = parts[0]
        subpath = parts[1] if len(parts) > 1 else ''

        q_flat = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in query_dict.items()}
        q_flat['case_id'] = case_id

        if subpath == 'timeline':
            self._handle_bridge_lawyer_get('case_timeline', q_flat)
        elif subpath == 'documents':
            self._handle_bridge_lawyer_get('case_documents', q_flat)
        elif subpath == 'status':
            self._handle_bridge_lawyer_get('case_detail', q_flat)
        else:
            # 单纯的案件详情
            self._handle_bridge_lawyer_get('case_detail', q_flat)
        return True

    def _match_lawyer_case_path_post(self, path, body, target_subpath, action):
        """解析律师案件动态路径（POST用）"""
        for prefix in ['/api/lawyer/cases/', '/api/v1/lawyer/cases/', '/lawyer/cases/']:
            if path.startswith(prefix):
                remainder = path[len(prefix):].rstrip('/')
                break
        else:
            return False

        parts = remainder.split('/')
        if len(parts) < 2:
            return False
        case_id = parts[0]
        subpath = parts[1]

        if subpath == target_subpath:
            body['case_id'] = case_id
            self._handle_bridge_lawyer(action, body)
            return True
        return False

    # ==================== 内置 GET 处理器 ====================

    def log_message(self, format, *args):
        """重写日志输出到自定义 logger"""
        logger.info(f"{self.address_string()} - {format % args}")

    def version_string(self):
        return 'HermesBusinessAPI/1.0'


# ==================== 启动服务器 ====================

def run_server():
    """启动 HTTP 服务器"""
    server = HTTPServer(('0.0.0.0', PORT), BusinessAPIHandler)
    logger.info(f"🚀 Hermes Business API 启动成功，端口: {PORT}")
    logger.info(f"📝 日志输出: {LOG_FILE}")
    logger.info(f"🗄️  数据库: {os.environ['DB_PATH']}")
    logger.info(f"📋 可用接口:")
    logger.info(f"   POST /auth/send_sms     - 发送验证码")
    logger.info(f"   POST /auth/login        - 手机号登录")
    logger.info(f"   POST /auth/wx_login     - 微信登录")
    logger.info(f"   POST /chat/send         - AI对话（P0）")
    logger.info(f"   POST /chat/history      - 获取对话历史（P0）")
    logger.info(f"   POST /token/balance     - 查询Token余额（P0）")
    logger.info(f"   POST /token/consume     - 消耗Token（P0）")
    logger.info(f"   POST /token/recharge    - 充值Token（P0）")
    logger.info(f"   POST /token/packages    - Token套餐列表（P0）")
    logger.info(f"   POST /member/status     - 会员状态（P0）")
    logger.info(f"   POST /member/plans      - 会员套餐列表（P0）")
    logger.info(f"   POST /member/order      - 创建会员订单（P0）")
    logger.info(f"   GET  /health            - 健康检查")
    logger.info(f"   P1 文书生成路由:")
    logger.info(f"   POST /document/generate  - 生成文书（P1）")
    logger.info(f"   GET  /document/templates - 文书模板列表（P1）")
    logger.info(f"   GET  /document/template/detail - 模板详情（P1）")
    logger.info(f"   GET  /document/history   - 用户文书历史（P1）")
    logger.info(f"   P1 积分系统路由:")
    logger.info(f"   POST /integral/sign       - 每日签到（P1）")
    logger.info(f"   POST /integral/sign/makeup - 补签（P1）")
    logger.info(f"   GET  /integral/sign/status - 签到状态（P1）")
    logger.info(f"   GET  /integral/balance    - 积分余额（P1）")
    logger.info(f"   GET  /integral/records    - 积分记录（P1）")
    logger.info(f"   GET  /integral/tasks      - 任务列表（P1）")
    logger.info(f"   POST /integral/task/complete - 完成任务（P1）")
    logger.info(f"   GET  /integral/shop       - 商城商品（P1）")
    logger.info(f"   POST /integral/exchange   - 兑换商品（P1）")
    logger.info(f"   GET  /integral/orders     - 兑换记录（P1）")
    logger.info(f"   P1 合伙人系统路由:")
    logger.info(f"   GET  /partner/level       - 合伙人等级（P1）")
    logger.info(f"   POST /partner/upgrade     - 升级等级（P1）")
    logger.info(f"   POST /referral/bind       - 绑定推荐（P1）")
    logger.info(f"   POST /referral/code       - 生成推荐码（P1）")
    logger.info(f"   GET  /referral/team       - 推荐团队（P1）")
    logger.info(f"   POST /commission/calculate - 计算佣金（P1）")
    logger.info(f"   GET  /commission/list     - 佣金记录（P1）")
    logger.info(f"   POST /withdrawal/apply    - 提现申请（P1）")
    logger.info(f"   GET  /withdrawal/list     - 提现记录（P1）")
    logger.info(f"   POST /withdrawal/approve  - 审批提现（P1）")
    logger.info(f"   POST /withdrawal/complete - 完成提现（P1）")
    logger.info(f"   GET  /partner/dashboard   - 数据看板（P1）")
    logger.info(f"   P1 微信支付路由:")
    logger.info(f"   POST /payment/wechat/create - 创建支付（P1）")
    logger.info(f"   POST /payment/wechat/notify - 支付回调（P1）")
    logger.info(f"   GET  /payment/wechat/status - 查询状态（P1）")
    logger.info(f"   POST /payment/wechat/refund - 申请退款（P1）")
    logger.info(f"   POST /payment/get_openid  - 获取微信OpenID（P0）")
    logger.info(f"   POST /ai/chat/validated   - 三模型交叉验证（P3）")
    logger.info(f"   GET  /model/stats         - 模型状态查询（P3）")
    logger.info(f"   P2 用户记忆路由:")
    logger.info(f"   POST /user/memory          - 保存记忆（P2）")
    logger.info(f"   GET  /user/memory          - 获取记忆（P2）")
    logger.info(f"   P2 对话历史路由:")
    logger.info(f"   GET  /chat/sessions        - 会话列表（P2）")
    logger.info(f"   DELETE /chat/sessions/:id  - 删除会话（P2）")
    logger.info(f"   PUT   /chat/sessions/:id/rename - 重命名（P2）")
    logger.info(f"   P2 自进化路由:")
    logger.info(f"   POST /feedback/submit      - 提交反馈（P2）")
    logger.info(f"   POST /feedback/quick       - 快速反馈（P2）")
    logger.info(f"   GET  /badcases/list        - 坏案例列表（P2）")
    logger.info(f"   POST /badcases/review      - 评审坏案例（P2）")
    logger.info(f"   P2 数据看板路由:")
    logger.info(f"   GET  /dashboard/overview   - 概览指标（P2）")
    logger.info(f"   GET  /dashboard/revenue-trend - 收入趋势（P2）")
    logger.info(f"   GET  /dashboard/membership-distribution - 会员分布（P2）")
    logger.info(f"   GET  /dashboard/order-stats - 订单统计（P2）")
    logger.info(f"   GET  /dashboard/user-growth - 用户增长（P2）")
    logger.info(f"   P2 推荐系统路由:")
    logger.info(f"   POST /recommend/user       - 用户推荐（P2）")
    logger.info(f"   POST /recommend/cases      - 相似案例（P2）")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("🛑 服务器关闭中...")
        server.server_close()
        logger.info("✅ 服务器已关闭")


if __name__ == '__main__':
    run_server()
