import { useState, useEffect, useCallback, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import { api } from './api';
import { ThemeProvider } from './context/ThemeContext';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [loadingConversationId, setLoadingConversationId] = useState(null);
  const [pendingConversationIds, setPendingConversationIds] = useState(() => new Set());
  const currentConversationIdRef = useRef(null);

  const loadConversations = useCallback(async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }, []);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load conversation details when selected
  useEffect(() => {
    currentConversationIdRef.current = currentConversationId;
    if (currentConversationId) {
      let isActive = true;
      api.getConversation(currentConversationId)
        .then((conv) => {
          if (isActive) {
            setCurrentConversation(conv);
          }
        })
        .catch((error) => {
          if (isActive) {
            console.error('Failed to load conversation:', error);
          }
        });
      return () => {
        isActive = false;
      };
    }
  }, [currentConversationId]);

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations((prev) => ([
        {
          id: newConv.id,
          created_at: newConv.created_at,
          title: newConv.title,
          is_pinned: newConv.is_pinned,
          is_archived: newConv.is_archived,
          message_count: newConv.messages?.length ?? 0,
        },
        ...prev,
      ]));
      setCurrentConversation(newConv);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = async (id) => {
    setCurrentConversation(null);
    setCurrentConversationId(id);
    try {
      await api.markAsRead(id);
      loadConversations();
    } catch (error) {
      console.error('Failed to mark conversation as read:', error);
    }
  };

  const handleTogglePin = async (id, isPinned) => {
    try {
      await api.updateConversation(id, { is_pinned: isPinned });
      loadConversations();
    } catch (error) {
      console.error('Failed to toggle pin:', error);
    }
  };

  const handleToggleArchive = async (id, isArchived) => {
    try {
      await api.updateConversation(id, { is_archived: isArchived });
      loadConversations();
      if (isArchived && currentConversationId === id) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
      }
    } catch (error) {
      console.error('Failed to toggle archive:', error);
    }
  };

  const handleDeleteConversation = async (id) => {
    if (!window.confirm('Are you sure you want to delete this conversation forever?')) return;
    try {
      await api.deleteConversation(id);
      loadConversations();
      if (currentConversationId === id) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const handleBulkDelete = async () => {
    const archived = conversations.filter(c => c.is_archived);
    if (archived.length === 0) return;
    if (!window.confirm(`Are you sure you want to delete all ${archived.length} archived conversations?`)) return;
    
    try {
      await Promise.all(archived.map(c => api.deleteConversation(c.id)));
      loadConversations();
    } catch (error) {
      console.error('Failed bulk delete:', error);
    }
  };

  const handleDuplicateConversation = async (id) => {
    try {
      const newConv = await api.duplicateConversation(id);
      await loadConversations();
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to duplicate conversation:', error);
    }
  };

  const handleHeaderAction = async (action, id) => {
    switch (action) {
      case 'duplicate':
        await handleDuplicateConversation(id);
        break;
      case 'archive':
        await handleToggleArchive(id, true);
        break;
      case 'delete':
        await handleDeleteConversation(id);
        break;
      default:
        console.warn('Unknown header action:', action);
    }
  };

  const handleUpdateTitle = async (id, newTitle) => {
    try {
      await api.updateConversation(id, { title: newTitle });
      // Update local state immediately for responsiveness
      if (currentConversation && currentConversation.id === id) {
        setCurrentConversation(prev => ({ ...prev, title: newTitle }));
      }
      loadConversations();
    } catch (error) {
      console.error('Failed to update title:', error);
    }
  };

  const refreshConversationUnreadState = useCallback(async (conversationId) => {
    if (conversationId === currentConversationIdRef.current) {
      try {
        await api.markAsRead(conversationId);
      } catch (error) {
        console.error('Failed to clear unread status:', error);
      }
    }
    loadConversations();
  }, [loadConversations]);

  const readFileContent = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = (e) => reject(e);
      reader.readAsText(file);
    });
  };

  const handleSendMessage = async (content, targetModel = null, files = []) => {
    if (!currentConversationId) return;

    const conversationId = currentConversationId;
    setPendingConversationIds((prev) => {
      const next = new Set(prev);
      next.add(conversationId);
      return next;
    });
    setLoadingConversationId(conversationId);
    try {
      // Optimistically add user message to UI (original content + file metadata)
      const fileMetadata = files.map(f => ({ name: f.name, size: f.size }));
      const userMessage = { role: 'user', content, files: fileMetadata };
      setCurrentConversation((prev) => {
        if (!prev || prev.id !== conversationId) return prev;
        return { ...prev, messages: [...prev.messages, userMessage] };
      });

      // Create and add a partial assistant message immediately
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        progress: {
          stage1: null,
          stage2: null,
        },
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
        },
      };

      setCurrentConversation((prev) => {
        if (!prev || prev.id !== conversationId) return prev;
        return { ...prev, messages: [...prev.messages, assistantMessage] };
      });

      const filesForRequest = await Promise.all(
        files.map(async (file) => ({
          name: file.name,
          content: await readFileContent(file),
          size: file.size,
        }))
      );

      // For follow-ups, we currently use the non-streaming endpoint as simple fallback
      if (targetModel === 'chairman') {
        try {
          const response = await api.sendMessage(
            currentConversationId,
            content,
            filesForRequest,
            'chairman'
          );
          setCurrentConversation((prev) => {
            if (!prev || prev.id !== conversationId) return prev;
            const messages = [...prev.messages];
            const lastMsg = messages[messages.length - 1];
            lastMsg.stage1 = response.stage1;
            lastMsg.stage2 = response.stage2;
            lastMsg.stage3 = response.stage3;
            lastMsg.metadata = response.metadata;
            lastMsg.loading = { stage1: false, stage2: false, stage3: false };
            return { ...prev, messages };
          });
          setLoadingConversationId((prev) => (prev === conversationId ? null : prev));
          await refreshConversationUnreadState(conversationId);
          setPendingConversationIds((prev) => {
            const next = new Set(prev);
            next.delete(conversationId);
            return next;
          });
          return;
        } catch (error) {
          console.error('Follow-up failed:', error);
          throw error;
        }
      }

      // Send message with streaming (Default Council flow)
      await api.sendMessageStream(currentConversationId, content, filesForRequest, (eventType, event) => {
        switch (eventType) {
          case 'stage_started': {
            const stage = event.stage;
            if (stage === 'stage1' || stage === 'stage2') {
              setCurrentConversation((prev) => {
                if (!prev || prev.id !== conversationId) return prev;
                const messages = [...prev.messages];
                const lastMsgIndex = messages.length - 1;
                messages[lastMsgIndex] = {
                  ...messages[lastMsgIndex],
                  loading: { ...messages[lastMsgIndex].loading, [stage]: true },
                  progress: {
                    ...messages[lastMsgIndex].progress,
                    [stage]: { completed: 0, total: event.total ?? 0 }
                  }
                };
                return { ...prev, messages };
              });
            } else if (stage === 'stage3') {
              setCurrentConversation((prev) => {
                if (!prev || prev.id !== conversationId) return prev;
                const messages = [...prev.messages];
                const lastMsgIndex = messages.length - 1;
                messages[lastMsgIndex] = {
                  ...messages[lastMsgIndex],
                  loading: { ...messages[lastMsgIndex].loading, stage3: true }
                };
                return { ...prev, messages };
              });
            }
            break;
          }

          case 'stage_progress': {
            const stage = event.stage;
            if (stage !== 'stage1' && stage !== 'stage2') break;
            setCurrentConversation((prev) => {
              if (!prev || prev.id !== conversationId) return prev;
              const messages = [...prev.messages];
              const lastMsgIndex = messages.length - 1;
              const current = messages[lastMsgIndex];
              messages[lastMsgIndex] = {
                ...current,
                progress: {
                  ...current.progress,
                  [stage]: {
                    completed: event.completed ?? current.progress?.[stage]?.completed ?? 0,
                    total: event.total ?? current.progress?.[stage]?.total ?? 0,
                  }
                }
              };
              return { ...prev, messages };
            });
            break;
          }

          case 'stage_completed': {
            const stage = event.stage;
            setCurrentConversation((prev) => {
              if (!prev || prev.id !== conversationId) return prev;
              const messages = [...prev.messages];
              const lastMsgIndex = messages.length - 1;

              if (stage === 'stage1') {
                messages[lastMsgIndex] = {
                  ...messages[lastMsgIndex],
                  stage1: event.data,
                  loading: { ...messages[lastMsgIndex].loading, stage1: false },
                  progress: { ...messages[lastMsgIndex].progress, stage1: null }
                };
              } else if (stage === 'stage2') {
                messages[lastMsgIndex] = {
                  ...messages[lastMsgIndex],
                  stage2: event.data,
                  metadata: event.metadata,
                  loading: { ...messages[lastMsgIndex].loading, stage2: false },
                  progress: { ...messages[lastMsgIndex].progress, stage2: null }
                };
              } else if (stage === 'stage3') {
                messages[lastMsgIndex] = {
                  ...messages[lastMsgIndex],
                  stage3: event.data,
                  loading: { ...messages[lastMsgIndex].loading, stage3: false }
                };
              }

              return { ...prev, messages };
            });
            break;
          }

          case 'title_updated':
            setCurrentConversation((prev) => {
              if (!prev || prev.id !== conversationId) return prev;
              return { ...prev, title: event.title };
            });
            loadConversations();
            break;

          case 'run_completed':
            refreshConversationUnreadState(conversationId);
            setLoadingConversationId((prev) => (prev === conversationId ? null : prev));
            setPendingConversationIds((prev) => {
              const next = new Set(prev);
              next.delete(conversationId);
              return next;
            });
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setLoadingConversationId((prev) => (prev === conversationId ? null : prev));
            setPendingConversationIds((prev) => {
              const next = new Set(prev);
              next.delete(conversationId);
              return next;
            });
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      });
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic messages on error
      setCurrentConversation((prev) => {
        if (!prev || prev.id !== conversationId) return prev;
        return { ...prev, messages: prev.messages.slice(0, -2) };
      });
      setLoadingConversationId((prev) => (prev === conversationId ? null : prev));
      setPendingConversationIds((prev) => {
        const next = new Set(prev);
        next.delete(conversationId);
        return next;
      });
    }
  };

  const isLoading = loadingConversationId === currentConversationId;

  return (
    <ThemeProvider>
      <div className="app">
        <Sidebar
          conversations={conversations}
          currentConversationId={currentConversationId}
          pendingConversationIds={pendingConversationIds}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onTogglePin={handleTogglePin}
          onToggleArchive={handleToggleArchive}
          onDeleteConversation={handleDeleteConversation}
          onBulkDelete={handleBulkDelete}
        />
        <ChatInterface
          conversation={currentConversation}
          onSendMessage={handleSendMessage}
          onHeaderAction={handleHeaderAction}
          onUpdateTitle={handleUpdateTitle}
          isLoading={isLoading}
        />
      </div>
    </ThemeProvider>
  );
}

export default App;
