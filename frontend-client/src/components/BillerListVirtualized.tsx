import React, { useState, useRef, UIEvent } from 'react';
import { Layers } from 'lucide-react';
import { Biller } from '../types';

interface BillerListVirtualizedProps {
  billers: Biller[];
  onSelectBiller: (biller: Biller) => void;
  selectedBillerId?: string;
  itemHeight?: number;
  height?: number;
}

export const BillerListVirtualized: React.FC<BillerListVirtualizedProps> = ({
  billers,
  onSelectBiller,
  selectedBillerId,
  itemHeight = 68,
  height = 400,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  
  const handleScroll = (e: UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop);
  };

  const totalHeight = billers.length * itemHeight;
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - 3);
  const endIndex = Math.min(billers.length, Math.ceil((scrollTop + height) / itemHeight) + 3);
  
  const visibleBillers = billers.slice(startIndex, endIndex);

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="overflow-y-auto border border-zinc-800/80 rounded-xl bg-zinc-950/40 scrollbar-thin scrollbar-thumb-zinc-800"
      style={{ height, position: 'relative' }}
    >
      <div style={{ height: totalHeight, width: '100%', pointerEvents: 'none' }} />
      <div
        className="absolute top-0 left-0 w-full"
        style={{
          transform: `translateY(${startIndex * itemHeight}px)`,
        }}
      >
        {visibleBillers.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center text-zinc-550 text-xs font-sans gap-2"
            style={{ height }}
          >
            <Layers size={20} className="text-zinc-650" />
            <span>No operators found matching criteria.</span>
          </div>
        ) : (
          visibleBillers.map((biller) => {
            const isSelected = selectedBillerId === biller.biller_id;
            return (
              <div
                key={biller.biller_id}
                onClick={() => onSelectBiller(biller)}
                className={`flex items-center justify-between px-4.5 py-2.5 border-b border-zinc-900/60 cursor-pointer select-none transition-all duration-150 ${
                  isSelected 
                    ? 'bg-cyan-950/20 border-l-4 border-l-cyan-400 border-zinc-850 shadow-[inset_0_0_12px_rgba(6,182,212,0.05)]' 
                    : 'bg-transparent hover:bg-zinc-900/30'
                }`}
                style={{ height: itemHeight, boxSizing: 'border-box' }}
              >
                <div className="flex-1 min-w-0 pr-2">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-xs text-zinc-200 truncate font-display">
                      {biller.biller_name}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2.5 mt-1 font-mono">
                    <span className="text-[10px] text-zinc-550 truncate">
                      {biller.biller_id}
                    </span>
                    <span className="text-[9px] px-1.5 py-0.2 bg-zinc-900 text-zinc-400 rounded border border-zinc-800/40">
                      {biller.category}
                    </span>
                  </div>
                </div>
                <div className="text-right text-[10px] text-zinc-400 font-mono">
                  <span className="block text-zinc-500">{biller.region}</span>
                  {biller.metadata?.min_amount && (
                    <span className="text-[9px] text-emerald-400 font-semibold block mt-0.5">
                      Min: ₹{biller.metadata.min_amount}
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default BillerListVirtualized;
