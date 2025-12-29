import { useState } from 'react';
import { Send, Maximize2, Minimize2 } from 'lucide-react';
import './ChatInput.css';

export default function ChatInput({ 
  onSendMessage, 
  onCancel,
  onFilesDropped,
  isLoading, 
  placeholder = "Ask your question... (Shift+Enter for new line, Enter to send)",
  autoFocus = false
}) {
  const [input, setInput] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

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

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isLoading) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (isLoading) return;

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0 && onFilesDropped) {
      onFilesDropped(files);
    }
  };

  return (
    <div 
      className={`chat-input-container ${isExpanded ? 'expanded' : ''} ${isDragging ? 'dragging' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="drag-overlay">
          <div className="drag-message">Drop files here</div>
        </div>
      )}
      <form className="chat-input-form" onSubmit={handleSubmit} aria-label="Chat Input Form">
        <div className="chat-input-wrapper">
          <textarea
            className="chat-input-textarea"
            placeholder={placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
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
        <div className="chat-input-actions">
          {onCancel && (
            <button
              type="button"
              className="chat-input-cancel-button"
              onClick={onCancel}
              disabled={isLoading}
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            className="chat-input-send-button"
            disabled={!input.trim() || isLoading}
          >
            <Send size={18} />
            <span>Send</span>
          </button>
        </div>
      </form>
    </div>
  );
}
