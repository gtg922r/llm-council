import { useState } from 'react';
import { Send, Maximize2, Minimize2 } from 'lucide-react';
import './ChatInput.css';

export default function ChatInput({ 
  onSendMessage, 
  isLoading, 
  placeholder = "Ask your question... (Shift+Enter for new line, Enter to send)",
  autoFocus = false
}) {
  const [input, setInput] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className={`chat-input-container ${isExpanded ? 'expanded' : ''}`}>
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <div className="chat-input-wrapper">
          <textarea
            className="chat-input-textarea"
            placeholder={placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={isExpanded ? 10 : 3}
            autoFocus={autoFocus}
          />
          <button
            type="button"
            className="chat-input-expand-button"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>
        </div>
        <button
          type="submit"
          className="chat-input-send-button"
          disabled={!input.trim() || isLoading}
        >
          <Send size={18} />
          <span>Send</span>
        </button>
      </form>
    </div>
  );
}
