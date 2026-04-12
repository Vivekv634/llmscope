import type { NextConfig } from "next";

const config: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/proxy/:path*",
        destination: "http://localhost:8080/:path*",
      },
    ];
  },
};

export default config;
