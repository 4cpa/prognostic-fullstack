"use client";

import { useState } from "react";

const STORAGE_KEY = "anthropic_api_key";

const STEPS = [
  {
    n: 1,
    title: "Anthropic-Konto öffnen",
    body: (
      <>
        Gehe zu{" "}
        <a
          href="https://console.anthropic.com"
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-amber-800 underline underline-offset-2"
        >
          console.anthropic.com
        </a>{" "}
        und melde dich an (oder erstelle ein kostenloses Konto).
      </>
    ),
  },
  {
    n: 2,
    title: "API-Key erstellen",
    body: (
      <>
        Klicke links auf <strong>API Keys</strong> → <strong>+ Create Key</strong>.
        Gib dem Key einen Namen (z. B. «4cpa») und kopiere ihn — er wird nur einmal angezeigt.
      </>
    ),
  },
  {
    n: 3,
    title: "Key hier eingeben",
    body: "Füge den Key unten ein und klicke «Speichern». Er wird nur in deinem Browser gespeichert.",
  },
];

interface Props {
  onSaved: () => void;
  onDismiss: () => void;
}

export default function ApiKeyGuide({ onSaved, onDismiss }: Props) {
  const [key, setKey] = useState("");
  const [step, setStep] = useState(0);
  const [saved, setSaved] = useState(false);

  function handleSave() {
    const trimmed = key.trim();
    if (!trimmed.startsWith("sk-")) return;
    localStorage.setItem(STORAGE_KEY, trimmed);
    setSaved(true);
    setTimeout(onSaved, 800);
  }

  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-amber-900">Kein API-Key gefunden</p>
          <p className="mt-0.5 text-xs text-amber-700">
            Für KI-gestützte Prognosen wird ein Anthropic-API-Key benötigt.
          </p>
        </div>
        <button
          onClick={onDismiss}
          className="mt-0.5 text-amber-400 hover:text-amber-700"
          aria-label="Schließen"
        >
          <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      </div>

      {/* Schritte */}
      <ol className="mb-4 space-y-3">
        {STEPS.map((s, i) => (
          <li
            key={s.n}
            className={`flex gap-3 rounded-xl px-3 py-2.5 text-xs transition ${
              step === i ? "bg-white ring-1 ring-amber-200" : "opacity-60"
            }`}
            onClick={() => setStep(i)}
            role="button"
          >
            <span
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                step === i ? "bg-amber-700 text-white" : "bg-amber-200 text-amber-700"
              }`}
            >
              {s.n}
            </span>
            <div>
              <p className="font-medium text-amber-900">{s.title}</p>
              <p className="mt-0.5 leading-relaxed text-amber-700">{s.body}</p>
            </div>
          </li>
        ))}
      </ol>

      {/* Key-Eingabe */}
      <div className="flex gap-2">
        <input
          type="password"
          value={key}
          onChange={(e) => { setKey(e.target.value); setStep(2); }}
          onKeyDown={(e) => e.key === "Enter" && handleSave()}
          placeholder="sk-ant-..."
          autoComplete="off"
          className="flex-1 rounded-xl border border-amber-300 bg-white px-3 py-2 text-sm outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-400"
        />
        <button
          onClick={handleSave}
          disabled={!key.trim().startsWith("sk-") || saved}
          className="rounded-xl bg-amber-700 px-4 py-2 text-sm font-medium text-white hover:bg-amber-800 disabled:opacity-40"
        >
          {saved ? "✓ Gespeichert" : "Speichern"}
        </button>
      </div>
    </div>
  );
}
