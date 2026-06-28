"use client";
import { create } from "zustand";
import type { User } from "@/types";
import api from "@/lib/api";

interface AuthState {
  user: User | null;
  token: string | null;
  hydrated: boolean;
  hydrate: () => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  // Initialized to null on both server-prerender and the first client render so
  // hydration matches. The real token is loaded from localStorage in hydrate(),
  // called from AuthGuard's effect after mount (avoids React #418 mismatch).
  token: null,
  hydrated: false,

  hydrate: () => {
    if (typeof window === "undefined") return;
    set({ token: localStorage.getItem("access_token"), hydrated: true });
  },

  login: async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    const token = res.data.access_token;
    localStorage.setItem("access_token", token);
    set({ token, hydrated: true });
    const me = await api.get("/auth/me");
    set({ user: me.data });
  },

  logout: () => {
    localStorage.removeItem("access_token");
    set({ user: null, token: null });
    window.location.href = "/login";
  },

  fetchMe: async () => {
    try {
      const res = await api.get("/auth/me");
      set({ user: res.data });
    } catch {
      set({ user: null, token: null });
    }
  },
}));
