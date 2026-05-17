"""
Phase 11: 文书增强 API
- 文书详情
- 在线编辑
- 下载 Word/PDF
- 分享功能
"""

import os
import sqlite3
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
import io

phase11_bp = Blueprint('phase11', __name__)

# 文书模板配置
DOCUMENT_TEMPLATES = {
    'civil_complaint': {'name': '民事起诉状', 'format': 'legal'},
    'defense': {'name': '答辩状', 'format': 'legal'},
    'lawyer_letter': {'name': '律师函', 'format': 'letter'},
    'rental_contract': {'name': '租房合同', 'format': 'contract'},
    'loan_agreement': {'name': '借款协议', 'format': 'contract'},
    'divorce_agreement': {'name': '离婚协议', 'format': 'agreement'},
    'labor_arbitration': {'name': '劳动仲裁申请书', 'format': 'legal'},
    'debt_transfer': {'name': '债权转让协议', 'format': 'contract'},
    'settlement': {'name': '和解协议', 'format': 'agreement'}
}

def get_db():
    db = sqlite3.connect('/home/admin/xinhai_legal.db')
    db.row_factory = sqlite3.Row
    return db

# ============== 文书详情 ==============

@phase11_bp.route('/api/v1/document/<doc_id>/detail', methods=['GET'])
def get_document_detail(doc_id):
    """
    获取文书详情
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
        doc = cursor.fetchone()
        
        if not doc:
            db.close()
            return jsonify({'code': 404, 'message': '文书不存在'}), 404
        
        # 增加浏览次数
        cursor.execute('UPDATE documents SET view_count = view_count + 1 WHERE id = ?', (doc_id,))
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': dict(doc)
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


# ============== 文书列表 ==============

@phase11_bp.route('/api/v1/document/list', methods=['GET'])
def get_document_list():
    """
    获取文书列表
    参数：user_id, page, limit, doc_type
    """
    try:
        user_id = request.args.get('user_id')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        doc_type = request.args.get('type', 'all')
        
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        if doc_type == 'all':
            cursor.execute('''
                SELECT id, title, doc_type, status, created_at, updated_at, view_count
                FROM documents
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, (page-1)*limit))
        else:
            cursor.execute('''
                SELECT id, title, doc_type, status, created_at, updated_at, view_count
                FROM documents
                WHERE user_id = ? AND doc_type = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, doc_type, limit, (page-1)*limit))
        
        documents = [dict(row) for row in cursor.fetchall()]
        
        # 获取总数
        if doc_type == 'all':
            cursor.execute('SELECT COUNT(*) as count FROM documents WHERE user_id = ?', (user_id,))
        else:
            cursor.execute('SELECT COUNT(*) as count FROM documents WHERE user_id = ? AND doc_type = ?', (user_id, doc_type))
        total = cursor.fetchone()['count']
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': total,
                'page': page,
                'limit': limit,
                'documents': documents
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


# ============== 文书更新 ==============

@phase11_bp.route('/api/v1/document/<doc_id>', methods=['PUT'])
def update_document(doc_id):
    """
    更新文书（在线编辑保存）
    参数：title, content, status
    """
    try:
        data = request.get_json()
        
        db = get_db()
        cursor = db.cursor()
        
        # 检查文书是否存在
        cursor.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
        if not cursor.fetchone():
            db.close()
            return jsonify({'code': 404, 'message': '文书不存在'}), 404
        
        # 构建更新字段
        updates = []
        values = []
        
        if 'title' in data:
            updates.append('title = ?')
            values.append(data['title'])
        
        if 'content' in data:
            updates.append('content = ?')
            values.append(data['content'])
        
        if 'status' in data:
            updates.append('status = ?')
            values.append(data['status'])
        
        updates.append('updated_at = ?')
        values.append(datetime.now().isoformat())
        values.append(doc_id)
        
        cursor.execute(f'''
            UPDATE documents SET {', '.join(updates)} WHERE id = ?
        ''', values)
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '保存成功'
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'保存失败：{str(e)}'}), 500


# ============== 文书下载 ==============

@phase11_bp.route('/api/v1/document/<doc_id>/download', methods=['GET'])
def download_document(doc_id):
    """
    下载文书
    参数：format (word/pdf)
    """
    try:
        format_type = request.args.get('format', 'word')
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
        doc = cursor.fetchone()
        
        if not doc:
            db.close()
            return jsonify({'code': 404, 'message': '文书不存在'}), 404
        
        db.close()
        
        # 获取文书模板信息
        template = DOCUMENT_TEMPLATES.get(doc['doc_type'], {'name': '法律文书', 'format': 'legal'})
        
        # 生成文件内容
        if format_type == 'word':
            return generate_word_document(doc, template)
        elif format_type == 'pdf':
            return generate_pdf_document(doc, template)
        else:
            return jsonify({'code': 400, 'message': '不支持的格式'}), 400
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'下载失败：{str(e)}'}), 500


def generate_word_document(doc, template):
    """
    生成 Word 文档
    实际部署时接入 python-docx 或 docxtpl
    """
    # TODO: 使用 python-docx 生成真实 Word 文档
    # 这里返回纯文本模拟
    
    content = f"""
{doc['title']}

{doc['content']}

---
生成时间：{doc['created_at']}
心海法律 AI 生成
"""
    
    # 创建模拟文件
    file_io = io.BytesIO()
    file_io.write(content.encode('utf-8'))
    file_io.seek(0)
    
    filename = f"{template['name']}.docx"
    
    return send_file(
        file_io,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name=filename
    )


def generate_pdf_document(doc, template):
    """
    生成 PDF 文档
    实际部署时接入 reportlab 或 weasyprint
    """
    # TODO: 使用 reportlab 生成真实 PDF
    # 这里返回纯文本模拟
    
    content = f"""
{doc['title']}

{doc['content']}

---
生成时间：{doc['created_at']}
心海法律 AI 生成
"""
    
    file_io = io.BytesIO()
    file_io.write(content.encode('utf-8'))
    file_io.seek(0)
    
    filename = f"{template['name']}.pdf"
    
    return send_file(
        file_io,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


# ============== 文书分享 ==============

@phase11_bp.route('/api/v1/document/<doc_id>/share', methods=['POST'])
def share_document(doc_id):
    """
    分享文书
    参数：share_type (wechat/link)
    """
    try:
        data = request.get_json()
        share_type = data.get('share_type', 'link')
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT * FROM documents WHERE id = ?', (doc_id,))
        doc = cursor.fetchone()
        
        if not doc:
            db.close()
            return jsonify({'code': 404, 'message': '文书不存在'}), 404
        
        # 生成分享链接
        share_url = f"https://xinclaw.com/share/doc/{doc_id}"
        
        # 记录分享
        cursor.execute('''
            INSERT INTO document_shares (document_id, share_type, share_url, created_at)
            VALUES (?, ?, ?, ?)
        ''', (doc_id, share_type, share_url, datetime.now().isoformat()))
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '分享链接已生成',
            'data': {
                'share_url': share_url,
                'share_type': share_type
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'分享失败：{str(e)}'}), 500


# ============== 文书删除 ==============

@phase11_bp.route('/api/v1/document/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """
    删除文书
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '删除成功'
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'删除失败：{str(e)}'}), 500


# ============== 数据库初始化 ==============

def init_phase11_tables():
    """
    初始化 Phase 11 数据库表
    """
    db = get_db()
    cursor = db.cursor()
    
    # 确保 documents 表有必要的字段
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            view_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    
    # 文书分享记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            share_type TEXT NOT NULL,
            share_url TEXT NOT NULL,
            view_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    db.commit()
    db.close()
    print("Phase 11 数据库表初始化完成")


if __name__ == '__main__':
    init_phase11_tables()
    print("Phase 11 文书增强 API 模块就绪")
