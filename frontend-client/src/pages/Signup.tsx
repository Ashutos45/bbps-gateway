import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../api/apiClient';
import { useToastStore } from '../state/toastStore';
import { User, Mail, Lock, Building, Loader2, ArrowLeft, ShieldAlert, KeyRound, Server } from 'lucide-react';

export const Signup: React.FC = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [organization, setOrganization] = useState('');
  const [company, setCompany] = useState('');
  
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { addToast } = useToastStore();
  const navigate = useNavigate();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !email.trim() || !password) {
      setError('Please fill in all mandatory fields.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await apiClient.post('/auth/register-client', {
        username: username.trim(),
        email: email.trim(),
        password,
        organization: organization.trim() || null,
        company: company.trim() || null
      });
      addToast('success', 'User account registered successfully. Please login to authenticate.');
      navigate('/login');
    } catch (err: any) {
      console.error('Signup error', err);
      let errMsg = 'Failed to register account. Please check inputs.';
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
      {/* Background patterns */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] pointer-events-none opacity-60"></div>
      <div className="absolute top-1/4 left-1/3 w-96 h-96 rounded-full blur-3xl pointer-events-none bg-cyan-900/10"></div>

      <div className="glass-card max-w-md w-full rounded-2xl p-8 relative z-10 border border-zinc-800/80 bg-zinc-950/40">
        {/* Navigation back to login */}
        <Link to="/login" className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-350 font-mono mb-6 uppercase tracking-wider transition-colors select-none">
          <ArrowLeft size={10} />
          <span>Back to Authorization Portal</span>
        </Link>

        {/* Top Header Node Bar */}
        <div className="flex items-center justify-between border-b border-zinc-900/60 pb-4 mb-6 font-mono">
          <span className="text-[10px] font-bold uppercase tracking-widest flex items-center gap-1.5 text-cyan-400">
            <span className="w-2 h-2 rounded-full animate-pulse bg-cyan-400"></span>
            BBPS NEXTGEN SIGN-UP
          </span>
          <span className="text-[10px] text-zinc-650 font-mono">v5.0_SECURED</span>
        </div>

        {/* Title */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4 border transition-all bg-cyan-500/10 border-cyan-500/30 text-cyan-400">
            <User size={22} className="stroke-[1.8]" />
          </div>
          <h1 className="text-2xl font-bold font-display text-zinc-100 tracking-tight">
            Register New User
          </h1>
          <p className="text-xs text-zinc-500 mt-2 font-mono uppercase">
            Create a standard CLIENT role gateway account
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

        <form onSubmit={handleSignup} className="space-y-4.5 font-mono text-xs">
          {/* Username */}
          <div className="flex flex-col space-y-1.5">
            <label className="text-[10px] text-zinc-500 uppercase tracking-wider">
              Username *
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-zinc-550">
                <User size={14} />
              </span>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="enter username"
                className="input-premium pl-10"
                disabled={loading}
                required
              />
            </div>
          </div>

          {/* Email */}
          <div className="flex flex-col space-y-1.5">
            <label className="text-[10px] text-zinc-500 uppercase tracking-wider">
              Email Address *
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-zinc-555">
                <Mail size={14} />
              </span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="enter email address"
                className="input-premium pl-10"
                disabled={loading}
                required
              />
            </div>
          </div>

          {/* Password */}
          <div className="flex flex-col space-y-1.5">
            <label className="text-[10px] text-zinc-500 uppercase tracking-wider">
              Access Password *
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-zinc-555">
                <Lock size={14} />
              </span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="input-premium pl-10"
                disabled={loading}
                required
              />
            </div>
          </div>

          {/* Organization */}
          <div className="flex flex-col space-y-1.5">
            <label className="text-[10px] text-zinc-555 uppercase tracking-wider">
              Organization Name (Optional)
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-zinc-650">
                <Building size={14} />
              </span>
              <input
                type="text"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                placeholder="e.g. Bank of Baroda"
                className="input-premium pl-10"
                disabled={loading}
              />
            </div>
          </div>

          {/* Company */}
          <div className="flex flex-col space-y-1.5">
            <label className="text-[10px] text-zinc-555 uppercase tracking-wider">
              Company Entity (Optional)
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-zinc-650">
                <Building size={14} />
              </span>
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. Baroda Fin Corp Ltd"
                className="input-premium pl-10"
                disabled={loading}
              />
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            className="w-full font-extrabold text-xs py-3 rounded-xl transition-all duration-200 shadow-lg flex items-center justify-center gap-2 cursor-pointer mt-4.5 disabled:bg-zinc-900 disabled:text-zinc-650 bg-cyan-600 hover:bg-cyan-500 text-black shadow-cyan-950/20"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                <span>Registering Account...</span>
              </>
            ) : (
              <span className="font-display uppercase tracking-wider font-black text-xs">
                Establish Client Account
              </span>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Signup;
