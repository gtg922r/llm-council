import { useState } from 'react';
import { MessageSquare } from 'lucide-react';
import ChatInput from './ChatInput';
import './FollowUpInput.css';

export default function FollowUpInput({ onSendFollowUp, isLoading }) {
  const [isInputVisible, setIsInputVisible] = useState(false);

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
      <ChatInput
        onSendMessage={(content) => {
          onSendFollowUp(content);
          setIsInputVisible(false);
        }}
        onCancel={() => setIsInputVisible(false)}
        isLoading={isLoading}
        placeholder="Follow up with the Chairman..."
        autoFocus
      />
    </div>
  );
}
