"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { formatFileSize, formatDate } from "@/lib/utils";

const ALLOWED_EXTENSIONS = ["csv", "xlsx", "xls"];
const MAX_FILE_SIZE = 50 * 1024 * 1024;

interface Dataset {
  id: string;
  name: string;
  filename: string;
  row_count: number;
  column_count: number;
  status: string;
  created_at: string;
  columns: unknown[];
}

function validateFile(file: File): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() || "";
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
  }
  if (file.size > MAX_FILE_SIZE) {
    return `File too large. Max ${Math.round(MAX_FILE_SIZE / 1024 / 1024)}MB`;
  }
  return null;
}

export default function DashboardPage() {
  const { user, token, isLoading, logout } = useAuth();
  const router = useRouter();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [uploadName, setUploadName] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !user) router.push("/login");
  }, [user, isLoading, router]);

  useEffect(() => {
    if (!token) return;
    setLoadError(null);
    api.datasets.list(token).then((res) => setDatasets(res.datasets || [])).catch(() => setLoadError("Failed to load datasets")).finally(() => setLoading(false));
  }, [token]);

  const handleUpload = async (file: File) => {
    if (!token) return;
    const validationError = validateFile(file);
    if (validationError) { alert(validationError); return; }
    setUploading(true);
    try {
      const ds = await api.datasets.upload(file, uploadName || file.name.split(".")[0], "", token);
      setDatasets((prev) => [ds, ...prev]);
      setShowUpload(false);
      setUploadName("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleDelete = async (id: string) => {
    if (!token || deleting) return;
    if (!confirm("Delete this dataset and all its conversations?")) return;
    setDeleting(id);
    try {
      await api.datasets.delete(id, token);
      setDatasets((prev) => prev.filter((d) => d.id !== id));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeleting(null);
    }
  };

  if (isLoading || !user) {
    return <div className="min-h-screen flex items-center justify-center"><div className="w-6 h-6 border-2 border-black border-t-transparent rounded-full animate-spin" /></div>;
  }

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="flex items-center justify-between px-8 py-4 border-b border-black/10">
        <Link href="/dashboard" className="text-lg font-bold tracking-tight">ChatWithData</Link>
        <div className="flex items-center gap-4">
          <span className="text-xs text-neutral-500">{user.name}</span>
          <button onClick={logout} className="text-xs text-neutral-400 hover:text-black transition-colors">Log out</button>
        </div>
      </nav>

      <main className="flex-1 max-w-5xl mx-auto w-full px-8 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Datasets</h1>
            <p className="text-sm text-neutral-500 mt-1">Upload CSV or Excel files to start chatting with your data</p>
          </div>
          <button onClick={() => setShowUpload(true)} className="px-5 py-2.5 bg-black text-white text-sm font-medium rounded-lg hover:bg-black/80 transition-colors">Upload dataset</button>
        </div>

        {showUpload && (
          <div className="mb-8 border border-black/10 rounded-xl p-6">
            <h3 className="text-sm font-medium mb-4">Upload new dataset</h3>
            <input type="text" value={uploadName} onChange={(e) => setUploadName(e.target.value.slice(0, 100))} placeholder="Dataset name (optional)" maxLength={100} className="w-full px-3.5 py-2.5 border border-black/20 rounded-lg text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-black/20" />
            <div onDragOver={(e) => { e.preventDefault(); setDragActive(true); }} onDragLeave={() => setDragActive(false)} onDrop={handleDrop} className={`border-2 border-dashed rounded-lg p-10 text-center transition-colors cursor-pointer ${dragActive ? "border-black bg-neutral-50" : "border-black/20 hover:border-black/40"}`} onClick={() => { const input = document.createElement("input"); input.type = "file"; input.accept = ".csv,.xlsx,.xls"; input.onchange = (e) => { const file = (e.target as HTMLInputElement).files?.[0]; if (file) handleUpload(file); }; input.click(); }}>
              {uploading ? (
                <div className="flex items-center justify-center gap-2"><div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" /><span className="text-sm text-neutral-500">Uploading...</span></div>
              ) : (
                <><p className="text-sm text-neutral-500">Drop a CSV or Excel file here, or click to browse</p><p className="text-xs text-neutral-400 mt-1">Max 50MB</p></>
              )}
            </div>
            <button onClick={() => { setShowUpload(false); setUploadName(""); }} className="mt-4 text-xs text-neutral-400 hover:text-black transition-colors">Cancel</button>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20"><div className="w-6 h-6 border-2 border-black border-t-transparent rounded-full animate-spin" /></div>
        ) : loadError ? (
          <div className="text-center py-20 border border-dashed border-black/20 rounded-xl">
            <p className="text-red-500 text-sm mb-2">{loadError}</p>
            <button onClick={() => { setLoadError(null); setLoading(true); if (token) { api.datasets.list(token).then((res) => setDatasets(res.datasets || [])).catch(() => setLoadError("Failed to load datasets")).finally(() => setLoading(false)); } }} className="text-xs text-neutral-500 hover:text-black transition-colors">Retry</button>
          </div>
        ) : datasets.length === 0 ? (
          <div className="text-center py-20 border border-dashed border-black/20 rounded-xl">
            <p className="text-neutral-500 text-sm">No datasets yet</p>
            <p className="text-neutral-400 text-xs mt-1">Upload a CSV or Excel file to get started</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {datasets.map((ds) => (
              <div key={ds.id} className="border border-black/10 rounded-xl p-5 hover:border-black/30 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="font-medium text-sm">{ds.name}</h3>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${ds.status === "ready" ? "bg-black text-white" : ds.status === "error" ? "bg-red-100 text-red-700" : "bg-neutral-200 text-neutral-600"}`}>{ds.status}</span>
                    </div>
                    <p className="text-xs text-neutral-500 mt-1">{ds.filename} &middot; {(ds.row_count ?? 0).toLocaleString()} rows &middot; {ds.column_count ?? 0} columns &middot; {formatDate(ds.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {ds.status === "ready" && <Link href={`/chat?dataset=${encodeURIComponent(ds.id)}`} className="px-4 py-2 bg-black text-white text-xs font-medium rounded-lg hover:bg-black/80 transition-colors">Chat</Link>}
                    <button onClick={() => handleDelete(ds.id)} disabled={deleting === ds.id} className="px-3 py-2 text-xs text-neutral-400 hover:text-black border border-black/10 rounded-lg hover:border-black/30 transition-colors disabled:opacity-30">{deleting === ds.id ? "Deleting..." : "Delete"}</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
