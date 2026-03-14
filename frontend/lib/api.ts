export type QuestionCreate = {
  title: string;
  description: string;
  category?: string;
  region?: string | null;
  country?: string | null;
  resolve_at: string;
  resolution_criteria: string;
  resolution_source_policy?: string;
};

export type QuestionRead = {
  id: string;
  title: string;
  description: string;
  category: string;
  region?: string | null;
  country?: string | null;
  created_at: string;
  resolve_at: string;
  resolution_criteria: string;
  resolution_source_policy: string;
  status: string;
  resolved_at?: string | null;
  resolved_by?: string | null;
  notes?: string | null;
};

export type ForecastRead = {
  id: string;
  question_id: string;
  probability: number; // 0..1
  method: string;
  method_version: string;
  explanation_md: string;
  inputs_hash: string;
  created_at?: string;
};

function apiBase(): string {
  const isBrowser = typeof window !== "undefined";

  const base = isBrowser
    ? process.env.NEXT_PUBLIC_API_BASE_URL || "/api"
    : process.env.API_BASE_URL || "http://backend:8000";

  return base.replace(/\/+$/, "");
}

function apiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${apiBase()}${normalizedPath}`;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = apiUrl(path);
  const res = await fetch(url, init);

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`${init?.method ?? "GET"} ${url} failed: ${res.status} ${msg}`);
  }

  return res.json() as Promise<T>;
}

export async function createQuestion(payload: QuestionCreate): Promise<QuestionRead> {
  return requestJson<QuestionRead>("/questions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function getQuestion(id: string): Promise<QuestionRead> {
  return requestJson<QuestionRead>(`/questions/${encodeURIComponent(id)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
}

export async function createForecast(
  questionId: string,
  methodVersion = "v0.1.0"
): Promise<ForecastRead> {
  return requestJson<ForecastRead>(
    `/questions/${encodeURIComponent(questionId)}/forecast?method_version=${encodeURIComponent(methodVersion)}`,
    {
      method: "POST",
      headers: { Accept: "application/json" },
    }
  );
}

export async function getForecasts(questionId: string): Promise<ForecastRead[]> {
  return requestJson<ForecastRead[]>(
    `/questions/${encodeURIComponent(questionId)}/forecasts`,
    {
      method: "GET",
      headers: { Accept: "application/json" },
    }
  );
}
