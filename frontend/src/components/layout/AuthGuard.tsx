"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { token, hydrated, hydrate, fetchMe, user } = useAuthStore();
  const router = useRouter();

  // Load the persisted token after mount so the first client render matches the
  // server-prerendered HTML (both see hydrated=false → render nothing).
  useEffect(() => {
    if (!hydrated) hydrate();
  }, [hydrated, hydrate]);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      router.push("/login");
    } else if (!user) {
      fetchMe();
    }
  }, [hydrated, token, user, router, fetchMe]);

  // Until we've checked localStorage, render nothing (consistent on server +
  // first client render). Prevents redirecting authed users to /login on refresh.
  if (!hydrated) return null;
  if (!token) return null;
  return <>{children}</>;
}
