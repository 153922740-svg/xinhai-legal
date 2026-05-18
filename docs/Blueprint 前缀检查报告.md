# Blueprint 前缀检查报告

✅ Phase 2 会员 - phase2_member_api.py
   期望前缀：/api/v2, 实际前缀：/api/v2
   原始定义：12:phase2_bp = Blueprint('phase2_member', __name__, url_prefix='/api/v2')

❌ Phase 2 Token - phase2_token_billing.py
   期望前缀：/api/v2, 实际前缀：/api/v2/token
   原始定义：13:phase2_token_bp = Blueprint('phase2_token', __name__, url_prefix='/api/v2/token')

❌ Phase 2 支付 - phase2_payment_wechat.py
   期望前缀：/api/v2, 实际前缀：/api/v2/payment
   原始定义：16:phase2_payment_bp = Blueprint('phase2_payment', __name__, url_prefix='/api/v2/payment')

❌ Phase 3 AI 对话 - phase3_ai_chat_api.py
   期望前缀：/api/v3, 实际前缀：未找到
   原始定义：

✅ Phase 3 文书 - phase3_document_generator.py
   期望前缀：/api/v3/document, 实际前缀：/api/v3/document
   原始定义：13:phase3_doc_bp = Blueprint('phase3_document', __name__, url_prefix='/api/v3/document')

✅ Phase 3 审阅 - phase3_contract_review.py
   期望前缀：/api/v3/contract, 实际前缀：/api/v3/contract
   原始定义：13:phase3_contract_bp = Blueprint('phase3_contract', __name__, url_prefix='/api/v3/contract')

✅ Phase 4 认证 - phase4_user_auth_api.py
   期望前缀：/api/v4, 实际前缀：/api/v4
   原始定义：10:phase4_bp = Blueprint('phase4_user', __name__, url_prefix='/api/v4')

✅ Phase 5 输入 - phase5_input_enhance_v2.py
   期望前缀：/api/v5, 实际前缀：/api/v5
   原始定义：20:phase5_bp = Blueprint('phase5_input', __name__, url_prefix='/api/v5')

❌ Phase 6 进化 - phase6_self_evolution_api.py
   期望前缀：/api/v6, 实际前缀：未找到
   原始定义：

❌ Phase 7 合伙人 - phase7_partner_system_api.py
   期望前缀：/api/v7, 实际前缀：未找到
   原始定义：

❌ Phase 8 认证 - phase8_user_auth_api.py
   期望前缀：/api/v1, 实际前缀：未找到
   原始定义：

❌ Phase 9 积分 - phase9_integral_system_api.py
   期望前缀：/api/v9, 实际前缀：未找到
   原始定义：

❌ Phase 10 验证 - phase10_cross_validation_api.py
   期望前缀：/api/v10, 实际前缀：未找到
   原始定义：

❌ Phase 11 文书 - phase11_document_enhance_api.py
   期望前缀：/api/v11, 实际前缀：未找到
   原始定义：

❌ Phase 13 历史 - phase13_history_api.py
   期望前缀：/api/v13, 实际前缀：未找到
   原始定义：

