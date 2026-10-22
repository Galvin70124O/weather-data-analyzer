import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, Loader2, LogOut } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SegmentedControl, SegmentedItem } from "@/components/ui/tabs";
import { useLogout, useMe, useUnits } from "@/hooks/use-auth";
import { useColorMode, type ColorMode } from "@/hooks/use-color-mode";
import { api } from "@/lib/api";
import type { Units } from "@/lib/types";
import { Field, FormError, passwordProblem } from "@/pages/auth-pages";

/** Client-side checks before asking the server (which checks the same rule and the current password). */
export function validatePasswordChange(current: string, next: string, confirm: string): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!current) errors.current = "Enter your current password.";
  const problem = passwordProblem(next);
  if (problem) errors.next = problem;
  else if (next === current) errors.next = "Choose a password different from the current one.";
  if (confirm !== next) errors.confirm = "The two new passwords don't match.";
  return errors;
}

function Row({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 py-4">
      <div>
        <p className="font-medium">{label}</p>
        {hint && <p className="text-sm text-muted-foreground">{hint}</p>}
      </div>
      {children}
    </div>
  );
}

function ChangePassword() {
  const [values, setValues] = useState({ current: "", next: "", confirm: "" });
  const [touched, setTouched] = useState(false);
  const change = useMutation({ mutationFn: () => api.changePassword(values.current, values.next) });
  const errors = touched ? validatePasswordChange(values.current, values.next, values.confirm) : {};
  const set = (key: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement>) => {
    change.reset();
    setValues({ ...values, [key]: e.target.value });
  };

  function submit(event: FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (Object.keys(validatePasswordChange(values.current, values.next, values.confirm)).length) return;
    change.mutate(undefined, {
      onSuccess: () => {
        setValues({ current: "", next: "", confirm: "" });
        setTouched(false);
      },
    });
  }

  return (
    <Card>
      <CardHeader className="block">
        <CardTitle>Change password</CardTitle>
        <CardDescription className="mt-1">Other devices are signed out; this one stays logged in.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="max-w-sm space-y-4" noValidate>
          <Field id="current-password" label="Current password" type="password" autoComplete="current-password" value={values.current} onChange={set("current")} error={errors.current} />
          <Field id="new-password" label="New password" type="password" autoComplete="new-password" value={values.next} onChange={set("next")} error={errors.next} />
          <Field id="confirm-password" label="New password again" type="password" autoComplete="new-password" value={values.confirm} onChange={set("confirm")} error={errors.confirm} />
          <FormError error={change.error} />
          {change.isSuccess && (
            <p role="status" className="flex items-center gap-2 rounded-md border border-success/40 bg-success/10 px-3 py-2 text-sm text-success">
              <CheckCircle2 className="size-4" aria-hidden="true" /> Password changed.
            </p>
          )}
          <Button type="submit" disabled={change.isPending}>
            {change.isPending && <Loader2 className="animate-spin" aria-hidden="true" />} Change password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export function AccountPage() {
  const { data: me } = useMe();
  const { units, setUnits } = useUnits();
  const { mode, setMode } = useColorMode();
  const logout = useLogout();
  const navigate = useNavigate();
  const since = me ? new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric" }).format(new Date(me.created_at)) : "";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Account</h1>
        <p className="text-muted-foreground">{me ? `${me.username} · ${me.email} · member since ${since}` : " "}</p>
      </div>

      <Card>
        <CardHeader className="block"><CardTitle>Preferences</CardTitle></CardHeader>
        <CardContent className="divide-y divide-border pt-2">
          <Row label="Temperature unit" hint="Saved on your account; wind and rain follow (km/h and mm, or mph and inches).">
            <SegmentedControl value={units} onValueChange={(v) => v && setUnits(v as Units)} aria-label="Temperature unit">
              <SegmentedItem value="metric">°C</SegmentedItem>
              <SegmentedItem value="imperial">°F</SegmentedItem>
            </SegmentedControl>
          </Row>
          <Row label="Appearance" hint="Remembered in this browser.">
            <SegmentedControl value={mode} onValueChange={(v) => v && setMode(v as ColorMode)} aria-label="Appearance">
              <SegmentedItem value="light">Light</SegmentedItem>
              <SegmentedItem value="dark">Dark</SegmentedItem>
            </SegmentedControl>
          </Row>
        </CardContent>
      </Card>

      <ChangePassword />

      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-medium">Log out</p>
            <p className="text-sm text-muted-foreground">Ends the session on this device.</p>
          </div>
          <Button variant="outline" onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/login") })} disabled={logout.isPending}>
            <LogOut aria-hidden="true" /> Log out
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
