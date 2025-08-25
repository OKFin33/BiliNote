import uuid
import json
from typing import Dict, List, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from app.gpt.gpt_factory import GPTFactory
from app.models.model_config import ModelConfig
from app.models.transcriber_model import TranscriptSegment
from app.services.provider import ProviderService
from app.utils.logger import get_logger
from app.db.engine import get_db
from app.db.models.chat_models import ChatSession, ChatMessage

logger = get_logger(__name__)


class ChatService:
    """聊天服务，管理聊天会话和消息"""
    
    def __init__(self):
        # 存储GPT实例的缓存
        self.gpt_instances: Dict[str, any] = {}
    
    def _get_db_session(self) -> Session:
        """获取数据库会话"""
        return next(get_db())
    
    def _get_gpt_instance(self, provider_id: str, model_name: str):
        """获取或创建GPT实例"""
        cache_key = f"{provider_id}_{model_name}"
        
        if cache_key not in self.gpt_instances:
            # 获取提供商信息
            provider = ProviderService.get_provider_by_id(provider_id)
            if not provider:
                raise ValueError(f"Provider not found: {provider_id}")
            
            # 创建模型配置
            config = ModelConfig(
                api_key=provider["api_key"],
                base_url=provider["base_url"],
                model_name=model_name,
                provider=provider["type"],
                name=provider["name"],
            )
            
            # 创建GPT实例
            gpt_instance = GPTFactory().from_config(config)
            self.gpt_instances[cache_key] = gpt_instance
        
        return self.gpt_instances[cache_key]
    
    def get_or_create_session(self, task_id: str, note_content: str, 
                            provider_id: str, model_name: str) -> Dict:
        """获取或创建聊天会话，支持转写数据"""
        try:
            db = self._get_db_session()
            
            # 获取转写数据
            segments = self._get_task_transcript(task_id)
            
            # 查找现有会话
            existing_session = db.query(ChatSession).filter(
                ChatSession.task_id == task_id,
                ChatSession.provider_id == provider_id,
                ChatSession.model_name == model_name
            ).first()
            
            if existing_session:
                # 如果会话存在，返回现有会话
                session_id = existing_session.id
                # 获取欢迎消息（第一条助手消息）
                welcome_message = db.query(ChatMessage).filter(
                    ChatMessage.session_id == session_id,
                    ChatMessage.role == 'assistant'
                ).order_by(ChatMessage.created_at.asc()).first()
                
                return {
                    "session_id": session_id,
                    "welcome_message": welcome_message.content if welcome_message else "欢迎回来！",
                    "status": "existing"
                }
            else:
                # 创建新会话
                session_id = f"chat_{task_id}_{uuid.uuid4().hex[:8]}"
                
                # 创建数据库会话记录
                new_session = ChatSession(
                    id=session_id,
                    task_id=task_id,
                    provider_id=provider_id,
                    model_name=model_name,
                    note_content=note_content
                )
                db.add(new_session)
                
                # 获取GPT实例并创建会话
                gpt_instance = self._get_gpt_instance(provider_id, model_name)
                welcome_message = gpt_instance.create_chat_session(session_id, note_content, segments)
                
                # 保存欢迎消息到数据库
                welcome_msg = ChatMessage(
                    session_id=session_id,
                    role='assistant',
                    content=welcome_message
                )
                db.add(welcome_msg)
                
                db.commit()
                
                return {
                    "session_id": session_id,
                    "welcome_message": welcome_message,
                    "status": "created"
                }
                
        except Exception as e:
            logger.error(f"Failed to get or create chat session: {e}")
            raise
        finally:
            db.close()
    
    def create_chat_session(self, task_id: str, note_content: str, 
                          provider_id: str, model_name: str) -> Dict:
        """创建聊天会话（保持向后兼容）"""
        return self.get_or_create_session(task_id, note_content, provider_id, model_name)
    
    def send_message(self, session_id: str, message: str, note_content: str,
                    provider_id: str, model_name: str, task_id: str = None) -> Dict:
        """发送聊天消息，支持转写数据"""
        try:
            db = self._get_db_session()
            
            # 获取转写数据
            segments = None
            if task_id:
                segments = self._get_task_transcript(task_id)
            
            # 保存用户消息到数据库
            user_msg = ChatMessage(
                session_id=session_id,
                role='user',
                content=message
            )
            db.add(user_msg)
            
            # 获取GPT实例
            gpt_instance = self._get_gpt_instance(provider_id, model_name)
            
            # 发送消息
            response = gpt_instance.send_chat_message(session_id, message, note_content, segments)
            
            # 保存AI回复到数据库
            assistant_msg = ChatMessage(
                session_id=session_id,
                role='assistant',
                content=response
            )
            db.add(assistant_msg)
            
            db.commit()
            
            return {
                "session_id": session_id,
                "response": response,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
        finally:
            db.close()
    
    def get_chat_history(self, session_id: str, provider_id: str, 
                        model_name: str) -> List[Dict]:
        """获取聊天历史"""
        try:
            db = self._get_db_session()
            
            # 从数据库获取聊天历史
            messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at.asc()).all()
            
            history = []
            for msg in messages:
                history.append({
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
            return []
        finally:
            db.close()
    
    def delete_chat_session(self, session_id: str, provider_id: str, 
                          model_name: str) -> bool:
        """删除聊天会话"""
        try:
            db = self._get_db_session()
            
            # 删除会话及其所有消息
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                db.delete(session)
                db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete chat session: {e}")
            return False
        finally:
            db.close() 

    def _get_task_transcript(self, task_id: str) -> Optional[List[TranscriptSegment]]:
        """获取任务的转写数据"""
        try:
            # 从缓存文件读取转写数据
            transcript_cache_file = Path(f"note_results/{task_id}_transcript.json")
            if transcript_cache_file.exists():
                data = json.loads(transcript_cache_file.read_text(encoding="utf-8"))
                segments = [TranscriptSegment(**seg) for seg in data.get("segments", [])]
                return segments
            return None
        except Exception as e:
            logger.error(f"Failed to get transcript for task {task_id}: {e}")
            return None 