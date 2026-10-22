import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { SearchProvider } from "@/components/search/command-palette";
import { Skeleton } from "@/components/ui/misc";
import { useMe } from "@/hooks/use-auth";
import { AccountPage } from "@/pages/account-page";
import { LoginPage, RegisterPage } from "@/pages/auth-pages";
import { CityPage } from "@/pages/city-page";
import { ComparePage } from "@/pages/compare-page";
import { DashboardPage } from "@/pages/dashboard-page";
import { HistoryPage } from "@/pages/history-page";

/**
 * Pages that need a login share one layout (shell + Ctrl+K search), so the shell isn't rebuilt
 * on every navigation. Shows a skeleton while we check; sends to /login (and back) if needed.
 */
function RequireLogin() {
  const { data: me, isPending } = useMe();
  const location = useLocation();
  if (isPending) {
    return <div className="mx-auto max-w-6xl space-y-4 p-6" aria-busy="true"><Skeleton className="h-10 w-64" /><Skeleton className="h-64" /></div>;
  }
  if (!me) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  return (
    <SearchProvider>
      <AppShell><Outlet /></AppShell>
    </SearchProvider>
  );
}

/** Logged-in users don't need the login/register pages. */
function GuestOnly() {
  const { data: me, isPending } = useMe();
  if (isPending) return null;
  return me ? <Navigate to="/" replace /> : <Outlet />;
}

export function App() {
  return (
    <Routes>
      <Route element={<GuestOnly />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      <Route element={<RequireLogin />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/cities/:cityId" element={<CityPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/account" element={<AccountPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
