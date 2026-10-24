// Bound decoded transport bytes before JSON parsing and collection traversal before Zod.
export const JSON_BYTES = 4 * 1024 * 1024;
export const AUDIO_BYTES = 16 * 1024 * 1024;
export class InputLimitError extends Error {}

export async function readBounded(response: Response, maximum: number): Promise<Uint8Array> {
  const declared = response.headers.get("content-length");
  if (declared && /^\d+$/.test(declared) && Number(declared) > maximum) {
    await response.body?.cancel();
    throw new InputLimitError();
  }
  if (!response.body) return new Uint8Array();
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maximum) throw new InputLimitError();
      chunks.push(value);
    }
  } catch (error) {
    await reader.cancel().catch(() => undefined);
    throw error;
  } finally { reader.releaseLock(); }
  const result = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.length; }
  return result;
}

export function checkShape(value: unknown): void {
  const pending: [unknown, number][] = [[value, 0]];
  let nodes = 0;
  while (pending.length) {
    const [item, depth] = pending.pop()!;
    if (++nodes > 20000 || depth > 32) throw new InputLimitError();
    if (typeof item === "string" && item.length > 262144) throw new InputLimitError();
    if (item && typeof item === "object") {
      if (Array.isArray(item) && item.length > 1000) throw new InputLimitError();
      const keys = Object.keys(item);
      if (!Array.isArray(item) && keys.length > 512) throw new InputLimitError();
      for (const key of keys) {
        if (key.length > 1024) throw new InputLimitError();
        pending.push([(item as Record<string, unknown>)[key], depth + 1]);
      }
    }
  }
}

export async function readJSON(response: Response): Promise<unknown> {
  const bytes = await readBounded(response, JSON_BYTES);
  const value: unknown = JSON.parse(new TextDecoder().decode(bytes));
  checkShape(value);
  return value;
}
