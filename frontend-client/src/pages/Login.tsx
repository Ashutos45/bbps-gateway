import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../state/authStore';
import apiClient from '../api/apiClient';
import { Lock, User, ShieldAlert, Loader2, KeyRound, Server } from 'lucide-react';

export const Login: React.FC = () => {
  const [username, setUsernameInput] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { setJwtToken, setRole, setUsername, setAdminAccessKey } = useAuthStore();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Please enter both username and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.post('/auth/login-client', {
        username: username.trim(),
        password,
      });

      const data = response.data;
      if (data.access_token) {
        setJwtToken(data.access_token);
        setRole(data.role);
        setUsername(username.trim());
        setAdminAccessKey(null);
        
        navigate('/');
      } else {
        setError('Authentication succeeded but token was not returned.');
      }
    } catch (err: any) {
      console.error('Login error', err);
      let errMsg = 'Failed to authenticate. Please try again.';
      if (err.response && err.response.data) {
        if (err.response.data.detail) {
          errMsg = err.response.data.detail;
        } else if (err.response.data.message) {
          errMsg = err.response.data.message;
        }
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
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-900/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-rose-900/5 rounded-full blur-3xl pointer-events-none"></div>

      <div className="glass-card max-w-md w-full rounded-2xl p-8 relative z-10 border border-zinc-800/80 bg-zinc-950/40">
        {/* Top Header Node Bar */}
        <div className="flex items-center justify-between border-b border-zinc-900/60 pb-4 mb-6 font-mono">
          <span className="text-[10px] text-cyan-400 font-bold uppercase tracking-widest flex items-center gap-1.5">
            <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse-cyan"></span>
            BBPS NEXTGEN GATE-AUTH
          </span>
          <span className="text-[10px] text-zinc-650">v5.0_SECURED</span>
        </div>

        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4 border transition-all bg-cyan-500/10 border-cyan-500/30 text-cyan-400">
            <User size={22} className="stroke-[1.8]" />
          </div>
          <h1 className="text-2xl font-bold font-display text-zinc-100 tracking-tight">
            Client Authorization
          </h1>
          <p className="text-xs text-zinc-500 mt-2 font-mono uppercase">
            Access Standard Consumer Bill Services
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
                placeholder="Enter client username"
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

          <button
            type="submit"
            className="w-full text-black font-extrabold text-xs py-3 rounded-xl transition-all duration-200 shadow-lg flex items-center justify-center gap-2 cursor-pointer mt-2 disabled:bg-zinc-900 disabled:text-zinc-650 disabled:cursor-not-allowed bg-cyan-600 hover:bg-cyan-500 shadow-cyan-950/20"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span className="font-mono text-[10px] uppercase tracking-wider">Verifying Cryptographic Tokens...</span>
              </>
            ) : (
              <span className="font-display uppercase tracking-wider text-[11px] font-black">
                Access Client Ledger
              </span>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-zinc-900 text-center font-mono space-y-2.5">
          <p className="text-[10px] text-zinc-500">
            New client to the gateway?{' '}
            <Link to="/signup" className="text-cyan-400 hover:underline">
              Register New User
            </Link>
          </p>
          <p className="text-[10px] text-zinc-500">
            Are you a staff member?{' '}
            <Link to="/login-admin" className="text-rose-400 hover:underline font-bold">
              Access Admin Portal
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
