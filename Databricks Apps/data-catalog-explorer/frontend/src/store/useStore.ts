import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { FilterOptions } from '../types';

interface AppState {
  favorites: string[];
  recentlyViewed: string[];
  searchQuery: string;
  filters: FilterOptions;
  toastMessage: string | null;

  toggleFavorite: (objectId: string) => void;
  addRecentlyViewed: (objectId: string) => void;
  setSearchQuery: (query: string) => void;
  setFilters: (filters: FilterOptions) => void;
  clearFilters: () => void;
  showToast: (message: string) => void;
  hideToast: () => void;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      favorites: [],
      recentlyViewed: [],
      searchQuery: '',
      filters: {},
      toastMessage: null,

      toggleFavorite: (objectId: string) => {
        const { favorites } = get();
        if (favorites.includes(objectId)) {
          set({ favorites: favorites.filter(id => id !== objectId) });
        } else {
          set({ favorites: [...favorites, objectId] });
        }
      },

      addRecentlyViewed: (objectId: string) => {
        const { recentlyViewed } = get();
        const filtered = recentlyViewed.filter(id => id !== objectId);
        set({ recentlyViewed: [objectId, ...filtered].slice(0, 20) });
      },

      setSearchQuery: (query: string) => set({ searchQuery: query }),

      setFilters: (filters: FilterOptions) => set({ filters }),

      clearFilters: () => set({ filters: {} }),

      showToast: (message: string) => {
        set({ toastMessage: message });
        setTimeout(() => set({ toastMessage: null }), 3000);
      },

      hideToast: () => set({ toastMessage: null }),
    }),
    {
      name: 'data-catalog-store',
      partialize: (state) => ({
        favorites: state.favorites,
        recentlyViewed: state.recentlyViewed,
      }),
    }
  )
);
