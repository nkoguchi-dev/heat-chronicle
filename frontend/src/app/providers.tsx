"use client";

import type { ReactNode } from "react";
import { ThemeProvider } from "@/features/shared/contexts/theme-context";

export function Providers({ children }: { children: ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}
