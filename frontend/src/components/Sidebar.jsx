import { useState, useRef, useEffect } from 'react';
import { 
  Plus, 
  Pin, 
  Archive, 
  Trash2, 
  RefreshCw, 
  ChevronDown, 
  ChevronRight,
  Settings
} from 'lucide-react';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onTogglePin,
  onToggleArchive,
  onDeleteConversation,
  onBulkDelete,
  theme,
  onToggleTheme,
}) {
  const [isArchiveExpanded, setIsArchiveExpanded] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const settingsRef = useRef(null);

  useEffect(() => {
    if (!isSettingsOpen) return;
    const handleClickOutside = (event) => {
      if (settingsRef.current && !settingsRef.current.contains(event.target)) {
        setIsSettingsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isSettingsOpen]);

  // Sort conversations: pinned first, then by date (date sorting is already handled by backend)
  const sortedConversations = [...conversations].sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1;
    if (!a.is_pinned && b.is_pinned) return 1;
    return 0;
  });

  const activeConversations = sortedConversations.filter((conv) => !conv.is_archived);
  const archivedConversations = sortedConversations.filter((conv) => conv.is_archived);

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-top">
          <h1>LLM Council</h1>
          <div className="settings-wrapper" ref={settingsRef}>
            <button
              className={`sidebar-settings-btn ${isSettingsOpen ? 'active' : ''}`}
              onClick={() => setIsSettingsOpen((prev) => !prev)}
              aria-haspopup="true"
              aria-expanded={isSettingsOpen}
              aria-label="Open settings"
            >
              <Settings size={16} />
            </button>
            {isSettingsOpen && (
              <div className="settings-popover">
                <div className="settings-row">
                  <span className="settings-label">Dark mode</span>
                  <button
                    className={`theme-toggle ${theme === 'dark' ? 'is-dark' : ''}`}
                    onClick={onToggleTheme}
                    aria-pressed={theme === 'dark'}
                    aria-label="Toggle dark mode"
                  >
                    <span className="toggle-thumb" />
                  </button>
                </div>
                <div className="settings-hint">Uses system theme until toggled.</div>
              </div>
            )}
          </div>
        </div>
        <button className="new-conversation-btn" onClick={onNewConversation}>
          <Plus size={16} /> New Conversation
        </button>
      </div>

      <div className="conversation-list">
        {activeConversations.length === 0 ? (
          <div className="no-conversations">No active conversations</div>
        ) : (
          activeConversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              } ${conv.is_pinned ? 'pinned' : ''}`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-content">
                <div className="conversation-title">
                  {conv.title || 'New Conversation'}
                </div>
                <div className="conversation-meta">
                  {conv.message_count} messages
                </div>
              </div>
              <div className="item-actions">
                <button
                  className="action-btn pin-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onTogglePin(conv.id, !conv.is_pinned);
                  }}
                  title={conv.is_pinned ? 'Unpin' : 'Pin'}
                >
                  <Pin size={14} fill={conv.is_pinned ? "currentColor" : "none"} />
                </button>
                <button
                  className="action-btn archive-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleArchive(conv.id, true);
                  }}
                  title="Archive"
                >
                  <Archive size={14} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {archivedConversations.length > 0 && (
        <div className="archive-section">
          <div 
            className="archive-header"
            onClick={() => setIsArchiveExpanded(!isArchiveExpanded)}
          >
            <div className="archive-title">
              <Archive size={14} />
              <span>Archived ({archivedConversations.length})</span>
            </div>
            {isArchiveExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>
          
          {isArchiveExpanded && (
            <div className="archived-list">
              <div className="bulk-actions">
                <button className="empty-trash-btn" onClick={onBulkDelete}>
                  <Trash2 size={12} /> Empty Trash
                </button>
              </div>
              {archivedConversations.map((conv) => (
                <div
                  key={conv.id}
                  className={`conversation-item archived-item ${
                    conv.id === currentConversationId ? 'active' : ''
                  }`}
                  onClick={() => onSelectConversation(conv.id)}
                >
                  <div className="conversation-content">
                    <div className="conversation-title">{conv.title}</div>
                  </div>
                  <div className="item-actions">
                    <button
                      className="action-btn restore-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleArchive(conv.id, false);
                      }}
                      title="Restore"
                    >
                      <RefreshCw size={14} />
                    </button>
                    <button
                      className="action-btn delete-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteConversation(conv.id);
                      }}
                      title="Delete Forever"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
