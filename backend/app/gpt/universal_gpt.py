from app.gpt.base import GPT
from app.gpt.prompt_builder import generate_base_prompt
from app.models.gpt_model import GPTSource
from app.gpt.prompt import BASE_PROMPT, AI_SUM, SCREENSHOT, LINK
from app.gpt.utils import fix_markdown
from app.models.transcriber_model import TranscriptSegment
from datetime import timedelta
from typing import List, Dict
import uuid


class UniversalGPT(GPT):
    def __init__(self, client, model: str, temperature: float = 0.7):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.screenshot = False
        self.link = False
        # 聊天会话存储（实际项目中应该使用数据库）
        self.chat_sessions = {}

    def _format_time(self, seconds: float) -> str:
        return str(timedelta(seconds=int(seconds)))[2:]

    def _build_segment_text(self, segments: List[TranscriptSegment]) -> str:
        return "\n".join(
            f"{self._format_time(seg.start)} - {seg.text.strip()}"
            for seg in segments
        )

    def ensure_segments_type(self, segments) -> List[TranscriptSegment]:
        return [TranscriptSegment(**seg) if isinstance(seg, dict) else seg for seg in segments]

    def create_messages(self, segments: List[TranscriptSegment], **kwargs):

        content_text = generate_base_prompt(
            title=kwargs.get('title'),
            segment_text=self._build_segment_text(segments),
            tags=kwargs.get('tags'),
            _format=kwargs.get('_format'),
            style=kwargs.get('style'),
            extras=kwargs.get('extras'),
        )

        # ⛳ 组装 content 数组，支持 text + image_url 混合
        content = [{"type": "text", "text": content_text}]
        video_img_urls = kwargs.get('video_img_urls', [])

        for url in video_img_urls:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": url,
                    "detail": "auto"
                }
            })

        #  正确格式：整体包在一个 message 里，role + content array
        messages = [{
            "role": "user",
            "content": content
        }]

        return messages

    def list_models(self):
        return self.client.models.list()

    def summarize(self, source: GPTSource) -> str:
        self.screenshot = source.screenshot
        self.link = source.link
        source.segment = self.ensure_segments_type(source.segment)

        messages = self.create_messages(
            source.segment,
            title=source.title,
            tags=source.tags,
            video_img_urls=source.video_img_urls,
            _format=source._format,
            style=source.style,
            extras=source.extras
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    # 实现聊天功能
    def create_chat_session(self, session_id: str, note_content: str, segments: List[TranscriptSegment] = None) -> str:
        """创建聊天会话，支持智能原文引用"""
        
        # 构建增强的system prompt
        system_prompt = self._build_enhanced_system_prompt(note_content, segments)
        
        system_message = {
            "role": "system",
            "content": system_prompt
        }
        
        # 初始化会话
        self.chat_sessions[session_id] = [system_message]
        
        # 如果有原文数据，添加到会话中
        if segments:
            transcript_text = self._build_segment_text(segments)
            self.chat_sessions[session_id].append({
                "role": "system",
                "content": f"完整转写原文：\n{transcript_text}"
            })
        
        # 发送欢迎消息
        welcome_message = {
            "role": "user",
            "content": "你好，我想和你讨论这个笔记的内容。"
        }
        
        response = self._send_chat_message_internal(session_id, welcome_message)
        return response

    def _build_enhanced_system_prompt(self, note_content: str, segments: List[TranscriptSegment] = None) -> str:
        """构建增强的system prompt"""
        
        base_prompt = f"""你是一个专业的视频笔记助手。用户正在查看以下笔记内容：

{note_content}

请基于这个笔记内容回答用户的问题，提供深入的分析和解释。
回答要准确、有用，并保持对话的自然性。
请用中文回答。"""

        if segments:
            base_prompt += f"""

**智能原文引用功能**

你还可以访问完整的视频转写原文，包含详细的时间戳和内容。请遵循以下原则：

**主要原则：**
1. **以笔记为主**：优先基于笔记内容回答问题，笔记是经过总结和提炼的核心信息
2. **必要时引用原文**：当用户需要详细信息、具体内容、准确引用或时间定位时，才引用原文
3. **智能判断**：根据用户问题的具体需求，决定是否需要补充原文信息

**引用场景：**
- 用户询问"具体说了什么"、"详细内容"、"原文"等
- 用户需要时间定位或精确引用
- 用户询问"为什么"、"如何"等需要深入分析的问题
- 笔记内容不够详细，需要补充原文信息

**引用格式：**
引用原文时使用以下格式：
📝 **原文引用 [时间戳]**: 具体内容

**示例：**
📝 **原文引用 [02:15]**: 这里提到了具体的概念...
📝 **原文引用 [05:30]**: 关于这个问题的详细解释...

请根据用户问题的具体需求，智能判断是否需要引用原文来提供更准确和详细的回答。"""

        return base_prompt

    def _build_segment_text(self, segments: List[TranscriptSegment]) -> str:
        """构建转写文本"""
        if not segments:
            return ""
        
        text_parts = []
        for segment in segments:
            # 将秒转换为 mm:ss 格式
            start_time = self._format_time(segment.start)
            end_time = self._format_time(segment.end)
            text_parts.append(f"[{start_time}-{end_time}] {segment.text}")
        
        return "\n".join(text_parts)

    def _format_time(self, seconds: float) -> str:
        """将秒转换为 mm:ss 格式"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def send_chat_message(self, session_id: str, message: str, note_content: str, segments: List[TranscriptSegment] = None) -> str:
        """发送聊天消息，支持智能原文引用"""
        if session_id not in self.chat_sessions:
            # 如果会话不存在，先创建
            self.create_chat_session(session_id, note_content, segments)
        
        user_message = {
            "role": "user",
            "content": message
        }
        
        return self._send_chat_message_internal(session_id, user_message)

    def _send_chat_message_internal(self, session_id: str, user_message: Dict) -> str:
        """内部方法：发送聊天消息"""
        # 添加用户消息到历史
        self.chat_sessions[session_id].append(user_message)
        
        # 调用API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.chat_sessions[session_id],
            temperature=self.temperature
        )
        
        # 获取AI回复
        assistant_message = {
            "role": "assistant",
            "content": response.choices[0].message.content
        }
        
        # 添加AI回复到历史
        self.chat_sessions[session_id].append(assistant_message)
        
        return assistant_message["content"]

    def get_chat_history(self, session_id: str) -> List[Dict]:
        """获取聊天历史"""
        if session_id not in self.chat_sessions:
            return []
        
        # 返回除系统消息外的所有消息
        return self.chat_sessions[session_id][1:]  # 跳过系统消息
