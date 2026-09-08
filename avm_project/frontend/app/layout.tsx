import type { Metadata } from 'next'
import '../styles/globals.css'

export const metadata: Metadata = {
  title: 'AVM Dashboard - 부동산 자동감정 모델',
  description: '부동산 자동감정가(AVM) 모델 성능 모니터링 대시보드',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className="bg-gray-100 text-neutral-900">
        {children}
      </body>
    </html>
  )
}
