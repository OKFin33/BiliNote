from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

from app.services.chat import ChatService
from app.utils.response import ResponseWrapper as R
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# 聊天服务实例
chat_service = ChatService()


class CreateChatSessionRequest(BaseModel):
    task_id: str
    note_content: str
    provider_id: str
    model_name: str


class SendMessageRequest(BaseModel):
    session_id: str
    message: str
    note_content: str
    provider_id: str
    model_name: str
    task_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


@router.post("/chat/sessions")
def create_chat_session(request: CreateChatSessionRequest):
    """创建聊天会话"""
    try:
        result = chat_service.create_chat_session(
            task_id=request.task_id,
            note_content=request.note_content,
            provider_id=request.provider_id,
            model_name=request.model_name
        )
        
        return R.success(
            data=result,
            msg="聊天会话创建成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}")
        return R.error(msg=f"创建聊天会话失败: {str(e)}")


@router.post("/chat/messages")
def send_message(request: SendMessageRequest):
    """发送聊天消息"""
    try:
        result = chat_service.send_message(
            session_id=request.session_id,
            message=request.message,
            note_content=request.note_content,
            provider_id=request.provider_id,
            model_name=request.model_name,
            task_id=request.task_id
        )
        
        return R.success(
            data=result,
            msg="消息发送成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return R.error(msg=f"发送消息失败: {str(e)}")


@router.get("/chat/sessions/{session_id}/history")
def get_chat_history(session_id: str, provider_id: str, model_name: str):
    """获取聊天历史"""
    try:
        history = chat_service.get_chat_history(
            session_id=session_id,
            provider_id=provider_id,
            model_name=model_name
        )
        
        return R.success(
            data={"session_id": session_id, "history": history},
            msg="获取聊天历史成功"
        )
        
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        return R.error(msg=f"获取聊天历史失败: {str(e)}")


@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id: str, provider_id: str, model_name: str):
    """删除聊天会话"""
    try:
        success = chat_service.delete_chat_session(
            session_id=session_id,
            provider_id=provider_id,
            model_name=model_name
        )
        
        if success:
            return R.success(msg="聊天会话删除成功")
        else:
            return R.error(msg="聊天会话删除失败")
        
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}")
        return R.error(msg=f"删除聊天会话失败: {str(e)}")


@router.get("/chat/test")
def test_chat_connection():
    """测试聊天功能连接"""
    try:
        return R.success(msg="聊天功能连接正常")
    except Exception as e:
        return R.error(msg=f"聊天功能连接失败: {str(e)}") 