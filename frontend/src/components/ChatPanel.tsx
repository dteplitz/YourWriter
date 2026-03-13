import { useState, useEffect, useRef } from 'react';
import type { ChatMessage } from '../types';
import * as api from '../api/client';

interface ChatPanelProps {
  writerId: string;
}

export default function ChatPanel({ writerId }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadHistory();
  }, [writerId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const loadHistory = async () => {
    try {
      const history = await api.getChatHistory(writerId);
      setMessages(history);
    } catch {
      // Chat history may not exist yet
      setMessages([]);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      writer_id: writerId,
      role: 'user',
      content: input.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    setStreamingContent('');

    try {
      let accumulated = '';
      const { messageId } = await api.sendMessageStream(
        writerId,
        userMessage.content,
        (token) => {
          accumulated += token;
          setStreamingContent(accumulated);
        },
      );

      // Replace streaming placeholder with the final persisted message
      const finalMessage: ChatMessage = {
        id: messageId,
        writer_id: writerId,
        role: 'assistant',
        content: accumulated,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, finalMessage]);
      setStreamingContent('');
    } catch (err) {
      setStreamingContent('');
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        writer_id: writerId,
        role: 'assistant',
        content: `Error: ${err instanceof Error ? err.message : 'Failed to send message'}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h3>Chat</h3>
      </div>
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            Start a conversation with your writer...
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-message chat-message--${msg.role}`}>
            <div className="chat-message-role">
              {msg.role === 'user' ? 'You' : 'Writer'}
            </div>
            <div className="chat-message-content">{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-message-role">Writer</div>
            <div className="chat-message-content">
              {streamingContent || <span className="chat-typing">Thinking...</span>}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input-area">
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          rows={2}
          disabled={loading}
        />
        <button
          className="btn btn-primary chat-send-btn"
          onClick={handleSend}
          disabled={!input.trim() || loading}
        >
          Send
        </button>
      </div>
    </div>
  );
}
