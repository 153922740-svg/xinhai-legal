"""
Phase 13: 历史对话 API
- 会话列表
- 会话详情
- 会话删除
- 会话重命名
"""

import sqlite3
from datetime import datetime
from flask import Blueprint, request, jsonify

phase13_bp = Blueprint('phase13', __name__)

def get_db():
    db = sqlite3.connect('/home/admin/xinhai_legal.db')
    db.row_factory = sqlite3.Row
    return db

@phase13_bp.route('/api/v1/chat/sessions', methods=['GET'])
def get_sessions():
    """获取会话列表"""
    try:
        user_id = request.args.get('user_id')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        if not user_id:
            return jsonify({'code': 400, 'message': '缺少 user_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            SELECT id, title, created_at, updated_at
            FROM chat_sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, (page-1)*limit))
        
        sessions = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute('SELECT COUNT(*) as count FROM chat_sessions WHERE user_id = ?', (user_id,))
        total = cursor.fetchone()['count']
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'total': total, 'page': page, 'limit': limit, 'sessions': sessions}
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500

@phase13_bp.route('/api/v1/chat/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """获取会话详情"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT * FROM chat_sessions WHERE id = ?', (session_id,))
        session = cursor.fetchone()
        
        if not session:
            db.close()
            return jsonify({'code': 404, 'message': '会话不存在'}), 404
        
        cursor.execute('''
            SELECT id, role, content, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY created_at ASC
        ''', (session_id,))
        
        messages = [dict(row) for row in cursor.fetchall()]
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'session': dict(session), 'messages': messages}
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500

@phase13_bp.route('/api/v1/chat/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除会话"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
        cursor.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
        
        db.commit()
        db.close()
        
        return jsonify({'code': 200, 'message': '删除成功'})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'删除失败：{str(e)}'}), 500

@phase13_bp.route('/api/v1/chat/sessions/<session_id>/rename', methods=['PUT'])
def rename_session(session_id):
    """重命名会话"""
    try:
        data = request.get_json()
        title = data.get('title')
        
        if not title:
            return jsonify({'code': 400, 'message': '缺少标题'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?',
                      (title, datetime.now().isoformat(), session_id))
        
        db.commit()
        db.close()
        
        return jsonify({'code': 200, 'message': '重命名成功'})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'操作失败：{str(e)}'}), 500

if __name__ == '__main__':
    print("Phase 13 历史对话 API 模块就绪")
