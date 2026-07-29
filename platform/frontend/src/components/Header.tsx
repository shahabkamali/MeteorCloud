import { Link } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { Button } from "@/components/ui/button";
import { useOrganizationContext } from "@/context/OrganizationContext";

export function Header() {
  const { user, isAuthenticated, logout } = useAuth();
  const { organizations, selectedOrganization, selectOrganization } = useOrganizationContext();

  return (
    <header className="border-b border-border/70 bg-white/60 px-6 py-4 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">Self-hosted Linux edge control plane</p>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            {isAuthenticated ? "Organizations" : "Foundation"}
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {isAuthenticated && organizations.length > 0 && (
            <select
              className="h-9 rounded-md border border-input bg-white px-3 text-sm"
              value={selectedOrganization?.id ?? ""}
              onChange={(event) => selectOrganization(event.target.value)}
              aria-label="Selected organization"
            >
              {organizations.map((organization) => (
                <option key={organization.id} value={organization.id}>
                  {organization.name}
                </option>
              ))}
            </select>
          )}
          {isAuthenticated ? (
            <>
              <span className="text-sm text-muted-foreground">{user?.email}</span>
              <Button variant="secondary" size="sm" onClick={logout}>
                Log out
              </Button>
            </>
          ) : (
            <>
              <Button variant="secondary" size="sm" asChild>
                <Link to="/login">Sign in</Link>
              </Button>
              <Button size="sm" asChild>
                <Link to="/register">Register</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
