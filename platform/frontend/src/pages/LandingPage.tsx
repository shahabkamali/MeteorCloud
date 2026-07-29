import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export function LandingPage() {
  return (
    <section className="mx-auto max-w-3xl">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">Edge Platform</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
        A clean foundation for the control plane
      </h1>
      <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
        Milestone 1 establishes the installer, backend, frontend shell, and developer workflow.
        Business features arrive in later milestones.
      </p>
      <div className="mt-8 flex flex-wrap gap-3">
        <Button asChild>
          <Link to="/health">Check health</Link>
        </Button>
        <Button variant="secondary" asChild>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
            Open API docs
          </a>
        </Button>
      </div>
    </section>
  );
}
