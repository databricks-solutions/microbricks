import { ThemeProvider } from "@/components/apx/theme-provider";
import { createRootRoute, Outlet } from "@tanstack/react-router";
import { Toaster } from "sonner";

export const Route = createRootRoute({
  component: () => (
    <ThemeProvider defaultTheme="dark" storageKey="apx-ui-theme">
      <Outlet />
      <Toaster richColors />
    </ThemeProvider>
  ),
});
