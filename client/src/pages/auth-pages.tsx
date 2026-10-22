import { motion } from "framer-motion";
import { BarChart3, Eye, EyeOff, History, Loader2, Star } from "lucide-react";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Logo } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/form";
import { useLogin, useRegister } from "@/hooks/use-auth";
import { WeatherIcon } from "@/components/weather/weather-icon";
import { ApiError } from "@/lib/api";
import { applyWeatherTheme } from "@/lib/weather-theme";

const USERNAME = /^[A-Za-z0-9._-]{3,32}$/;

/** Same rules as the server (server/app/schemas/auth.py), so mistakes show before submitting. */
export function validateRegistration(username: string, email: string, password: string): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!USERNAME.test(username.trim())) errors.username = "3-32 characters: letters, numbers, dot, dash or underscore.";
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) errors.email = "Enter a valid email address.";
  if (password.length < 8) errors.password = "At least 8 characters.";
  else if (new TextEncoder().encode(password).length > 72) errors.password = "At most 72 bytes.";
  return errors;
}

/** No city yet, so the login scene follows the visitor's own clock: clear day or clear night. */
export function visitorScene(now: Date = new Date()): "clear-day" | "clear-night" {
  const hour = now.getHours();
  return hour >= 7 && hour < 19 ? "clear-day" : "clear-night";
}

function useVisitorScene(): "clear-day" | "clear-night" {
  const [scene] = useState(() => visitorScene());
  useEffect(() => {
    applyWeatherTheme({ wx: scene, tod: scene === "clear-day" ? "day" : "night" });
    return () => applyWeatherTheme(null);
  }, [scene]);
  return scene;
}

const FEATURES = [
  { icon: Star, text: "Favourite cities with live weather" },
  { icon: History, text: "30, 90 or 365 days against the 1991–2020 normal" },
  { icon: BarChart3, text: "Compare up to three cities side by side" },
];

function AuthLayout({ title, subtitle, children, footer }: { title: string; subtitle: string; children: ReactNode; footer: ReactNode }) {
  const scene = useVisitorScene();
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <div className="wx-scene fixed inset-0 -z-10" aria-hidden="true" />
      {/* Desktop only: a short pitch on the themed scene */}
      <aside className="hidden flex-col justify-between p-12 lg:flex">
        <Logo className="text-lg" />
        <div className="max-w-md space-y-8">
          <WeatherIcon code={scene === "clear-day" ? "01d" : "01n"} className="-ml-4 size-36" />
          <h2 className="text-4xl font-semibold leading-tight tracking-tight">Today&apos;s weather, and how unusual it is.</h2>
          <ul className="space-y-3">
            {FEATURES.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-muted-foreground">
                <span className="grid size-8 place-items-center rounded-md bg-card/55 text-foreground"><Icon className="size-4" aria-hidden="true" /></span>
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-sm text-muted-foreground">Weather: OpenWeatherMap · History and normals: Open-Meteo (CC BY 4.0)</p>
      </aside>
      <div className="grid place-items-center px-4 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="w-full max-w-sm">
        <Logo className="mb-8 justify-center text-lg lg:hidden" />
        <Card glass>
          <CardContent className="space-y-6">
            <div className="space-y-1 text-center">
              <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            </div>
            {children}
          </CardContent>
        </Card>
        <p className="mt-6 text-center text-sm text-muted-foreground">{footer}</p>
      </motion.div>
      </div>
    </div>
  );
}

function Field({ id, label, error, type, ...input }: { id: string; label: string; error?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  const [visible, setVisible] = useState(false);
  const isPassword = type === "password";
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input id={id} name={id} type={isPassword && visible ? "text" : type} className={isPassword ? "pr-11" : undefined}
               aria-invalid={error ? true : undefined} aria-describedby={error ? `${id}-error` : undefined} {...input} />
        {isPassword && (
          <button type="button" onClick={() => setVisible(!visible)} aria-pressed={visible}
                  aria-label={visible ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 grid w-11 place-items-center rounded-r-md text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-accent">
            {visible ? <EyeOff className="size-4" aria-hidden="true" /> : <Eye className="size-4" aria-hidden="true" />}
          </button>
        )}
      </div>
      {error && <p id={`${id}-error`} className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

function FormError({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
  return <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">{message}</p>;
}

/** Only same-app paths: "/cities/3" yes; "//evil.com", "https://..." no. */
export function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") && !next.startsWith("/\\") ? next : "/";
}

export function LoginPage() {
  const login = useLogin();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  function submit(event: FormEvent) {
    event.preventDefault();
    const missing: Record<string, string> = {};
    if (!identifier.trim()) missing.identifier = "Enter your username or email.";
    if (!password) missing.password = "Enter your password.";
    setErrors(missing);
    if (Object.keys(missing).length) return;
    login.mutate({ identifier, password }, { onSuccess: () => navigate(safeNext(params.get("next")), { replace: true }) });
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Log in to see your cities and their weather."
      footer={<>New here? <Link className="font-medium text-accent hover:underline" to="/register">Create an account</Link></>}
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field id="identifier" label="Username or email" autoComplete="username" required value={identifier} onChange={(e) => setIdentifier(e.target.value)} error={errors.identifier} />
        <Field id="password" label="Password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} error={errors.password} />
        <FormError error={login.error} />
        <Button type="submit" className="w-full" size="lg" disabled={login.isPending}>
          {login.isPending && <Loader2 className="animate-spin" aria-hidden="true" />} Log in
        </Button>
      </form>
    </AuthLayout>
  );
}

export function RegisterPage() {
  const registration = useRegister();
  const navigate = useNavigate();
  const [values, setValues] = useState({ username: "", email: "", password: "" });
  const [touched, setTouched] = useState(false);
  const errors = touched ? validateRegistration(values.username, values.email, values.password) : {};

  function submit(event: FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (Object.keys(validateRegistration(values.username, values.email, values.password)).length) return;
    registration.mutate(values, { onSuccess: () => navigate("/", { replace: true }) });
  }

  const set = (key: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement>) => setValues({ ...values, [key]: e.target.value });

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Save cities, compare them, and see how this year stacks up."
      footer={<>Already have an account? <Link className="font-medium text-accent hover:underline" to="/login">Log in</Link></>}
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field id="username" label="Username" autoComplete="username" value={values.username} onChange={set("username")} error={errors.username} />
        <Field id="email" label="Email" type="email" autoComplete="email" value={values.email} onChange={set("email")} error={errors.email} />
        <Field id="password" label="Password" type="password" autoComplete="new-password" value={values.password} onChange={set("password")} error={errors.password} />
        <FormError error={registration.error} />
        <Button type="submit" className="w-full" size="lg" disabled={registration.isPending}>
          {registration.isPending && <Loader2 className="animate-spin" aria-hidden="true" />} Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
