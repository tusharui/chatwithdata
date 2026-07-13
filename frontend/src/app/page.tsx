"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user) {
      router.push("/dashboard");
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-black border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (user) return null;

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="flex items-center justify-between px-8 py-4 border-b border-black/10">
        <span className="text-lg font-bold tracking-tight">ChatWithData</span>
        <div className="flex items-center gap-3">
          <Link href="/login" className="px-4 py-2 text-sm text-neutral-600 hover:text-black transition-colors">
            Sign in
          </Link>
          <Link href="/register" className="px-4 py-2 bg-black text-white text-sm font-medium rounded-lg hover:bg-black/80 transition-colors">
            Get started
          </Link>
        </div>
      </nav>

      <main className="flex-1 flex flex-col items-center justify-center text-center px-8">
        <div className="w-16 h-16 bg-black rounded-2xl flex items-center justify-center mb-6">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <h1 className="text-4xl font-bold tracking-tight mb-3">Chat with your data</h1>
        <p className="text-neutral-500 text-lg max-w-lg mb-8">
          Upload CSV or Excel files and ask questions in natural language. Get instant SQL-powered answers with charts.
        </p>
        <div className="flex gap-3">
          <Link href="/register" className="px-6 py-3 bg-black text-white font-medium rounded-xl hover:bg-black/80 transition-colors">
            Start for free
          </Link>
          <Link href="/login" className="px-6 py-3 border border-black/20 font-medium rounded-xl hover:border-black/40 transition-colors">
            Sign in
          </Link>
        </div>
      </main>
    </div>
  );
}
