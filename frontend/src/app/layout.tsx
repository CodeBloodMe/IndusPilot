import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IndusPilot — Intelligent Manufacturing Procurement & Quotation",
  description: "Agentic AI platform for manufacturing procurement, mathematical optimization, and quotation intelligence. Built for Tech4Bharat 2026.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full bg-slate-900 text-slate-100">
      <body className="min-h-full flex flex-col font-sans antialiased bg-slate-950 text-slate-100 selection:bg-teal-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
