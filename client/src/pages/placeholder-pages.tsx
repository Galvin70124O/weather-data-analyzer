import { useQuery } from "@tanstack/react-query";
import { Construction, Star } from "lucide-react";
import { Link } from "react-router-dom";

import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/states";
import { useMe } from "@/hooks/use-auth";
import { api } from "@/lib/api";

/**
 * Phase 4 step 1 only builds the shell, the auth pages and the City page. These pages are
 * built in step 2 (Dashboard with live cards, Compare, History, Account, Ctrl+K search).
 */
export function ComingSoon({ title }: { title: string }) {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <EmptyState icon={<Construction />} title="Coming in the next step" message={`The ${title} page is designed in step 2.`} />
    </div>
  );
}

/** Temporary dashboard: a greeting and links to your favourite cities. */
export function DashboardPlaceholder() {
  const { data: me } = useMe();
  const favorites = useQuery({ queryKey: ["favorites"], queryFn: api.favorites });
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Hello, {me?.username}</h1>
      {favorites.data?.length ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {favorites.data.map(({ city }) => (
            <Link key={city.id} to={`/cities/${city.id}`} className="rounded-lg focus-visible:outline-2 focus-visible:outline-accent">
              <Card className="p-4 transition-colors hover:bg-muted/50">
                <p className="font-medium">{city.name}</p>
                <p className="text-sm text-muted-foreground">{city.label}</p>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState icon={<Star />} title="No favourite cities yet" message="Star a city on its page to see it here. City search arrives in the next step." />
      )}
    </div>
  );
}
