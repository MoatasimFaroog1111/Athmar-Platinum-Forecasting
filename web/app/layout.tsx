import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "Athmar Platinum Intelligence", description: "Shadow forecasting and approval intelligence for platinum." };

export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html>; }
