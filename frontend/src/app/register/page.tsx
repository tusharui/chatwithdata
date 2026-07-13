"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(email, name, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Link href="/" className="text-lg font-bold tracking-tight">ChatWithData</Link>
          <p className="text-sm text-neutral-500 mt-2">Create your account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-xs px-3 py-2 rounded-lg">
              {error}
            </div>
          )}
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Full name"
            required
            className="w-full px-3.5 py-2.5 border border-black/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
          />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email address"
            required
            className="w-full px-3.5 py-2.5 border border-black/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password (min 8 characters)"
            required
            minLength={8}
            className="w-full px-3.5 py-2.5 border border-black/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black/20"
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2.5 bg-black text-white text-sm font-medium rounded-lg hover:bg-black/80 disabled:opacity-30 transition-colors"
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="text-center text-xs text-neutral-500 mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-black font-medium hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
