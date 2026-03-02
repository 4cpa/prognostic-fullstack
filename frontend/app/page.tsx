"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

function slugify(input: string) {
  return input
    .trim()
    .toLowerCase()
    .replace(/ä/g, "ae")
    .replace(/ö/g, "oe")
    .replace(/ü/g, "ue")
    .replace(/ß/g, "ss")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

export default function Home() {
  const router = useRouter();
  const [question, setQuestion] = useState("");

  const slug = useMemo(() => slugify(question), [question]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!slug) return;
    router.push(`/forecast/${encodeURIComponent(slug)}`);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-black px-6">
      <main className="w-full max-w-3xl rounded-2xl bg-white dark:bg-black shadow-md p-10">
        <h1 className="text-3xl font-bold mb-2 text-black dark:text-zinc-50">
          4cpa Prognostic
        </h1>

        <p className="text-zinc-600 dark:text-zinc-400 mb-8">
          Gib eine politische oder wirtschaftliche Frage ein – wir erzeugen
          automatisch eine Prognose-Seite.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder='z.B. "Wird die EU zerbrechen?"'
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-700 px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-black/20 dark:bg-zinc-900 dark:text-white"
          />

          <button
            type="submit"
            disabled={!slug}
            className="h-12 rounded-lg bg-black text-white font-medium transition hover:bg-zinc-800 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-zinc-200"
          >
            Prognose anzeigen
          </button>
        </form>

        {slug && (
          <p className="mt-6 text-sm text-zinc-500 dark:text-zinc-400">
            Ziel-URL:{" "}
            <span className="font-mono">
              /forecast/{slug}
            </span>
          </p>
        )}

        <div className="mt-12 text-xs text-zinc-400">
          Beispiel:{" "}
          <a
            href="/forecast/wird-die-eu-zerbrechen"
            className="underline"
          >
            /forecast/wird-die-eu-zerbrechen
          </a>
        </div>
      </main>
    </div>
  );
}
