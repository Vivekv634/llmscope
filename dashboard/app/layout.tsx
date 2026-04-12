import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LLMScope",
  description: "Local LLM inference observatory",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-6">
          <a href="/" className="text-lg font-semibold tracking-tight">
            LLMScope
          </a>
          <nav className="flex gap-4 text-sm text-gray-600">
            <a href="/" className="hover:text-gray-900">
              Runs
            </a>
            <a href="/compare" className="hover:text-gray-900">
              Compare
            </a>
          </nav>
        </header>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
