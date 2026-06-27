"use client";
import { create } from "zustand";
import type { User } from "@/types";
import api from "@/lib/api";

interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: typeof window !== "undefined" ? localStorage.getItem("access_token") : null,

  login: async (email, password) => {
    const res = await api.post("/auth/login", { email, password });
    const token = res.data.access_token;
    localStorage.setItem("access_token", token);
    set({ token });
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
