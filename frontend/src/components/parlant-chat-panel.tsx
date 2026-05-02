"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Loader2, SendHorizonal } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ParlantChatPanelProps = {
  customerId: string;
  customerEmail?: string | null;
  locale: "pt" | "en";
};

type ParlantEvent = {
  id: string;
  source: string;
  kind: string;
  offset: number;
  data?: unknown;
};
const POLL_SECONDS = 25;

function extractMessageText(event: ParlantEvent): string {
  const payload = event.data;
  if (!payload || typeof payload !== "object") {
    return "";
  }

  const data = payload as Record<string, unknown>;
  if (typeof data.message === "string") {
    return data.message;
  }
  if (typeof data.content === "string") {
    return data.content;
  }
  if (typeof data.text === "string") {
    return data.text;
  }
  return "";
}

function sourceLabel(source: string, locale: "pt" | "en"): string {
  if (source === "customer" || source === "customer_ui") {
    return locale === "pt" ? "Voce" : "You";
  }
  if (source === "ai_agent") {
    return "Centi";
  }
  return source;
}

export function ParlantChatPanel({
  customerId,
  customerEmail,
  locale,
}: ParlantChatPanelProps) {
  const server = process.env.NEXT_PUBLIC_PARLANT_SERVER_URL;
  const agentId = process.env.NEXT_PUBLIC_PARLANT_AGENT_ID;
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [events, setEvents] = useState<ParlantEvent[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const pendingCustomerOffsetRef = useRef<number | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const isInitializing = sessionId === null;
  const sessionStorageKey = useMemo(
    () => `parlant:session:${agentId ?? "unknown"}:${customerId}`,
    [agentId, customerId],
  );
  const text = {
    configure:
      locale === "pt"
        ? "Configure `NEXT_PUBLIC_PARLANT_SERVER_URL` e `NEXT_PUBLIC_PARLANT_AGENT_ID` para usar o chat."
        : "Set `NEXT_PUBLIC_PARLANT_SERVER_URL` and `NEXT_PUBLIC_PARLANT_AGENT_ID` to use chat.",
    initError: locale === "pt" ? "Erro ao iniciar chat." : "Could not initialize chat.",
    streamError: locale === "pt" ? "Erro no stream." : "Streaming connection error.",
    sendError: locale === "pt" ? "Erro ao enviar mensagem." : "Could not send message.",
    sessionUnavailable: locale === "pt" ? "Sessao indisponivel." : "Session unavailable.",
    emptyState:
      locale === "pt"
        ? "Envie a primeira mensagem para iniciar a conversa."
        : "Send the first message to start chatting.",
    emptyMessage: locale === "pt" ? "(mensagem vazia)" : "(empty message)",
    placeholder:
      locale === "pt" ? "Digite sua mensagem..." : "Type your message...",
    sessionTitle: locale === "pt" ? "Chat Centi" : "Centi Chat",
  };
  const { initError, streamError, sendError, sessionUnavailable, sessionTitle } = text;

  const resetSession = useCallback(() => {
    window.localStorage.removeItem(sessionStorageKey);
    pendingCustomerOffsetRef.current = null;
    setEvents([]);
    setSessionId(null);
  }, [sessionStorageKey]);

  const messages = useMemo(
    () =>
      events.filter(
        (event) =>
          event.kind === "message" &&
          (event.source === "customer" ||
            event.source === "customer_ui" ||
            event.source === "ai_agent" ||
            event.source === "human_agent"),
      ),
    [events],
  );

  const mergeEvents = (incoming: ParlantEvent[]) => {
    if (incoming.length === 0) {
      return;
    }

    const pendingOffset = pendingCustomerOffsetRef.current;
    if (
      pendingOffset !== null &&
      incoming.some((event) => event.source === "ai_agent" && event.offset > pendingOffset)
    ) {
      pendingCustomerOffsetRef.current = null;
    }

    setEvents((previous) => {
      const merged = new Map(previous.map((event) => [event.id, event]));
      incoming.forEach((event) => merged.set(event.id, event));
      return [...merged.values()].sort((a, b) => a.offset - b.offset);
    });
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  useEffect(() => {
    if (!server || !agentId || !customerId || sessionId) {
      return;
    }

    let cancelled = false;

    const initSession = async () => {
      try {
        // Reuse a Parlant customer mapped to this authenticated Supabase user.
        const customersResponse = await fetch(`${server}/customers`, { method: "GET" });
        if (!customersResponse.ok) {
          throw new Error(`Falha ao listar customers (${customersResponse.status}).`);
        }
        const customers = (await customersResponse.json()) as Array<{
          id: string;
          metadata?: Record<string, string>;
        }>;

        let parlantCustomerId =
          customers.find((item) => item.metadata?.user_id === customerId)?.id ?? null;

        if (!parlantCustomerId) {
          const createCustomerResponse = await fetch(`${server}/customers`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: customerEmail || customerId,
              metadata: {
                user_id: customerId,
                ...(customerEmail ? { email: customerEmail } : {}),
              },
            }),
          });

          if (!createCustomerResponse.ok) {
            throw new Error(
              `Falha ao criar customer no Parlant (${createCustomerResponse.status}).`,
            );
          }

          const createdCustomer = (await createCustomerResponse.json()) as { id: string };
          parlantCustomerId = createdCustomer.id;
        }

        const cachedSessionId = window.localStorage.getItem(sessionStorageKey);
        if (cachedSessionId) {
          const cachedSessionResponse = await fetch(
            `${server}/sessions/${encodeURIComponent(cachedSessionId)}`,
            { method: "GET" },
          );

          if (cachedSessionResponse.ok) {
            if (!cancelled) {
              setSessionId(cachedSessionId);
            }
            return;
          }
        }

        const createSessionResponse = await fetch(`${server}/sessions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            agent_id: agentId,
            customer_id: parlantCustomerId,
            title: sessionTitle,
          }),
        });

        if (!createSessionResponse.ok) {
          throw new Error(`Falha ao criar sessao (${createSessionResponse.status}).`);
        }

        const session = (await createSessionResponse.json()) as { id: string };
        if (!cancelled) {
          window.localStorage.setItem(sessionStorageKey, session.id);
          setSessionId(session.id);
        }
      } catch (error) {
        if (!cancelled) {
          toast.error(error instanceof Error ? error.message : initError);
        }
      }
    };

    void initSession();

    return () => {
      cancelled = true;
    };
  }, [
    agentId,
    customerEmail,
    customerId,
    initError,
    server,
    sessionId,
    sessionStorageKey,
    sessionTitle,
  ]);

  useEffect(() => {
    if (!server || !sessionId) {
      return;
    }

    let cancelled = false;
    let nextOffset = 0;
    let pollingStarted = false;
    let eventSource: EventSource | null = null;

    const fetchEvents = async (waitForData: number) => {
      const response = await fetch(
        `${server}/sessions/${encodeURIComponent(sessionId)}/events?min_offset=${nextOffset}&wait_for_data=${waitForData}&kinds=message,status`,
        { method: "GET" },
      );

      if (response.status === 504) {
        return [];
      }
      if (response.status === 404) {
        throw new Error("SESSION_NOT_FOUND");
      }
      if (!response.ok) {
        throw new Error(`Falha no stream (${response.status}).`);
      }

      return (await response.json()) as ParlantEvent[];
    };

    const consumeIncoming = (incoming: ParlantEvent[]) => {
      if (incoming.length === 0) {
        return;
      }
      nextOffset = Math.max(nextOffset, Math.max(...incoming.map((event) => event.offset)) + 1);
      mergeEvents(incoming);
    };

    const startPolling = async () => {
      if (pollingStarted) {
        return;
      }
      pollingStarted = true;

      while (!cancelled) {
        try {
          const incoming = await fetchEvents(POLL_SECONDS);
          consumeIncoming(incoming);
        } catch (error) {
          if (!cancelled) {
            if (error instanceof Error && error.message === "SESSION_NOT_FOUND") {
              resetSession();
              return;
            }
            toast.error(error instanceof Error ? error.message : streamError);
            await new Promise((resolve) => setTimeout(resolve, 1500));
          }
        }
      }
    };

    const startSse = () => {
      const sseUrl =
        `${server}/sessions/${encodeURIComponent(sessionId)}/events` +
        `?min_offset=${nextOffset}&kinds=message,status&sse=true`;
      eventSource = new EventSource(sseUrl);

      eventSource.onmessage = (messageEvent) => {
        if (cancelled || !messageEvent.data) {
          return;
        }

        try {
          const parsed = JSON.parse(messageEvent.data) as ParlantEvent | ParlantEvent[];
          const incoming = Array.isArray(parsed) ? parsed : [parsed];
          consumeIncoming(incoming);
        } catch {
          // Ignore keep-alive or non-payload SSE messages.
        }
      };

      eventSource.onerror = () => {
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }

        if (!cancelled) {
          void startPolling();
        }
      };
    };

    const bootstrapAndStart = async () => {
      try {
        const initial = await fetchEvents(0);
        consumeIncoming(initial);
        if (!cancelled) {
          startSse();
        }
      } catch (error) {
        if (!cancelled) {
          if (error instanceof Error && error.message === "SESSION_NOT_FOUND") {
            resetSession();
            return;
          }
          void startPolling();
        }
      }
    };

    void bootstrapAndStart();

    return () => {
      cancelled = true;
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [resetSession, server, sessionId, streamError]);

  const onSend = async () => {
    if (!server || !sessionId) {
      toast.error(sessionUnavailable);
      return;
    }
    const message = draft.trim();
    if (!message) {
      return;
    }

    setIsSending(true);
    try {
      const response = await fetch(
        `${server}/sessions/${encodeURIComponent(sessionId)}/events`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            kind: "message",
            source: "customer",
            message,
          }),
        },
      );
      if (!response.ok) {
        throw new Error(`Falha ao enviar mensagem (${response.status}).`);
      }

      const created = (await response.json()) as ParlantEvent;
      setDraft("");
      pendingCustomerOffsetRef.current = created.offset;
      setEvents((previous) => {
        const merged = new Map(previous.map((event) => [event.id, event]));
        merged.set(created.id, created);
        return [...merged.values()].sort((a, b) => a.offset - b.offset);
      });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : sendError);
    } finally {
      setIsSending(false);
    }
  };

  if (!server || !agentId) {
    return (
      <p className="text-sm text-muted-foreground">
        {text.configure}
      </p>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 pt-4 pb-4">
        {messages.length === 0 ? (
          <p className="text-sm text-muted-foreground">{text.emptyState}</p>
        ) : (
          messages.map((event) => {
            const isCustomer =
              event.source === "customer" || event.source === "customer_ui";
            const messageText = extractMessageText(event);

            return (
              <div
                key={`${event.id}-${event.offset}-${event.source}`}
                className={`flex ${isCustomer ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-xl border px-3 py-2 text-sm ${
                    isCustomer
                      ? "border-primary/20 bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  <p className="mb-1 text-[11px] opacity-80">
                    {sourceLabel(event.source, locale)}
                  </p>
                  <p className="whitespace-pre-wrap">
                    {messageText || text.emptyMessage}
                  </p>
                </div>
              </div>
            );
          })
        )}
        <div ref={endRef} />
      </div>

      <form
        className="mt-2 flex items-center gap-2 border-t px-4 pt-3 pb-4"
        onSubmit={(event) => {
          event.preventDefault();
          void onSend();
        }}
      >
        <Input
          className="h-11"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={text.placeholder}
          disabled={isInitializing || !sessionId || isSending}
        />
        <Button
          type="submit"
          className="h-11 w-11 shrink-0"
          disabled={isInitializing || !sessionId || isSending}
        >
          {isSending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <SendHorizonal className="size-4" />
          )}
        </Button>
      </form>
    </div>
  );
}
