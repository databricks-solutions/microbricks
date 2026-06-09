import { Outlet, createRootRoute } from "@tanstack/react-router";

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-white/70 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-lg">🏥</span>
            <div>
              <div className="text-sm font-semibold leading-tight">clinic-sim</div>
              <div className="text-[11px] text-muted-foreground leading-tight">
                Patient-journey simulator · microbricks
              </div>
            </div>
          </div>
          <a
            href="/api/sim/healthz"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] rounded-md border border-border px-2 py-1 text-muted-foreground hover:bg-muted transition-colors"
          >
            BFF healthz
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>
    </div>
  );
}
