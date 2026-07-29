export function Header() {
  return (
    <header className="border-b border-border/70 bg-white/60 px-6 py-4 backdrop-blur">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">Self-hosted Linux edge control plane</p>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">Foundation</h2>
        </div>
        <div className="rounded-md border border-border bg-secondary px-3 py-1.5 text-xs font-medium text-secondary-foreground">
          v0.1.0
        </div>
      </div>
    </header>
  );
}
