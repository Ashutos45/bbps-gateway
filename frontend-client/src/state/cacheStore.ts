import { create } from 'zustand';
import { getCacheCount, getUniqueCategoriesAndRegions, hydrateBillerCache } from '../cache/db';

interface CacheState {
  cacheCount: number;
  hydrating: boolean;
  hydrationPercent: number;
  hydrationStatusText: string;
  error: string | null;
  categories: string[];
  regions: string[];

  checkCacheStatus: () => Promise<void>;
  hydrate: () => Promise<void>;
}

export const useCacheStore = create<CacheState>((set, get) => ({
  cacheCount: 0,
  hydrating: false,
  hydrationPercent: 0,
  hydrationStatusText: 'Uninitialized',
  error: null,
  categories: [],
  regions: [],

  checkCacheStatus: async () => {
    try {
      const count = await getCacheCount();
      const filters = await getUniqueCategoriesAndRegions();
      set({ 
        cacheCount: count, 
        categories: filters.categories, 
        regions: filters.regions 
      });
    } catch (err) {
      console.error('Failed to check cache count status', err);
    }
  },

  hydrate: async () => {
    const { hydrating } = get();
    if (hydrating) return;

    set({ 
      hydrating: true, 
      hydrationPercent: 0, 
      hydrationStatusText: 'Initiating...', 
      error: null 
    });
    
    const sourceId = import.meta.env.VITE_SOURCE_ID || 'mbanking';

    try {
      await hydrateBillerCache(sourceId, (percent, statusText) => {
        set({ 
          hydrationPercent: percent, 
          hydrationStatusText: statusText 
        });
      });
      await get().checkCacheStatus();
      set({ hydrating: false });
    } catch (err: any) {
      console.error('Hydration failed', err);
      set({ 
        hydrating: false, 
        error: err.message || 'Hydration process failed.' 
      });
    }
  }
}));
