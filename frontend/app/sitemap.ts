import type { MetadataRoute } from "next";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const BASE_URL = "https://4cpa.org";

type QuestionItem = {
  id: string;
  created_at?: string | null;
};

async function fetchQuestions(): Promise<QuestionItem[]> {
  const apiBase = (
    process.env.INTERNAL_API_BASE_URL ||
    process.env.API_BASE_URL ||
    "http://backend:8000"
  ).replace(/\/+$/, "");

  try {
    const res = await fetch(`${apiBase}/questions?limit=500`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return [];
    const data = await res.json();
    const items: QuestionItem[] = Array.isArray(data)
      ? data
      : Array.isArray(data?.items)
      ? data.items
      : [];
    return items;
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const questions = await fetchQuestions();

  const forecastEntries: MetadataRoute.Sitemap = questions
    .filter((q) => q.id)
    .map((q) => ({
      url: `${BASE_URL}/forecast/${q.id}`,
      lastModified: q.created_at ? new Date(q.created_at) : new Date(),
      changeFrequency: "weekly" as const,
      priority: 0.7,
    }));

  return [
    {
      url: BASE_URL,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1.0,
    },
    ...forecastEntries,
  ];
}
