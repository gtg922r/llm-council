import { MessageSquare } from 'lucide-react';
import './FollowUpInput.css';

export default function FollowUpInput({ onActivate, isLoading }) {
  return (
    <div className="follow-up-trigger">
      <button 
        className="follow-up-button" 
        onClick={onActivate}
        disabled={isLoading}
      >
        <MessageSquare size={16} />
        <span>Send Message to Chairman</span>
      </button>
    </div>
  );
}
