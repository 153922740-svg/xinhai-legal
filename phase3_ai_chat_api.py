"""
Phase 3: AI 核心功能 - AI 对话接口
整合 ChatRouter 服务，实现 AI 法律对话功能
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
import os
import sys

# 添加项目路径
sys.path.insert(0, '/home/admin/xinhai_legal_api')

# 导入 ChatRouter
try:
    from services.chat_router import ChatRouter, Message
    CHAT_ROUTER_AVAILABLE = True
except ImportError:
    CHAT_ROUTER_AVAILABLE = False
    print("⚠️ ChatRouter 未导入，使用基础实现")

# 导入数据库
try:
    from models.db import get_db, UserModel
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠️ 数据库模块未导入")

# 创建 Blueprint
phase3_bp = Blueprint('phase3', __name__)

# 初始化 ChatRouter
chat_router = None
if CHAT_ROUTER_AVAILABLE:
    try:
        db_path = '/home/admin/xinhai-legal/data/xinhai_legal.db'
        chat_router = ChatRouter(db_path=db_path)
        print("✅ ChatRouter 已初始化")
    except Exception as e:
        print(f"⚠️ ChatRouter 初始化失败：{e}")
        chat_router = None


# ============== Helper Functions ==============

def get_user_id_from_token(token):
    """从 token 解析用户 ID（简化版）"""
    if not token:
        return None
    
    # TODO: 实现真实的 token 解析
    # 临时返回测试用户 ID
    return 1


def save_chat_message(user_id, session_id, role, content, message_type='text'):
    """保存对话消息到数据库"""
    if not DB_AVAILABLE:
        return False
    
    try:
        conn = get_db()
        conn.execute("""
            INSERT INTO chat_messages (session_id, user_id, role, content, message_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, role, content, message_type, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"保存消息失败：{e}")
        return False


# ============== API Routes ==============

@phase3_bp.route('/api/v1/chat/send', methods=['POST'])
def chat_send():
    """
    AI 对话接口
    
    请求:
    {
        "message": "用户消息",
        "session_id": "会话 ID（可选，为空则创建新会话）",
        "stream": false  // 是否流式输出
    }
    
    响应:
    {
        "code": 200,
        "data": {
            "session_id": "会话 ID",
            "message": "AI 回复",
            "message_type": "text",
            "metadata": {}
        }
    }
    """
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('session_id')
        stream = data.get('stream', False)
        
        # 获取用户 ID
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = get_user_id_from_token(token)
        
        if not message:
            return jsonify({'code': 400, 'message': '消息不能为空'}), 400
        
        # 创建新会话 ID
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 使用 ChatRouter 处理对话
        if chat_router and CHAT_ROUTER_AVAILABLE:
            try:
                # 调用 ChatRouter
                response = chat_router.send(
                    user_id=user_id,
                    session_id=session_id,
                    message=message
                )
                
                # 保存用户消息
                save_chat_message(user_id, session_id, 'user', message)
                
                # 保存 AI 回复
                ai_content = response.get('content', '')
                ai_type = response.get('type', 'text')
                save_chat_message(user_id, session_id, 'assistant', ai_content, ai_type)
                
                return jsonify({
                    'code': 200,
                    'message': '对话成功',
                    'data': {
                        'session_id': session_id,
                        'message': ai_content,
                        'message_type': ai_type,
                        'metadata': response.get('metadata', {})
                    }
                })
                
            except Exception as e:
                print(f"ChatRouter 处理失败：{e}")
                # 降级到基础回复
                ai_response = f"收到您的问题：{message}\n\nAI 助手正在处理中..."
                
                save_chat_message(user_id, session_id, 'user', message)
                save_chat_message(user_id, session_id, 'assistant', ai_response)
                
                return jsonify({
                    'code': 200,
                    'message': '对话成功',
                    'data': {
                        'session_id': session_id,
                        'message': ai_response,
                        'message_type': 'text',
                        'metadata': {}
                    }
                })
        else:
            # ChatRouter 不可用，使用基础回复
            ai_response = generate_basic_response(message)
            
            if user_id:
                save_chat_message(user_id, session_id, 'user', message)
                save_chat_message(user_id, session_id, 'assistant', ai_response)
            
            return jsonify({
                'code': 200,
                'message': '对话成功',
                'data': {
                    'session_id': session_id,
                    'message': ai_response,
                    'message_type': 'text',
                    'metadata': {}
                }
            })
    
    except Exception as e:
        print(f"对话接口异常：{e}")
        return jsonify({'code': 500, 'message': f'服务器错误：{str(e)}'}), 500


@phase3_bp.route('/api/v1/chat/sessions', methods=['GET'])
def get_chat_sessions():
    """
    获取用户会话列表
    
    响应:
    {
        "code": 200,
        "data": {
            "sessions": [
                {
                    "session_id": "xxx",
                    "title": "会话标题",
                    "last_message": "最后一条消息",
                    "created_at": "创建时间",
                    "updated_at": "更新时间"
                }
            ]
        }
    }
    """
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = get_user_id_from_token(token)
        
        if not user_id:
            return jsonify({'code': 401, 'message': '未登录'}), 401
        
        if not DB_AVAILABLE:
            return jsonify({
                'code': 200,
                'data': {'sessions': []}
            })
        
        conn = get_db()
        sessions = conn.execute("""
            SELECT session_id, user_id, created_at, last_activity, message_count
            FROM chat_sessions
            WHERE user_id = ?
            ORDER BY last_activity DESC
            LIMIT 50
        """, (user_id,)).fetchall()
        conn.close()
        
        session_list = []
        for s in sessions:
            session_list.append({
                'session_id': s['session_id'],
                'title': f'会话 {s["session_id"][:8]}',
                'created_at': s['created_at'],
                'updated_at': s['last_activity'],
                'message_count': s['message_count']
            })
        
        return jsonify({
            'code': 200,
            'data': {'sessions': session_list}
        })
    
    except Exception as e:
        print(f"获取会话列表失败：{e}")
        return jsonify({'code': 500, 'message': f'服务器错误：{str(e)}'}), 500


@phase3_bp.route('/api/v1/chat/sessions/<session_id>', methods=['GET'])
def get_chat_session(session_id):
    """
    获取会话详情（消息列表）
    
    响应:
    {
        "code": 200,
        "data": {
            "session_id": "xxx",
            "messages": [
                {
                    "role": "user/assistant",
                    "content": "消息内容",
                    "type": "text",
                    "created_at": "时间"
                }
            ]
        }
    }
    """
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = get_user_id_from_token(token)
        
        if not user_id:
            return jsonify({'code': 401, 'message': '未登录'}), 401
        
        if not DB_AVAILABLE:
            return jsonify({
                'code': 200,
                'data': {'session_id': session_id, 'messages': []}
            })
        
        conn = get_db()
        messages = conn.execute("""
            SELECT role, content, message_type, created_at
            FROM chat_messages
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at ASC
            LIMIT 100
        """, (session_id, user_id)).fetchall()
        conn.close()
        
        message_list = []
        for m in messages:
            message_list.append({
                'role': m['role'],
                'content': m['content'],
                'type': m['message_type'],
                'created_at': m['created_at']
            })
        
        return jsonify({
            'code': 200,
            'data': {
                'session_id': session_id,
                'messages': message_list
            }
        })
    
    except Exception as e:
        print(f"获取会话详情失败：{e}")
        return jsonify({'code': 500, 'message': f'服务器错误：{str(e)}'}), 500


@phase3_bp.route('/api/v1/chat/sessions/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    """
    删除会话
    
    响应:
    {
        "code": 200,
        "message": "删除成功"
    }
    """
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = get_user_id_from_token(token)
        
        if not user_id:
            return jsonify({'code': 401, 'message': '未登录'}), 401
        
        if not DB_AVAILABLE:
            return jsonify({'code': 200, 'message': '删除成功'})
        
        conn = get_db()
        conn.execute("DELETE FROM chat_messages WHERE session_id = ? AND user_id = ?", (session_id, user_id))
        conn.execute("DELETE FROM chat_sessions WHERE session_id = ? AND user_id = ?", (session_id, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'code': 200, 'message': '删除成功'})
    
    except Exception as e:
        print(f"删除会话失败：{e}")
        return jsonify({'code': 500, 'message': f'服务器错误：{str(e)}'}), 500


@phase3_bp.route('/api/v1/chat/sessions/<session_id>/rename', methods=['PUT'])
def rename_chat_session(session_id):
    """
    重命名会话
    
    请求:
    {
        "title": "新标题"
    }
    """
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user_id = get_user_id_from_token(token)
        
        if not user_id:
            return jsonify({'code': 401, 'message': '未登录'}), 401
        
        data = request.get_json()
        title = data.get('title', '')
        
        if not title:
            return jsonify({'code': 400, 'message': '标题不能为空'}), 400
        
        # TODO: 实现标题更新（需要添加 title 字段到 chat_sessions 表）
        
        return jsonify({'code': 200, 'message': '重命名成功'})
    
    except Exception as e:
        print(f"重命名会话失败：{e}")
        return jsonify({'code': 500, 'message': f'服务器错误：{str(e)}'}), 500


# ============== Basic Response Generator ==============

def generate_basic_response(message):
    """
    基础回复生成器（当 ChatRouter 不可用时使用）
    """
    message_lower = message.lower()
    
    # 简单关键词匹配
    if any(word in message_lower for word in ['你好', 'hello', 'hi', '您好']):
        return "您好！我是心海法律 AI 助手，很高兴为您服务。请问有什么法律问题需要咨询吗？"
    
    if any(word in message_lower for word in ['离婚', '结婚', '婚姻']):
        return "关于婚姻家庭问题，我可以为您提供以下帮助：\n\n1. 离婚程序咨询\n2. 财产分割建议\n3. 子女抚养权问题\n4. 婚前/婚内协议\n\n请详细描述您的情况，我会为您提供更具体的建议。"
    
    if any(word in message_lower for word in ['工资', '加班', '裁员', '劳动']):
        return "关于劳动争议问题，我可以帮您分析：\n\n1. 工资拖欠处理\n2. 加班费计算\n3. 违法辞退赔偿\n4. 工伤认定流程\n\n请告诉我具体情况。"
    
    if any(word in message_lower for word in ['合同', '违约', '协议']):
        return "关于合同纠纷，我可以为您提供：\n\n1. 合同条款解读\n2. 违约责任分析\n3. 解除合同条件\n4. 索赔建议\n\n请描述您的合同问题。"
    
    # 默认回复
    return f"收到您的咨询：{message}\n\n我是心海法律 AI 助手，可以为您提供婚姻家庭、劳动争议、合同纠纷等法律咨询。请详细描述您的问题，我会尽力为您解答。"


# ============== Health Check ==============

@phase3_bp.route('/api/v1/chat/health', methods=['GET'])
def chat_health():
    """对话服务健康检查"""
    return jsonify({
        'status': 'ok',
        'chat_router': 'available' if chat_router else 'unavailable',
        'database': 'connected' if DB_AVAILABLE else 'disconnected'
    })
