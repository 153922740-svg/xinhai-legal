"""
Phase 5: 输入增强 API
- 语音识别（阿里云）
- 文件上传（PDF/Word）
- 图片上传 + OCR 识别
"""

import os
import uuid
import sqlite3
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

phase5_bp = Blueprint('phase5', __name__)

# 配置
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
UPLOAD_FOLDER = '/home/admin/xinhai_legal_uploads'
VOICE_FOLDER = os.path.join(UPLOAD_FOLDER, 'voice')
FILE_FOLDER = os.path.join(UPLOAD_FOLDER, 'files')
IMAGE_FOLDER = os.path.join(UPLOAD_FOLDER, 'images')

# 确保目录存在
for folder in [UPLOAD_FOLDER, VOICE_FOLDER, FILE_FOLDER, IMAGE_FOLDER]:
    os.makedirs(folder, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    db = sqlite3.connect('/home/admin/xinhai_legal.db')
    db.row_factory = sqlite3.Row
    return db

# ============== 语音识别 ==============

@phase5_bp.route('/api/v1/voice/recognize', methods=['POST'])
def voice_recognize():
    """
    语音识别 - 将语音文件转换为文字
    支持：mp3, wav, amr, m4a
    """
    try:
        if 'audio' not in request.files:
            return jsonify({'code': 400, 'message': '请上传音频文件'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'code': 400, 'message': '文件名为空'}), 400
        
        # 验证文件类型
        filename = secure_filename(audio_file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        allowed_audio = {'mp3', 'wav', 'amr', 'm4a', 'webm'}
        if ext not in allowed_audio:
            return jsonify({'code': 400, 'message': f'不支持的音频格式，支持：{allowed_audio}'}), 400
        
        # 保存文件
        voice_id = str(uuid.uuid4())
        voice_filename = f"{voice_id}.{ext}"
        voice_path = os.path.join(VOICE_FOLDER, voice_filename)
        audio_file.save(voice_path)
        
        # 调用阿里云语音识别 API（模拟）
        # 实际部署时需要配置阿里云 SDK
        recognized_text = recognize_voice_with_ali(voice_path)
        
        # 记录到数据库
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO voice_records (user_id, file_path, recognized_text, duration, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            request.headers.get('X-User-ID', 'anonymous'),
            voice_path,
            recognized_text,
            0,  # 时长需要音频处理获取
            datetime.now().isoformat()
        ))
        db.commit()
        record_id = cursor.lastrowid
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '语音识别成功',
            'data': {
                'voice_id': voice_id,
                'record_id': record_id,
                'text': recognized_text,
                'file_path': f'/uploads/voice/{voice_filename}'
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'语音识别失败：{str(e)}'}), 500


def recognize_voice_with_ali(file_path):
    """
    使用阿里云语音识别服务
    需要配置：ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET
    """
    # TODO: 实际部署时接入阿里云智能语音交互服务
    # 参考：https://help.aliyun.com/product/30463.html
    
    # 模拟返回
    return "[语音识别内容] 这是一个测试文本，实际使用时需要接入阿里云语音识别 API"


# ============== 文件上传 ==============

@phase5_bp.route('/api/v1/file/upload', methods=['POST'])
def file_upload():
    """
    文件上传 - 支持 PDF/Word/TXT
    上传后自动提取文本内容
    """
    try:
        if 'file' not in request.files:
            return jsonify({'code': 400, 'message': '请上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'code': 400, 'message': '文件名为空'}), 400
        
        # 验证文件类型
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        allowed_docs = {'pdf', 'doc', 'docx', 'txt'}
        if ext not in allowed_docs:
            return jsonify({'code': 400, 'message': f'不支持的文件格式，支持：{allowed_docs}'}), 400
        
        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置指针
        if file_size > MAX_FILE_SIZE:
            return jsonify({'code': 400, 'message': f'文件大小超过限制 ({MAX_FILE_SIZE/1024/1024}MB)'}), 400
        
        # 保存文件
        file_id = str(uuid.uuid4())
        file_filename = f"{file_id}.{ext}"
        file_path = os.path.join(FILE_FOLDER, file_filename)
        file.save(file_path)
        
        # 提取文本内容
        extracted_text = extract_text_from_file(file_path, ext)
        
        # 记录到数据库
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO uploaded_files (user_id, file_path, file_name, file_type, extracted_text, file_size, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.headers.get('X-User-ID', 'anonymous'),
            file_path,
            filename,
            ext,
            extracted_text,
            file_size,
            datetime.now().isoformat()
        ))
        db.commit()
        record_id = cursor.lastrowid
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '文件上传成功',
            'data': {
                'file_id': file_id,
                'record_id': record_id,
                'file_name': filename,
                'file_type': ext,
                'file_size': file_size,
                'text_length': len(extracted_text),
                'extracted_text': extracted_text[:500] + '...' if len(extracted_text) > 500 else extracted_text,
                'file_path': f'/uploads/files/{file_filename}'
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'文件上传失败：{str(e)}'}), 500


def extract_text_from_file(file_path, ext):
    """
    从文件中提取文本
    """
    try:
        if ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif ext == 'pdf':
            # 使用 PyPDF2 或 pdfplumber 提取 PDF 文本
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                return text
            except ImportError:
                return "[PDF 文本提取] 需要安装 pdfplumber: pip install pdfplumber"
        
        elif ext in ['doc', 'docx']:
            # 使用 python-docx 提取 Word 文本
            try:
                from docx import Document
                doc = Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
                return text
            except ImportError:
                return "[Word 文本提取] 需要安装 python-docx: pip install python-docx"
        
        return ""
    
    except Exception as e:
        return f"[文本提取失败] {str(e)}"


# ============== 图片上传 + OCR ==============

@phase5_bp.route('/api/v1/image/upload', methods=['POST'])
def image_upload():
    """
    图片上传 + OCR 识别
    支持：png, jpg, jpeg, gif
    """
    try:
        if 'image' not in request.files:
            return jsonify({'code': 400, 'message': '请上传图片'}), 400
        
        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'code': 400, 'message': '文件名为空'}), 400
        
        # 验证文件类型
        filename = secure_filename(image_file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        allowed_images = {'png', 'jpg', 'jpeg', 'gif'}
        if ext not in allowed_images:
            return jsonify({'code': 400, 'message': f'不支持的图片格式，支持：{allowed_images}'}), 400
        
        # 保存文件
        image_id = str(uuid.uuid4())
        image_filename = f"{image_id}.{ext}"
        image_path = os.path.join(IMAGE_FOLDER, image_filename)
        image_file.save(image_path)
        
        # OCR 识别
        ocr_text = ocr_with_ali(image_path)
        
        # 记录到数据库
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO uploaded_images (user_id, file_path, ocr_text, created_at)
            VALUES (?, ?, ?, ?)
        ''', (
            request.headers.get('X-User-ID', 'anonymous'),
            image_path,
            ocr_text,
            datetime.now().isoformat()
        ))
        db.commit()
        record_id = cursor.lastrowid
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '图片上传成功',
            'data': {
                'image_id': image_id,
                'record_id': record_id,
                'ocr_text': ocr_text,
                'file_path': f'/uploads/images/{image_filename}'
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'图片上传失败：{str(e)}'}), 500


def ocr_with_ali(image_path):
    """
    使用阿里云 OCR 服务识别图片文字
    需要配置：ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET
    """
    # TODO: 实际部署时接入阿里云 OCR 服务
    # 参考：https://help.aliyun.com/product/28922.html
    
    # 模拟返回
    return "[OCR 识别内容] 这是一个测试文本，实际使用时需要接入阿里云 OCR API"


# ============== 查询上传记录 ==============

@phase5_bp.route('/api/v1/uploads/history', methods=['GET'])
def get_upload_history():
    """
    获取用户上传历史
    参数：type=voice|file|image, page, limit
    """
    try:
        upload_type = request.args.get('type', 'all')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        user_id = request.headers.get('X-User-ID', 'anonymous')
        
        db = get_db()
        cursor = db.cursor()
        
        results = []
        
        if upload_type in ['voice', 'all']:
            cursor.execute('''
                SELECT 'voice' as type, record_id as id, recognized_text as content, created_at
                FROM voice_records WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            ''', (user_id, limit, (page-1)*limit))
            results.extend([dict(row) for row in cursor.fetchall()])
        
        if upload_type in ['file', 'all']:
            cursor.execute('''
                SELECT 'file' as type, record_id as id, file_name as content, created_at
                FROM uploaded_files WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            ''', (user_id, limit, (page-1)*limit))
            results.extend([dict(row) for row in cursor.fetchall()])
        
        if upload_type in ['image', 'all']:
            cursor.execute('''
                SELECT 'image' as type, record_id as id, ocr_text as content, created_at
                FROM uploaded_images WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            ''', (user_id, limit, (page-1)*limit))
            results.extend([dict(row) for row in cursor.fetchall()])
        
        db.close()
        
        # 按时间排序
        results.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': len(results),
                'page': page,
                'limit': limit,
                'items': results
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


# ============== 数据库初始化 ==============

def init_phase5_tables():
    """
    初始化 Phase 5 数据库表
    """
    db = get_db()
    cursor = db.cursor()
    
    # 语音记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            recognized_text TEXT,
            duration INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    # 上传文件表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploaded_files (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            extracted_text TEXT,
            file_size INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    # 上传图片表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploaded_images (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            ocr_text TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    db.commit()
    db.close()
    print("Phase 5 数据库表初始化完成")


if __name__ == '__main__':
    init_phase5_tables()
    print("Phase 5 输入增强 API 模块就绪")
