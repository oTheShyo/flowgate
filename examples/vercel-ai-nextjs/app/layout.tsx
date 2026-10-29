import './globals.css';
import type { ReactNode } from 'react';

export const metadata = {
  title: 'flowgate + Vercel AI SDK',
  description: 'Use flowgate as the backend for Vercel AI SDK useChat.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

