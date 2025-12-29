import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  MoreVertical,
  Copy,
  Archive,
  Trash2
} from 'lucide-react';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import CollapsibleSection from './CollapsibleSection';
import EditableTitle from './EditableTitle';
import FollowUpInput from './FollowUpInput';
import ChatInput from './ChatInput';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  onSendMessage,
  onHeaderAction,
  onUpdateTitle,
  isLoading,
}) {
  const [showMenu, setShowMenu] = useState(false);
  const [inputMode, setInputMode] = useState('council'); // 'council' or 'chairman'
  const [isInputManual, setIsInputManual] = useState(false); // Used to show input for follow-up
  const messagesEndRef = useRef(null);
  const menuRef = useRef(null);

  useEffect(() => {
    // Reset manual input state when loading starts
    if (isLoading) {
      setIsInputManual(false);
    }
  }, [isLoading]);

  // Determine if we should show the input
  const isNewConversation = conversation?.messages.length === 0;
  const lastMessage = conversation?.messages[conversation.messages.length - 1];
  const isWaitingForCouncil = lastMessage?.role === 'user' || isLoading;
  
  const showInput = (isNewConversation || isInputManual) && !isLoading;

  const lastMessageIsAssistantLoading = lastMessage?.role === 'assistant' && (
    lastMessage.loading?.stage1 || 
    lastMessage.loading?.stage2 || 
    lastMessage.loading?.stage3
  );

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const handleSendMessage = (content) => {
    onSendMessage(content, inputMode === 'chairman' ? 'chairman' : undefined);
    setIsInputManual(false);
    setInputMode('council');
  };

  const handleMenuAction = (action) => {
    setShowMenu(false);
    onHeaderAction(action, conversation.id);
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to LLM Council</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="title-wrapper" style={{ flex: 1, minWidth: 0, marginRight: 16 }}>
          <EditableTitle 
            title={conversation.title} 
            onSave={(newTitle) => onUpdateTitle(conversation.id, newTitle)} 
          />
        </div>
        <div className="header-actions" ref={menuRef}>          <button 
            className="menu-toggle"
            onClick={() => setShowMenu(!showMenu)}
            title="Conversation Options"
          >
            <MoreVertical size={20} />
          </button>
          {showMenu && (
            <div className="header-menu">
              <button onClick={() => handleMenuAction('duplicate')}>
                <Copy size={16} /> Duplicate
              </button>
              <button onClick={() => handleMenuAction('archive')}>
                <Archive size={16} /> Archive
              </button>
              <button className="danger" onClick={() => handleMenuAction('delete')}>
                <Trash2 size={16} /> Delete
              </button>
            </div>
          )}
        </div>
      </div>
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    <div className="markdown-content">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label">
                    {msg.stage3 && (!msg.stage1 || msg.stage1.length === 0) ? 'Chairman' : 'LLM Council'}
                  </div>

                  {/* Stage 1 */}
                  {msg.loading?.stage1 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 1: Collecting individual responses...</span>
                      {msg.progress?.stage1 && (
                        <span className="stage-progress">
                          ({msg.progress.stage1.completed} of {msg.progress.stage1.total} completed)
                        </span>
                      )}
                    </div>
                  )}
                  {msg.stage1 && msg.stage1.length > 0 && (
                    <CollapsibleSection title="Stage 1: Council Responses" defaultExpanded={false}>
                      <Stage1 responses={msg.stage1} />
                    </CollapsibleSection>
                  )}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 2: Peer rankings...</span>
                      {msg.progress?.stage2 && (
                        <span className="stage-progress">
                          ({msg.progress.stage2.completed} of {msg.progress.stage2.total} completed)
                        </span>
                      )}
                    </div>
                  )}
                  {msg.stage2 && msg.stage2.length > 0 && (
                    <CollapsibleSection title="Stage 2: Peer Review & Rankings" defaultExpanded={false}>
                      <Stage2
                        rankings={msg.stage2}
                        labelToModel={msg.metadata?.label_to_model}
                        aggregateRankings={msg.metadata?.aggregate_rankings}
                      />
                    </CollapsibleSection>
                  )}

                  {/* Stage 3 */}
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Running Stage 3: Final synthesis...</span>
                    </div>
                  )}
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}

                  {/* Follow-up Trigger */}
                  {msg.stage3 && index === conversation.messages.length - 1 && !isLoading && !isInputManual && (
                    <FollowUpInput 
                      onActivate={() => {
                        setInputMode('chairman');
                        setIsInputManual(true);
                      }}
                      isLoading={isLoading}
                    />
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && !lastMessageIsAssistantLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {showInput && (
        <ChatInput 
          onSendMessage={handleSendMessage} 
          isLoading={isLoading}
          onCancel={isInputManual ? () => {
            setIsInputManual(false);
            setInputMode('council');
          } : undefined}
          placeholder={inputMode === 'chairman' ? "Follow up with the Chairman..." : undefined}
          autoFocus={inputMode === 'chairman'}
        />
      )}
    </div>
  );
}
