import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ShieldAlert, ArrowLeft, Terminal } from 'lucide-react';
import { useAuthStore } from '../state/authStore';

const Unauthorized: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { role, username } = useAuthStore();
  const timestamp = new Date().toISOString();

  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] px-4">
      {/* Visual glowing warning card */}
      <div className="w-full max-w-lg bg-zinc-950/80 border border-rose-500/20 backdrop-blur-xl rounded-2xl p-8 relative overflow-hidden shadow-[0_0_50px_rgba(239,68,68,0.1)]">
        {/* Glow accent */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-rose-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-rose-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col items-center text-center">
          <div className="w-16 h-16 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mb-6 shadow-[0_0_20px_rgba(239,68,68,0.2)] animate-pulse">
            <ShieldAlert className="text-rose-500" size={32} />
          </div>

          <h1 className="text-2xl font-extrabold text-zinc-100 tracking-tight font-display mb-2">
            ACCESS DENIED (403)
          </h1>
          <p className="text-zinc-400 text-sm max-w-sm mb-6 leading-relaxed">
            Your current security role <span className="text-rose-400 font-mono font-bold px-1.5 py-0.5 rounded bg-rose-950/30 border border-rose-500/20">{role}</span> is not authorized to access this resource path.
          </p>

          {/* Interactive terminal audit box */}
          <div className="w-full bg-[#050507] border border-zinc-900 rounded-lg p-4 mb-6 font-mono text-[11px] text-left text-zinc-500 relative">
            <div className="flex items-center gap-2 mb-2 text-zinc-600 border-b border-zinc-900/60 pb-1.5">
              <Terminal size={12} className="text-rose-500" />
              <span>SECURITY COMPLIANCE AUDIT LOG</span>
            </div>
            <div className="space-y-1 select-all">
              <div><span className="text-zinc-600">[{timestamp}]</span> <span className="text-rose-500 font-bold">WARN:</span> PRIVILEGE_VIOLATION</div>
              <div><span className="text-zinc-600">[{timestamp}]</span> USER: &quot;{username}&quot;</div>
              <div><span className="text-zinc-600">[{timestamp}]</span> PATH_ATTEMPT: &quot;{location.pathname || 'unknown'}&quot;</div>
              <div><span className="text-zinc-600">[{timestamp}]</span> ACTION: BLOCKED_BY_GUARD</div>
            </div>
          </div>

          <button
            onClick={() => navigate('/')}
            className="flex items-center justify-center gap-2 w-full bg-zinc-900 hover:bg-zinc-800 hover:text-zinc-100 border border-zinc-800 text-zinc-300 font-semibold py-2.5 px-4 rounded-xl transition-all cursor-pointer text-xs"
          >
            <ArrowLeft size={14} />
            <span>Return to Safe Zone Dashboard</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Unauthorized;
