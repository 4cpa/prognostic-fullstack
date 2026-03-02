"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

function slugify(input: string) {
  return input
    .trim()
    .toLowerCase()
    // deutsche Umlaute grob
    .replace(/ä/g, "ae")
    .replace(/ö/g, "oe")
    .replace(/ü/g, "ue")
    .replace(/ß/g, "ss")
    // alles was kein buchstabe/zahl ist -> "-"
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

export default function SearchForm() {
  const router = useRouter();
  const [q, setQ] = useState("");

  const slug = useMemo(() => slugify(q), [q]);

  return (
    <form
      className="w-full max-w-2xl"
      onSubmit={(e) => {
        e.preventDefault();
        const s = slugify(q);
        if (!s) return;
        router.push(`/forecast/${encodeURIComponent(s)}`);
      }}
    >
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Frage eingeben
      </label>

      <div className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder='z.B. "Wird die EU zerbrechen?"'
          className="flex-1 rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-black/20"
        />
        <button
          type="submit"
          className="rounded-lg bg-black text-white px-5 py-3 font-medium disabled:opacity-50"
          disabled={!slug}
        >
          Prognose
        </button>
      </div>

      <p className="mt-3 text-sm text-gray-500">
        Ziel: <span className="font-mono">/forecast/{slug || "..."}</span>
      </p>
    </form>
  );
}
