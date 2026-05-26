import React from 'react';
import { useToastStore } from '../state/toastStore';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

export const ToastManager: React.FC = () => {
  const { toasts, removeToast } = useToastStore();

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((toast) => {
        let bgColor = 'bg-zinc-800 border-zinc-700';
        let Icon = Info;
        let iconColor = 'text-blue-400';

        if (toast.type === 'success') {
          bgColor = 'bg-emerald-950/80 border-emerald-900';
          Icon = CheckCircle;
          iconColor = 'text-emerald-400';
        } else if (toast.type === 'error') {
          bgColor = 'bg-rose-950/80 border-rose-900';
          Icon = AlertCircle;
          iconColor = 'text-rose-400';
        }

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg border shadow-xl backdrop-blur-md transition-all animate-in slide-in-from-right-8 fade-in ${bgColor}`}
          >
            <Icon size={18} className={iconColor} />
            <p className="text-sm font-mono text-zinc-200">{toast.message}</p>
            <button
              onClick={() => removeToast(toast.id)}
              className="ml-4 text-zinc-500 hover:text-zinc-300"
            >
              <X size={16} />
            </button>
          </div>
        );
      })}
    </div>
  );
};
