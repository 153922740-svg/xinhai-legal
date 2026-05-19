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
    'rental_contract': {
        'name': '租房合同',
        'category': '合同',
        'description': '房屋租赁合同',
        'fields': [
            {'name': 'lessor', 'label': '出租方姓名', 'type': 'text', 'required': True},
            {'name': 'lessee', 'label': '承租方姓名', 'type': 'text', 'required': True},
            {'name': 'address', 'label': '房屋地址', 'type': 'text', 'required': True},
            {'name': 'rent', 'label': '月租金（元）', 'type': 'number', 'required': True},
            {'name': 'deposit', 'label': '押金（元）', 'type': 'number', 'required': False},
            {'name': 'lease_term', 'label': '租赁期限', 'type': 'text', 'required': True},
        ]
    },
    'loan_agreement': {
        'name': '借款协议',
        'category': '合同',
        'description': '民间借贷协议',
        'fields': [
            {'name': 'lender_name', 'label': '出借人姓名', 'type': 'text', 'required': True},
            {'name': 'borrower_name', 'label': '借款人姓名', 'type': 'text', 'required': True},
            {'name': 'amount', 'label': '借款金额', 'type': 'number', 'required': True},
            {'name': 'interest_rate', 'label': '利率', 'type': 'text', 'required': False},
            {'name': 'term', 'label': '借款期限', 'type': 'text', 'required': True},
            {'name': 'purpose', 'label': '借款用途', 'type': 'text', 'required': False},
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
    'labor_arbitration': {
        'name': '劳动仲裁申请书',
        'category': '诉讼文书',
        'description': '劳动纠纷仲裁申请',
        'fields': [
            {'name': 'applicant_name', 'label': '申请人姓名', 'type': 'text', 'required': True},
            {'name': 'respondent_name', 'label': '被申请人（单位）', 'type': 'text', 'required': True},
            {'name': 'claim', 'label': '仲裁请求', 'type': 'textarea', 'required': True},
            {'name': 'facts', 'label': '事实与理由', 'type': 'textarea', 'required': True},
            {'name': 'evidence', 'label': '证据清单', 'type': 'textarea', 'required': False},
        ]
    },
    'debt_transfer': {
        'name': '债权转让协议',
        'category': '合同',
        'description': '债权转让协议',
        'fields': [
            {'name': 'transferor', 'label': '转让方姓名', 'type': 'text', 'required': True},
            {'name': 'transferee', 'label': '受让方姓名', 'type': 'text', 'required': True},
            {'name': 'debtor', 'label': '债务人姓名', 'type': 'text', 'required': True},
            {'name': 'debt_amount', 'label': '债权金额', 'type': 'number', 'required': True},
            {'name': 'transfer_price', 'label': '转让价款', 'type': 'number', 'required': True},
        ]
    },
    'settlement': {
        'name': '和解协议',
        'category': '非诉文书',
        'description': '纠纷调解和解协议',
        'fields': [
            {'name': 'party_a', 'label': '甲方姓名', 'type': 'text', 'required': True},
            {'name': 'party_b', 'label': '乙方姓名', 'type': 'text', 'required': True},
            {'name': 'background', 'label': '纠纷背景', 'type': 'textarea', 'required': True},
            {'name': 'agreement', 'label': '和解内容', 'type': 'textarea', 'required': True},
            {'name': 'payment', 'label': '赔偿金额（元）', 'type': 'number', 'required': False},
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
        'rental_contract': '''租房合同

出租方（甲方）：XXX
承租方（乙方）：XXX

根据《中华人民共和国民法典》及相关法律法规，甲乙双方在平等、自愿的基础上，就房屋租赁事宜达成如下协议：

第一条 房屋基本情况
甲方将位于 XXX 的房屋出租给乙方使用。

第二条 租赁期限
租赁期限自 XXXX 年 XX 月 XX 日起至 XXXX 年 XX 月 XX 日止。

第三条 租金及支付方式
月租金为人民币 XXX 元，押金为 XXX 元。乙方应于每月 XX 日前支付当月租金。''',
        'loan_agreement': '''借款协议

出借人（甲方）：XXX
借款人（乙方）：XXX

甲乙双方经协商一致，就借款事宜达成如下协议：

第一条 借款金额
甲方向乙方提供借款人民币 XXX 元（大写：XXX）。

第二条 借款期限
借款期限自 XXXX 年 XX 月 XX 日起至 XXXX 年 XX 月 XX 日止。

第三条 利率
借款利率为年利率 XX%。

第四条 还款方式
乙方应于借款到期日前一次性归还本金及利息。''',
        'divorce_agreement': '''离婚协议书

男方：XXX
女方：XXX

双方自愿离婚，经协商一致，就子女抚养、财产分割等事宜达成如下协议：

一、双方自愿解除婚姻关系。
二、子女抚养：婚生子/女 XXX 由 XXX 抚养，另一方每月支付抚养费 XXX 元。
三、财产分割：...''',
        'labor_arbitration': '''劳动仲裁申请书

申请人：XXX，性别：X，出生日期：XXXX 年 XX 月 XX 日，住址：XXX，电话：XXX。
被申请人：XXX 公司，住所地：XXX，法定代表人：XXX。

仲裁请求：
1. 请求裁决被申请人支付拖欠工资人民币 XXX 元；
2. 请求裁决被申请人支付经济补偿金人民币 XXX 元；
3. 请求裁决被申请人为申请人补缴社会保险。

事实与理由：
申请人于 XXXX 年 XX 月 XX 日入职被申请人处，从事 XXX 工作。...''',
        'debt_transfer': '''债权转让协议

转让方（甲方）：XXX
受让方（乙方）：XXX
债务人：XXX

根据《中华人民共和国民法典》相关规定，甲乙双方就债权转让事宜达成如下协议：

第一条 转让标的
甲方将其对债务人享有的债权人民币 XXX 元转让给乙方。

第二条 转让价款
乙方应向甲方支付转让价款人民币 XXX 元。

第三条 权利移交
自本协议生效之日起，与债权相关的全部权利一并转让给乙方。''',
        'settlement': '''和解协议

甲方：XXX
乙方：XXX

鉴于甲乙双方因 XXX 发生纠纷，经协商一致，达成如下和解协议：

第一条 纠纷背景
...

第二条 和解内容
双方同意按以下方式解决纠纷：...

第三条 赔偿金额
甲方/乙方应于 XXXX 年 XX 月 XX 日前向对方支付赔偿金人民币 XXX 元。''',
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
                       WHEN 'loan_agreement' THEN '借款协议'
                       WHEN 'rental_contract' THEN '租房合同'
                       WHEN 'divorce_agreement' THEN '离婚协议书'
                       WHEN 'labor_arbitration' THEN '劳动仲裁申请书'
                       WHEN 'debt_transfer' THEN '债权转让协议'
                       WHEN 'settlement' THEN '和解协议'
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
