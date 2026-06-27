"use client";
import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // A stale cached HTML shell can reference chunk filenames that no longer
    // exist after a redeploy, producing a ChunkLoadError. A single hard reload
    // fetches the current shell and recovers. Guard against reload loops.
    const isChunkError =
      error?.name === "ChunkLoadError" ||
      /Loading chunk|dynamically imported module|Failed to fetch/i.test(
        error?.message || ""
      );
    if (isChunkError && typeof window !== "undefined") {
      if (!sessionStorage.getItem("chunk_reloaded")) {
        sessionStorage.setItem("chunk_reloaded", "1");
        window.location.reload();
      }
    }
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-6">
      <div className="max-w-md w-full text-center">
        <h1 className="text-xl font-semibold text-white mb-2">
          Something went wrong
        </h1>
        <p className="text-slate-400 text-sm mb-6">
          The app hit an unexpected error. Reloading usually fixes it.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => {
              if (typeof window !== "undefined")
                sessionStorage.removeItem("chunk_reloaded");
              reset();
            }}
            className="bg-primary-600 hover:bg-primary-500 text-white px-4 py-2 rounded-lg text-sm transition-colors"
          >
            Try again
          </button>
          <button
            onClick={() => {
              if (typeof window !== "undefined") window.location.reload();
            }}
            className="bg-surface-3 hover:bg-surface-2 text-slate-200 px-4 py-2 rounded-lg text-sm transition-colors"
          >
            Reload page
          </button>
        </div>
      </div>
    </div>
  );
}
