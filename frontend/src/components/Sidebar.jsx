import { useState } from 'react';
import { 
  Plus, 
  Pin, 
  Archive, 
  Trash2, 
  RefreshCw, 
  ChevronDown, 
  ChevronRight
} from 'lucide-react';
import ThemeToggle from './ThemeToggle';
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
}) {
  const [isArchiveExpanded, setIsArchiveExpanded] = useState(false);

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
        <h1>LLM Council</h1>
        <button className="new-conversation-btn" onClick={onNewConversation}>
          <Plus size={16} /> New Conversation
        </button>
        <div className="sidebar-theme-toggle">
          <ThemeToggle />
        </div>
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
