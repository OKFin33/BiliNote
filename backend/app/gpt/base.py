from abc import ABC,abstractmethod

from typing import List, Dict, Optional
from app.models.gpt_model import GPTSource


class GPT(ABC):
    def summarize(self, source:GPTSource )->str:
        '''

        :param source: 
        :return:
        '''
        pass
    def create_messages(self, segments:list,**kwargs)->list:
        pass
    def list_models(self):
        pass
    
    # 新增聊天相关方法
    def create_chat_session(self, session_id: str, note_content: str) -> str:
        """创建聊天会话"""
        pass
    
    def send_chat_message(self, session_id: str, message: str, note_content: str) -> str:
        """发送聊天消息"""
        pass
    
    def get_chat_history(self, session_id: str) -> List[Dict]:
        """获取聊天历史"""
        pass