"use client";

import { useState } from "react";

interface TableData {
  rows: Record<string, unknown>[];
  total_rows: number;
}

export function DataTable({ data }: { data: TableData }) {
  const [page, setPage] = useState(0);
  const pageSize = 10;
  const totalPages = Math.ceil(data.rows.length / pageSize);
  const currentRows = data.rows.slice(page * pageSize, (page + 1) * pageSize);
  const columns = data.rows.length > 0 ? Object.keys(data.rows[0]) : [];

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-neutral-500">
          {data.total_rows.toLocaleString()} total rows
          {data.rows.length < data.total_rows && ` (showing ${data.rows.length})`}
        </p>
      </div>
      <div className="overflow-x-auto border border-black/10 rounded-lg">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-neutral-100 border-b border-black/10">
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 text-left font-medium text-neutral-600 whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {currentRows.map((row, i) => (
              <tr key={i} className="border-b border-black/5 last:border-0">
                {columns.map((col) => (
                  <td key={col} className="px-3 py-2 text-neutral-700 whitespace-nowrap max-w-[200px] truncate">
                    {row[col] === null ? (
                      <span className="text-neutral-300 italic">null</span>
                    ) : (
                      String(row[col])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-2">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="text-[11px] text-neutral-500 hover:text-black disabled:opacity-30 transition-colors"
          >
            &larr; Previous
          </button>
          <span className="text-[11px] text-neutral-400">
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="text-[11px] text-neutral-500 hover:text-black disabled:opacity-30 transition-colors"
          >
            Next &rarr;
          </button>
        </div>
      )}
    </div>
  );
}
