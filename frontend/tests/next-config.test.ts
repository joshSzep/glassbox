import { describe, expect, it } from "vitest";

import { createDevRewrites, normalizeFastApiOrigin } from "../next.config";

describe("Next.js development proxy configuration", () => {
  it("normalizes the FastAPI origin", () => {
    expect(normalizeFastApiOrigin(undefined)).toBe("http://127.0.0.1:8765");
    expect(normalizeFastApiOrigin("http://127.0.0.1:9000/")).toBe("http://127.0.0.1:9000");
  });

  it("proxies FastAPI HTTP and SSE routes from the dev server root", () => {
    expect(createDevRewrites("http://127.0.0.1:9000/")).toEqual([
      {
        source: "/healthz",
        destination: "http://127.0.0.1:9000/healthz",
        basePath: false,
      },
      {
        source: "/sessions",
        destination: "http://127.0.0.1:9000/sessions",
        basePath: false,
      },
      {
        source: "/sessions/:path*",
        destination: "http://127.0.0.1:9000/sessions/:path*",
        basePath: false,
      },
    ]);
  });
});
