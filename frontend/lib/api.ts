export type QuestionCreate = {
  text: string;
};

export type QuestionRead = {
  id: string;
  text: string;
  status?: string;
  forecast?: unknown;
  result?: unknown;
};

export async function createQuestion(text: string): Promise<QuestionRead> {
  const res = await fetch("/api/questions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text } satisfies QuestionCreate),
  });

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`POST /api/questions failed: ${res.status} ${msg}`);
  }

  return res.json();
}

export async function getQuestion(id: string): Promise<QuestionRead> {
  const res = await fetch(`/api/questions/${encodeURIComponent(id)}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`GET /api/questions/${id} failed: ${res.status} ${msg}`);
  }

  return res.json();
}
