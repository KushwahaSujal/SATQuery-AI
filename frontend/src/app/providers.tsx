"use client";

import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CommandPaletteProvider } from "@/components/ui/CommandPaletteContext";
import CommandPalette from "@/components/ui/CommandPalette";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={client}>
      <CommandPaletteProvider>
        {children}
        <CommandPalette />
      </CommandPaletteProvider>
    </QueryClientProvider>
  );
}
