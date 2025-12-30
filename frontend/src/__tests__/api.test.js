import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api } from '../api';

describe('api client', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sendMessage includes files in the request body', async () => {
    const files = [{ name: 'notes.txt', content: 'hello', size: 5 }];
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    await api.sendMessage('conv-1', 'hi', files, 'chairman');

    const [, options] = fetch.mock.calls[0];
    const body = JSON.parse(options.body);

    expect(body).toEqual({
      content: 'hi',
      target_model: 'chairman',
      files,
    });
  });

  it('sendMessageStream includes files in the request body', async () => {
    const files = [{ name: 'notes.txt', content: 'hello', size: 5 }];
    const encoder = new TextEncoder();
    let readCount = 0;
    const reader = {
      read: vi.fn().mockImplementation(async () => {
        if (readCount === 0) {
          readCount += 1;
          return { done: false, value: encoder.encode('data: {"type":"complete"}\n\n') };
        }
        return { done: true, value: undefined };
      }),
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      body: {
        getReader: () => reader,
      },
    });

    await api.sendMessageStream('conv-1', 'hi', files, vi.fn());

    const [, options] = fetch.mock.calls[0];
    const body = JSON.parse(options.body);

    expect(body).toEqual({
      content: 'hi',
      target_model: null,
      files,
    });
  });

  it('markAsRead calls updateConversation with has_unread: false', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ has_unread: false }),
    });

    await api.markAsRead('conv-1');

    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe('/api/conversations/conv-1');
    expect(options.method).toBe('PATCH');
    expect(JSON.parse(options.body)).toEqual({ has_unread: false });
  });
});
