import { Link, createFileRoute } from "@tanstack/react-router";
import Navbar from "@/components/apx/navbar";
import { Button } from "@/components/ui/button";
import { BubbleBackground } from "@/components/backgrounds/bubble";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  return (
    <div className="relative flex h-screen w-screen flex-col overflow-hidden">
      <Navbar />

      <main className="grid flex-1 md:grid-cols-2">
        <BubbleBackground interactive />

        <div className="relative flex flex-col items-center justify-center border-l p-8 md:p-12">
          <div className="max-w-lg space-y-8 text-center">
            <h1 className="text-5xl font-bold md:text-6xl lg:text-7xl">
              Welcome to {__APP_NAME__}
            </h1>
            <p className="text-muted-foreground">
              Reference healthcare BFF that fans out across six backend
              services. The patient summary view shows the canonical concurrent
              fan-out pattern in action.
            </p>
            <div className="flex justify-center gap-3">
              <Button asChild>
                <Link to="/patients">Browse patients</Link>
              </Button>
            </div>
          </div>
        </div>
      </main>

      <div className="absolute inset-0 -z-10 h-full w-full bg-background" />
    </div>
  );
}
