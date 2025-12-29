import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '../api';

describe('api client', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  it('sendMessage should include files in the request body', async () => {
    const mockResponse = { id: 'msg-1' };
    fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const files = [{ name: 'test.txt', content: 'hello' }];
    const result = await api.sendMessage('conv-1', 'hello', null, files);

    expect(fetch).toHaveBeenCalledWith(
      '/api/conversations/conv-1/message',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ 
          content: 'hello', 
          target_model: null, 
          files: files 
        }),
      })
    );
    expect(result).toEqual(mockResponse);
  });

  it('sendMessageStream should include files in the request body', async () => {
    // Mock for streaming is a bit more involved, but we just want to check the fetch call
    const mockReader = {
      read: vi.fn().mockResolvedValue({ done: true }),
    };
    const mockResponse = {
      ok: true,
      body: {
        getReader: () => mockReader,
      },
    };
    fetch.mockResolvedValue(mockResponse);

    const files = [{ name: 'test.txt', content: 'hello' }];
    await api.sendMessageStream('conv-1', 'hello', vi.fn(), null, files);

    expect(fetch).toHaveBeenCalledWith(
      '/api/conversations/conv-1/message/stream',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ 
          content: 'hello', 
          target_model: null, 
          files: files 
        }),
      })
    );
  });
});
