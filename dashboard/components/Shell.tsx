"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, LogOut, Menu, PanelLeft } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { authDisabled } from "@/lib/api";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

function NavLinks({
  onNavigate,
  onKbs,
}: {
  onNavigate?: () => void;
  onKbs: boolean;
}) {
  return (
    <nav className="flex flex-col gap-1 px-2">
      <Link
        href="/kbs"
        onClick={onNavigate}
        className={cn(
          "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium no-underline transition-colors",
          onKbs
            ? "bg-sidebar-accent text-sidebar-accent-foreground"
            : "text-muted-foreground hover:bg-muted hover:text-foreground",
        )}
      >
        <BookOpen className="size-4" />
        Knowledge bases
      </Link>
    </nav>
  );
}

function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  const auth = useAuth();
  const pathname = usePathname();
  const onKbs = pathname === "/kbs" || pathname?.startsWith("/kbs/");
  const initials = (auth.name || auth.email || "G")
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 px-4 py-5">
        <Link
          href="/kbs"
          onClick={onNavigate}
          className="text-[15px] font-normal tracking-normal text-foreground no-underline hover:no-underline"
        >
          grphly
        </Link>
        {authDisabled() ? (
          <Badge variant="secondary" className="text-[10px]">
            dev
          </Badge>
        ) : null}
      </div>

      <Separator />

      <div className="flex-1 py-4">
        {auth.isAuthenticated ? (
          <NavLinks onNavigate={onNavigate} onKbs={!!onKbs} />
        ) : (
          <p className="px-4 text-sm text-muted-foreground">Sign in to continue</p>
        )}
      </div>

      <Separator />

      <div className="p-3">
        {auth.ready && auth.isAuthenticated ? (
          <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-2.5">
            <Avatar className="size-8">
              <AvatarFallback className="bg-sidebar-accent text-xs font-normal text-primary">
                {initials || "G"}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-foreground">
                {auth.name || "Signed in"}
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {auth.email || "Account"}
              </p>
            </div>
            {!authDisabled() ? (
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                onClick={auth.logout}
                aria-label="Sign out"
              >
                <LogOut className="size-4" />
              </Button>
            ) : null}
          </div>
        ) : (
          <div className="flex items-center gap-2 px-1 text-sm text-muted-foreground">
            <PanelLeft className="size-4" />
            Dashboard
          </div>
        )}
      </div>
    </div>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 border-r border-sidebar-border bg-sidebar md:block">
        <SidebarBody />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background/90 px-4 backdrop-blur md:hidden">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button type="button" variant="outline" size="icon-sm">
                <Menu className="size-4" />
                <span className="sr-only">Open menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0">
              <SheetHeader className="sr-only">
                <SheetTitle>Navigation</SheetTitle>
              </SheetHeader>
              <SidebarBody onNavigate={() => setMobileOpen(false)} />
            </SheetContent>
          </Sheet>
          <span className="text-[15px] font-normal">grphly</span>
        </header>

        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
