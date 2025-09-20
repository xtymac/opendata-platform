import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Data Link App',
  description: 'Upload, link, and visualize your data',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body suppressHydrationWarning={true}>{children}</body>
    </html>
  )
}