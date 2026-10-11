import { expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "@/providers/auth-provider";
import { csrf, response, tokens, user } from "./fixtures";
function Probe() { const auth = useAuth(); return <p>{auth.status === "authenticated" ? auth.user?.username : auth.status}</p>; }
it("renews an idle authenticated session once at expiry and stops on an outage", async () => {
 vi.useFakeTimers(); vi.stubGlobal("BroadcastChannel", undefined);
 const fetcher = vi.fn(url => Promise.resolve(response(String(url).endsWith("/csrf") ? { csrf_token: csrf } : String(url).endsWith("/refresh") ? tokens : user)));
 vi.stubGlobal("fetch", fetcher);
 render(<QueryClientProvider client={new QueryClient()}><AuthProvider><Probe /></AuthProvider></QueryClientProvider>);
 await act(async () => { await vi.advanceTimersByTimeAsync(0); });
 expect(screen.getByText(user.username)).toBeVisible(); expect(fetcher).toHaveBeenCalledTimes(3);
 await act(async () => { await vi.advanceTimersByTimeAsync(894000); }); expect(fetcher).toHaveBeenCalledTimes(3);
 await act(async () => { await vi.advanceTimersByTimeAsync(1000); }); expect(fetcher).toHaveBeenCalledTimes(6);
 fetcher.mockRejectedValue(new TypeError("offline"));
 await act(async () => { await vi.advanceTimersByTimeAsync(895000); }); expect(screen.getByText("unavailable")).toBeVisible();
 const attempts = fetcher.mock.calls.length; await act(async () => { await vi.advanceTimersByTimeAsync(1800000); }); expect(fetcher).toHaveBeenCalledTimes(attempts);
});
