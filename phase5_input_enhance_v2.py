"""
心海法律 AI - Phase 5 输入增强 API
语音识别、文件上传、图片 OCR、智能输入建议
"""

import os
import uuid
import json
import sqlite3
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename

phase5_bp = Blueprint('phase5_input', __name__, url_prefix='/api/v5')

# 配置
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'gif'}
VOICE_EXTENSIONS = {'mp3', 'wav', 'amr', 'm4a', 'aac'}
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_VOICE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

UPLOAD_FOLDER = '/home/admin/xinhai_legal_uploads'
VOICE_FOLDER = os.path.join(UPLOAD_FOLDER, 'voice')
FILE_FOLDER = os.path.join(UPLOAD_FOLDER, 'files')
IMAGE_FOLDER = os.path.join(UPLOAD_FOLDER, 'images')

# 确保目录存在
for folder in [UPLOAD_FOLDER, VOICE_FOLDER, FILE_FOLDER, IMAGE_FOLDER]:
    os.makedirs(folder, exist_ok=True)


def allowed_file(filename, extensions):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions


def get_db():
    """获取数据库连接"""
    if not hasattr(g, 'db'):
        g.db = sqlite3.connect('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        g.db.row_factory = sqlite3.Row
    return g.db


# ============== 语音识别 ==============

@phase5_bp.route('/voice/recognize', methods=['POST'])
def voice_recognize():
    """
    语音识别 - 将语音文件转换为文字
    POST /api/v5/voice/recognize
    
    Form Data:
    - audio: 音频文件 (mp3/wav/amr/m4a/aac)
    - user_id: 用户 ID
    
    Response:
    {
        "code": 200,
        "data": {
            "text": "我想咨询离婚问题...",
            "duration": 15.5,
            "file_url": "/uploads/voice/xxx.wav"
        }
    }
    """
    try:
        if 'audio' not in request.files:
            return jsonify({'code': 400, 'message': '请上传音频文件'}), 400
        
        audio_file = request.files['audio']
        user_id = request.form.get('user_id', type=int)
        
        if audio_file.filename == '':
            return jsonify({'code': 400, 'message': '请选择文件'}), 400
        
        if not allowed_file(audio_file.filename, VOICE_EXTENSIONS):
            return jsonify({'code': 400, 'message': '不支持的音频格式'}), 400
        
        # 检查文件大小
        audio_file.seek(0, 2)  # 移动到文件末尾
        file_size = audio_file.tell()
        audio_file.seek(0)  # 重置指针
        
        if file_size > MAX_VOICE_SIZE:
            return jsonify({'code': 400, 'message': '文件大小超过 20MB 限制'}), 400
        
        # 生成唯一文件名
        ext = audio_file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(VOICE_FOLDER, filename)
        
        # 保存文件
        audio_file.save(filepath)
        
        # ========== 语音识别（模拟）==========
        # 生产环境调用阿里云语音识别 API
        recognized_text = "我想咨询离婚问题，请问需要什么材料？"
        duration = file_size / 16000  # 估算时长
        
        # 保存识别记录
        conn = get_db()
        cursor = conn.execute("""
            INSERT INTO upload_history (user_id, file_type, file_path, original_text, created_at)
            VALUES (?, 'voice', ?, ?, ?)
        """, (user_id, f'/uploads/voice/{filename}', recognized_text, datetime.now().isoformat()))
        conn.commit()
        upload_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': '语音识别成功',
            'data': {
                'upload_id': upload_id,
                'text': recognized_text,
                'duration': round(duration, 2),
                'file_url': f'/uploads/voice/{filename}',
                'file_size': file_size
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'语音识别失败：{str(e)}',
            'data': None
        }), 500


# ============== 文件上传 ==============

@phase5_bp.route('/file/upload', methods=['POST'])
def file_upload():
    """
    文件上传 - 支持 PDF/Word/TXT
    POST /api/v5/file/upload
    
    Form Data:
    - file: 文件 (pdf/doc/docx/txt)
    - user_id: 用户 ID
    - file_type: 文件类型 (contract/evidence/document)
    
    Response:
    {
        "code": 200,
        "data": {
            "file_id": 123,
            "file_url": "/uploads/files/xxx.pdf",
            "file_name": "合同.pdf",
            "file_size": 102400,
            "extracted_text": "合同内容..."
        }
    }
    """
    try:
        if 'file' not in request.files:
            return jsonify({'code': 400, 'message': '请上传文件'}), 400
        
        uploaded_file = request.files['file']
        user_id = request.form.get('user_id', type=int)
        file_type = request.form.get('file_type', 'document')
        
        if uploaded_file.filename == '':
            return jsonify({'code': 400, 'message': '请选择文件'}), 400
        
        if not allowed_file(uploaded_file.filename, ALLOWED_EXTENSIONS):
            return jsonify({'code': 400, 'message': '不支持的文件格式'}), 400
        
        # 检查文件大小
        uploaded_file.seek(0, 2)
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'code': 400, 'message': '文件大小超过 10MB 限制'}), 400
        
        # 生成唯一文件名
        ext = uploaded_file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(FILE_FOLDER, filename)
        
        # 保存文件
        uploaded_file.save(filepath)
        
        # ========== 文件内容提取（模拟）==========
        # 生产环境调用 PDF/Word 解析库
        extracted_text = ""
        if ext == 'txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                extracted_text = f.read()[:5000]  # 限制长度
        else:
            extracted_text = f"[{ext.upper()} 文件内容已保存，待解析]"
        
        # 保存上传记录
        conn = get_db()
        cursor = conn.execute("""
            INSERT INTO upload_history (user_id, file_type, file_path, original_text, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, file_type, f'/uploads/files/{filename}', extracted_text[:500], datetime.now().isoformat()))
        conn.commit()
        upload_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': '文件上传成功',
            'data': {
                'upload_id': upload_id,
                'file_url': f'/uploads/files/{filename}',
                'file_name': uploaded_file.filename,
                'file_size': file_size,
                'file_type': ext,
                'extracted_text': extracted_text
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'文件上传失败：{str(e)}',
            'data': None
        }), 500


# ============== 图片上传 + OCR ==============

@phase5_bp.route('/image/upload', methods=['POST'])
def image_upload():
    """
    图片上传 + OCR 识别
    POST /api/v5/image/upload
    
    Form Data:
    - image: 图片文件 (png/jpg/jpeg/gif/webp)
    - user_id: 用户 ID
    - ocr_enabled: 是否启用 OCR (true/false)
    
    Response:
    {
        "code": 200,
        "data": {
            "image_url": "/uploads/images/xxx.jpg",
            "ocr_text": "图片中的文字内容...",
            "confidence": 0.95
        }
    }
    """
    try:
        if 'image' not in request.files:
            return jsonify({'code': 400, 'message': '请上传图片'}), 400
        
        image_file = request.files['image']
        user_id = request.form.get('user_id', type=int)
        ocr_enabled = request.form.get('ocr_enabled', 'true').lower() == 'true'
        
        if image_file.filename == '':
            return jsonify({'code': 400, 'message': '请选择文件'}), 400
        
        if not allowed_file(image_file.filename, IMAGE_EXTENSIONS):
            return jsonify({'code': 400, 'message': '不支持的图片格式'}), 400
        
        # 检查文件大小
        image_file.seek(0, 2)
        file_size = image_file.tell()
        image_file.seek(0)
        
        if file_size > MAX_IMAGE_SIZE:
            return jsonify({'code': 400, 'message': '文件大小超过 10MB 限制'}), 400
        
        # 生成唯一文件名
        ext = image_file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(IMAGE_FOLDER, filename)
        
        # 保存文件
        image_file.save(filepath)
        
        # ========== OCR 识别（模拟）==========
        # 生产环境调用阿里云/百度 OCR API
        ocr_text = ""
        confidence = 0.0
        
        if ocr_enabled:
            # 模拟 OCR 识别结果
            ocr_text = "证据材料\n日期：2026 年 5 月 17 日\n内容：借款合同..."
            confidence = 0.95
        
        # 保存上传记录
        conn = get_db()
        cursor = conn.execute("""
            INSERT INTO upload_history (user_id, file_type, file_path, original_text, created_at)
            VALUES (?, 'image', ?, ?, ?)
        """, (user_id, f'/uploads/images/{filename}', ocr_text[:500], datetime.now().isoformat()))
        conn.commit()
        upload_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'code': 200,
            'message': '图片上传成功' if not ocr_enabled else 'OCR 识别成功',
            'data': {
                'upload_id': upload_id,
                'image_url': f'/uploads/images/{filename}',
                'file_name': image_file.filename,
                'file_size': file_size,
                'ocr_text': ocr_text,
                'confidence': confidence
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'图片上传失败：{str(e)}',
            'data': None
        }), 500


# ============== 智能输入建议 ==============

@phase5_bp.route('/input/suggestions', methods=['POST'])
def input_suggestions():
    """
    智能输入建议 - 根据用户输入提供法律咨询建议
    POST /api/v5/input/suggestions
    
    Body:
    {
        "user_input": "我想离婚",
        "context": "marriage"  // 上下文类型
    }
    
    Response:
    {
        "code": 200,
        "data": {
            "suggestions": [
                "离婚需要哪些材料？",
                "离婚流程是怎样的？",
                "财产如何分割？"
            ],
            "intent": "divorce_consultation",
            "entities": {"type": "离婚"}
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求体不能为空'}), 400
        
        user_input = data.get('user_input', '')
        context = data.get('context', '')
        
        if not user_input:
            return jsonify({'code': 400, 'message': '缺少用户输入'}), 400
        
        # ========== 智能建议生成（规则引擎）==========
        suggestions = []
        intent = "general"
        entities = {}
        
        # 关键词匹配
        input_lower = user_input.lower()
        
        if any(kw in input_lower for kw in ['离婚', '分手', '分居']):
            intent = "divorce_consultation"
            entities = {"type": "离婚"}
            suggestions = [
                "离婚需要哪些材料？",
                "离婚流程是怎样的？",
                "财产如何分割？",
                "孩子抚养权怎么判定？",
                "离婚冷静期是多久？"
            ]
        elif any(kw in input_lower for kw in ['合同', '协议', '签约']):
            intent = "contract_review"
            entities = {"type": "合同"}
            suggestions = [
                "合同有哪些风险条款？",
                "如何修改合同保护自己？",
                "合同违约怎么办？",
                "合同效力如何认定？"
            ]
        elif any(kw in input_lower for kw in ['借款', '欠款', '债务']):
            intent = "debt_dispute"
            entities = {"type": "债务"}
            suggestions = [
                "借条怎么写才有效？",
                "欠款不还怎么办？",
                "诉讼时效是多久？",
                "如何收集证据？"
            ]
        elif any(kw in input_lower for kw in ['劳动', '工资', '辞退', '加班']):
            intent = "labor_dispute"
            entities = {"type": "劳动纠纷"}
            suggestions = [
                "被违法辞退怎么赔偿？",
                "加班费怎么计算？",
                "劳动仲裁流程？",
                "如何收集劳动证据？"
            ]
        else:
            suggestions = [
                "能详细描述一下您的问题吗？",
                "这件事发生在什么时候？",
                "有相关的证据材料吗？",
                "您希望达到什么目的？"
            ]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'suggestions': suggestions,
                'intent': intent,
                'entities': entities,
                'input_length': len(user_input)
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'生成建议失败：{str(e)}',
            'data': None
        }), 500


# ============== 上传历史 ==============

@phase5_bp.route('/uploads/history', methods=['GET'])
def get_upload_history():
    """
    获取用户上传历史
    GET /api/v5/uploads/history?user_id=1&limit=20&offset=0
    
    Response:
    {
        "code": 200,
        "data": {
            "uploads": [
                {
                    "id": 1,
                    "file_type": "voice",
                    "file_path": "/uploads/voice/xxx.wav",
                    "original_text": "我想咨询...",
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
        file_type = request.args.get('type', '')
        
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少参数 user_id'}), 400
        
        conn = get_db()
        
        query = "SELECT * FROM upload_history WHERE user_id=?"
        params = [user_id]
        
        if file_type:
            query += " AND file_type=?"
            params.append(file_type)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        uploads = conn.execute(query, params).fetchall()
        
        # 获取总数
        count_query = "SELECT COUNT(*) FROM upload_history WHERE user_id=?"
        count_params = [user_id]
        if file_type:
            count_query += " AND file_type=?"
            count_params.append(file_type)
        
        total = conn.execute(count_query, count_params).fetchone()[0]
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'uploads': [dict(u) for u in uploads],
                'total': total,
                'limit': limit,
                'offset': offset
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'查询上传历史失败：{str(e)}',
            'data': None
        }), 500


# ============== 健康检查 ==============

@phase5_bp.route('/health', methods=['GET'])
def input_health():
    """
    输入增强系统健康检查
    GET /api/v5/health
    """
    try:
        import sqlite3
        conn = sqlite3.connect('/home/admin/xinhai_legal_api/data/xinhai_legal.db')
        conn.execute("SELECT 1")
        conn.close()
        
        # 检查上传目录
        dirs_ok = all([
            os.path.exists(VOICE_FOLDER),
            os.path.exists(FILE_FOLDER),
            os.path.exists(IMAGE_FOLDER)
        ])
        
        return jsonify({
            'status': 'ok',
            'input_router': 'available',
            'upload_dirs': 'ready' if dirs_ok else 'not_ready',
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'input_router': 'unavailable',
            'error': str(e)
        }), 500
