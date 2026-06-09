/**
 * Types + event-source helper for the simulator stream.
 *
 * Server endpoint: GET /api/sim/stream?count=...&register_probability=...
 * Each SSE `data:` line is a JSON-encoded `SimEvent`.
 */

export type Stage =
  | "entering"
  | "reception"
  | "waiting"
  | "exam"
  | "lab"
  | "pharmacy"
  | "checkout"
  | "leaving"
  | "done"
  | "failed";

export interface SimEvent {
  journey_id: number;
  stage: Stage;
  elapsed_ms: number;
  patient_name: string;
  patient_id?: string | null;
  detail?: string | null;
  service?: string | null;
  op?: string | null;
  status_code?: number | null;
  latency_ms?: number | null;
  error?: string | null;
}

export interface SimParams {
  count: number;
  register_probability?: number;
  lab_probability?: number;
  rx_probability?: number;
  max_concurrency?: number;
  journey_spacing_ms?: number;
}

/**
 * Open the SSE stream and dispatch events to `onEvent`. Returns a cancel
 * function that closes the stream and cancels in-flight journeys server-side.
 *
 * Why fetch+ReadableStream instead of EventSource? EventSource doesn't
 * support custom headers — and in production the Apps platform injects
 * `X-Forwarded-Access-Token` automatically (same origin), but during local
 * dev the dev-server-injected `Authorization: Bearer` header would be lost.
 * fetch+stream gives us a single code path that works in both.
 */
export function openSimStream(
  params: SimParams,
  onEvent: (e: SimEvent) => void,
  onComplete?: () => void,
  onError?: (msg: string) => void,
): () => void {
  const search = new URLSearchParams();
  search.set("count", String(params.count));
  if (params.register_probability !== undefined) {
    search.set("register_probability", String(params.register_probability));
  }
  if (params.lab_probability !== undefined) {
    search.set("lab_probability", String(params.lab_probability));
  }
  if (params.rx_probability !== undefined) {
    search.set("rx_probability", String(params.rx_probability));
  }
  if (params.max_concurrency !== undefined) {
    search.set("max_concurrency", String(params.max_concurrency));
  }
  if (params.journey_spacing_ms !== undefined) {
    search.set("journey_spacing_ms", String(params.journey_spacing_ms));
  }

  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`/api/sim/stream?${search.toString()}`, {
        method: "GET",
        signal: controller.signal,
        headers: { Accept: "text/event-stream" },
      });
      if (!res.ok || !res.body) {
        onError?.(`HTTP ${res.status} ${res.statusText}`);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        // SSE messages are separated by a blank line; split on \n\n.
        let idx: number;
        while ((idx = buf.indexOf("\n\n")) >= 0) {
          const raw = buf.slice(0, idx);
          buf = buf.slice(idx + 2);

          // Skip comment lines (": ..."). Parse `event:` + `data:`.
          let eventName = "message";
          let dataText = "";
          for (const line of raw.split("\n")) {
            if (line.startsWith(":")) continue;
            if (line.startsWith("event:")) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataText += line.slice(5).trimStart();
            }
          }

          if (eventName === "complete") {
            onComplete?.();
            return;
          }
          if (eventName === "error") {
            try {
              const parsed = JSON.parse(dataText);
              onError?.(parsed.error ?? "stream error");
            } catch {
              onError?.(dataText || "stream error");
            }
            return;
          }
          if (!dataText) continue;

          try {
            const parsed = JSON.parse(dataText) as SimEvent;
            onEvent(parsed);
          } catch {
            // ignore malformed payloads — never crash the run for parse errors
          }
        }
      }
      onComplete?.();
    } catch (err) {
      if ((err as { name?: string }).name === "AbortError") return;
      onError?.(String(err));
    }
  })();

  return () => controller.abort();
}
