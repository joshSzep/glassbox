import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: "/app",
  images: {
    unoptimized: true,
  },
  output: "export",
  poweredByHeader: false,
};

export default nextConfig;
