/** How long to wait for the backend before giving up. */
export const REQUEST_TIMEOUT_MS = 10_000;

export class RequestTimeoutError extends Error {
  constructor() {
    super('The server did not respond in time.');
    this.name = 'RequestTimeoutError';
  }
}

/** True when the caller cancelled the request through its own AbortSignal. */
export function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError';
}

/**
 * Runs `work` with an AbortSignal that fires after `timeoutMs`, or when the
 * caller's own `signal` aborts. React Native's fetch has no timeout of its own,
 * so without this a request to an unreachable backend can hang indefinitely.
 */
export async function withTimeout<T>(
  work: (signal: AbortSignal) => Promise<T>,
  { signal, timeoutMs = REQUEST_TIMEOUT_MS }: { signal?: AbortSignal; timeoutMs?: number } = {}
): Promise<T> {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const forwardAbort = () => controller.abort();

  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', forwardAbort);

  try {
    return await work(controller.signal);
  } catch (error: unknown) {
    if (timedOut) throw new RequestTimeoutError();
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', forwardAbort);
  }
}

export function fetchWithTimeout(
  url: string,
  init: RequestInit = {},
  timeoutMs?: number
): Promise<Response> {
  return withTimeout((signal) => fetch(url, { ...init, signal }), {
    signal: init.signal ?? undefined,
    timeoutMs,
  });
}
