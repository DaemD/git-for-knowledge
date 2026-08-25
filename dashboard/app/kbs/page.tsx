"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import {
  apiGet,
  apiPost,
  type KnowledgeBase,
  type Me,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type ListResponse = {
  username: string;
  knowledge_bases: KnowledgeBase[];
};

function slugifyKbId(name: string): string {
  const slug = name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
  if (!slug) return "";
  if (/^[a-z0-9]/.test(slug)) return slug;
  return `kb-${slug}`.slice(0, 64);
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function KnowledgeBasesPage() {
  const auth = useAuth();
  const [me, setMe] = useState<Me | null>(null);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    if (!auth.token) return;
    setLoading(true);
    setError(null);
    try {
      const [meRes, listRes] = await Promise.all([
        apiGet<Me>("/api/v1/me", auth.token),
        apiGet<ListResponse>("/api/v1/kbs", auth.token),
      ]);
      setMe(meRes);
      setKbs(listRes.knowledge_bases);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [auth.token]);

  useEffect(() => {
    if (!auth.ready) return;
    if (!auth.isAuthenticated) {
      setLoading(false);
      return;
    }
    void load();
  }, [auth.isAuthenticated, auth.ready, load]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    if (!auth.token) return;
    const label = name.trim();
    const kbId = slugifyKbId(label);
    if (!kbId) {
      setError("Enter a name for the knowledge base");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await apiPost("/api/v1/kbs", auth.token, {
        kb_id: kbId,
        name: label,
      });
      setName("");
      setShowCreate(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setCreating(false);
    }
  }

  if (!auth.ready) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <Card className="mx-auto mt-[12vh] max-w-md gap-4 py-8">
        <CardHeader className="px-6">
          <CardTitle className="font-display text-[26px]">Sign in to grphly</CardTitle>
          <CardDescription>
            Use your Google account to manage knowledge bases.
          </CardDescription>
        </CardHeader>
        <CardContent className="px-6">
          {auth.error ? (
            <p className="mb-3 text-sm text-destructive">{auth.error}</p>
          ) : null}
          <Button type="button" className="w-full" onClick={auth.login}>
            Continue with Google
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!auth.token) {
    return <p className="text-sm text-muted-foreground">Preparing session…</p>;
  }

  const suggestedId = slugifyKbId(name);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-[26px] font-[460] tracking-normal">
            Knowledge bases
          </h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span>{kbs.length} total</span>
            {me ? (
              <Badge variant="secondary" className="capitalize">
                Plan {me.plan_status}
              </Badge>
            ) : null}
          </p>
        </div>

        <Dialog open={showCreate} onOpenChange={setShowCreate}>
          <DialogTrigger asChild>
            <Button type="button">
              <Plus className="size-4" />
              New knowledge base
            </Button>
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={onCreate}>
              <DialogHeader>
                <DialogTitle>Create knowledge base</DialogTitle>
                <DialogDescription>
                  Pick a name — we’ll slugify an ID you can use in chat.
                </DialogDescription>
              </DialogHeader>
              <div className="mt-4 space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Acme research"
                  required
                  autoFocus
                />
                {suggestedId ? (
                  <p className="font-mono text-xs text-muted-foreground">
                    ID will be {suggestedId}
                  </p>
                ) : null}
              </div>
              <DialogFooter className="mt-6">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreate(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={creating || !suggestedId}>
                  {creating ? "Creating…" : "Create"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : null}

      {!loading && kbs.length === 0 ? (
        <Card className="py-10">
          <CardContent className="px-6 text-center">
            <p className="text-sm text-muted-foreground">
              No knowledge bases yet. Create one to get started.
            </p>
          </CardContent>
        </Card>
      ) : null}

      {!loading && kbs.length > 0 ? (
        <Card className="gap-0 overflow-hidden py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>ID</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {kbs.map((kb) => (
                <TableRow key={kb.kb_id}>
                  <TableCell>
                    <Link
                      href={`/kbs/${kb.kb_id}`}
                      className="font-normal text-link no-underline hover:underline"
                    >
                      {kb.name}
                    </Link>
                    {kb.shared && kb.owner_email ? (
                      <div className="text-xs text-muted-foreground">
                        Owner {kb.owner_email}
                      </div>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <code className="font-mono text-xs">{kb.kb_id}</code>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{kb.role}</Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(kb.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : null}
    </div>
  );
}
