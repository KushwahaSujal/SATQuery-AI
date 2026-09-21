"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/providers";
import { MobileNavProvider } from "@/components/layout/MobileNavContext";
import { CommandPaletteProvider } from "@/components/ui/CommandPaletteContext";
import CommandPalette from "@/components/ui/CommandPalette";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
  },
});

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <MobileNavProvider>
          {/* CommandPalette was complete but only ever mounted by the dead
              app/providers.tsx, so Cmd/Ctrl+K did nothing. It is mounted here now. */}
          <CommandPaletteProvider>
            {children}
            <CommandPalette />
          </CommandPaletteProvider>
        </MobileNavProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
