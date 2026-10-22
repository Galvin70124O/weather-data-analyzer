import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { SearchProvider } from "@/components/search/command-palette";
import { Skeleton } from "@/components/ui/misc";
import { useMe } from "@/hooks/use-auth";
import { LoginPage, RegisterPage } from "@/pages/auth-pages";
import { DashboardPage } from "@/pages/dashboard-page";

// The first screens (login, dashboard) are in the main bundle; the other pages load when opened
const named = <K extends string>(load: () => Promise<Record<K, React.ComponentType>>, name: K) =>
  lazy(() => load().then((module) => ({ default: module[name] })));
const CityPage = named(() => import("@/pages/city-page"), "CityPage");
const ComparePage = named(() => import("@/pages/compare-page"), "ComparePage");
const HistoryPage = named(() => import("@/pages/history-page"), "HistoryPage");
const AccountPage = named(() => import("@/pages/account-page"), "AccountPage");

function PageSkeleton() {
  return <div className="space-y-4" aria-busy="true"><Skeleton className="h-10 w-64" /><Skeleton className="h-64" /></div>;
}

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
      <AppShell><Suspense fallback={<PageSkeleton />}><Outlet /></Suspense></AppShell>
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
