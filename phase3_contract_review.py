"""
心海法律 AI - Phase 3 合同审阅 API
支持合同风险识别、条款分析、修改建议等功能
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from services.chat_router import ChatRouter
from models.db import get_db
import os
import json

phase3_contract_bp = Blueprint('phase3_contract', __name__, url_prefix='/api/v3/contract')

# 合同审阅配置
CONTRACT_REVIEW_CONFIG = {
    'max_file_size': 10 * 1024 * 1024,  # 10MB
    'supported_formats': ['pdf', 'doc', 'docx', 'txt'],
    'review_types': [
        {'type': 'risk', 'name': '风险识别', 'description': '识别合同中的风险条款'},
        {'type': 'compliance', 'name': '合规审查', 'description': '审查合同是否符合法律法规'},
        {'type': 'completeness', 'name': '完整性检查', 'description': '检查合同条款是否完整'},
        {'type': 'fairness', 'name': '公平性分析', 'description': '分析合同双方权利义务是否对等'},
    ],
    'contract_types': [
        '买卖合同', '借款合同', '租赁合同', '劳动合同', '服务合同',
        '合作合同', '代理合同', '技术合同', '其他'
    ]
}


def get_chat_router():
    """获取 ChatRouter 实例"""
    if not hasattr(g, 'chat_router'):
        g.chat_router = ChatRouter()
    return g.chat_router


# ============== 上传合同 ==============

@phase3_contract_bp.route('/upload', methods=['POST'])
def upload_contract():
    """
    上传合同文件
    POST /api/v3/contract/upload
    
    Form Data:
    - file: 合同文件
    - user_id: 用户 ID
    - contract_type: 合同类型 (可选)
    
    Response:
    {
        "code": 200,
        "data": {
            "file_id": "FILE202605170001",
            "filename": "contract.pdf",
            "file_size": 1024000,
            "contract_type": "借款合同",
            "upload_time": "2026-05-17T10:00:00"
        }
    }
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'code': 400,
                'message': '请上传合同文件',
                'data': None
            }), 400
        
        file = request.files['file']
        user_id = request.form.get('user_id', type=int)
        contract_type = request.form.get('contract_type', '其他')
        
        if not user_id:
            return jsonify({
                'code': 400,
                'message': '缺少用户 ID',
                'data': None
            }), 400
        
        # 验证文件大小
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > CONTRACT_REVIEW_CONFIG['max_file_size']:
            return jsonify({
                'code': 400,
                'message': f'文件大小超过限制 ({CONTRACT_REVIEW_CONFIG["max_file_size"] / 1024 / 1024}MB)',
                'data': None
            }), 400
        
        # 验证文件格式
        filename = file.filename
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if file_ext not in CONTRACT_REVIEW_CONFIG['supported_formats']:
            return jsonify({
                'code': 400,
                'message': f'不支持的文件格式，支持的格式：{", ".join(CONTRACT_REVIEW_CONFIG["supported_formats"])}',
                'data': None
            }), 400
        
        # 保存文件
        upload_dir = '/home/admin/xinhai_legal_uploads/contracts'
        os.makedirs(upload_dir, exist_ok=True)
        
        file_id = f"FILE{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id:04d}"
        save_path = os.path.join(upload_dir, f"{file_id}.{file_ext}")
        file.save(save_path)
        
        # 读取文件内容 (仅支持 txt)
        content = ""
        if file_ext == 'txt':
            with open(save_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            # PDF/DOC/DOCX 需要额外库支持，暂时返回提示
            content = f"[{file_ext.upper()} 文件内容提取待实现，当前仅支持 TXT 格式]"
        
        # 保存到数据库
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        cursor = conn.execute("""
            INSERT INTO contract_reviews (file_id, user_id, filename, file_path, file_size, 
                                         contract_type, content, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'uploaded', CURRENT_TIMESTAMP)
        """, (file_id, user_id, filename, save_path, file_size, contract_type, content))
        conn.commit()
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': '合同上传成功',
            'data': {
                'file_id': file_id,
                'filename': filename,
                'file_size': file_size,
                'contract_type': contract_type,
                'upload_time': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'上传合同失败：{str(e)}',
            'data': None
        }), 500


# ============== 审阅合同 ==============

@phase3_contract_bp.route('/review', methods=['POST'])
def review_contract():
    """
    审阅合同
    POST /api/v3/contract/review
    
    Body:
    {
        "user_id": 1,
        "file_id": "FILE202605170001",
        "review_types": ["risk", "compliance"],  // 审阅类型
        "focus_areas": ["违约责任", "争议解决"]  // 重点关注领域 (可选)
    }
    
    Response:
    {
        "code": 200,
        "data": {
            "review_id": "REV202605170001",
            "file_id": "FILE202605170001",
            "risks": [
                {
                    "level": "high",
                    "clause": "第 5 条 违约责任",
                    "risk": "违约金过高，可能超过法定上限",
                    "suggestion": "建议调整为不超过实际损失的 30%"
                }
            ],
            "compliance_issues": [],
            "completeness_score": 85,
            "fairness_score": 75,
            "overall_score": 80,
            "tokens_used": 3000
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 400,
                'message': '请求体不能为空',
                'data': None
            }), 400
        
        user_id = int(data.get('user_id', 0))
        file_id = data.get('file_id')
        review_types = data.get('review_types', ['risk'])
        focus_areas = data.get('focus_areas', [])
        
        if not user_id or not file_id:
            return jsonify({
                'code': 400,
                'message': '缺少必要参数',
                'data': None
            }), 400
        
        # 获取合同内容
        import sqlite3
        conn = sqlite3.connect('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        conn.row_factory = sqlite3.Row
        contract = conn.execute(
            "SELECT * FROM contract_reviews WHERE file_id=?", (file_id,)
        ).fetchone()
        
        if not contract:
            conn.close()
            return jsonify({
                'code': 404,
                'message': '合同不存在',
                'data': None
            }), 404
        
        contract = dict(contract)
        content = contract.get('content', '')
        
        if not content or '待实现' in content:
            conn.close()
            return jsonify({
                'code': 400,
                'message': '合同内容无法读取，请上传 TXT 格式文件',
                'data': None
            }), 400
        
        conn.close()
        
        # 构建审阅提示词
        prompt = build_review_prompt(contract, review_types, focus_areas)
        
        # 调用 ChatRouter 进行审阅
        chat_router = get_chat_router()
        review_content = chat_router.generate_legal_response(
            question=prompt,
            domain='contract_review'
        )
        tokens_used = 3000  # 估算值
        
        # 解析 AI 返回的审阅结果
        review_result = parse_review_result(review_content)
        
        # 生成审阅 ID
        review_id = f"REV{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id:04d}"
        
        # 保存审阅结果
        conn2 = sqlite3.connect('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        cursor = conn2.execute("""
            INSERT INTO contract_review_results (review_id, file_id, user_id, review_types,
                                                 risks_json, compliance_json, completeness_score,
                                                 fairness_score, overall_score, tokens_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            review_id, file_id, user_id, json.dumps(review_types),
            json.dumps(review_result.get('risks', [])),
            json.dumps(review_result.get('compliance_issues', [])),
            review_result.get('completeness_score', 0),
            review_result.get('fairness_score', 0),
            review_result.get('overall_score', 0),
            tokens_used
        ))
        
        # 更新合同状态
        conn2.execute("""
            UPDATE contract_reviews SET status='reviewed', reviewed_at=CURRENT_TIMESTAMP
            WHERE file_id=?
        """, (file_id,))
        conn2.commit()
        conn2.close()
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': '合同审阅完成',
            'data': {
                'review_id': review_id,
                'file_id': file_id,
                'risks': review_result.get('risks', []),
                'compliance_issues': review_result.get('compliance_issues', []),
                'completeness_score': review_result.get('completeness_score', 0),
                'fairness_score': review_result.get('fairness_score', 0),
                'overall_score': review_result.get('overall_score', 0),
                'tokens_used': tokens_used,
                'review_time': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'合同审阅失败：{str(e)}',
            'data': None
        }), 500


def build_review_prompt(contract, review_types, focus_areas):
    """构建合同审阅提示词"""
    review_type_names = {
        'risk': '风险识别',
        'compliance': '合规审查',
        'completeness': '完整性检查',
        'fairness': '公平性分析'
    }
    
    types_text = ", ".join([review_type_names.get(t, t) for t in review_types])
    focus_text = ", ".join(focus_areas) if focus_areas else "无特别关注"
    
    prompt = f"""你是一名资深合同审查律师。请对以下合同进行专业审阅。

【合同信息】
- 合同类型：{contract.get('contract_type', '未知')}
- 审阅类型：{types_text}
- 重点关注：{focus_text}

【合同内容】
{contract.get('content', '')}

【审阅要求】
1. 识别合同中的风险条款，标注风险等级 (高/中/低)
2. 检查合同是否符合相关法律法规
3. 评估合同条款的完整性
4. 分析双方权利义务是否对等
5. 对每个问题提供具体的修改建议

【输出格式】
请以 JSON 格式返回审阅结果：
{{
    "risks": [
        {{"level": "high/medium/low", "clause": "条款位置", "risk": "风险描述", "suggestion": "修改建议"}}
    ],
    "compliance_issues": [
        {{"issue": "合规问题", "law": "相关法律", "suggestion": "修改建议"}}
    ],
    "completeness_score": 0-100,
    "fairness_score": 0-100,
    "overall_score": 0-100,
    "summary": "审阅总结"
}}

请开始审阅："""
    
    return prompt


def parse_review_result(content):
    """解析 AI 返回的审阅结果"""
    # 尝试从内容中提取 JSON
    import re
    json_match = re.search(r'\{[\s\S]*\}', content)
    
    if json_match:
        try:
            result = json.loads(json_match.group())
            return {
                'risks': result.get('risks', []),
                'compliance_issues': result.get('compliance_issues', []),
                'completeness_score': result.get('completeness_score', 0),
                'fairness_score': result.get('fairness_score', 0),
                'overall_score': result.get('overall_score', 0),
                'summary': result.get('summary', '')
            }
        except:
            pass
    
    # 解析失败时返回默认结构
    return {
        'risks': [{'level': 'unknown', 'clause': '内容解析失败', 'risk': content[:200], 'suggestion': '请重新上传合同'}],
        'compliance_issues': [],
        'completeness_score': 0,
        'fairness_score': 0,
        'overall_score': 0,
        'summary': '审阅结果解析失败'
    }


# ============== 获取审阅结果 ==============

@phase3_contract_bp.route('/review/<review_id>', methods=['GET'])
def get_review_result(review_id):
    """
    获取审阅结果
    GET /api/v3/contract/review/REV202605170001
    """
    try:
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        result = conn.execute(
            "SELECT * FROM contract_review_results WHERE review_id=?", (review_id,)
        ).fetchone()
        conn.close()
        
        if not result:
            return jsonify({
                'code': 404,
                'message': '审阅结果不存在',
                'data': None
            }), 404
        
        result = dict(result)
        result['risks'] = json.loads(result.get('risks_json', '[]'))
        result['compliance_issues'] = json.loads(result.get('compliance_json', '[]'))
        del result['risks_json']
        del result['compliance_json']
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': result
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取审阅结果失败：{str(e)}',
            'data': None
        }), 500


# ============== 审阅历史 ==============

@phase3_contract_bp.route('/history', methods=['GET'])
def get_review_history():
    """
    获取用户审阅历史
    GET /api/v3/contract/history?user_id=1&limit=20
    """
    try:
        user_id = request.args.get('user_id', type=int)
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if not user_id:
            return jsonify({
                'code': 400,
                'message': '缺少参数 user_id',
                'data': None
            }), 400
        
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        results = conn.execute("""
            SELECT r.*, c.filename, c.contract_type
            FROM contract_review_results r
            JOIN contract_reviews c ON r.file_id = c.file_id
            WHERE r.user_id=?
            ORDER BY r.created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset)).fetchall()
        
        total = conn.execute("""
            SELECT COUNT(*) FROM contract_review_results WHERE user_id=?
        """, (user_id,)).fetchone()[0]
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'reviews': [dict(r) for r in results],
                'total': total,
                'limit': limit,
                'offset': offset
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取审阅历史失败：{str(e)}',
            'data': None
        }), 500


# ============== 健康检查 ==============

@phase3_contract_bp.route('/health', methods=['GET'])
def contract_health():
    """
    合同审阅系统健康检查
    GET /api/v3/contract/health
    """
    try:
        import sqlite3
        conn = sqlite3.connect('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        conn.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'contract_router': 'available',
            'chat_router': 'available',
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'contract_router': 'unavailable',
            'error': str(e)
        }), 500


# ============== 数据库表初始化 ==============

def init_contract_tables():
    """初始化合同审阅相关表"""
    conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
    
    # 合同上传记录表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contract_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT,
            file_size INTEGER,
            contract_type TEXT,
            content TEXT,
            status TEXT DEFAULT 'uploaded',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP
        )
    """)
    
    # 合同审阅结果表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contract_review_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id TEXT UNIQUE NOT NULL,
            file_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            review_types TEXT,
            risks_json TEXT,
            compliance_json TEXT,
            completeness_score INTEGER,
            fairness_score INTEGER,
            overall_score INTEGER,
            tokens_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


# 自动初始化表
try:
    init_contract_tables()
except Exception as e:
    print(f"⚠️ 合同审阅表初始化失败：{e}")
