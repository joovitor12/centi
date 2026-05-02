import type { Newsletter, NewsletterPayload } from "@/types/newsletter";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(body?.detail ?? "Request failed.");
  }

  return (await response.json()) as T;
}

export async function listNewsletters(userId: string): Promise<Newsletter[]> {
  const search = new URLSearchParams({ user_id: userId });
  const response = await request<{ newsletters: Newsletter[] }>(
    `/newsletters?${search.toString()}`,
  );
  return response.newsletters;
}

export async function createNewsletter(
  userId: string,
  payload: NewsletterPayload,
): Promise<Newsletter> {
  return request<Newsletter>("/newsletters", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      ...payload,
    }),
  });
}

export async function updateNewsletter(
  newsletterId: number,
  userId: string,
  payload: Partial<NewsletterPayload> & { is_active?: boolean },
): Promise<Newsletter> {
  const search = new URLSearchParams({ user_id: userId });
  return request<Newsletter>(`/newsletters/${newsletterId}?${search.toString()}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteNewsletter(
  newsletterId: number,
  userId: string,
): Promise<void> {
  const search = new URLSearchParams({ user_id: userId });
  await request<{ ok: boolean }>(`/newsletters/${newsletterId}?${search.toString()}`, {
    method: "DELETE",
  });
}

export async function generateNewsletter(
  newsletterId: number,
  userId: string,
): Promise<Newsletter> {
  const search = new URLSearchParams({ user_id: userId, language: "pt-BR" });
  return request<Newsletter>(
    `/newsletters/${newsletterId}/generate?${search.toString()}`,
    {
      method: "POST",
    },
  );
}

export async function sendNewsletter(
  newsletterId: number,
  userId: string,
): Promise<{ ok: boolean; provider_message_id: string }> {
  const search = new URLSearchParams({ user_id: userId });
  return request<{ ok: boolean; provider_message_id: string }>(
    `/newsletters/${newsletterId}/send?${search.toString()}`,
    {
      method: "POST",
    },
  );
}
