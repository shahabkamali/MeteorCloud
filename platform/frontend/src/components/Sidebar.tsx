import { Activity, Building2, LayoutDashboard, LogIn, UserPlus } from "lucide-react";
import { NavLink } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const { isAuthenticated } = useAuth();

  const navItems = [
    { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
    { to: "/health", label: "Health", icon: Activity, end: false },
    ...(isAuthenticated
      ? [{ to: "/organizations", label: "Organizations", icon: Building2, end: false }]
      : [
          { to: "/login", label: "Sign in", icon: LogIn, end: false },
          { to: "/register", label: "Register", icon: UserPlus, end: false },
        ]),
  ];

  return (
    <aside className="hidden w-64 shrink-0 border-r border-border/70 bg-white/70 backdrop-blur md:flex md:flex-col">
      <div className="border-b border-border/70 px-6 py-5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
          Edge Platform
        </p>
        <h1 className="mt-2 text-lg font-semibold text-foreground">Control Plane</h1>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition hover:bg-secondary hover:text-foreground",
                isActive && "bg-accent text-accent-foreground",
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
