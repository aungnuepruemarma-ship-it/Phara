"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import clsx from "clsx";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/projects", label: "Projects" },
  { href: "/chat", label: "Agent Chat" },
  { href: "/research", label: "Research" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  return (
    <aside className="w-56 min-h-screen bg-surface-2 flex flex-col border-r border-surface-3">
      <div className="px-6 py-5 border-b border-surface-3">
        <span className="text-primary-500 font-bold text-lg tracking-tight">UIL</span>
        <p className="text-xs text-slate-400 mt-0.5">Intelligence Lab</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              "block px-3 py-2 rounded-md text-sm font-medium transition-colors",
              pathname.startsWith(item.href)
                ? "bg-primary-700 text-white"
                : "text-slate-300 hover:bg-surface-3"
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      {user && (
        <div className="px-4 py-4 border-t border-surface-3">
          <p className="text-xs text-slate-400 truncate">{user.email}</p>
          <p className="text-xs text-slate-500 capitalize">{user.role}</p>
          <button
            onClick={logout}
            className="mt-2 text-xs text-red-400 hover:text-red-300 transition-colors"
          >
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}
