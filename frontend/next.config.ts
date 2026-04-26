import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

const DEFAULT_FASTAPI_ORIGIN = "http://127.0.0.1:8765";

type DevRewrite = {
  source: string;
  destination: string;
  basePath: false;
};

export function normalizeFastApiOrigin(origin: string | undefined): string {
  return (origin ?? DEFAULT_FASTAPI_ORIGIN).replace(/\/+$/, "");
}

export function createDevRewrites(origin: string | undefined): DevRewrite[] {
  const fastApiOrigin = normalizeFastApiOrigin(origin);

  return [
    {
      source: "/healthz",
      destination: `${fastApiOrigin}/healthz`,
      basePath: false,
    },
    {
      source: "/sessions",
      destination: `${fastApiOrigin}/sessions`,
      basePath: false,
    },
    {
      source: "/sessions/:path*",
      destination: `${fastApiOrigin}/sessions/:path*`,
      basePath: false,
    },
  ];
}

const nextConfig: NextConfig = {
  basePath: "/app",
  images: {
    unoptimized: true,
  },
  poweredByHeader: false,
};

export default function config(phase: string): NextConfig {
  if (phase !== PHASE_DEVELOPMENT_SERVER) {
    return {
      ...nextConfig,
      output: "export",
    };
  }

  return {
    ...nextConfig,
    async rewrites() {
      return createDevRewrites(process.env.GLASSBOX_FASTAPI_ORIGIN);
    },
  };
}
