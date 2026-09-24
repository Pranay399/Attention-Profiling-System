import type { Metadata } from 'next';
import '@/styles/globals.css';
import '@/styles/components.css';
import { AuthProvider } from '@/lib/auth-context';

import { Toaster } from 'sonner';

export const metadata: Metadata = {
  title: 'Attention Profiling System',
  description: 'Education analytics platform for classroom behavior analysis',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
        <Toaster position="top-right" richColors />
      </body>
    </html>
  );
}
