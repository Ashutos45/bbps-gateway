import React from 'react';
import { Trash2, CreditCard, ShieldCheck } from 'lucide-react';
import { FavoriteBiller } from '../types';

interface FavoriteBillersProps {
  favorites: FavoriteBiller[];
  loading: boolean;
  onSelect: (fav: FavoriteBiller) => void;
  onDelete: (billerAccountId: string) => void;
}

export const FavoriteBillers: React.FC<FavoriteBillersProps> = ({
  favorites,
  loading,
  onSelect,
  onDelete,
}) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 text-zinc-550 font-mono text-xs animate-pulse">
        Loading registered billers shortcut deck...
      </div>
    );
  }

  if (favorites.length === 0) {
    return (
      <div className="border border-dashed border-zinc-800 rounded-xl p-8 text-center text-zinc-500 font-sans text-xs bg-zinc-950/10">
        No registered favorite billers. Add operators in the panel below to configure quick payment shortcuts.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5">
      {favorites.map((fav) => {
        const isAutopay = fav.autopay_status === 'Y';
        
        return (
          <div
            key={fav.billeraccountid}
            className="glass-card rounded-xl p-4.5 flex flex-col justify-between font-mono text-xs hover:border-zinc-800 transition-all border-zinc-900/60 bg-zinc-950/40 relative group overflow-hidden"
          >
            {/* Hover decorative glow */}
            <div className="absolute -top-12 -right-12 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl group-hover:bg-cyan-500/10 transition-all pointer-events-none"></div>

            <div>
              <div className="flex justify-between items-start">
                <span className="font-extrabold text-zinc-200 text-sm truncate pr-2 font-display block" title={fav.short_name}>
                  {fav.short_name}
                </span>
                <button
                  onClick={() => onDelete(fav.billeraccountid)}
                  className="text-zinc-600 hover:text-rose-400 p-1 transition-colors cursor-pointer rounded hover:bg-rose-950/15"
                  title="Remove Favorite"
                >
                  <Trash2 size={13} />
                </button>
              </div>

              <div className="text-[10px] text-zinc-500 mt-2.5 space-y-0.5">
                <div>Biller ID: <span className="text-zinc-400 font-semibold">{fav.biller_id}</span></div>
                <div>Account Ref: <span className="text-zinc-400 font-semibold select-all">{fav.billeraccountid}</span></div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-zinc-900/80 flex justify-between items-center">
              {/* Autopay status */}
              <div>
                <span className="block text-[8px] text-zinc-550 leading-none uppercase font-bold tracking-wider">AutoPay System</span>
                {isAutopay ? (
                  <span className="text-emerald-400 font-bold text-[9px] block mt-1 flex items-center gap-0.5">
                    <ShieldCheck size={9} />
                    ACTIVE (₹{fav.autopay_amount || 'Max'})
                  </span>
                ) : (
                  <span className="text-zinc-650 text-[9px] block mt-1">DISABLED</span>
                )}
              </div>

              {/* Action */}
              <button
                onClick={() => onSelect(fav)}
                className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-cyan-400 text-[10px] px-3.5 py-1.5 rounded-lg transition-all cursor-pointer font-extrabold flex items-center gap-1 hover:shadow-md"
              >
                <CreditCard size={11} />
                <span>QUICK PAY</span>
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default FavoriteBillers;
