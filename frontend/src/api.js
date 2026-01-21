/**
 * API client for the Symposia backend.
 * All requests include Firebase auth tokens.
 */

import { auth } from './firebase';

const API_BASE = '';

/**
 * Get the current user's ID token for API authentication.
 * @returns {Promise<string|null>}
 */
async function getAuthToken() {
  const user = auth.currentUser;
  if (!user) return null;
  try {
    return await user.getIdToken();
  } catch (err) {
    console.error('Failed to get auth token:', err);
    return null;
  }
}

/**
 * Create headers with auth token.
 * @param {Object} additionalHeaders - Additional headers to include
 * @returns {Promise<Object>}
 */
async function getAuthHeaders(additionalHeaders = {}) {
  const token = await getAuthToken();
  const headers = { ...additionalHeaders };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Handle response errors, including auth errors.
 * @param {Response} response
 * @param {string} errorMessage
 */
function handleResponseError(response, errorMessage) {
  if (response.status === 401) {
    // Token expired or invalid - could trigger re-auth here
    throw new Error('Authentication required. Please sign in again.');
  }
  if (response.status === 403) {
    throw new Error('Access denied.');
  }
  throw new Error(errorMessage);
}

export const api = {
  /**
   * List all conversations for the current user.
   */
  async listConversations() {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE}/api/conversations`, { headers });
    if (!response.ok) {
      handleResponseError(response, 'Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const headers = await getAuthHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers,
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      handleResponseError(response, 'Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const headers = await getAuthHeaders();
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`,
      { headers }
    );
    if (!response.ok) {
      handleResponseError(response, 'Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content, files = [], targetModel = null, modelMode = 'smart') {
    const headers = await getAuthHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({ content, files, target_model: targetModel, model_mode: modelMode }),
      }
    );
    if (!response.ok) {
      handleResponseError(response, 'Failed to send message');
    }
    return response.json();
  },

  /**
   * Update conversation metadata.
   */
  async updateConversation(conversationId, updates) {
    const headers = await getAuthHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(updates),
    });
    if (!response.ok) {
      handleResponseError(response, 'Failed to update conversation');
    }
    return response.json();
  },

  /**
   * Mark a conversation as read.
   */
  async markAsRead(conversationId) {
    return api.updateConversation(conversationId, { has_unread: false });
  },

  /**
   * Delete a conversation.
   */
  async deleteConversation(conversationId) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
      method: 'DELETE',
      headers,
    });
    if (!response.ok) {
      handleResponseError(response, 'Failed to delete conversation');
    }
    return response.json();
  },

  /**
   * Duplicate a conversation.
   */
  async duplicateConversation(conversationId) {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/duplicate`, {
      method: 'POST',
      headers,
    });
    if (!response.ok) {
      handleResponseError(response, 'Failed to duplicate conversation');
    }
    return response.json();
  },

  /**
   * Send a message with streaming response.
   */
  async sendMessageStream(conversationId, content, files, onEvent, targetModel = null, modelMode = 'smart') {
    const headers = await getAuthHeaders({ 'Content-Type': 'application/json' });
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({ content, files, target_model: targetModel, model_mode: modelMode }),
      }
    );

    if (!response.ok) {
      handleResponseError(response, 'Failed to send message');
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
