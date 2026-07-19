import { afterEach, describe, expect, it, vi } from "vitest";

import type { GatewayClient } from "@/lib/gateway/GatewayClient";
import { CustomRuntimeProvider } from "@/lib/runtime/custom/provider";

describe("CustomRuntimeProvider", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hydrates chat history from the runtime persistence endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          messages: [
            {
              id: 1,
              role: "user",
              content: "Persist this",
              created_at: 100,
            },
            {
              id: 2,
              role: "assistant",
              content: "Persisted",
              created_at: 101,
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );
    const provider = new CustomRuntimeProvider(
      {} as GatewayClient,
      "http://127.0.0.1:7770",
      { runtimeToken: "runtime-secret" }
    );

    const result = await provider.call<{
      sessionKey: string;
      messages: Array<{ role: string; content: string; timestamp: number }>;
    }>("chat.history", { sessionKey: "agent:programmer:main" });

    expect(result.messages).toEqual([
      { role: "user", content: "Persist this", timestamp: 100_000 },
      { role: "assistant", content: "Persisted", timestamp: 101_000 },
    ]);
    const requestBody = JSON.parse(String(fetchSpy.mock.calls[0]?.[1]?.body));
    expect(requestBody).toMatchObject({
      runtimeUrl: "http://127.0.0.1:7770",
      token: "runtime-secret",
      pathname: "/sessions/agent%3Aprogrammer%3Amain/messages",
      method: "GET",
    });
  });
});
