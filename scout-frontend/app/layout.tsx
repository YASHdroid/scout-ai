import GoogleProvider from "../components/GoogleProvider";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Geist, Geist_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";


const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const scoutWordmark = Space_Grotesk({
  variable: "--font-scout-wordmark",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const scoutFont = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Scout — The answer is only the beginning",
  description:
    "Explore sources, connect ideas, and uncover the evidence behind what matters with Scout.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} antialiased`}>
        <GoogleProvider>
          {children}
        </GoogleProvider>
      </body>
    </html>
  );
}
