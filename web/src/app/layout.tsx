import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Campus Reserve",
  description: "Unified library and sports facility booking",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
