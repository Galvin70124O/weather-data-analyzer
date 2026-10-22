import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { Units, User } from "@/lib/types";

export const ME_KEY = ["me"] as const;

/** The logged-in user, or null when not logged in (a 401 is an answer, not an error). */
export function useMe() {
  return useQuery<User | null>({
    queryKey: ME_KEY,
    queryFn: async () => {
      try {
        return await api.me();
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    staleTime: 5 * 60_000,
  });
}

export function useLogin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ identifier, password }: { identifier: string; password: string }) => api.login(identifier, password),
    onSuccess: (user) => client.setQueryData(ME_KEY, user),
  });
}

export function useRegister() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ username, email, password }: { username: string; email: string; password: string }) =>
      api.register(username, email, password),
    onSuccess: (user) => client.setQueryData(ME_KEY, user),
  });
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.logout(),
    onSuccess: () => {
      client.clear();                       // forget every cached answer from this account
      client.setQueryData(ME_KEY, null);
    },
  });
}

/** °C/°F: saved on the account (users.units), shown immediately, rolled back if saving fails. */
export function useUnits(): { units: Units; setUnits: (units: Units) => void } {
  const client = useQueryClient();
  const { data: me } = useMe();
  const mutation = useMutation({
    mutationFn: (units: Units) => api.setUnits(units),
    onMutate: async (units) => {
      const previous = client.getQueryData<User | null>(ME_KEY);
      if (previous) client.setQueryData(ME_KEY, { ...previous, units });
      return { previous };
    },
    onError: (_error, _units, context) => client.setQueryData(ME_KEY, context?.previous ?? null),
    onSuccess: (user) => client.setQueryData(ME_KEY, user),
  });
  return { units: me?.units ?? "metric", setUnits: (units) => mutation.mutate(units) };
}
