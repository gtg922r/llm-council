/**
 * API client for the LLM Council backend.
 */

const API_BASE = '';

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {Array} files - Array of file objects
   * @param {string|null} targetModel - Target model (e.g., 'chairman' for follow-up)
   * @param {string} modelMode - Model mode: 'fast' or 'smart'
   */
  async sendMessage(conversationId, content, files = [], targetModel = null, modelMode = 'smart') {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content, files, target_model: targetModel, model_mode: modelMode }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Update conversation metadata (title, pinned, archived).
   */
  async updateConversation(conversationId, updates) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });
    if (!response.ok) {
      throw new Error('Failed to update conversation');
    }
    return response.json();
  },

  /**
   * Mark a conversation as read by clearing has_unread.
   */
  async markAsRead(conversationId) {
    return api.updateConversation(conversationId, { has_unread: false });
  },

  /**
   * Permanently delete a conversation.
   */
  async deleteConversation(conversationId) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
    return response.json();
  },

  /**
   * Duplicate a conversation.
   */
  async duplicateConversation(conversationId) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/duplicate`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to duplicate conversation');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {Array} files - Array of file objects
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @param {string|null} targetModel - Target model (e.g., 'chairman' for follow-up)
   * @param {string} modelMode - Model mode: 'fast' or 'smart'
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, files, onEvent, targetModel = null, modelMode = 'smart') {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content, files, target_model: targetModel, model_mode: modelMode }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const eventBlock of events) {
        const lines = eventBlock.split('\n');
        const dataLines = lines
          .filter((line) => line.startsWith('data: '))
          .map((line) => line.slice(6));

        if (dataLines.length === 0) continue;

        const data = dataLines.join('\n');
        try {
          const event = JSON.parse(data);
          onEvent(event.type, event);
        } catch (e) {
          console.error('Failed to parse SSE event:', e);
        }
      }
    }

    if (buffer.trim()) {
      const lines = buffer.split('\n');
      const dataLines = lines
        .filter((line) => line.startsWith('data: '))
        .map((line) => line.slice(6));

      if (dataLines.length > 0) {
        const data = dataLines.join('\n');
        try {
          const event = JSON.parse(data);
          onEvent(event.type, event);
        } catch (e) {
          console.error('Failed to parse SSE event:', e);
        }
      }
    }
  },
};
