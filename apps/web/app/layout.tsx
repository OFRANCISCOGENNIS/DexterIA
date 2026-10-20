import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GENISIA AI",
  description: "Ecossistema inteligente de desenvolvimento de software com agentes especializados e supervisão humana.",
};

// Aplica o tema salvo (ou o do sistema) antes da pintura para evitar flash.
const themeScript = `(function(){try{var t=localStorage.getItem('genisia.theme');if(!t){t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}document.documentElement.dataset.theme=t}catch(e){}})()`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
