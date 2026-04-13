"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "anthropic_api_key";

export function getStoredApiKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(STORAGE_KEY) ?? "";
}

export default function ApiKeyBanner() {
  const [key, setKey] = useState("");
  const [saved, setSaved] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const stored = getStoredApiKey();
    if (stored) {
      setKey(stored);
      setSaved(true);
    } else {
      setOpen(true);
    }
  }, []);

  function handleSave() {
    localStorage.setItem(STORAGE_KEY, key.trim());
    setSaved(true);
    setOpen(false);
  }

  function handleClear() {
    localStorage.removeItem(STORAGE_KEY);
    setKey("");
    setSaved(false);
    setOpen(true);
  }

  if (!open) {
    return (
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-500">
        <span>
          {saved ? (
            <span className="text-green-700 font-medium">✓ Anthropic API-Key gespeichert</span>
          ) : (
            <span className="text-amber-700 font-medium">⚠ Kein API-Key — LLM deaktiviert</span>
          )}
        </span>
        <button
          onClick={() => setOpen(true)}
          className="ml-4 rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-200 hover:text-slate-800"
        >
          {saved ? "Ändern" : "Key eingeben"}
        </button>
      </div>
    );
  }

  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-3">
      <div className="mx-auto max-w-3xl">
        <p className="mb-2 text-sm font-medium text-amber-900">
          Anthropic API-Key eingeben (wird nur im Browser gespeichert)
        </p>
        <div className="flex gap-2">
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSave()}
            placeholder="sk-ant-..."
            autoComplete="off"
            className="flex-1 rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
          />
          <button
            onClick={handleSave}
            disabled={!key.trim().startsWith("sk-")}
            className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-medium text-white hover:bg-amber-800 disabled:opacity-40"
          >
            Speichern
          </button>
          {saved && (
            <button
              onClick={handleClear}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
            >
              Löschen
            </button>
          )}
        </div>
        <p className="mt-1.5 text-xs text-amber-700">
          Key wird nur in deinem Browser gespeichert und direkt an den Server gesendet — kein Logging.
        </p>
      </div>
    </div>
  );
}
