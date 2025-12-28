import { useState } from 'react';
import { Send, MessageSquare } from 'lucide-react';
import './FollowUpInput.css';

export default function FollowUpInput({ onSendFollowUp, isLoading }) {
  const [isInputVisible, setIsInputVisible] = useState(false);
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSendFollowUp(inputValue);
      setInputValue('');
      setIsInputVisible(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!isInputVisible) {
    return (
      <div className="follow-up-trigger">
        <button 
          className="follow-up-button" 
          onClick={() => setIsInputVisible(true)}
          disabled={isLoading}
        >
          <MessageSquare size={16} />
          <span>Send Message to Chairman</span>
        </button>
      </div>
    );
  }

  return (
    <div className="follow-up-container">
      <form className="follow-up-form" onSubmit={handleSubmit}>
        <div className="follow-up-input-wrapper">
          <textarea
            className="follow-up-input"
            placeholder="Follow up with the Chairman..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={2}
            autoFocus
          />
        </div>
        <div className="follow-up-actions">
          <button 
            type="button" 
            className="cancel-button" 
            onClick={() => setIsInputVisible(false)}
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="send-follow-up-button"
            disabled={!inputValue.trim() || isLoading}
          >
            <Send size={16} />
            <span>Send</span>
          </button>
        </div>
      </form>
    </div>
  );
}
