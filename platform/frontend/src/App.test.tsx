import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { App } from "@/App";

function renderApp(initialEntries: string[] = ["/"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App shell", () => {
  it("renders the landing page", () => {
    renderApp(["/"]);

    expect(screen.getAllByText("Edge Platform").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("heading", {
        name: /a clean foundation for the control plane/i,
      }),
    ).toBeInTheDocument();
  });

  it("renders the health page shell", () => {
    renderApp(["/health"]);

    expect(screen.getByRole("heading", { name: /system health/i })).toBeInTheDocument();
  });
});
