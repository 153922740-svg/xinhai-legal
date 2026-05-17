"""
心海法律 AI - 服务模块
"""

from .chat_router import ChatRouter, Message, ChatContext, MessageType, create_chat_router

__all__ = [
    'ChatRouter',
    'Message',
    'ChatContext', 
    'MessageType',
    'create_chat_router'
]
