"""
心海法律 AI - 统一 API 路由入口
整合所有 Phase 的 API 模块
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys

# 添加 API 目录到路径
sys.path.insert(0, '/home/admin/xinhai_legal_api')

app = Flask(__name__)
CORS(app)

# 配置
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 最大上传

# ============== 注册蓝图 ==============

# Phase 2: 会员与计费
try:
    from phase2_member_api import phase2_bp
    app.register_blueprint(phase2_bp)
    print("✅ Phase 2 会员系统 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 2 会员系统 API 未加载：{e}")

try:
    from phase2_token_billing import phase2_token_bp
    app.register_blueprint(phase2_token_bp)
    print("✅ Phase 2 Token 计费 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 2 Token 计费 API 未加载：{e}")

try:
    from phase2_dashboard_api import phase2_dashboard_bp
    app.register_blueprint(phase2_dashboard_bp)
    print("✅ Phase 2 数据看板 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 2 数据看板 API 未加载：{e}")

try:
    from phase2_payment_wechat import phase2_payment_bp
    app.register_blueprint(phase2_payment_bp)
    print("✅ Phase 2 微信支付 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 2 微信支付 API 未加载：{e}")

# Phase 3: AI 核心功能
try:
    from phase3_ai_chat_api import phase3_bp
    app.register_blueprint(phase3_bp)
    print("✅ Phase 3 AI 对话 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 3 AI 对话 API 未加载：{e}")

try:
    from phase3_document_generator import phase3_doc_bp
    app.register_blueprint(phase3_doc_bp)
    print("✅ Phase 3 文书生成 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 3 文书生成 API 未加载：{e}")

try:
    from phase3_contract_review import phase3_contract_bp
    app.register_blueprint(phase3_contract_bp)
    print("✅ Phase 3 合同审阅 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 3 合同审阅 API 未加载：{e}")

# Phase 3: AI 核心功能
try:
    from phase3_ai_chat_api import phase3_bp
    app.register_blueprint(phase3_bp)
    print("✅ Phase 3 AI 对话 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 3 AI 对话 API 未加载：{e}")

# Phase 4: 用户认证
try:
    from phase4_user_auth_api import phase4_bp
    app.register_blueprint(phase4_bp)
    print("✅ Phase 4 用户认证 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 4 用户认证 API 未加载：{e}")

# Phase 5: 输入增强
try:
    from phase5_input_enhance_v2 import phase5_bp
    app.register_blueprint(phase5_bp)
    print("✅ Phase 5 输入增强 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 5 输入增强 API 未加载：{e}")

# Phase 6: 自进化能力
try:
    from phase6_self_evolution_api import phase6_bp
    app.register_blueprint(phase6_bp)
    print("✅ Phase 6 自进化能力 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 6 自进化能力 API 未加载：{e}")

# Phase 7: 代理合伙人
try:
    from phase7_partner_system_api import phase7_bp
    app.register_blueprint(phase7_bp)
    print("✅ Phase 7 代理合伙人 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 7 代理合伙人 API 未加载：{e}")

# Phase 8: 用户认证
try:
    from phase8_user_auth_api import phase8_bp
    app.register_blueprint(phase8_bp)  # Blueprint 路由已包含 /api/v1/ 前缀
    print("✅ Phase 8 用户认证 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 8 用户认证 API 未加载：{e}")

# Phase 9: 积分系统
try:
    from phase9_integral_system_api import phase9_bp
    app.register_blueprint(phase9_bp)
    print("✅ Phase 9 积分系统 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 9 积分系统 API 未加载：{e}")

# Phase 10: 三模型交叉验证
try:
    from phase10_cross_validation_api import phase10_bp
    app.register_blueprint(phase10_bp)
    print("✅ Phase 10 三模型验证 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 10 三模型验证 API 未加载：{e}")

# Phase 11: 文书增强
try:
    from phase11_document_enhance_api import phase11_bp
    app.register_blueprint(phase11_bp)
    print("✅ Phase 11 文书增强 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 11 文书增强 API 未加载：{e}")

# Phase 13: 历史对话
try:
    from phase13_history_api import phase13_bp
    app.register_blueprint(phase13_bp)
    print("✅ Phase 13 历史对话 API 已注册")
except Exception as e:
    print(f"⚠️ Phase 13 历史对话 API 未加载：{e}")

# ============== 律师板块 ==============
try:
    from lawyer_blueprint import lawyer_bp, init_lawyer_module
    app.register_blueprint(lawyer_bp)
    init_lawyer_module()
    print("✅ 律师板块 API 已注册（35+接口）")
except Exception as e:
    print(f"⚠️ 律师板块 API 未加载：{e}")

# ============== 健康检查 ==============

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': '心海法律 AI API 服务运行中',
        'version': '1.1.0'
    })

@app.route('/api/v1', methods=['GET'])
def api_index():
    return jsonify({
        'name': '心海法律 AI API',
        'version': '1.1.0',
        'modules': [
            'Phase 2: 会员系统，Token 计费，数据看板，微信支付',
            'Phase 3: AI 对话，文书生成，合同审阅',
            'Phase 4: 用户系统',
            'Phase 5: 语音识别，文件上传，图片上传',
            'Phase 6: 反馈收集，自进化能力',
            'Phase 7: 代理合伙人体系'
        ]
    })

# ============== 错误处理 ==============

@app.errorhandler(404)
def not_found(error):
    return jsonify({'code': 404, 'message': '接口不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'code': 500, 'message': '服务器内部错误'}), 500

# ============== 启动 ==============

if __name__ == '__main__':
    print("\n" + "="*50)
    print("心海法律 AI API 服务启动")
    print("="*50 + "\n")
    
    # 创建上传目录
    upload_dirs = [
        '/home/admin/xinhai_legal_uploads',
        '/home/admin/xinhai_legal_uploads/voice',
        '/home/admin/xinhai_legal_uploads/files',
        '/home/admin/xinhai_legal_uploads/images'
    ]
    for d in upload_dirs:
        os.makedirs(d, exist_ok=True)
    print("✅ 上传目录已创建")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
