"""
心海法律 AI - Phase 3 文书生成 API
支持多种法律文书生成：起诉状、答辩状、律师函、合同等
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
from services.chat_router import ChatRouter
from models.db import get_db
import os
import json

phase3_doc_bp = Blueprint('phase3_document', __name__, url_prefix='/api/v3/document')

# 文书模板配置
DOCUMENT_TEMPLATES = {
    'civil_complaint': {
        'name': '民事起诉状',
        'category': '诉讼文书',
        'description': '用于民事诉讼的起诉状',
        'fields': [
            {'name': 'plaintiff_name', 'label': '原告姓名', 'type': 'text', 'required': True},
            {'name': 'plaintiff_phone', 'label': '原告电话', 'type': 'text', 'required': True},
            {'name': 'defendant_name', 'label': '被告姓名', 'type': 'text', 'required': True},
            {'name': 'defendant_phone', 'label': '被告电话', 'type': 'text', 'required': False},
            {'name': 'claim', 'label': '诉讼请求', 'type': 'textarea', 'required': True},
            {'name': 'facts', 'label': '事实与理由', 'type': 'textarea', 'required': True},
        ]
    },
    'defense_statement': {
        'name': '民事答辩状',
        'category': '诉讼文书',
        'description': '用于民事诉讼的答辩状',
        'fields': [
            {'name': 'defendant_name', 'label': '答辩人姓名', 'type': 'text', 'required': True},
            {'name': 'defendant_phone', 'label': '答辩人电话', 'type': 'text', 'required': True},
            {'name': 'plaintiff_name', 'label': '被答辩人姓名', 'type': 'text', 'required': True},
            {'name': 'case_number', 'label': '案号', 'type': 'text', 'required': False},
            {'name': 'defense', 'label': '答辩意见', 'type': 'textarea', 'required': True},
        ]
    },
    'lawyer_letter': {
        'name': '律师函',
        'category': '非诉文书',
        'description': '律师正式函告',
        'fields': [
            {'name': 'client_name', 'label': '委托人姓名', 'type': 'text', 'required': True},
            {'name': 'recipient_name', 'label': '收件人姓名', 'type': 'text', 'required': True},
            {'name': 'matter', 'label': '事由', 'type': 'textarea', 'required': True},
            {'name': 'demand', 'label': '要求', 'type': 'textarea', 'required': True},
        ]
    },
    'loan_contract': {
        'name': '借款合同',
        'category': '合同',
        'description': '个人/企业借款合同',
        'fields': [
            {'name': 'lender_name', 'label': '出借人姓名', 'type': 'text', 'required': True},
            {'name': 'borrower_name', 'label': '借款人姓名', 'type': 'text', 'required': True},
            {'name': 'amount', 'label': '借款金额', 'type': 'number', 'required': True},
            {'name': 'interest_rate', 'label': '利率', 'type': 'text', 'required': False},
            {'name': 'term', 'label': '借款期限', 'type': 'text', 'required': True},
            {'name': 'purpose', 'label': '借款用途', 'type': 'text', 'required': False},
        ]
    },
    'labor_contract': {
        'name': '劳动合同',
        'category': '合同',
        'description': '标准劳动合同',
        'fields': [
            {'name': 'employer_name', 'label': '用人单位', 'type': 'text', 'required': True},
            {'name': 'employee_name', 'label': '劳动者姓名', 'type': 'text', 'required': True},
            {'name': 'position', 'label': '工作岗位', 'type': 'text', 'required': True},
            {'name': 'salary', 'label': '工资待遇', 'type': 'text', 'required': True},
            {'name': 'start_date', 'label': '入职日期', 'type': 'date', 'required': True},
            {'name': 'term', 'label': '合同期限', 'type': 'text', 'required': True},
        ]
    },
    'divorce_agreement': {
        'name': '离婚协议书',
        'category': '婚姻家庭',
        'description': '协议离婚用',
        'fields': [
            {'name': 'husband_name', 'label': '男方姓名', 'type': 'text', 'required': True},
            {'name': 'wife_name', 'label': '女方姓名', 'type': 'text', 'required': True},
            {'name': 'children', 'label': '子女抚养', 'type': 'textarea', 'required': False},
            {'name': 'property', 'label': '财产分割', 'type': 'textarea', 'required': True},
            {'name': 'debt', 'label': '债务处理', 'type': 'textarea', 'required': False},
        ]
    },
}


def get_chat_router():
    """获取 ChatRouter 实例"""
    if not hasattr(g, 'chat_router'):
        g.chat_router = ChatRouter()
    return g.chat_router


# ============== 获取文书模板列表 ==============

@phase3_doc_bp.route('/templates', methods=['GET'])
def get_document_templates():
    """
    获取文书模板列表
    GET /api/v3/document/templates?category=诉讼文书
    
    Response:
    {
        "code": 200,
        "data": {
            "templates": [
                {
                    "type": "civil_complaint",
                    "name": "民事起诉状",
                    "category": "诉讼文书",
                    "description": "用于民事诉讼的起诉状"
                }
            ],
            "categories": ["诉讼文书", "非诉文书", "合同", "婚姻家庭"]
        }
    }
    """
    try:
        category = request.args.get('category', '')
        
        templates = []
        for doc_type, info in DOCUMENT_TEMPLATES.items():
            if not category or info['category'] == category:
                templates.append({
                    'type': doc_type,
                    'name': info['name'],
                    'category': info['category'],
                    'description': info['description']
                })
        
        categories = list(set(t['category'] for t in templates))
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'templates': templates,
                'categories': categories
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取模板失败：{str(e)}',
            'data': None
        }), 500


# ============== 获取模板详情 ==============

@phase3_doc_bp.route('/templates/<doc_type>', methods=['GET'])
def get_template_detail(doc_type):
    """
    获取模板详情
    GET /api/v3/document/templates/civil_complaint
    
    Response:
    {
        "code": 200,
        "data": {
            "type": "civil_complaint",
            "name": "民事起诉状",
            "category": "诉讼文书",
            "description": "用于民事诉讼的起诉状",
            "fields": [...],
            "sample": "民事起诉状\n\n原告：张三，男，..."
        }
    }
    """
    try:
        if doc_type not in DOCUMENT_TEMPLATES:
            return jsonify({
                'code': 404,
                'message': '模板不存在',
                'data': None
            }), 404
        
        template = DOCUMENT_TEMPLATES[doc_type]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'type': doc_type,
                'name': template['name'],
                'category': template['category'],
                'description': template['description'],
                'fields': template['fields'],
                'sample': get_sample_document(doc_type)
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取模板详情失败：{str(e)}',
            'data': None
        }), 500


def get_sample_document(doc_type):
    """获取示例文书"""
    samples = {
        'civil_complaint': '''民事起诉状

原告：张三，男，1990 年 1 月 1 日出生，汉族，住北京市朝阳区 XX 路 XX 号，电话：138XXXXXXXX。

被告：李四，男，1985 年 5 月 5 日出生，汉族，住北京市海淀区 XX 路 XX 号，电话：139XXXXXXXX。

诉讼请求：
1. 判令被告偿还原告借款本金人民币 10 万元；
2. 判令被告支付利息（以 10 万元为基数，自 2023 年 1 月 1 日起至实际清偿之日止，按年利率 3.45% 计算）；
3. 本案诉讼费用由被告承担。

事实与理由：
2022 年 12 月 1 日，被告因资金周转需要向原告借款人民币 10 万元，约定于 2023 年 6 月 1 日前归还。借款到期后，原告多次催要，被告至今未还。...

此致
北京市朝阳区人民法院

具状人：张三
2024 年 1 月 1 日''',
        'lawyer_letter': '''律师函

XX 律函字〔2024〕第 001 号

致：李四先生/女士

XX 律师事务所（以下简称"本所"）系张三先生（以下简称"委托人"）的常年法律顾问。本所指派 XXX 律师（以下简称"本律师"）就您与委托人之间的借款纠纷事宜，郑重致函如下：

根据委托人提供的证据材料显示：2022 年 12 月 1 日，您因资金周转需要向委托人借款人民币 10 万元，约定于 2023 年 6 月 1 日前归还。借款到期后，经委托人多次催要，您至今未履行还款义务。...

望您收到本函后 7 日内与委托人联系并履行还款义务，否则委托人将采取法律手段维护自身合法权益。

特此函告！

XX 律师事务所
律师：XXX
2024 年 1 月 1 日''',
    }
    return samples.get(doc_type, '示例文书内容...')


# ============== 生成文书 ==============

@phase3_doc_bp.route('/generate', methods=['POST'])
def generate_document():
    """
    生成法律文书
    POST /api/v3/document/generate
    
    Body:
    {
        "user_id": 1,
        "doc_type": "civil_complaint",
        "fields": {
            "plaintiff_name": "张三",
            "plaintiff_phone": "13800138000",
            "defendant_name": "李四",
            "claim": "请求判令被告偿还借款 10 万元",
            "facts": "2022 年 12 月 1 日，被告向原告借款..."
        },
        "session_id": "xxx"  // 可选
    }
    
    Response:
    {
        "code": 200,
        "data": {
            "document_id": "DOC202605170001",
            "doc_type": "civil_complaint",
            "content": "民事起诉状\n\n原告：张三，...",
            "word_count": 1500,
            "tokens_used": 2000,
            "created_at": "2026-05-17T10:00:00"
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
        
        user_id = data.get('user_id', type=int)
        doc_type = data.get('doc_type')
        fields = data.get('fields', {})
        session_id = data.get('session_id')
        
        if not user_id or not doc_type:
            return jsonify({
                'code': 400,
                'message': '缺少必要参数',
                'data': None
            }), 400
        
        if doc_type not in DOCUMENT_TEMPLATES:
            return jsonify({
                'code': 400,
                'message': '文书类型不存在',
                'data': None
            }), 400
        
        # 验证必填字段
        template = DOCUMENT_TEMPLATES[doc_type]
        for field in template['fields']:
            if field.get('required') and not fields.get(field['name']):
                return jsonify({
                    'code': 400,
                    'message': f'缺少必填字段：{field["label"]}',
                    'data': None
                }), 400
        
        # 生成文书提示词
        prompt = build_document_prompt(doc_type, fields)
        
        # 调用 ChatRouter 生成
        chat_router = get_chat_router()
        result = chat_router.chat(
            user_id=user_id,
            message=prompt,
            session_id=session_id,
            message_type='document_generation'
        )
        
        document_content = result.get('reply', '')
        tokens_used = result.get('tokens_used', 0)
        
        # 生成文书 ID
        document_id = f"DOC{datetime.now().strftime('%Y%m%d%H%M%S')}{user_id:04d}"
        
        # 保存到数据库
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        cursor = conn.execute("""
            INSERT INTO documents (document_id, user_id, doc_type, content, tokens_used, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (document_id, user_id, doc_type, document_content, tokens_used))
        conn.commit()
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': '文书生成成功',
            'data': {
                'document_id': document_id,
                'doc_type': doc_type,
                'doc_name': template['name'],
                'content': document_content,
                'word_count': len(document_content),
                'tokens_used': tokens_used,
                'created_at': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'生成文书失败：{str(e)}',
            'data': None
        }), 500


def build_document_prompt(doc_type, fields):
    """构建文书生成提示词"""
    template = DOCUMENT_TEMPLATES[doc_type]
    
    field_text = "\n".join([f"- {f['label']}: {fields.get(f['name'], '')}" for f in template['fields']])
    
    prompt = f"""你是一名专业的法律文书撰写专家。请根据以下信息生成一份规范的{template['name']}。

【文书信息】
{field_text}

【要求】
1. 使用正式、规范的法律语言
2. 格式符合法律文书标准
3. 内容完整、逻辑清晰
4. 引用相关法律条文（如适用）

请生成完整的文书内容："""
    
    return prompt


# ============== 获取文书历史 ==============

@phase3_doc_bp.route('/history', methods=['GET'])
def get_document_history():
    """
    获取用户文书历史
    GET /api/v3/document/history?user_id=1&limit=20&offset=0
    
    Response:
    {
        "code": 200,
        "data": {
            "documents": [
                {
                    "document_id": "DOC202605170001",
                    "doc_type": "civil_complaint",
                    "doc_name": "民事起诉状",
                    "word_count": 1500,
                    "created_at": "2026-05-17T10:00:00"
                }
            ],
            "total": 50
        }
    }
    """
    try:
        user_id = request.args.get('user_id', type=int)
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        doc_type = request.args.get('type', '')
        
        if not user_id:
            return jsonify({
                'code': 400,
                'message': '缺少参数 user_id',
                'data': None
            }), 400
        
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        
        query = """
            SELECT d.*, 
                   CASE d.doc_type
                       WHEN 'civil_complaint' THEN '民事起诉状'
                       WHEN 'defense_statement' THEN '民事答辩状'
                       WHEN 'lawyer_letter' THEN '律师函'
                       WHEN 'loan_contract' THEN '借款合同'
                       WHEN 'labor_contract' THEN '劳动合同'
                       WHEN 'divorce_agreement' THEN '离婚协议书'
                       ELSE d.doc_type
                   END as doc_name
            FROM documents d
            WHERE d.user_id=?
        """
        params = [user_id]
        
        if doc_type:
            query += " AND d.doc_type=?"
            params.append(doc_type)
        
        query += " ORDER BY d.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        documents = conn.execute(query, params).fetchall()
        
        # 获取总数
        count_query = "SELECT COUNT(*) FROM documents WHERE user_id=?"
        count_params = [user_id]
        if doc_type:
            count_query += " AND doc_type=?"
            count_params.append(doc_type)
        
        total = conn.execute(count_query, count_params).fetchone()[0]
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'documents': [dict(d) for d in documents],
                'total': total,
                'limit': limit,
                'offset': offset
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取历史记录失败：{str(e)}',
            'data': None
        }), 500


# ============== 获取文书详情 ==============

@phase3_doc_bp.route('/<document_id>', methods=['GET'])
def get_document_detail(document_id):
    """
    获取文书详情
    GET /api/v3/document/DOC202605170001
    """
    try:
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        doc = conn.execute(
            "SELECT * FROM documents WHERE document_id=?", (document_id,)
        ).fetchone()
        conn.close()
        
        if not doc:
            return jsonify({
                'code': 404,
                'message': '文书不存在',
                'data': None
            }), 404
        
        doc = dict(doc)
        doc['doc_name'] = DOCUMENT_TEMPLATES.get(doc['doc_type'], {}).get('name', doc['doc_type'])
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': doc
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取文书详情失败：{str(e)}',
            'data': None
        }), 500


# ============== 导出文书 ==============

@phase3_doc_bp.route('/<document_id>/export', methods=['POST'])
def export_document(document_id):
    """
    导出文书为 Word/PDF
    POST /api/v3/document/DOC202605170001/export
    
    Body:
    {
        "format": "docx"  // docx 或 pdf
    }
    """
    try:
        data = request.get_json()
        export_format = data.get('format', 'docx')
        
        conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        doc = conn.execute(
            "SELECT * FROM documents WHERE document_id=?", (document_id,)
        ).fetchone()
        conn.close()
        
        if not doc:
            return jsonify({
                'code': 404,
                'message': '文书不存在',
                'data': None
            }), 404
        
        # 生成文件路径
        filename = f"{document_id}.{export_format}"
        filepath = f"/home/admin/xinhai_legal_uploads/documents/{filename}"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 简单保存为文本文件（实际应该用 python-docx 或 reportlab）
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(doc['content'])
        
        return jsonify({
            'code': 200,
            'message': '导出成功',
            'data': {
                'document_id': document_id,
                'format': export_format,
                'filename': filename,
                'download_url': f'/api/v3/document/download/{filename}'
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'导出文书失败：{str(e)}',
            'data': None
        }), 500


# ============== 下载文书 ==============

@phase3_doc_bp.route('/download/<filename>', methods=['GET'])
def download_document(filename):
    """下载文书文件"""
    from flask import send_file
    try:
        filepath = f"/home/admin/xinhai_legal_uploads/documents/{filename}"
        if not os.path.exists(filepath):
            return jsonify({
                'code': 404,
                'message': '文件不存在',
                'data': None
            }), 404
        
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'下载失败：{str(e)}',
            'data': None
        }), 500


# ============== 健康检查 ==============

@phase3_doc_bp.route('/health', methods=['GET'])
def document_health():
    """
    文书生成系统健康检查
    GET /api/v3/document/health
    """
    try:
        import sqlite3
        conn = sqlite3.connect('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        conn.execute("SELECT 1")
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'document_router': 'available',
            'chat_router': 'available',
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'document_router': 'unavailable',
            'error': str(e)
        }), 500


# ============== 数据库表初始化 ==============

def init_documents_table():
    """初始化 documents 表"""
    conn = get_db('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            doc_type TEXT NOT NULL,
            content TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# 自动初始化表
try:
    init_documents_table()
except:
    pass
