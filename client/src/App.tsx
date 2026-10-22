import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { Skeleton } from "@/components/ui/misc";
import { useMe } from "@/hooks/use-auth";
import { LoginPage, RegisterPage } from "@/pages/auth-pages";
import { CityPage } from "@/pages/city-page";
import { ComingSoon, DashboardPlaceholder } from "@/pages/placeholder-pages";

/** Pages that need a login: show a skeleton while we check, send to /login (and back) if needed. */
function RequireLogin({ children }: { children: ReactNode }) {
  const { data: me, isPending } = useMe();
  const location = useLocation();
  if (isPending) {
    return <div className="mx-auto max-w-6xl space-y-4 p-6" aria-busy="true"><Skeleton className="h-10 w-64" /><Skeleton className="h-64" /></div>;
  }
  if (!me) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  return <AppShell>{children}</AppShell>;
}

/** Logged-in users don't need the login/register pages. */
function GuestOnly({ children }: { children: ReactNode }) {
  const { data: me, isPending } = useMe();
  if (isPending) return null;
  return me ? <Navigate to="/" replace /> : <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><RegisterPage /></GuestOnly>} />
      <Route path="/" element={<RequireLogin><DashboardPlaceholder /></RequireLogin>} />
      <Route path="/cities/:cityId" element={<RequireLogin><CityPage /></RequireLogin>} />
      <Route path="/compare" element={<RequireLogin><ComingSoon title="Compare" /></RequireLogin>} />
      <Route path="/history" element={<RequireLogin><ComingSoon title="History" /></RequireLogin>} />
      <Route path="/account" element={<RequireLogin><ComingSoon title="Account" /></RequireLogin>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
