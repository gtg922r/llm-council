import { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  MoreVertical,
  Copy,
  Archive,
  Trash2,
  Paperclip,
  Menu,
  Plus,
  Pin,
  MessageSquare
} from 'lucide-react';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import CollapsibleSection from './CollapsibleSection';
import EditableTitle from './EditableTitle';
import FollowUpInput from './FollowUpInput';
import ChatInput from './ChatInput';

import './ChatInterface.css';
import SymposiaLogo from '../assets/SymposiaLogo';

export default function ChatInterface({
  conversation,
  conversations = [],
  onSendMessage,
  onHeaderAction,
  onUpdateTitle,
  onNewConversation,
  onSelectConversation,
  isLoading,
  isMobile = false,
  onMenuClick,
}) {
  const [showMenu, setShowMenu] = useState(false);
  const [inputMode, setInputMode] = useState('council'); // 'council' or 'chairman'
  const [isInputManual, setIsInputManual] = useState(false); // Used to show input for follow-up
  const [stagedFiles, setStagedFiles] = useState([]);
  const messagesEndRef = useRef(null);
  const menuRef = useRef(null);
  const shouldScrollOnUpdateRef = useRef(false);

  useEffect(() => {
    // Reset manual input state when loading starts
    if (isLoading) {
      setIsInputManual(false);
    }
  }, [isLoading]);

  // Reset scroll behavior when switching conversations
  useEffect(() => {
    shouldScrollOnUpdateRef.current = false;
  }, [conversation?.id]);

  const handleFilesDropped = (files) => {
    const MAX_SIZE = 1024 * 1024; // 1MB
    const SUPPORTED_EXTENSIONS = [
      'txt', 'md', 'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'json', 'csv', 'c', 'cpp', 'h', 'java', 'go', 'rs', 'php', 'rb', 'sh', 'sql', 'yaml', 'yml'
    ];

    const validFiles = [];
    for (const file of files) {
      const ext = file.name.split('.').pop().toLowerCase();
      
      if (file.size > MAX_SIZE) {
        alert(`File "${file.name}" is too large (> 1MB).`);
        continue;
      }
      
      if (!SUPPORTED_EXTENSIONS.includes(ext)) {
        alert(`File "${file.name}" has an unsupported extension. Please provide text-based files.`);
        continue;
      }

      // Avoid duplicates
      if (!stagedFiles.find(f => f.name === file.name && f.size === file.size)) {
        validFiles.push(file);
      }
    }

    if (validFiles.length > 0) {
      setStagedFiles(prev => [...prev, ...validFiles]);
    }
  };

  const handleRemoveFile = (index) => {
    setStagedFiles(prev => prev.filter((_, i) => i !== index));
  };

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
    // Only scroll to bottom when user sends a message, not when loading a conversation
    if (shouldScrollOnUpdateRef.current) {
      scrollToBottom();
    }
  }, [conversation]);

  const handleSendMessage = useCallback(async (content) => {
    // We pass the raw content and the files separately.
    // The concatenation for the LLM prompt will happen in the API handler.
    shouldScrollOnUpdateRef.current = true; // Enable scroll-to-bottom for new messages
    onSendMessage(content, inputMode === 'chairman' ? 'chairman' : undefined, stagedFiles);
    
    setIsInputManual(false);
    setInputMode('council');
    setStagedFiles([]); // Clear staged files after sending
  }, [stagedFiles, inputMode, onSendMessage]);

  const handleMenuAction = (action) => {
    setShowMenu(false);
    onHeaderAction(action, conversation.id);
  };

  if (!conversation) {
    const pinnedConversations = conversations.filter(c => c.is_pinned && !c.is_archived);
    const recentConversations = conversations
      .filter(c => !c.is_pinned && !c.is_archived)
      .slice(0, 3);

    return (
      <div className="chat-interface">
        {isMobile && (
          <div className="chat-header chat-header-empty">
            <button
              type="button"
              className="hamburger-button"
              onClick={onMenuClick}
              aria-label="Open navigation menu"
            >
              <Menu size={22} />
            </button>
            <span className="empty-header-title">Symposia</span>
          </div>
        )}
        <div className="empty-state">
          <SymposiaLogo size={80} className="empty-state-logo" />
          <h2>Welcome to Symposia</h2>
          <p>Create a new conversation to get started</p>
          
          <button 
            className="empty-state-new-btn" 
            onClick={onNewConversation}
          >
            <Plus size={18} /> New Conversation
          </button>

          {(pinnedConversations.length > 0 || recentConversations.length > 0) && (
            <div className="empty-state-recent">
              <h3>Recent Conversations</h3>
              <div className="recent-list">
                {pinnedConversations.map(conv => (
                  <button 
                    key={conv.id} 
                    className="recent-item pinned"
                    onClick={() => onSelectConversation(conv.id)}
                  >
                    <Pin size={14} fill="currentColor" />
                    <span className="recent-item-title">{conv.title || 'New Conversation'}</span>
                  </button>
                ))}
                {recentConversations.map(conv => (
                  <button 
                    key={conv.id} 
                    className="recent-item"
                    onClick={() => onSelectConversation(conv.id)}
                  >
                    <MessageSquare size={14} />
                    <span className="recent-item-title">{conv.title || 'New Conversation'}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Determine if we should show the input
  const messages = conversation.messages ?? [];
  const isNewConversation = messages.length === 0;
  const lastMessage = messages[messages.length - 1];
  const showInput = (isNewConversation || isInputManual) && !isLoading;

  const lastMessageIsAssistant = lastMessage?.role === 'assistant';
  const lastMessageHasLoadingState = lastMessageIsAssistant && (
    lastMessage.loading?.stage1 || 
    lastMessage.loading?.stage2 || 
    lastMessage.loading?.stage3
  );

  return (
    <div className="chat-interface">
      <div className="chat-header">
        {isMobile && (
          <button
            type="button"
            className="hamburger-button"
            onClick={onMenuClick}
            aria-label="Open navigation menu"
          >
            <Menu size={22} />
          </button>
        )}
        <div className="title-wrapper" style={{ flex: 1, minWidth: 0, marginRight: 16 }}>
          <EditableTitle 
            title={conversation.title} 
            onSave={(newTitle) => onUpdateTitle(conversation.id, newTitle)} 
          />
        </div>
        <div className="header-actions" ref={menuRef}>
          <button 
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
        {messages.length === 0 ? (
          <div className="empty-state">
            <SymposiaLogo size={80} className="empty-state-logo" />
            <h2>Start a conversation</h2>
            <p>Ask a question to consult the AI Council</p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div key={index} className="message-group">
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="message-label">You</div>
                  <div className="message-content">
                    {msg.files && msg.files.length > 0 && (
                      <div className="message-files">
                        {msg.files.map((file, fIndex) => (
                          <div key={fIndex} className="file-chip">
                            <Paperclip size={14} />
                            <span className="file-chip-name">{file.filename || file.name}</span>
                          </div>
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
                    {msg.stage3 && (!msg.stage1 || msg.stage1.length === 0) ? 'Chairman' : 'Symposia'}
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
                  {msg.stage3 && msg.stage3.response && <Stage3 finalResponse={msg.stage3} />}

                  {/* Follow-up Trigger */}
                  {msg.stage3 && msg.stage3.response && index === messages.length - 1 && !isLoading && !isInputManual && (
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

        {isLoading && !lastMessageHasLoadingState && (
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
          onFilesDropped={handleFilesDropped}
          stagedFiles={stagedFiles}
          onRemoveFile={handleRemoveFile}
          onCancel={isInputManual ? () => {
            setIsInputManual(false);
            setInputMode('council');
            setStagedFiles([]);
          } : undefined}
          placeholder={inputMode === 'chairman' ? "Follow up with the Chairman..." : undefined}
          autoFocus={inputMode === 'chairman'}
        />
      )}
    </div>
  );
}
