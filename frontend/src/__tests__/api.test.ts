import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '@/lib/api';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function errorResponse(detail: string, status = 400): Response {
  return new Response(JSON.stringify({ detail }), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('api', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    localStorage.clear();
  });

  describe('register', () => {
    it('sends POST with email, password, full_name', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ access_token: 'tok', token_type: 'bearer', refresh_token: 'ref' })
      );
      const result = await api.register({ email: 'a@b.com', password: 'secret', full_name: 'A' });
      expect(mockFetch).toHaveBeenCalledOnce();
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toContain('/api/auth/register');
      expect(init.method).toBe('POST');
      const body = JSON.parse(init.body);
      expect(body.email).toBe('a@b.com');
      expect(body.password).toBe('secret');
      expect(body.full_name).toBe('A');
      expect(result.access_token).toBe('tok');
    });

    it('throws ApiError on failure', async () => {
      mockFetch.mockResolvedValueOnce(errorResponse('email already registered', 409));
      await expect(api.register({ email: 'x@x.com', password: 'p' })).rejects.toThrow('email already registered');
    });
  });

  describe('login', () => {
    it('sends POST with email and password', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ access_token: 'login-tok', token_type: 'bearer', refresh_token: 'ref' })
      );
      const result = await api.login({ email: 'a@b.com', password: 'secret' });
      const [, init] = mockFetch.mock.calls[0];
      expect(init.method).toBe('POST');
      expect(result.access_token).toBe('login-tok');
    });
  });

  describe('me', () => {
    it('sends GET to /api/me with Authorization header', async () => {
      localStorage.setItem('deepblender_token', 'my-token');
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ user: { id: '1', email: 'a@b.com', full_name: 'A', created_at: '' }, memberships: [] })
      );
      await api.me();
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toContain('/api/me');
      expect(init.headers?.Authorization).toBe('Bearer my-token');
    });
  });

  describe('createOrganization', () => {
    it('sends POST with name', async () => {
      localStorage.setItem('deepblender_token', 'tok');
      mockFetch.mockResolvedValueOnce(jsonResponse({ id: '1', name: 'Org', owner_id: '1', created_at: '', role: 'owner' }));
      await api.createOrganization('Org');
      const [, init] = mockFetch.mock.calls[0];
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body).name).toBe('Org');
    });
  });

  describe('listOrganizations', () => {
    it('returns array', async () => {
      localStorage.setItem('deepblender_token', 'tok');
      mockFetch.mockResolvedValueOnce(jsonResponse([]));
      const result = await api.listOrganizations();
      expect(result).toEqual([]);
    });
  });

  describe('error handling', () => {
    it('throws ApiError with status for HTTP errors', async () => {
      localStorage.setItem('deepblender_token', 'tok');
      mockFetch.mockResolvedValueOnce(errorResponse('forbidden', 403));
      await expect(api.getOrganization('1')).rejects.toThrow('forbidden');
    });

    it('throws ApiError on network failure', async () => {
      localStorage.setItem('deepblender_token', 'tok');
      mockFetch.mockRejectedValueOnce(new Error('Network error'));
      await expect(api.getOrganization('1')).rejects.toThrow('Impossible de joindre le serveur DeepBlender.');
    });
  });

  describe('deleteProject', () => {
    it('sends DELETE', async () => {
      localStorage.setItem('deepblender_token', 'tok');
      mockFetch.mockResolvedValueOnce(new Response(null, { status: 204 }));
      await api.deleteProject('proj-1');
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toContain('/api/projects/proj-1');
      expect(init.method).toBe('DELETE');
    });
  });

  describe('runProduction', () => {
    it('sends POST to /run', async () => {
      localStorage.setItem('deepblender_token', 'tok');
      mockFetch.mockResolvedValueOnce(jsonResponse({ id: 'p1', status: 'running' }));
      await api.runProduction('p1');
      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toContain('/api/productions/p1/run');
      expect(init.method).toBe('POST');
    });
  });
});
