import { describe, it, expect, beforeEach } from 'vitest';
import { getToken, getEmail, saveAuth, clearAuth } from '@/lib/auth';

describe('auth', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns null when no token is stored', () => {
    expect(getToken()).toBeNull();
    expect(getEmail()).toBeNull();
  });

  it('stores and retrieves token and email', () => {
    saveAuth('test-token-123', 'user@example.com');
    expect(getToken()).toBe('test-token-123');
    expect(getEmail()).toBe('user@example.com');
  });

  it('clears stored auth data', () => {
    saveAuth('test-token', 'user@example.com');
    clearAuth();
    expect(getToken()).toBeNull();
    expect(getEmail()).toBeNull();
  });

  it('overwrites existing auth data', () => {
    saveAuth('token-1', 'a@example.com');
    saveAuth('token-2', 'b@example.com');
    expect(getToken()).toBe('token-2');
    expect(getEmail()).toBe('b@example.com');
  });
});
