import uuid
from typing import Dict, List, Optional
from app.gpt.gpt_factory import GPTFactory
from app.models.model_config import ModelConfig
from app.services.provider import ProviderService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ChatService:
    """聊天服务，管理聊天会话和消息"""
    
    def __init__(self):
        # 存储GPT实例的缓存
        self.gpt_instances: Dict[str, any] = {}
    
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
    
    def create_chat_session(self, task_id: str, note_content: str, 
                          provider_id: str, model_name: str) -> Dict:
        """创建聊天会话"""
        try:
            # 生成会话ID
            session_id = f"chat_{task_id}_{uuid.uuid4().hex[:8]}"
            
            # 获取GPT实例
            gpt_instance = self._get_gpt_instance(provider_id, model_name)
            
            # 创建会话
            welcome_message = gpt_instance.create_chat_session(session_id, note_content)
            
            return {
                "session_id": session_id,
                "welcome_message": welcome_message,
                "status": "created"
            }
            
        except Exception as e:
            logger.error(f"Failed to create chat session: {e}")
            raise
    
    def send_message(self, session_id: str, message: str, note_content: str,
                    provider_id: str, model_name: str) -> Dict:
        """发送聊天消息"""
        try:
            # 获取GPT实例
            gpt_instance = self._get_gpt_instance(provider_id, model_name)
            
            # 发送消息
            response = gpt_instance.send_chat_message(session_id, message, note_content)
            
            return {
                "session_id": session_id,
                "response": response,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    def get_chat_history(self, session_id: str, provider_id: str, 
                        model_name: str) -> List[Dict]:
        """获取聊天历史"""
        try:
            # 获取GPT实例
            gpt_instance = self._get_gpt_instance(provider_id, model_name)
            
            # 获取历史
            history = gpt_instance.get_chat_history(session_id)
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
            return []
    
    def delete_chat_session(self, session_id: str, provider_id: str, 
                          model_name: str) -> bool:
        """删除聊天会话"""
        try:
            # 获取GPT实例
            gpt_instance = self._get_gpt_instance(provider_id, model_name)
            
            # 从内存中删除会话（实际项目中应该持久化到数据库）
            if hasattr(gpt_instance, 'chat_sessions') and session_id in gpt_instance.chat_sessions:
                del gpt_instance.chat_sessions[session_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete chat session: {e}")
            return False 