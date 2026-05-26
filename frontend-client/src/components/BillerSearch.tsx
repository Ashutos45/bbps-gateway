import React from 'react';
import { Search, SlidersHorizontal, RotateCcw } from 'lucide-react';

interface BillerSearchProps {
  search: string;
  category: string;
  region: string;
  categories: string[];
  regions: string[];
  onSearchChange: (val: string) => void;
  onCategoryChange: (val: string) => void;
  onRegionChange: (val: string) => void;
  onClearFilters: () => void;
}

export const BillerSearch: React.FC<BillerSearchProps> = ({
  search,
  category,
  region,
  categories,
  regions,
  onSearchChange,
  onCategoryChange,
  onRegionChange,
  onClearFilters,
}) => {
  return (
    <div className="bg-transparent space-y-4">
      {/* Grid search filters */}
      <div className="space-y-3.5">
        {/* Search Query */}
        <div className="relative">
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Search Biller / ID</label>
          <div className="relative">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-zinc-500">
              <Search size={14} />
            </span>
            <input
              type="text"
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="e.g. UPPCL, DTH, MOCK..."
              className="input-premium pl-9 font-mono"
            />
          </div>
        </div>

        {/* Category Select */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Biller Category</label>
          <div className="relative">
            <select
              value={category}
              onChange={(e) => onCategoryChange(e.target.value)}
              className="input-premium appearance-none bg-zinc-950 font-mono pr-8"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
            <span className="absolute inset-y-0 right-0 pr-3 flex items-center text-zinc-500 pointer-events-none">
              <SlidersHorizontal size={12} />
            </span>
          </div>
        </div>

        {/* Region Select */}
        <div>
          <label className="block text-[10px] font-mono font-bold text-zinc-550 mb-1.5 uppercase tracking-wider">Biller Region</label>
          <div className="relative">
            <select
              value={region}
              onChange={(e) => onRegionChange(e.target.value)}
              className="input-premium appearance-none bg-zinc-950 font-mono pr-8"
            >
              <option value="">All Regions</option>
              {regions.map((reg) => (
                <option key={reg} value={reg}>
                  {reg}
                </option>
              ))}
            </select>
            <span className="absolute inset-y-0 right-0 pr-3 flex items-center text-zinc-500 pointer-events-none">
              <SlidersHorizontal size={12} />
            </span>
          </div>
        </div>
      </div>

      {/* Action / Reset Button */}
      {(search || category || region) && (
        <div className="flex justify-end pt-1">
          <button
            onClick={onClearFilters}
            className="text-[10px] font-mono text-zinc-550 hover:text-zinc-350 transition-colors flex items-center gap-1 cursor-pointer underline underline-offset-2"
          >
            <RotateCcw size={10} />
            <span>Reset Filters</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default BillerSearch;
