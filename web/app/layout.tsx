import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Genny — AI Platform Builder",
  description: "Genny AI Platform Builder",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-gray-950">{children}</body>
    </html>
  );
}
