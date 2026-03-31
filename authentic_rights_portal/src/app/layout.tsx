import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import ConditionalHeader from "@/components/ConditionalHeader";
import ThemeRegistry from "@/theme/ThemeRegistry";
import ChatbotWidget from "@/components/ChatbotWidget";
import { ClerkProvider } from "@clerk/nextjs";
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "BVIRAL - Get Viral Clips",
  description:
    "A BVIRAL content subscription is the easiest way to grow your brand and audience with minimal time and effort.",
  icons: {
    icon: "/BVIRAL_favicon.webp",
    apple: "/BVIRAL_favicon.webp",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable}`}
        style={{
          WebkitFontSmoothing: "antialiased",
          MozOsxFontSmoothing: "grayscale",
        }}
        suppressHydrationWarning
      >
        <ClerkProvider>
          <ThemeRegistry>
            <ConditionalHeader />
            <main>{children}</main>
            <ChatbotWidget />
          </ThemeRegistry>
        </ClerkProvider>
      </body>
    </html>
  );
}
