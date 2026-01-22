import { useState, useEffect, useCallback, useRef } from 'react';
import { useIsMobile } from './hooks/useMediaQuery';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import DeleteConfirmationModal from './components/DeleteConfirmationModal';
import LoginScreen from './components/LoginScreen';
import UserMenu from './components/UserMenu';
import { api } from './api';
import { SettingsProvider, useSettings } from './context/SettingsContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import './App.css';

function AppContent() {
  const { mode: modelMode } = useSettings();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [loadingConversationId, setLoadingConversationId] = useState(null);
  const [pendingConversationIds, setPendingConversationIds] = useState(() => new Set());
  const [deleteModalConfig, setDeleteModalConfig] = useState({ 
    isOpen: false, 
    type: null, // 'single' or 'bulk'
    id: null 
  });
  const currentConversationIdRef = useRef(null);

  // Mobile responsive state
  const isMobile = useIsMobile(768);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Close sidebar when switching to desktop
  useEffect(() => {
    if (!isMobile) {
      setIsSidebarOpen(false);
    }
  }, [isMobile]);

  const loadConversations = useCallback(async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }, []);

  // Load conversations when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadConversations();
    }
  }, [loadConversations, isAuthenticated]);

  // Load conversation details when selected
  useEffect(() => {
    currentConversationIdRef.current = currentConversationId;
    if (currentConversationId) {
      let isActive = true;
      api.getConversation(currentConversationId)
        .then((conv) => {
          if (!isActive) return;

          // If this conversation is currently pending locally, 
          // only overwrite if the server has MORE data than we currently have.
          const localLastMsg = currentConversation?.messages?.[currentConversation?.messages?.length - 1];
          const serverLastMsg = conv.messages?.[conv.messages?.length - 1];
          
          const serverHasMoreData = 
            !currentConversation || 
            (conv.messages?.length > currentConversation?.messages?.length) ||
            (serverLastMsg?.role === 'assistant' && (
              ((serverLastMsg.stage1?.length || 0) > (localLastMsg?.stage1?.length || 0)) ||
              ((serverLastMsg.stage2?.length || 0) > (localLastMsg?.stage2?.length || 0)) ||
              (!!serverLastMsg.stage3?.response && !localLastMsg?.stage3?.response)
            ));

          let finalConv = { ...conv };
          if (pendingConversationIds.has(conv.id) && currentConversation && !serverHasMoreData) {
            finalConv = { ...currentConversation };
          }

          // Ensure we show correct loading state for pending conversations
          if (pendingConversationIds.has(finalConv.id)) {
            const messages = [...(finalConv.messages || [])];
            if (messages.length > 0) {
              let lastMessage = { ...messages[messages.length - 1] };
              
              if (lastMessage.role !== 'assistant') {
                messages.push({
                  role: 'assistant',
                  stage1: null,
                  stage2: null,
                  stage3: null,
                  metadata: null,
                  progress: { stage1: null, stage2: null },
                  loading: { stage1: true, stage2: false, stage3: false },
                });
              } else {
                const hasS1 = !!(lastMessage.stage1 && lastMessage.stage1.length > 0);
                const hasS2 = !!(lastMessage.stage2 && lastMessage.stage2.length > 0);
                const hasS3 = !!(lastMessage.stage3 && (lastMessage.stage3.response || lastMessage.stage3.content));

                lastMessage.loading = {
                  stage1: !hasS1,
                  stage2: hasS1 && !hasS2,
                  stage3: hasS2 && !hasS3
                };
              }
              messages[messages.length - 1] = lastMessage;
              finalConv.messages = messages;
            }
          }
          setCurrentConversation(finalConv);
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
      // Close sidebar on mobile after creating
      if (isMobile) {
        setIsSidebarOpen(false);
      }
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = async (id) => {
    if (currentConversationId !== id) {
      setCurrentConversation(null);
      setCurrentConversationId(id);
    }
    // Close sidebar on mobile after selecting
    if (isMobile) {
      setIsSidebarOpen(false);
    }
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

  const handleDeleteConversation = (id) => {
    setDeleteModalConfig({
      isOpen: true,
      type: 'single',
      id
    });
  };

  const handleConfirmDelete = async () => {
    const { type, id } = deleteModalConfig;
    
    try {
      if (type === 'single') {
        await api.deleteConversation(id);
        if (currentConversationId === id) {
          setCurrentConversationId(null);
          setCurrentConversation(null);
        }
      } else if (type === 'bulk') {
        const archived = conversations.filter(c => c.is_archived);
        await Promise.all(archived.map(c => api.deleteConversation(c.id)));
      }
      
      loadConversations();
    } catch (error) {
      console.error('Deletion failed:', error);
    } finally {
      setDeleteModalConfig({ isOpen: false, type: null, id: null });
    }
  };

  const handleBulkDelete = () => {
    const archived = conversations.filter(c => c.is_archived);
    if (archived.length === 0) return;
    
    setDeleteModalConfig({
      isOpen: true,
      type: 'bulk',
      id: null
    });
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
            'chairman',
            modelMode
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

      const USE_STREAMING = true;
      
      if (!USE_STREAMING) {
        // Non-streaming: single request, wait for complete response
        const result = await api.sendMessage(conversationId, content, filesForRequest, null, modelMode);
        
        // Update conversation with results
        setCurrentConversation((prev) => {
          if (!prev || prev.id !== conversationId) return prev;
          const messages = [...prev.messages];
          let lastAssistantIndex = messages.length - 1;
          if (messages[lastAssistantIndex]?.role !== 'assistant') {
            messages.push({ role: 'assistant' });
            lastAssistantIndex = messages.length - 1;
          }
          messages[lastAssistantIndex] = {
            ...messages[lastAssistantIndex],
            stage1: result.stage1,
            stage2: result.stage2,
            stage3: result.stage3,
            metadata: result.metadata,
            loading: { stage1: false, stage2: false, stage3: false },
          };
          return { ...prev, messages };
        });
        
        // Refresh conversation list
        await refreshConversationUnreadState(conversationId);
        setLoadingConversationId((prev) => (prev === conversationId ? null : prev));
        setPendingConversationIds((prev) => {
          const next = new Set(prev);
          next.delete(conversationId);
          return next;
        });
        return;
      }
      
      // Streaming path
      await api.sendMessageStream(currentConversationId, content, filesForRequest, (eventType, event) => {
        const updateAssistantMessage = (prev, updater) => {
          if (!prev || prev.id !== conversationId) return prev;
          const messages = [...prev.messages];
          
          // Find the last assistant message that is either loading or was just added
          let lastAssistantIndex = -1;
          for (let i = messages.length - 1; i >= 0; i--) {
            if (messages[i].role === 'assistant') {
              lastAssistantIndex = i;
              break;
            }
          }

          if (lastAssistantIndex === -1) {
            // If no assistant message found (e.g. re-loaded from server), add one
            const newAssistantMsg = {
              role: 'assistant',
              stage1: null,
              stage2: null,
              stage3: null,
              metadata: null,
              progress: { stage1: null, stage2: null },
              loading: { stage1: false, stage2: false, stage3: false },
            };
            messages.push(newAssistantMsg);
            lastAssistantIndex = messages.length - 1;
          }

          messages[lastAssistantIndex] = updater(messages[lastAssistantIndex]);
          return { ...prev, messages };
        };

        switch (eventType) {
          case 'stage_start':
            setCurrentConversation((prev) => updateAssistantMessage(prev, (msg) => {
              if (event.stage === 1) {
                return {
                  ...msg,
                  loading: { stage1: true, stage2: false, stage3: false },
                  progress: {
                    ...msg.progress,
                    stage1: { completed: 0, total: event.total ?? 0 }
                  }
                };
              } else if (event.stage === 2) {
                return {
                  ...msg,
                  loading: { stage1: false, stage2: true, stage3: false },
                  progress: {
                    ...msg.progress,
                    stage2: { completed: 0, total: event.total ?? 0 }
                  }
                };
              } else if (event.stage === 3) {
                return {
                  ...msg,
                  loading: { stage1: false, stage2: false, stage3: true }
                };
              }
              return msg;
            }));
            break;

          case 'stage_progress':
            setCurrentConversation((prev) => updateAssistantMessage(prev, (msg) => {
              if (event.stage === 1) {
                return {
                  ...msg,
                  progress: {
                    ...msg.progress,
                    stage1: {
                      completed: event.completed ?? msg.progress?.stage1?.completed ?? 0,
                      total: event.total ?? msg.progress?.stage1?.total ?? 0,
                    }
                  }
                };
              } else if (event.stage === 2) {
                return {
                  ...msg,
                  progress: {
                    ...msg.progress,
                    stage2: {
                      completed: event.completed ?? msg.progress?.stage2?.completed ?? 0,
                      total: event.total ?? msg.progress?.stage2?.total ?? 0,
                    }
                  }
                };
              }
              return msg;
            }));
            break;

          case 'stage_complete':
            setCurrentConversation((prev) => updateAssistantMessage(prev, (msg) => {
              if (event.stage === 1) {
                return {
                  ...msg,
                  stage1: event.data,
                  loading: { ...msg.loading, stage1: false },
                  progress: { ...msg.progress, stage1: null }
                };
              } else if (event.stage === 2) {
                return {
                  ...msg,
                  stage2: event.data,
                  metadata: event.metadata,
                  loading: { ...msg.loading, stage2: false },
                  progress: { ...msg.progress, stage2: null }
                };
              } else if (event.stage === 3) {
                return {
                  ...msg,
                  stage3: event.data,
                  loading: { ...msg.loading, stage3: false }
                };
              }
              return msg;
            }));
            break;

          case 'title_complete':
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'complete':
            // Stream complete, reload conversations list
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
      }, null, modelMode);
    } catch (error) {
      console.error('Failed to send message (stream):', error);
      
      // If streaming failed due to network issues, try non-streaming fallback
      if (error.message?.includes('network') || error.name === 'TypeError') {
        console.log('Attempting non-streaming fallback...');
        try {
          // Rebuild files for request (in case filesForRequest wasn't set)
          const fallbackFiles = await Promise.all(
            files.map(async (file) => ({
              name: file.name,
              content: await readFileContent(file),
              size: file.size,
            }))
          );
          // Use non-streaming endpoint
          const result = await api.sendMessage(conversationId, content, fallbackFiles, null, modelMode);
          
          // Update conversation with results
          setCurrentConversation((prev) => {
            if (!prev || prev.id !== conversationId) return prev;
            const messages = [...prev.messages];
            // Find or create assistant message
            let lastAssistantIndex = messages.length - 1;
            if (messages[lastAssistantIndex]?.role !== 'assistant') {
              messages.push({ role: 'assistant' });
              lastAssistantIndex = messages.length - 1;
            }
            messages[lastAssistantIndex] = {
              ...messages[lastAssistantIndex],
              stage1: result.stage1,
              stage2: result.stage2,
              stage3: result.stage3,
              metadata: result.metadata,
              loading: { stage1: false, stage2: false, stage3: false },
            };
            return { ...prev, messages };
          });
          
          // Refresh conversation list
          await refreshConversationUnreadState(conversationId);
          setLoadingConversationId((prev) => (prev === conversationId ? null : prev));
          setPendingConversationIds((prev) => {
            const next = new Set(prev);
            next.delete(conversationId);
            return next;
          });
          return; // Success via fallback
        } catch (fallbackError) {
          console.error('Fallback also failed:', fallbackError);
        }
      }
      
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

  // Show loading state while checking auth
  if (authLoading) {
    return (
      <div className="app app-loading">
        <div className="loading-spinner" />
      </div>
    );
  }

  // Show login screen if not authenticated
  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  return (
    <div className={`app ${isMobile ? 'app-mobile' : ''}`}>
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
          isMobile={isMobile}
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
        />
        <ChatInterface
          conversation={currentConversation}
          conversations={conversations}
          onSendMessage={handleSendMessage}
          onHeaderAction={handleHeaderAction}
          onUpdateTitle={handleUpdateTitle}
          onNewConversation={handleNewConversation}
          onSelectConversation={handleSelectConversation}
          isLoading={isLoading}
          isMobile={isMobile}
          onMenuClick={() => setIsSidebarOpen(true)}
        />
      <DeleteConfirmationModal
        isOpen={deleteModalConfig.isOpen}
        onClose={() => setDeleteModalConfig({ ...deleteModalConfig, isOpen: false })}
        onConfirm={handleConfirmDelete}
        title={deleteModalConfig.type === 'bulk' ? "Delete All Archived" : undefined}
        message={deleteModalConfig.type === 'bulk' 
          ? `Are you sure you want to delete all ${conversations.filter(c => c.is_archived).length} archived conversations?` 
          : undefined}
      />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <SettingsProvider>
        <AppContent />
      </SettingsProvider>
    </AuthProvider>
  );
}

export default App;
