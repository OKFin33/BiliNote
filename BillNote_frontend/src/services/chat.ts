import request from '@/utils/request'

export interface ChatSession {
  session_id: string
  welcome_message: string
  status: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface SendMessageRequest {
  session_id: string
  message: string
  note_content: string
  provider_id: string
  model_name: string
  task_id?: string
}

export interface CreateSessionRequest {
  task_id: string
  note_content: string
  provider_id: string
  model_name: string
}

export const chatService = {
  /**
   * 创建聊天会话
   */
  async createSession(data: CreateSessionRequest): Promise<ChatSession> {
    try {
      const response = await request.post('/chat/sessions', data)
      return response
    } catch (error) {
      console.error('Failed to create chat session:', error)
      throw error
    }
  },

  /**
   * 发送聊天消息
   */
  async sendMessage(data: SendMessageRequest): Promise<{ response: string; session_id: string }> {
    try {
      const response = await request.post('/chat/messages', data)
      return response
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    }
  },

  /**
   * 获取聊天历史
   */
  async getChatHistory(sessionId: string, providerId: string, modelName: string): Promise<ChatMessage[]> {
    try {
      const response = await request.get(`/chat/sessions/${sessionId}/history`, {
        params: {
          provider_id: providerId,
          model_name: modelName
        }
      })
      return response.history || []
    } catch (error) {
      console.error('Failed to get chat history:', error)
      return []
    }
  },

  /**
   * 删除聊天会话
   */
  async deleteSession(sessionId: string, providerId: string, modelName: string): Promise<boolean> {
    try {
      await request.delete(`/chat/sessions/${sessionId}`, {
        params: {
          provider_id: providerId,
          model_name: modelName
        }
      })
      return true
    } catch (error) {
      console.error('Failed to delete chat session:', error)
      return false
    }
  },

  /**
   * 测试聊天连接
   */
  async testConnection(): Promise<boolean> {
    try {
      await request.get('/chat/test')
      return true
    } catch (error) {
      console.error('Chat connection test failed:', error)
      return false
    }
  }
} 