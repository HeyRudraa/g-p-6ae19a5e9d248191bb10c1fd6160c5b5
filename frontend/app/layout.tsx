import './globals.css';
import type { Metadata } from 'next';
export const metadata: Metadata = { title: 'Orbit — your learning space', description: 'Classrooms, coding, study tools, all in one calm workspace.' };
export default function RootLayout({ children }: Readonly<{children:React.ReactNode}>) { return <html lang="en"><body>{children}</body></html>; }
