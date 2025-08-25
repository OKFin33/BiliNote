import React, { useState, useEffect, useRef } from 'react'
import { chatService, ChatMessage, CreateSessionRequest } from '@/services/chat'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Send, MessageCircle, Loader2, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'

interface ChatContainerProps {
  taskId: string
  noteContent: string
  providerId: string
  modelName: string
  onClose?: () => void
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  taskId,
  noteContent,
  providerId,
  modelName,
  onClose
}) => {
  const [sessionId, setSessionId] = useState<string>('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isInitializing, setIsInitializing] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 初始化聊天会话
  useEffect(() => {
    const initializeChat = async () => {
      try {
        setIsInitializing(true)
        const request: CreateSessionRequest = {
          task_id: taskId,
          note_content: noteContent,
          provider_id: providerId,
          model_name: modelName
        }

        const session = await chatService.createSession(request)
        setSessionId(session.session_id)
        
        if (session.status === 'existing') {
          // 如果是现有会话，加载历史记录
          const history = await chatService.getChatHistory(session.session_id, providerId, modelName)
          if (history.length > 0) {
            setMessages(history)
            toast.success('聊天记录已加载')
          } else {
            // 如果没有历史记录，添加欢迎消息
            setMessages([{
              role: 'assistant',
              content: session.welcome_message
            }])
          }
        } else {
          // 新会话，添加欢迎消息
          setMessages([{
            role: 'assistant',
            content: session.welcome_message
          }])
          toast.success('聊天会话已创建')
        }
      } catch (error) {
        console.error('Failed to initialize chat:', error)
        toast.error('聊天会话加载失败')
      } finally {
        setIsInitializing(false)
      }
    }

    initializeChat()
  }, []) // 移除所有依赖项，只在组件挂载时执行一次

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !sessionId || isLoading) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputMessage
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      const response = await chatService.sendMessage({
        session_id: sessionId,
        message: inputMessage,
        note_content: noteContent,
        provider_id: providerId,
        model_name: modelName,
        task_id: taskId
      })

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Failed to send message:', error)
      toast.error('消息发送失败')
      
      // 移除用户消息（因为发送失败）
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteMessage = (index: number) => {
    // 不能删除欢迎消息（第一条消息）
    if (index === 0) {
      toast.error('不能删除欢迎消息')
      return
    }
    
    // 删除消息及其对应的回复
    const newMessages = [...messages]
    if (newMessages[index].role === 'user') {
      // 删除用户消息和对应的AI回复
      newMessages.splice(index, 2)
    } else {
      // 删除AI消息
      newMessages.splice(index, 1)
    }
    
    setMessages(newMessages)
    toast.success('消息已删除')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  if (isInitializing) {
    return (
      <Card className="w-full h-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5" />
            与AI讨论笔记（支持原文引用）
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-full">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            正在初始化聊天...
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full h-full flex flex-col">
      <CardHeader className="flex-shrink-0">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5" />
            与AI讨论笔记（支持原文引用）
          </div>
          {onClose && (
            <Button variant="ghost" size="sm" onClick={onClose}>
              关闭
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      
      <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
        <ScrollArea className="flex-1 h-full px-4 overflow-y-auto">
          <div className="space-y-4 py-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`group flex items-start gap-2 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`relative max-w-[80%] rounded-lg px-4 py-2 ${
                    message.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {/* 删除按钮 - 只在非欢迎消息时显示，悬停时显示 */}
                  {index > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteMessage(index)}
                      className="absolute -top-2 -left-2 h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity bg-white border border-gray-200 shadow-sm hover:bg-red-50"
                      title="删除消息"
                    >
                      <Trash2 className="h-3 w-3 text-gray-400 hover:text-red-500" />
                    </Button>
                  )}
                  
                  <div className="whitespace-pre-wrap">{message.content}</div>
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg px-4 py-2">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    AI正在思考...
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
        
        <div className="flex-shrink-0 p-4 border-t">
          <div className="flex gap-2">
            <Input
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="向AI提问关于笔记的问题（支持原文引用）..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={isLoading || !inputMessage.trim()}
              size="icon"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
} 