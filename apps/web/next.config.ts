import type { NextConfig } from "next";

// O frontend chama /api/* e o Next encaminha para o backend FastAPI (evita CORS no navegador).
const apiUrl = process.env.GENISIA_API_URL ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
  },
};

export default config;
