import React, { useState, useRef, useEffect } from 'react';
import { getApiUrl } from '../utils/config';

type Message = { sender: 'user' | 'assistant' | 'system', text: string };

const STORAGE_KEY = 'smartvenue_chat_history';

const DEFAULT_WELCOME: Message = { 
  sender: 'system', 
  text: "👋 Hi, I'm the Venue AI. Ask me about wait times or the fastest route to your gate!" 
};

export const ChatWidget: React.FC<{ sessionToken: string }> = ({ sessionToken }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed.length > 0 ? parsed : [DEFAULT_WELCOME];
      } catch (e) {
        return [DEFAULT_WELCOME];
      }
    }
    return [DEFAULT_WELCOME];
  });
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
    // Persist to local storage
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages, isTyping]);

  const toggleChat = () => setIsOpen(!isOpen);

  const clearHistory = () => {
    if (confirm('Clear chat history?')) {
      setMessages([DEFAULT_WELCOME]);
      localStorage.removeItem(STORAGE_KEY);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setInput('');
    setIsTyping(true);

    try {
      const res = await fetch(`${getApiUrl()}/api/chat`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ message: userMsg, session_id: 'session-react-1' }) // The backend handles context scaling
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, { sender: 'assistant', text: data.reply }]);
      } else {
        const errData = await res.json();
        setMessages(prev => [...prev, { sender: 'system', text: `Error: ${errData.detail || 'Backend error'}`}]);
      }
    } catch {
      setMessages(prev => [...prev, { sender: 'system', text: 'Server is offline.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <>
      <button 
        id="chat-btn" 
        aria-label="Open venue assistant chat" 
        aria-haspopup="dialog" 
        aria-expanded={isOpen}
        onClick={toggleChat}
      >
        💬
      </button>

      <div id="chat-panel" className={isOpen ? 'open' : ''} role="dialog" aria-modal="true" aria-labelledby="chat-heading" aria-hidden={!isOpen}>
        <div className="chat-head">
          <span id="chat-heading">🏟 Venue Assistant</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button id="chat-clear" aria-label="Clear chat memory" onClick={clearHistory} title="Clear Memory">🗑️</button>
            <button id="chat-close" aria-label="Close chat" onClick={toggleChat}>✕</button>
          </div>
        </div>
        
        <div id="chat-messages" aria-live="polite" aria-label="Chat conversation">
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.sender}`}>
              {m.text}
            </div>
          ))}
          {isTyping && <div className="msg typing assistant">Assistant is thinking...</div>}
          <div ref={messagesEndRef} />
        </div>
        
        <form id="chat-form" role="form" aria-label="Send a message" onSubmit={sendMessage}>
          <label htmlFor="chat-input" className="sr-only" style={{ position: 'absolute', clip: 'rect(0,0,0,0)' }}>Message</label>
          <input
            id="chat-input"
            type="text"
            placeholder="Ask: Which gate is fastest?"
            maxLength={500}
            autoComplete="off"
            aria-label="Type your question"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button id="chat-send" type="submit" aria-label="Send message" disabled={!input || isTyping}>
            Send
          </button>
        </form>
      </div>
    </>
  );
};
