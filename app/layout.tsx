import './globals.css'

export const metadata = {
  title: "Rubik's Cube Solver",
  description: 'AI-powered Rubiks cube solver using computer vision',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}