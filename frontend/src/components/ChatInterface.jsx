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
  const [isFollowUpMode, setIsFollowUpMode] = useState(false);
  const messagesEndRef = useRef(null);
  const menuRef = useRef(null);

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

  useEffect(() => {
    setIsFollowUpMode(false);
  }, [conversation?.id]);

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

  const lastMessage = conversation.messages[conversation.messages.length - 1];
  const canRequestFollowUp = Boolean(
    lastMessage &&
    lastMessage.role === 'assistant' &&
    lastMessage.stage3 &&
    !isLoading
  );
  const shouldShowInput = !isLoading && (isFollowUpMode || conversation.messages.length === 0);

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
                    {msg.files && msg.files.length > 0 && (
                      <div className="message-file-chips">
                        {msg.files.map((file, fileIndex) => (
                          <span key={`${file.name}-${fileIndex}`} className="message-file-chip">
                            {file.name}
                          </span>
                        ))}
                      </div>
                    )}
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

                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting the council...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {canRequestFollowUp && !isFollowUpMode && (
        <div className="follow-up-trigger">
          <button
            className="follow-up-button"
            onClick={() => setIsFollowUpMode(true)}
            disabled={isLoading}
          >
            Send Message to Chairman
          </button>
        </div>
      )}

      {shouldShowInput && (
        <ChatInput
          variant="main"
          layout="inline"
          placeholder={
            isFollowUpMode
              ? "Follow up with the Chairman..."
              : "Ask your question... (Shift+Enter for new line, Enter to send)"
          }
          submitLabel="Send"
          onSend={(content, files) => {
            onSendMessage(content, isFollowUpMode ? 'chairman' : null, files);
            setIsFollowUpMode(false);
          }}
          isLoading={isLoading}
        />
      )}
    </div>
  );
}
