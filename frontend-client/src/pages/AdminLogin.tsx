import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../state/authStore';
import apiClient from '../api/apiClient';
import { Lock, User, ShieldAlert, Loader2, Server } from 'lucide-react';

export const AdminLogin: React.FC = () => {
  const [username, setUsernameInput] = useState('');
  const [password, setPassword] = useState('');
  const [adminAccessKey, setAdminAccessKeyInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { setJwtToken, setRole, setUsername, setAdminAccessKey } = useAuthStore();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Please enter both username/email and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.post('/auth/admin/login', {
        username: username.trim(),
        password,
        admin_access_key: adminAccessKey.trim(),
      });

      const data = response.data;
      if (data.access_token) {
        setJwtToken(data.access_token);
        setRole(data.role);
        setUsername(username.trim());
        setAdminAccessKey(null); // No longer needed post-activation
        
        navigate('/');
      } else {
        setError('Authentication succeeded but token was not returned.');
      }
    } catch (err: any) {
      console.error('Admin login error', err);
      let errMsg = 'Failed to authenticate. Please try again.';
      if (err.response && err.response.data && err.response.data.detail) {
        errMsg = err.response.data.detail;
      } else if (err.message) {
        errMsg = err.message;
      }
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#030303] px-4 font-sans relative overflow-hidden">
      {/* Dynamic Grid Background Overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] pointer-events-none opacity-60"></div>
      
      {/* Sleek Neon Backdrop Circles */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-rose-900/10 rounded-full blur-3xl pointer-events-none"></div>

      <div className="glass-card max-w-md w-full rounded-2xl p-8 relative z-10 border border-zinc-800/80 bg-zinc-950/40">
        {/* Top Header Node Bar */}
        <div className="flex items-center justify-between border-b border-zinc-900/60 pb-4 mb-6 font-mono">
          <span className="text-[10px] text-rose-400 font-bold uppercase tracking-widest flex items-center gap-1.5">
            <span className="w-2 h-2 bg-rose-500 rounded-full animate-pulse"></span>
            BBPS NEXTGEN ADMIN PORTAL
          </span>
          <span className="text-[10px] text-zinc-650">v5.0_SECURED</span>
        </div>

        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4 border bg-rose-500/10 border-rose-500/30 text-rose-400">
            <Server size={22} className="stroke-[1.8]" />
          </div>
          <h1 className="text-2xl font-bold font-display text-zinc-100 tracking-tight">
            Admin Credentials
          </h1>
          <p className="text-xs text-zinc-500 mt-2 font-mono uppercase">
            Establish Operational Console Tunnel
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-rose-950/20 border border-rose-900/40 rounded-xl flex items-start gap-3 animate-fade-in">
            <ShieldAlert className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-rose-350 font-mono leading-relaxed">
              {error}
            </div>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          <div className="flex flex-col space-y-1.5">
            <label className="text-[10px] font-mono uppercase text-zinc-500 tracking-wider">
              Username or Email
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-zinc-500">
                <User size={15} />
              </span>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsernameInput(e.target.value)}
                placeholder="Enter admin username/email"
                className="input-premium pl-10 text-xs"
                disabled={loading}
                autoFocus
                required
              />
            </div>
          </div>

          <div className="flex flex-col space-y-1.5">
            <label className="text-[10px] font-mono uppercase text-zinc-500 tracking-wider">
              Secret Passphrase
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-zinc-500">
                <Lock size={15} />
              </span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="input-premium pl-10 text-xs"
                disabled={loading}
                required
              />
            </div>
          </div>

          <div className="flex flex-col space-y-1.5">
            <label className="text-[10px] font-mono uppercase text-zinc-500 tracking-wider">
              Admin Access Key
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-zinc-500">
                <ShieldAlert size={15} />
              </span>
              <input
                type="password"
                value={adminAccessKey}
                onChange={(e) => setAdminAccessKeyInput(e.target.value)}
                placeholder="Secure access token"
                className="input-premium pl-10 text-xs"
                disabled={loading}
                required
              />
            </div>
          </div>

          <button
            type="submit"
            className="w-full text-black font-extrabold text-xs py-3 rounded-xl transition-all duration-200 shadow-lg flex items-center justify-center gap-2 cursor-pointer mt-2 disabled:bg-zinc-900 disabled:text-zinc-650 disabled:cursor-not-allowed bg-rose-600 hover:bg-rose-500 shadow-rose-950/20"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span className="font-mono text-[10px] uppercase tracking-wider">Verifying Cryptographic Tokens...</span>
              </>
            ) : (
              <span className="font-display uppercase tracking-wider text-[11px] font-black">
                Access Admin Central Command
              </span>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-zinc-900 text-center font-mono">
          <div className="space-y-2.5">
            <p className="text-[10px] text-zinc-500">
              First-time staff setup?{' '}
              <Link to="/activate-admin" className="text-rose-400 hover:underline">
                Activate Admin Account
              </Link>
            </p>
            <p className="text-[10px] text-zinc-500">
              Are you a client?{' '}
              <Link to="/login" className="text-cyan-400 hover:underline font-bold">
                Access Client Portal
              </Link>
            </p>
            <p className="text-[9px] text-zinc-650 leading-relaxed pt-2">
              Zero-Trust and anti-privilege logs are active.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminLogin;
