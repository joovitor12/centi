"use client";

import { useCallback, useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { useTheme } from "next-themes";
import {
  Languages,
  Loader2,
  LogOut,
  Mail,
  MessageSquare,
  Moon,
  Newspaper,
  RefreshCcw,
  Send,
  Sparkles,
  Sun,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import {
  createNewsletter,
  deleteNewsletter,
  generateNewsletter,
  listNewsletters,
  sendNewsletter,
  updateNewsletter,
} from "@/lib/api";
import { getSupabaseClient } from "@/lib/supa-client";
import type { FrequencyType, Newsletter, NewsletterPayload } from "@/types/newsletter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ParlantChatPanel } from "@/components/parlant-chat-panel";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";

type Locale = "pt" | "en";
type AppTab = "chat" | "newsletter";

const copy = {
  pt: {
    title: "Centi",
    tabChat: "Chat",
    tabNewsletter: "Newsletters",
    themeAria: "Alternar tema",
    signOut: "Sair",
    authTitleLogin: "Entrar",
    authTitleSignup: "Criar conta",
    authDescription: "Use seu usuario Supabase para acessar o Centi.",
    email: "Email",
    password: "Senha",
    createAccount: "Criar conta",
    iHaveAccount: "Ja tenho conta",
    checkingSession: "Verificando sessao...",
    configureAuthTitle: "Configure autenticacao",
    configureAuthDescription:
      "Defina `NEXT_PUBLIC_SUPABASE_URL` e `NEXT_PUBLIC_SUPABASE_ANON_KEY` no `.env.local`.",
    chatCardTitle: "Chat do Centi",
    chatCardDescription: "Conversa em tempo real no estilo ChatGPT.",
    newsletterCreateTitle: "Nova newsletter",
    newsletterCreateDescription: "Crie uma configuracao de envio recorrente.",
    themes: "Temas (separados por virgula)",
    frequency: "Frequencia",
    intervalDays: "Intervalo (dias)",
    createNewsletter: "Criar newsletter",
    newsletterListTitle: "Newsletters",
    newsletterListDescription: "Lista atual para",
    refresh: "Atualizar",
    tableTitle: "Titulo",
    tableEmail: "Email",
    tableThemes: "Temas",
    tableFrequency: "Frequencia",
    tableActive: "Ativa",
    tableActions: "Acoes",
    noNewsletters: "Nenhuma newsletter encontrada.",
    edit: "Editar",
    saveChanges: "Salvar alteracoes",
    generate: "Gerar",
    send: "Enviar",
    delete: "Excluir",
    editNewsletterTitle: "Editar newsletter",
    loginRequired: "Faca login para continuar.",
    fillTitleEmail: "Preencha titulo e email.",
    authNotConfigured: "Supabase nao configurado no frontend.",
    fillAuth: "Preencha email e senha.",
    signupSuccess: "Conta criada. Confirme o email se necessario.",
    loginSuccess: "Login realizado.",
    authError: "Erro na autenticacao.",
    logoutSuccess: "Sessao finalizada.",
    loadError: "Erro ao carregar dados.",
    createSuccess: "Newsletter criada.",
    createError: "Erro ao criar newsletter.",
    deleteSuccess: "Newsletter excluida.",
    deleteError: "Erro ao excluir newsletter.",
    generateSuccess: "Conteudo gerado com sucesso.",
    generateError: "Erro ao gerar newsletter.",
    sendSuccess: "Newsletter enviada.",
    sendError: "Erro ao enviar newsletter.",
    statusSuccess: "Status atualizado.",
    statusError: "Erro ao atualizar status.",
    updateSuccess: "Newsletter atualizada.",
    updateError: "Erro ao salvar atualizacao.",
    themeDaily: "Diaria",
    themeWeekly: "Semanal",
    themeEveryNDays: "A cada N dias",
  },
  en: {
    title: "Centi",
    tabChat: "Chat",
    tabNewsletter: "Newsletter",
    themeAria: "Toggle theme",
    signOut: "Sign out",
    authTitleLogin: "Sign in",
    authTitleSignup: "Create account",
    authDescription: "Use your Supabase account to access Centi.",
    email: "Email",
    password: "Password",
    createAccount: "Create account",
    iHaveAccount: "I already have an account",
    checkingSession: "Checking session...",
    configureAuthTitle: "Configure authentication",
    configureAuthDescription:
      "Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `.env.local`.",
    chatCardTitle: "Centi Chat",
    chatCardDescription: "Real-time conversation in a ChatGPT-style layout.",
    newsletterCreateTitle: "New newsletter",
    newsletterCreateDescription: "Create a recurring delivery configuration.",
    themes: "Themes (comma separated)",
    frequency: "Frequency",
    intervalDays: "Interval (days)",
    createNewsletter: "Create newsletter",
    newsletterListTitle: "Newsletters",
    newsletterListDescription: "Current list for",
    refresh: "Refresh",
    tableTitle: "Title",
    tableEmail: "Email",
    tableThemes: "Themes",
    tableFrequency: "Frequency",
    tableActive: "Active",
    tableActions: "Actions",
    noNewsletters: "No newsletters found.",
    edit: "Edit",
    saveChanges: "Save changes",
    generate: "Generate",
    send: "Send",
    delete: "Delete",
    editNewsletterTitle: "Edit newsletter",
    loginRequired: "Please sign in to continue.",
    fillTitleEmail: "Fill in title and email.",
    authNotConfigured: "Supabase is not configured in frontend.",
    fillAuth: "Fill in email and password.",
    signupSuccess: "Account created. Confirm email if required.",
    loginSuccess: "Signed in successfully.",
    authError: "Authentication error.",
    logoutSuccess: "Session ended.",
    loadError: "Failed to load data.",
    createSuccess: "Newsletter created.",
    createError: "Failed to create newsletter.",
    deleteSuccess: "Newsletter deleted.",
    deleteError: "Failed to delete newsletter.",
    generateSuccess: "Content generated successfully.",
    generateError: "Failed to generate newsletter.",
    sendSuccess: "Newsletter sent.",
    sendError: "Failed to send newsletter.",
    statusSuccess: "Status updated.",
    statusError: "Failed to update status.",
    updateSuccess: "Newsletter updated.",
    updateError: "Failed to save changes.",
    themeDaily: "Daily",
    themeWeekly: "Weekly",
    themeEveryNDays: "Every N days",
  },
} as const;

const initialForm: NewsletterPayload = {
  title: "",
  email: "",
  themes: ["tecnologia"],
  frequency_type: "daily",
  frequency_interval_days: 1,
};

function parseThemes(value: string): string[] {
  return value
    .split(",")
    .map((theme) => theme.trim())
    .filter(Boolean);
}

export default function Home() {
  const { resolvedTheme, setTheme } = useTheme();
  const supabase = getSupabaseClient();
  const [locale, setLocale] = useState<Locale>("en");
  const [activeTab, setActiveTab] = useState<AppTab>("chat");
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(Boolean(supabase));
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [isAuthSubmitting, setIsAuthSubmitting] = useState(false);
  const [form, setForm] = useState<NewsletterPayload>(initialForm);
  const [newsletters, setNewsletters] = useState<Newsletter[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selected, setSelected] = useState<Newsletter | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const t = copy[locale];
  const frequencyLabels: Record<FrequencyType, string> = {
    daily: t.themeDaily,
    weekly: t.themeWeekly,
    every_n_days: t.themeEveryNDays,
  };

  const refresh = useCallback(
    async (withLoader = true) => {
      if (!currentUser) {
        return;
      }

      if (withLoader) {
        setIsLoading(true);
      }

      try {
        const data = await listNewsletters(currentUser.id);
        setNewsletters(data);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : t.loadError);
      } finally {
        if (withLoader) {
          setIsLoading(false);
        }
      }
    },
    [currentUser, t.loadError],
  );

  useEffect(() => {
    if (!supabase) {
      return;
    }

    let mounted = true;
    void supabase.auth.getSession().then(({ data }) => {
      if (!mounted) {
        return;
      }

      setCurrentUser(data.session?.user ?? null);
      setIsAuthLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setCurrentUser(session?.user ?? null);
      setIsAuthLoading(false);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [supabase]);

  useEffect(() => {
    if (!currentUser) {
      return;
    }

    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh(false);
  }, [currentUser, refresh]);

  const onAuthSubmit = async () => {
    if (!supabase) {
      toast.error(t.authNotConfigured);
      return;
    }

    if (!authEmail || !authPassword) {
      toast.error(t.fillAuth);
      return;
    }

    setIsAuthSubmitting(true);
    try {
      if (authMode === "signup") {
        const { error } = await supabase.auth.signUp({
          email: authEmail,
          password: authPassword,
          options: {
            emailRedirectTo: window.location.origin,
          },
        });
        if (error) {
          throw error;
        }
        toast.success(t.signupSuccess);
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email: authEmail,
          password: authPassword,
        });
        if (error) {
          throw error;
        }
        toast.success(t.loginSuccess);
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t.authError);
    } finally {
      setIsAuthSubmitting(false);
    }
  };

  const onLogout = async () => {
    if (!supabase) {
      return;
    }
    const { error } = await supabase.auth.signOut();
    if (error) {
      toast.error(error.message);
      return;
    }
    setNewsletters([]);
    setCurrentUser(null);
    toast.success(t.logoutSuccess);
  };

  const onCreate = async () => {
    if (!currentUser) {
      toast.error(t.loginRequired);
      return;
    }

    const email = form.email || currentUser.email || "";
    if (!form.title || !email) {
      toast.error(t.fillTitleEmail);
      return;
    }

    setIsSubmitting(true);
    try {
      await createNewsletter(currentUser.id, {
        ...form,
        email,
      });
      toast.success(t.createSuccess);
      setForm(initialForm);
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t.createError);
    } finally {
      setIsSubmitting(false);
    }
  };

  const onDelete = async (newsletterId: number) => {
    if (!currentUser) {
      return;
    }
    try {
      await deleteNewsletter(newsletterId, currentUser.id);
      toast.success(t.deleteSuccess);
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t.deleteError);
    }
  };

  const onGenerate = async (newsletterId: number) => {
    if (!currentUser) {
      return;
    }
    try {
      await generateNewsletter(newsletterId, currentUser.id);
      toast.success(t.generateSuccess);
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t.generateError);
    }
  };

  const onSend = async (newsletterId: number) => {
    if (!currentUser) {
      return;
    }
    try {
      await sendNewsletter(newsletterId, currentUser.id);
      toast.success(t.sendSuccess);
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t.sendError);
    }
  };

  const onToggleActive = async (newsletter: Newsletter, checked: boolean) => {
    if (!currentUser) {
      return;
    }
    try {
      await updateNewsletter(newsletter.id, currentUser.id, { is_active: checked });
      toast.success(t.statusSuccess);
      await refresh();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t.statusError);
    }
  };

  const onSaveEdit = async () => {
    if (!selected || !currentUser) {
      return;
    }
    try {
      await updateNewsletter(selected.id, currentUser.id, {
        title: selected.title,
        email: selected.email,
        themes: selected.themes,
        frequency_type: selected.frequency_type,
        frequency_interval_days: selected.frequency_interval_days,
      });
      toast.success(t.updateSuccess);
      setIsDialogOpen(false);
      setSelected(null);
      await refresh();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : t.updateError,
      );
    }
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,hsl(var(--primary)/0.16),transparent_30%),radial-gradient(circle_at_90%_90%,hsl(var(--primary)/0.12),transparent_30%)]" />
      <div className="relative flex min-h-screen w-full overflow-hidden bg-card/90 backdrop-blur">
        <aside className="w-72 border-r bg-muted/30 p-4">
          <div className="mb-5 rounded-xl border bg-background/80 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Workspace
            </p>
            <h1 className="mt-2 text-2xl font-semibold">{t.title}</h1>
            <p className="mt-1 text-xs text-muted-foreground">
              {locale === "pt"
                ? "Assistente inteligente com chat e newsletters."
                : "Intelligent assistant with chat and newsletters."}
            </p>
          </div>

          <nav className="space-y-2">
            <Button
              variant={activeTab === "chat" ? "secondary" : "ghost"}
              className="h-11 w-full justify-start rounded-xl text-sm"
              onClick={() => setActiveTab("chat")}
            >
              <MessageSquare className="mr-2 size-4" />
              {t.tabChat}
            </Button>
            <Button
              variant={activeTab === "newsletter" ? "secondary" : "ghost"}
              className="h-11 w-full justify-start rounded-xl text-sm"
              onClick={() => setActiveTab("newsletter")}
            >
              <Newspaper className="mr-2 size-4" />
              {t.tabNewsletter}
            </Button>
          </nav>

          <div className="mt-6 space-y-3 rounded-xl border bg-background/70 p-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Languages className="size-3.5" />
              Multilingual
            </div>
            <Tabs
              value={locale}
              onValueChange={(value) => setLocale(value as Locale)}
              className="w-full"
            >
              <TabsList className="grid w-full grid-cols-2 rounded-lg">
                <TabsTrigger value="pt">PT-BR</TabsTrigger>
                <TabsTrigger value="en">EN</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </aside>

        <section className="flex flex-1 flex-col">
          <header className="flex items-center justify-between border-b px-5 py-4">
            <div className="font-medium">
              {activeTab === "chat" ? t.tabChat : t.tabNewsletter}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
                aria-label={t.themeAria}
                className="relative rounded-xl"
                suppressHydrationWarning
              >
                <Sun className="size-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                <Moon className="absolute size-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              </Button>
              {currentUser ? (
                <>
                  <div className="flex items-center gap-2 rounded-xl border px-2 py-1">
                    <Avatar className="size-7 border">
                      <AvatarFallback className="text-xs">
                        {(currentUser.email ?? "U").slice(0, 2).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <span className="max-w-[220px] truncate text-sm text-muted-foreground">
                      {currentUser.email ?? currentUser.id}
                    </span>
                  </div>
                  <Button variant="outline" onClick={() => void onLogout()} className="rounded-xl">
                    <LogOut className="mr-2 size-4" />
                    {t.signOut}
                  </Button>
                </>
              ) : null}
            </div>
          </header>

          <div className="flex-1 overflow-hidden p-5">
            {!supabase ? (
              <Card className="border-dashed">
                <CardHeader>
                  <CardTitle>{t.configureAuthTitle}</CardTitle>
                  <CardDescription>{t.configureAuthDescription}</CardDescription>
                </CardHeader>
              </Card>
            ) : null}

            {isAuthLoading ? (
              <Card className="border-dashed">
                <CardContent className="py-8">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="size-4 animate-spin" />
                    {t.checkingSession}
                  </div>
                </CardContent>
              </Card>
            ) : null}

            {!isAuthLoading && supabase && !currentUser ? (
              <Card className="mx-auto mt-8 w-full max-w-md rounded-2xl">
                <CardHeader>
                  <CardTitle>
                    {authMode === "login" ? t.authTitleLogin : t.authTitleSignup}
                  </CardTitle>
                  <CardDescription>{t.authDescription}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="auth-email">{t.email}</Label>
                    <Input
                      id="auth-email"
                      type="email"
                      value={authEmail}
                      onChange={(event) => setAuthEmail(event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="auth-password">{t.password}</Label>
                    <Input
                      id="auth-password"
                      type="password"
                      value={authPassword}
                      onChange={(event) => setAuthPassword(event.target.value)}
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={() => void onAuthSubmit()} disabled={isAuthSubmitting}>
                      {isAuthSubmitting ? (
                        <Loader2 className="mr-2 size-4 animate-spin" />
                      ) : null}
                      {authMode === "login" ? t.authTitleLogin : t.authTitleSignup}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() =>
                        setAuthMode((mode) => (mode === "login" ? "signup" : "login"))
                      }
                    >
                      {authMode === "login" ? t.createAccount : t.iHaveAccount}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : null}

            {currentUser && activeTab === "chat" ? (
              <div className="h-full min-h-0">
                <ParlantChatPanel
                  key={currentUser.id}
                  customerId={currentUser.id}
                  customerEmail={currentUser.email}
                  locale={locale}
                />
              </div>
            ) : null}

            {currentUser && activeTab === "newsletter" ? (
              <div className="space-y-4">
                <Card className="rounded-2xl">
                  <CardHeader>
                    <CardTitle>{t.newsletterCreateTitle}</CardTitle>
                    <CardDescription>{t.newsletterCreateDescription}</CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="title">{t.tableTitle}</Label>
            <Input
              id="title"
              placeholder={locale === "pt" ? "Resumo diario de tecnologia" : "Daily tech summary"}
              value={form.title}
              onChange={(event) =>
                setForm((previous) => ({ ...previous, title: event.target.value }))
              }
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">{t.email}</Label>
            <Input
              id="email"
              type="email"
              placeholder="voce@dominio.com"
              value={form.email}
              onChange={(event) =>
                setForm((previous) => ({ ...previous, email: event.target.value }))
              }
            />
          </div>

          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="themes">{t.themes}</Label>
            <Textarea
              id="themes"
              value={form.themes.join(", ")}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  themes: parseThemes(event.target.value),
                }))
              }
            />
          </div>

          <div className="space-y-2">
            <Label>{t.frequency}</Label>
            <Select
              value={form.frequency_type}
              onValueChange={(value) =>
                setForm((previous) => ({
                  ...previous,
                  frequency_type: value as FrequencyType,
                }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">{t.themeDaily}</SelectItem>
                <SelectItem value="weekly">{t.themeWeekly}</SelectItem>
                <SelectItem value="every_n_days">{t.themeEveryNDays}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="interval">{t.intervalDays}</Label>
            <Input
              id="interval"
              min={1}
              type="number"
              value={form.frequency_interval_days}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  frequency_interval_days: Math.max(1, Number(event.target.value)),
                }))
              }
              disabled={form.frequency_type !== "every_n_days"}
            />
          </div>

          <div className="md:col-span-2">
            <Button onClick={() => void onCreate()} disabled={isSubmitting}>
              {isSubmitting ? (
                <Loader2 className="mr-2 size-4 animate-spin" />
              ) : (
                <Mail className="mr-2 size-4" />
              )}
              {t.createNewsletter}
            </Button>
          </div>
                  </CardContent>
                </Card>

                <Card className="rounded-2xl">
                  <CardHeader className="flex flex-row items-center justify-between gap-3 border-b">
          <div>
            <CardTitle>{t.newsletterListTitle}</CardTitle>
            <CardDescription>
              {t.newsletterListDescription} <span className="font-mono">{currentUser.id}</span>
            </CardDescription>
          </div>
          <Button variant="outline" onClick={() => void refresh()} disabled={isLoading}>
            {isLoading ? (
              <Loader2 className="mr-2 size-4 animate-spin" />
            ) : (
              <RefreshCcw className="mr-2 size-4" />
            )}
            {t.refresh}
          </Button>
                  </CardHeader>
                  <CardContent className="pt-6">
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t.tableTitle}</TableHead>
                  <TableHead>{t.tableEmail}</TableHead>
                  <TableHead>{t.tableThemes}</TableHead>
                  <TableHead>{t.tableFrequency}</TableHead>
                  <TableHead>{t.tableActive}</TableHead>
                  <TableHead className="text-right">{t.tableActions}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {newsletters.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      {t.noNewsletters}
                    </TableCell>
                  </TableRow>
                ) : (
                  newsletters.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.title}</TableCell>
                      <TableCell>{item.email}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {item.themes.map((theme) => (
                            <Badge key={`${item.id}-${theme}`} variant="secondary">
                              {theme}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        {frequencyLabels[item.frequency_type]}
                        {item.frequency_type === "every_n_days"
                          ? ` (${item.frequency_interval_days})`
                          : ""}
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={item.is_active}
                          onCheckedChange={(checked) =>
                            void onToggleActive(item, Boolean(checked))
                          }
                          aria-label="Ativar ou desativar newsletter"
                        />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex flex-wrap justify-end gap-2">
                          <Dialog
                            open={isDialogOpen && selected?.id === item.id}
                            onOpenChange={(open) => {
                              setIsDialogOpen(open);
                              if (!open) {
                                setSelected(null);
                              }
                            }}
                          >
                            <Button
                              variant="outline"
                              onClick={() => {
                                setSelected(item);
                                setIsDialogOpen(true);
                              }}
                            >
                              {t.edit}
                            </Button>
                            <DialogContent className="sm:max-w-xl">
                              <DialogHeader>
                                <DialogTitle>{t.editNewsletterTitle}</DialogTitle>
                              </DialogHeader>

                              {selected ? (
                                <div className="grid gap-4">
                                  <div className="space-y-2">
                                    <Label htmlFor={`edit-title-${selected.id}`}>
                                      {t.tableTitle}
                                    </Label>
                                    <Input
                                      id={`edit-title-${selected.id}`}
                                      value={selected.title}
                                      onChange={(event) =>
                                        setSelected({
                                          ...selected,
                                          title: event.target.value,
                                        })
                                      }
                                    />
                                  </div>
                                  <div className="space-y-2">
                                    <Label htmlFor={`edit-email-${selected.id}`}>{t.email}</Label>
                                    <Input
                                      id={`edit-email-${selected.id}`}
                                      type="email"
                                      value={selected.email}
                                      onChange={(event) =>
                                        setSelected({
                                          ...selected,
                                          email: event.target.value,
                                        })
                                      }
                                    />
                                  </div>
                                  <div className="space-y-2">
                                    <Label htmlFor={`edit-themes-${selected.id}`}>{t.tableThemes}</Label>
                                    <Textarea
                                      id={`edit-themes-${selected.id}`}
                                      value={selected.themes.join(", ")}
                                      onChange={(event) =>
                                        setSelected({
                                          ...selected,
                                          themes: parseThemes(event.target.value),
                                        })
                                      }
                                    />
                                  </div>
                                  <div className="grid gap-4 sm:grid-cols-2">
                                    <div className="space-y-2">
                                      <Label>{t.frequency}</Label>
                                      <Select
                                        value={selected.frequency_type}
                                        onValueChange={(value) =>
                                          setSelected({
                                            ...selected,
                                            frequency_type: value as FrequencyType,
                                          })
                                        }
                                      >
                                        <SelectTrigger>
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="daily">{t.themeDaily}</SelectItem>
                                          <SelectItem value="weekly">{t.themeWeekly}</SelectItem>
                                          <SelectItem value="every_n_days">{t.themeEveryNDays}</SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </div>
                                    <div className="space-y-2">
                                      <Label htmlFor={`edit-interval-${selected.id}`}>
                                        {t.intervalDays}
                                      </Label>
                                      <Input
                                        id={`edit-interval-${selected.id}`}
                                        type="number"
                                        min={1}
                                        value={selected.frequency_interval_days}
                                        onChange={(event) =>
                                          setSelected({
                                            ...selected,
                                            frequency_interval_days: Math.max(
                                              1,
                                              Number(event.target.value),
                                            ),
                                          })
                                        }
                                        disabled={selected.frequency_type !== "every_n_days"}
                                      />
                                    </div>
                                  </div>

                                  <Separator />
                                  <Button onClick={() => void onSaveEdit()}>
                                    {t.saveChanges}
                                  </Button>
                                </div>
                              ) : null}
                            </DialogContent>
                          </Dialog>

                          <Button variant="outline" onClick={() => void onGenerate(item.id)}>
                            <Sparkles className="mr-2 size-4" />
                            {t.generate}
                          </Button>
                          <Button variant="outline" onClick={() => void onSend(item.id)}>
                            <Send className="mr-2 size-4" />
                            {t.send}
                          </Button>
                          <Button
                            variant="destructive"
                            onClick={() => void onDelete(item.id)}
                          >
                            <Trash2 className="mr-2 size-4" />
                            {t.delete}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
                  </CardContent>
                </Card>
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
