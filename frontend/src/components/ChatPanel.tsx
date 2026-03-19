import { useState, useEffect, useRef } from 'react';
import type { ChatMessage, EvolutionDetectedEvent } from '../types';
import * as api from '../api/client';

interface ChatPanelProps {
  writerId: string;
  onEnterStudio?: () => void;
  onEvolution?: (event: EvolutionDetectedEvent) => void;
}

export default function ChatPanel({ writerId, onEnterStudio, onEvolution }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [currentPhase, setCurrentPhase] = useState<string | null>(null);
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
    setCurrentPhase(null);

    try {
      let accumulated = '';
      // sendMessageStream keeps the SSE open after `done` waiting for evolution_detected.
      // onDone re-enables the UI immediately when `done` arrives — before evolution completes.
      await api.sendMessageStream(
        writerId,
        userMessage.content,
        (token) => {
          accumulated += token;
          setStreamingContent(accumulated);
          setCurrentPhase(null);
        },
        (phase) => {
          setCurrentPhase(phase);
        },
        onEvolution,
        (messageId) => {
          setLoading(false);
          setCurrentPhase(null);
          setMessages((prev) => [...prev, {
            id: messageId,
            writer_id: writerId,
            role: 'assistant',
            content: accumulated,
            created_at: new Date().toISOString(),
          }]);
          setStreamingContent('');
        },
      );
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
      setCurrentPhase(null);
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
        {onEnterStudio && (
          <button
            className="btn btn-primary studio-enter-btn"
            onClick={onEnterStudio}
          >
            Studio →
          </button>
        )}
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
              {streamingContent || (
                <span className="chat-typing">
                  {currentPhase === 'outlining' && 'Planning the outline...'}
                  {currentPhase === 'drafting' && 'Writing the first draft...'}
                  {currentPhase === 'refining' && 'Polishing the final version...'}
                  {!currentPhase && 'Thinking...'}
                </span>
              )}
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
