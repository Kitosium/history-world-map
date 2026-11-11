import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  distDir: "../.next",
  reactStrictMode: true,
  outputFileTracingIncludes: {
    "/api/static/\\[\\[\\.\\.\\.path\\]\\]": ["../data/**/*"]
  }
};

export default nextConfig;
