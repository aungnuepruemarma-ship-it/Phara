"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { token, fetchMe, user } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!token) {
      router.push("/login");
    } else if (!user) {
      fetchMe();
    }
  }, [token, user, router, fetchMe]);

  if (!token) return null;
  return <>{children}</>;
}
