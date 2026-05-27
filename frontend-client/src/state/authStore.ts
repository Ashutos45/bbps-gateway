import { create } from 'zustand';

export type UserRole = 'SUPER_ADMIN' | 'ADMIN' | 'OPERATIONS' | 'CLIENT' | 'AUDITOR';

interface AuthState {
  role: UserRole;
  apiKey: string;
  jwtToken: string | null;
  username: string | null;
  adminAccessKey: string | null;
  setRole: (role: UserRole) => void;
  setJwtToken: (token: string | null) => void;
  setUsername: (username: string | null) => void;
  setAdminAccessKey: (key: string | null) => void;
  logout: () => void;
}

const roleKeys: Record<UserRole, string> = {
  SUPER_ADMIN: 'admin_key_123',
  ADMIN: 'admin_key_123',
  OPERATIONS: 'operator_key_123',
  CLIENT: 'client_key_123',
  AUDITOR: 'auditor_key_123',
};

// Reusable JWT decoder
export function decodeJwt(token: string): any {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      window
        .atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error("JWT decoding failed", e);
    return null;
  }
}

// Map legacy roles for backward compatibility
function normalizeRole(role: string): UserRole {
  const upper = (role || '').toUpperCase();
  if (upper === 'SUPER_ADMIN') {
    return 'SUPER_ADMIN';
  }
  if (upper === 'OPERATOR' || upper === 'CUSTOMER_SUPPORT') {
    return 'OPERATIONS';
  }
  if (upper === 'SECURITY_ANALYST') {
    return 'AUDITOR';
  }
  if (upper === 'ADMIN' || upper === 'CLIENT' || upper === 'AUDITOR' || upper === 'OPERATIONS') {
    return upper as UserRole;
  }
  return 'CLIENT';
}

const getInitialAuthState = () => {
  const token = localStorage.getItem('jwt_token') || null;
  const adminAccessKey = localStorage.getItem('admin_access_key') || null;
  let role: UserRole = 'CLIENT';
  let username: string | null = null;
  let apiKey = 'client_key_123';

  if (token) {
    const claims = decodeJwt(token);
    if (claims && claims.role) {
      role = normalizeRole(claims.role);
      username = claims.sub || null;
      apiKey = roleKeys[role] || 'client_key_123';
    } else {
      // Invalid/tampered token, clear storage
      localStorage.removeItem('jwt_token');
      localStorage.removeItem('user_role');
      localStorage.removeItem('api_key');
      localStorage.removeItem('username');
      localStorage.removeItem('admin_access_key');
    }
  }

  return { role, apiKey, jwtToken: token, username, adminAccessKey };
};

const initialState = getInitialAuthState();

export const useAuthStore = create<AuthState>((set) => ({
  role: initialState.role,
  apiKey: initialState.apiKey,
  jwtToken: initialState.jwtToken,
  username: initialState.username,
  adminAccessKey: initialState.adminAccessKey,

  setRole: (role: UserRole) => {
    const key = roleKeys[role];
    localStorage.setItem('user_role', role);
    localStorage.setItem('api_key', key);
    set({ role, apiKey: key });
  },

  setJwtToken: (token: string | null) => {
    if (token) {
      localStorage.setItem('jwt_token', token);
      // Auto-extract role from token on token update
      const claims = decodeJwt(token);
      if (claims && claims.role) {
        const tokenRole = normalizeRole(claims.role);
        localStorage.setItem('user_role', tokenRole);
        const key = roleKeys[tokenRole] || 'client_key_123';
        localStorage.setItem('api_key', key);
        set({ jwtToken: token, role: tokenRole, apiKey: key });
        return;
      }
    } else {
      localStorage.removeItem('jwt_token');
    }
    set({ jwtToken: token });
  },

  setUsername: (username: string | null) => {
    if (username) {
      localStorage.setItem('username', username);
    } else {
      localStorage.removeItem('username');
    }
    set({ username });
  },

  setAdminAccessKey: (key: string | null) => {
    if (key) {
      localStorage.setItem('admin_access_key', key);
    } else {
      localStorage.removeItem('admin_access_key');
    }
    set({ adminAccessKey: key });
  },

  logout: () => {
    localStorage.removeItem('jwt_token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('api_key');
    localStorage.removeItem('username');
    localStorage.removeItem('admin_access_key');
    set({ jwtToken: null, role: 'CLIENT', apiKey: 'client_key_123', username: null, adminAccessKey: null });
  },
}));
