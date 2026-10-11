// Cookie mutations are serialized within one tab and, on supporting browsers,
// across same-origin tabs. Always bootstrap CSRF INSIDE the lock.
let pending: Promise<unknown> = Promise.resolve();
export async function withSessionLock<T>(action: () => Promise<T>): Promise<T> {
  if (typeof navigator !== "undefined" && navigator.locks) {
    return await navigator.locks.request("codemate-auth-cookie", action);
  }
  const result = pending.then(action, action);
  pending = result.catch(() => undefined);
  return result;
}
