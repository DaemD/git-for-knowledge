"""PostgreSQL control plane: users, knowledge bases, memory_writes ledger."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

import asyncpg

from app.utils import new_id


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS graphs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kb_id TEXT NOT NULL,
    name TEXT NOT NULL,
    nams_conversation_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, kb_id)
);

CREATE TABLE IF NOT EXISTS memory_writes (
    idempotency_key TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    graph_id TEXT NOT NULL REFERENCES graphs(id) ON DELETE CASCADE,
    nams_message_id TEXT,
    client_id TEXT,
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    accepted_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS graphs_user_id_idx ON graphs (user_id);
CREATE INDEX IF NOT EXISTS memory_writes_graph_id_idx ON memory_writes (graph_id);
CREATE INDEX IF NOT EXISTS memory_writes_nams_message_id_idx
    ON memory_writes (nams_message_id);

CREATE TABLE IF NOT EXISTS kb_invites (
    id TEXT PRIMARY KEY,
    graph_id TEXT NOT NULL REFERENCES graphs(id) ON DELETE CASCADE,
    invitee_email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('read', 'write')),
    invited_by TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'accepted', 'revoked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    UNIQUE (graph_id, invitee_email)
);

CREATE TABLE IF NOT EXISTS graph_members (
    graph_id TEXT NOT NULL REFERENCES graphs(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('read', 'write')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (graph_id, user_id)
);

CREATE INDEX IF NOT EXISTS graph_members_user_id_idx ON graph_members (user_id);
CREATE INDEX IF NOT EXISTS kb_invites_email_lower_idx
    ON kb_invites (LOWER(invitee_email));
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class UserRecord:
    id: str
    email: str | None
    display_name: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class GraphRecord:
    id: str
    user_id: str
    kb_id: str
    name: str
    nams_conversation_id: str
    created_at: datetime


@dataclass(frozen=True)
class MemoryWrite:
    idempotency_key: str
    user_id: str
    graph_id: str
    nams_message_id: str | None
    client_id: str | None
    content_hash: str
    status: str
    accepted_at: str
    completed_at: str | None


@dataclass(frozen=True)
class BeginWriteResult:
    should_submit: bool
    write: MemoryWrite


@dataclass(frozen=True)
class GraphAccess:
    graph: GraphRecord
    role: str
    can_write: bool


@dataclass(frozen=True)
class KbInviteRecord:
    id: str
    graph_id: str
    invitee_email: str
    role: str
    invited_by: str
    status: str
    created_at: datetime
    accepted_at: datetime | None


@dataclass(frozen=True)
class GraphMemberRecord:
    graph_id: str
    user_id: str
    role: str
    joined_at: datetime
    email: str | None = None
    display_name: str | None = None


@dataclass(frozen=True)
class AccessibleGraph:
    graph: GraphRecord
    role: str
    owner_email: str | None = None


class ControlStore(Protocol):
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def upsert_user(
        self,
        subject: str,
        *,
        email: str | None = None,
        display_name: str | None = None,
    ) -> UserRecord: ...
    async def get_user(self, user_id: str) -> UserRecord | None: ...
    async def list_graphs(self, user_id: str) -> list[GraphRecord]: ...
    async def get_graph_by_kb(
        self,
        user_id: str,
        kb_id: str,
    ) -> GraphRecord | None: ...
    async def create_graph(
        self,
        user_id: str,
        kb_id: str,
        name: str,
        nams_conversation_id: str,
    ) -> GraphRecord: ...
    async def begin_write(
        self,
        *,
        idempotency_key: str,
        user_id: str,
        graph_id: str,
        client_id: str,
        content_hash: str,
        accepted_at: str,
    ) -> BeginWriteResult: ...
    async def mark_completed(
        self,
        idempotency_key: str,
        nams_message_id: str,
        completed_at: str,
    ) -> None: ...
    async def mark_failed(self, idempotency_key: str) -> None: ...
    async def get_by_message_ids(
        self,
        graph_id: str,
        message_ids: set[str],
    ) -> dict[str, MemoryWrite]: ...
    async def get_graph_by_id(self, graph_id: str) -> GraphRecord | None: ...
    async def find_user_by_email(self, email: str) -> UserRecord | None: ...
    async def list_accessible_graphs(self, user_id: str) -> list[AccessibleGraph]: ...
    async def list_member_graphs_by_kb(
        self,
        user_id: str,
        kb_id: str,
    ) -> list[tuple[GraphRecord, str]]: ...
    async def upsert_kb_invite(
        self,
        *,
        graph_id: str,
        invitee_email: str,
        role: str,
        invited_by: str,
    ) -> KbInviteRecord: ...
    async def upsert_graph_member(
        self,
        *,
        graph_id: str,
        user_id: str,
        role: str,
    ) -> GraphMemberRecord: ...
    async def accept_pending_invites(
        self,
        user_id: str,
        email: str,
    ) -> int: ...
    async def list_kb_members(self, graph_id: str) -> list[GraphMemberRecord]: ...
    async def list_pending_invites(self, graph_id: str) -> list[KbInviteRecord]: ...
    async def revoke_kb_access(
        self,
        graph_id: str,
        invitee_email: str,
    ) -> bool: ...


class PostgresControlStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = _normalize_database_url(database_url)
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            self._database_url,
            min_size=1,
            max_size=10,
        )
        async with self._pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL)
            # Lightweight migration for earlier MVP schemas.
            await conn.execute(
                "ALTER TABLE graphs ADD COLUMN IF NOT EXISTS kb_id TEXT"
            )
            await conn.execute(
                """
                UPDATE graphs
                SET kb_id = id
                WHERE kb_id IS NULL OR kb_id = ''
                """
            )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _pool_required(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Control store has not finished starting")
        return self._pool

    async def upsert_user(
        self,
        subject: str,
        *,
        email: str | None = None,
        display_name: str | None = None,
    ) -> UserRecord:
        now = utcnow()
        async with self._pool_required().acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (id, email, display_name, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $4)
                ON CONFLICT (id) DO UPDATE SET
                    email = COALESCE(EXCLUDED.email, users.email),
                    display_name = COALESCE(
                        EXCLUDED.display_name, users.display_name
                    ),
                    updated_at = EXCLUDED.updated_at
                RETURNING id, email, display_name, created_at, updated_at
                """,
                subject,
                email,
                display_name,
                now,
            )
        return _user_from_row(row)

    async def get_user(self, user_id: str) -> UserRecord | None:
        async with self._pool_required().acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, display_name, created_at, updated_at
                FROM users
                WHERE id = $1
                """,
                user_id,
            )
        return _user_from_row(row) if row else None

    async def list_graphs(self, user_id: str) -> list[GraphRecord]:
        async with self._pool_required().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, kb_id, name, nams_conversation_id, created_at
                FROM graphs
                WHERE user_id = $1
                ORDER BY created_at ASC
                """,
                user_id,
            )
        return [_graph_from_row(row) for row in rows]

    async def get_graph_by_kb(
        self,
        user_id: str,
        kb_id: str,
    ) -> GraphRecord | None:
        async with self._pool_required().acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, kb_id, name, nams_conversation_id, created_at
                FROM graphs
                WHERE user_id = $1 AND kb_id = $2
                """,
                user_id,
                kb_id,
            )
        return _graph_from_row(row) if row else None

    async def create_graph(
        self,
        user_id: str,
        kb_id: str,
        name: str,
        nams_conversation_id: str,
    ) -> GraphRecord:
        now = utcnow()
        graph_id = new_id("graph")
        async with self._pool_required().acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO graphs (
                        id, user_id, kb_id, name, nams_conversation_id, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id, user_id, kb_id, name, nams_conversation_id,
                              created_at
                    """,
                    graph_id,
                    user_id,
                    kb_id,
                    name,
                    nams_conversation_id,
                    now,
                )
            except asyncpg.UniqueViolationError as exc:
                raise ValueError(
                    f"A knowledge base with kb_id {kb_id!r} already exists"
                ) from exc
        return _graph_from_row(row)

    async def begin_write(
        self,
        *,
        idempotency_key: str,
        user_id: str,
        graph_id: str,
        client_id: str,
        content_hash: str,
        accepted_at: str,
    ) -> BeginWriteResult:
        async with self._pool_required().acquire() as conn:
            async with conn.transaction():
                try:
                    row = await conn.fetchrow(
                        """
                        INSERT INTO memory_writes (
                            idempotency_key, user_id, graph_id, client_id,
                            content_hash, status, accepted_at
                        )
                        VALUES ($1, $2, $3, $4, $5, 'pending', $6)
                        RETURNING idempotency_key, user_id, graph_id,
                                  nams_message_id, client_id, content_hash,
                                  status, accepted_at, completed_at
                        """,
                        idempotency_key,
                        user_id,
                        graph_id,
                        client_id,
                        content_hash,
                        accepted_at,
                    )
                    return BeginWriteResult(
                        should_submit=True,
                        write=_memory_from_row(row),
                    )
                except asyncpg.UniqueViolationError:
                    existing = await conn.fetchrow(
                        """
                        SELECT idempotency_key, user_id, graph_id,
                               nams_message_id, client_id, content_hash,
                               status, accepted_at, completed_at
                        FROM memory_writes
                        WHERE idempotency_key = $1
                        FOR UPDATE
                        """,
                        idempotency_key,
                    )
                    if existing is None:
                        raise RuntimeError(
                            "Could not read the existing memory write"
                        )
                    write = _memory_from_row(existing)
                    if write.status == "failed":
                        row = await conn.fetchrow(
                            """
                            UPDATE memory_writes
                            SET status = 'pending',
                                nams_message_id = NULL,
                                completed_at = NULL,
                                user_id = $2,
                                graph_id = $3,
                                client_id = $4,
                                content_hash = $5
                            WHERE idempotency_key = $1
                            RETURNING idempotency_key, user_id, graph_id,
                                      nams_message_id, client_id, content_hash,
                                      status, accepted_at, completed_at
                            """,
                            idempotency_key,
                            user_id,
                            graph_id,
                            client_id,
                            content_hash,
                        )
                        return BeginWriteResult(
                            should_submit=True,
                            write=_memory_from_row(row),
                        )
                    return BeginWriteResult(should_submit=False, write=write)

    async def mark_completed(
        self,
        idempotency_key: str,
        nams_message_id: str,
        completed_at: str,
    ) -> None:
        async with self._pool_required().acquire() as conn:
            await conn.execute(
                """
                UPDATE memory_writes
                SET nams_message_id = $2,
                    status = 'completed',
                    completed_at = $3
                WHERE idempotency_key = $1
                """,
                idempotency_key,
                nams_message_id,
                completed_at,
            )

    async def mark_failed(self, idempotency_key: str) -> None:
        async with self._pool_required().acquire() as conn:
            await conn.execute(
                """
                UPDATE memory_writes
                SET status = 'failed'
                WHERE idempotency_key = $1
                """,
                idempotency_key,
            )

    async def get_by_message_ids(
        self,
        graph_id: str,
        message_ids: set[str],
    ) -> dict[str, MemoryWrite]:
        if not message_ids:
            return {}
        async with self._pool_required().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT idempotency_key, user_id, graph_id, nams_message_id,
                       client_id, content_hash, status, accepted_at, completed_at
                FROM memory_writes
                WHERE graph_id = $1
                  AND nams_message_id = ANY($2::text[])
                """,
                graph_id,
                list(message_ids),
            )
        return {
            str(row["nams_message_id"]): _memory_from_row(row)
            for row in rows
            if row["nams_message_id"] is not None
        }

    async def get_graph_by_id(self, graph_id: str) -> GraphRecord | None:
        async with self._pool_required().acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, kb_id, name, nams_conversation_id, created_at
                FROM graphs
                WHERE id = $1
                """,
                graph_id,
            )
        return _graph_from_row(row) if row else None

    async def find_user_by_email(self, email: str) -> UserRecord | None:
        normalized = _normalize_email(email)
        async with self._pool_required().acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, display_name, created_at, updated_at
                FROM users
                WHERE LOWER(email) = $1
                """,
                normalized,
            )
        return _user_from_row(row) if row else None

    async def list_accessible_graphs(self, user_id: str) -> list[AccessibleGraph]:
        async with self._pool_required().acquire() as conn:
            owned_rows = await conn.fetch(
                """
                SELECT g.id, g.user_id, g.kb_id, g.name, g.nams_conversation_id,
                       g.created_at, u.email AS owner_email
                FROM graphs g
                LEFT JOIN users u ON u.id = g.user_id
                WHERE g.user_id = $1
                ORDER BY g.created_at ASC
                """,
                user_id,
            )
            shared_rows = await conn.fetch(
                """
                SELECT g.id, g.user_id, g.kb_id, g.name, g.nams_conversation_id,
                       g.created_at, gm.role, owner.email AS owner_email
                FROM graph_members gm
                JOIN graphs g ON g.id = gm.graph_id
                LEFT JOIN users owner ON owner.id = g.user_id
                WHERE gm.user_id = $1
                ORDER BY g.created_at ASC
                """,
                user_id,
            )
        owned = [
            AccessibleGraph(
                graph=_graph_from_row(row),
                role="owner",
                owner_email=row["owner_email"],
            )
            for row in owned_rows
        ]
        shared = [
            AccessibleGraph(
                graph=_graph_from_row(row),
                role=str(row["role"]),
                owner_email=row["owner_email"],
            )
            for row in shared_rows
        ]
        return owned + shared

    async def list_member_graphs_by_kb(
        self,
        user_id: str,
        kb_id: str,
    ) -> list[tuple[GraphRecord, str]]:
        async with self._pool_required().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT g.id, g.user_id, g.kb_id, g.name, g.nams_conversation_id,
                       g.created_at, gm.role
                FROM graph_members gm
                JOIN graphs g ON g.id = gm.graph_id
                WHERE gm.user_id = $1 AND g.kb_id = $2
                ORDER BY g.created_at ASC
                """,
                user_id,
                kb_id,
            )
        return [(_graph_from_row(row), str(row["role"])) for row in rows]

    async def upsert_kb_invite(
        self,
        *,
        graph_id: str,
        invitee_email: str,
        role: str,
        invited_by: str,
    ) -> KbInviteRecord:
        normalized = _normalize_email(invitee_email)
        now = utcnow()
        invite_id = new_id("invite")
        async with self._pool_required().acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO kb_invites (
                    id, graph_id, invitee_email, role, invited_by, status,
                    created_at
                )
                VALUES ($1, $2, $3, $4, $5, 'pending', $6)
                ON CONFLICT (graph_id, invitee_email) DO UPDATE SET
                    role = EXCLUDED.role,
                    invited_by = EXCLUDED.invited_by,
                    status = CASE
                        WHEN kb_invites.status = 'revoked' THEN 'pending'
                        ELSE kb_invites.status
                    END
                RETURNING id, graph_id, invitee_email, role, invited_by, status,
                          created_at, accepted_at
                """,
                invite_id,
                graph_id,
                normalized,
                role,
                invited_by,
                now,
            )
        return _invite_from_row(row)

    async def upsert_graph_member(
        self,
        *,
        graph_id: str,
        user_id: str,
        role: str,
    ) -> GraphMemberRecord:
        now = utcnow()
        async with self._pool_required().acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO graph_members (graph_id, user_id, role, joined_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (graph_id, user_id) DO UPDATE SET
                    role = EXCLUDED.role
                RETURNING graph_id, user_id, role, joined_at
                """,
                graph_id,
                user_id,
                role,
                now,
            )
        return GraphMemberRecord(
            graph_id=row["graph_id"],
            user_id=row["user_id"],
            role=row["role"],
            joined_at=row["joined_at"],
        )

    async def accept_pending_invites(self, user_id: str, email: str) -> int:
        normalized = _normalize_email(email)
        now = utcnow()
        async with self._pool_required().acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch(
                    """
                    SELECT id, graph_id, invitee_email, role, invited_by, status,
                           created_at, accepted_at
                    FROM kb_invites
                    WHERE LOWER(invitee_email) = $1 AND status = 'pending'
                    """,
                    normalized,
                )
                accepted = 0
                for row in rows:
                    await conn.execute(
                        """
                        INSERT INTO graph_members (graph_id, user_id, role, joined_at)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (graph_id, user_id) DO UPDATE SET
                            role = EXCLUDED.role
                        """,
                        row["graph_id"],
                        user_id,
                        row["role"],
                        now,
                    )
                    await conn.execute(
                        """
                        UPDATE kb_invites
                        SET status = 'accepted', accepted_at = $2
                        WHERE id = $1
                        """,
                        row["id"],
                        now,
                    )
                    accepted += 1
        return accepted

    async def list_kb_members(self, graph_id: str) -> list[GraphMemberRecord]:
        async with self._pool_required().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT gm.graph_id, gm.user_id, gm.role, gm.joined_at,
                       u.email, u.display_name
                FROM graph_members gm
                JOIN users u ON u.id = gm.user_id
                WHERE gm.graph_id = $1
                ORDER BY gm.joined_at ASC
                """,
                graph_id,
            )
        return [_member_from_row(row) for row in rows]

    async def list_pending_invites(self, graph_id: str) -> list[KbInviteRecord]:
        async with self._pool_required().acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, graph_id, invitee_email, role, invited_by, status,
                       created_at, accepted_at
                FROM kb_invites
                WHERE graph_id = $1 AND status = 'pending'
                ORDER BY created_at ASC
                """,
                graph_id,
            )
        return [_invite_from_row(row) for row in rows]

    async def revoke_kb_access(self, graph_id: str, invitee_email: str) -> bool:
        normalized = _normalize_email(invitee_email)
        async with self._pool_required().acquire() as conn:
            async with conn.transaction():
                invite_result = await conn.execute(
                    """
                    UPDATE kb_invites
                    SET status = 'revoked'
                    WHERE graph_id = $1
                      AND LOWER(invitee_email) = $2
                      AND status IN ('pending', 'accepted')
                    """,
                    graph_id,
                    normalized,
                )
                user_row = await conn.fetchrow(
                    """
                    SELECT id FROM users WHERE LOWER(email) = $1
                    """,
                    normalized,
                )
                member_result = "DELETE 0"
                if user_row is not None:
                    member_result = await conn.execute(
                        """
                        DELETE FROM graph_members
                        WHERE graph_id = $1 AND user_id = $2
                        """,
                        graph_id,
                        user_row["id"],
                    )
        invite_changed = invite_result.split()[-1] != "0"
        member_changed = member_result.split()[-1] != "0"
        return invite_changed or member_changed


@dataclass
class InMemoryControlStore:
    """Test double mirroring PostgreSQL control-plane semantics."""

    users: dict[str, UserRecord] = field(default_factory=dict)
    graphs: dict[str, GraphRecord] = field(default_factory=dict)
    memory_writes: dict[str, MemoryWrite] = field(default_factory=dict)
    kb_invites: dict[str, KbInviteRecord] = field(default_factory=dict)
    graph_members: dict[str, GraphMemberRecord] = field(default_factory=dict)

    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def upsert_user(
        self,
        subject: str,
        *,
        email: str | None = None,
        display_name: str | None = None,
    ) -> UserRecord:
        existing = self.users.get(subject)
        now = utcnow()
        if existing is None:
            record = UserRecord(
                id=subject,
                email=email,
                display_name=display_name,
                created_at=now,
                updated_at=now,
            )
        else:
            record = UserRecord(
                id=subject,
                email=email if email is not None else existing.email,
                display_name=(
                    display_name
                    if display_name is not None
                    else existing.display_name
                ),
                created_at=existing.created_at,
                updated_at=now,
            )
        self.users[subject] = record
        return record

    async def get_user(self, user_id: str) -> UserRecord | None:
        return self.users.get(user_id)

    async def list_graphs(self, user_id: str) -> list[GraphRecord]:
        return sorted(
            [graph for graph in self.graphs.values() if graph.user_id == user_id],
            key=lambda item: item.created_at,
        )

    async def get_graph_by_kb(
        self,
        user_id: str,
        kb_id: str,
    ) -> GraphRecord | None:
        for graph in self.graphs.values():
            if graph.user_id == user_id and graph.kb_id == kb_id:
                return graph
        return None

    async def create_graph(
        self,
        user_id: str,
        kb_id: str,
        name: str,
        nams_conversation_id: str,
    ) -> GraphRecord:
        if await self.get_graph_by_kb(user_id, kb_id) is not None:
            raise ValueError(
                f"A knowledge base with kb_id {kb_id!r} already exists"
            )
        record = GraphRecord(
            id=new_id("graph"),
            user_id=user_id,
            kb_id=kb_id,
            name=name,
            nams_conversation_id=nams_conversation_id,
            created_at=utcnow(),
        )
        self.graphs[record.id] = record
        return record

    async def begin_write(
        self,
        *,
        idempotency_key: str,
        user_id: str,
        graph_id: str,
        client_id: str,
        content_hash: str,
        accepted_at: str,
    ) -> BeginWriteResult:
        existing = self.memory_writes.get(idempotency_key)
        if existing is None:
            write = MemoryWrite(
                idempotency_key=idempotency_key,
                user_id=user_id,
                graph_id=graph_id,
                nams_message_id=None,
                client_id=client_id,
                content_hash=content_hash,
                status="pending",
                accepted_at=accepted_at,
                completed_at=None,
            )
            self.memory_writes[idempotency_key] = write
            return BeginWriteResult(should_submit=True, write=write)

        if existing.status == "failed":
            write = MemoryWrite(
                idempotency_key=idempotency_key,
                user_id=user_id,
                graph_id=graph_id,
                nams_message_id=None,
                client_id=client_id,
                content_hash=content_hash,
                status="pending",
                accepted_at=existing.accepted_at,
                completed_at=None,
            )
            self.memory_writes[idempotency_key] = write
            return BeginWriteResult(should_submit=True, write=write)

        return BeginWriteResult(should_submit=False, write=existing)

    async def mark_completed(
        self,
        idempotency_key: str,
        nams_message_id: str,
        completed_at: str,
    ) -> None:
        existing = self.memory_writes[idempotency_key]
        self.memory_writes[idempotency_key] = MemoryWrite(
            idempotency_key=existing.idempotency_key,
            user_id=existing.user_id,
            graph_id=existing.graph_id,
            nams_message_id=nams_message_id,
            client_id=existing.client_id,
            content_hash=existing.content_hash,
            status="completed",
            accepted_at=existing.accepted_at,
            completed_at=completed_at,
        )

    async def mark_failed(self, idempotency_key: str) -> None:
        existing = self.memory_writes[idempotency_key]
        self.memory_writes[idempotency_key] = MemoryWrite(
            idempotency_key=existing.idempotency_key,
            user_id=existing.user_id,
            graph_id=existing.graph_id,
            nams_message_id=existing.nams_message_id,
            client_id=existing.client_id,
            content_hash=existing.content_hash,
            status="failed",
            accepted_at=existing.accepted_at,
            completed_at=existing.completed_at,
        )

    async def get_by_message_ids(
        self,
        graph_id: str,
        message_ids: set[str],
    ) -> dict[str, MemoryWrite]:
        result: dict[str, MemoryWrite] = {}
        for write in self.memory_writes.values():
            if (
                write.graph_id == graph_id
                and write.nams_message_id
                and write.nams_message_id in message_ids
            ):
                result[write.nams_message_id] = write
        return result

    async def get_graph_by_id(self, graph_id: str) -> GraphRecord | None:
        return self.graphs.get(graph_id)

    async def find_user_by_email(self, email: str) -> UserRecord | None:
        normalized = _normalize_email(email)
        for user in self.users.values():
            if user.email and _normalize_email(user.email) == normalized:
                return user
        return None

    async def list_accessible_graphs(self, user_id: str) -> list[AccessibleGraph]:
        owned = sorted(
            (
                AccessibleGraph(
                    graph=graph,
                    role="owner",
                    owner_email=(
                        self.users[graph.user_id].email
                        if graph.user_id in self.users
                        else None
                    ),
                )
                for graph in self.graphs.values()
                if graph.user_id == user_id
            ),
            key=lambda item: item.graph.created_at,
        )
        shared: list[AccessibleGraph] = []
        for member in self.graph_members.values():
            if member.user_id != user_id:
                continue
            graph = self.graphs.get(member.graph_id)
            if graph is None:
                continue
            owner = self.users.get(graph.user_id)
            shared.append(
                AccessibleGraph(
                    graph=graph,
                    role=member.role,
                    owner_email=owner.email if owner else None,
                )
            )
        shared.sort(key=lambda item: item.graph.created_at)
        return owned + shared

    async def list_member_graphs_by_kb(
        self,
        user_id: str,
        kb_id: str,
    ) -> list[tuple[GraphRecord, str]]:
        matches: list[tuple[GraphRecord, str]] = []
        for member in self.graph_members.values():
            if member.user_id != user_id:
                continue
            graph = self.graphs.get(member.graph_id)
            if graph is not None and graph.kb_id == kb_id:
                matches.append((graph, member.role))
        matches.sort(key=lambda item: item[0].created_at)
        return matches

    async def upsert_kb_invite(
        self,
        *,
        graph_id: str,
        invitee_email: str,
        role: str,
        invited_by: str,
    ) -> KbInviteRecord:
        normalized = _normalize_email(invitee_email)
        key = f"{graph_id}:{normalized}"
        existing = self.kb_invites.get(key)
        now = utcnow()
        if existing is None or existing.status == "revoked":
            record = KbInviteRecord(
                id=new_id("invite"),
                graph_id=graph_id,
                invitee_email=normalized,
                role=role,
                invited_by=invited_by,
                status="pending",
                created_at=now,
                accepted_at=None,
            )
        else:
            record = KbInviteRecord(
                id=existing.id,
                graph_id=graph_id,
                invitee_email=normalized,
                role=role,
                invited_by=invited_by,
                status=existing.status,
                created_at=existing.created_at,
                accepted_at=existing.accepted_at,
            )
        self.kb_invites[key] = record
        return record

    async def upsert_graph_member(
        self,
        *,
        graph_id: str,
        user_id: str,
        role: str,
    ) -> GraphMemberRecord:
        key = f"{graph_id}:{user_id}"
        existing = self.graph_members.get(key)
        record = GraphMemberRecord(
            graph_id=graph_id,
            user_id=user_id,
            role=role,
            joined_at=existing.joined_at if existing else utcnow(),
        )
        self.graph_members[key] = record
        return record

    async def accept_pending_invites(self, user_id: str, email: str) -> int:
        normalized = _normalize_email(email)
        accepted = 0
        now = utcnow()
        for key, invite in list(self.kb_invites.items()):
            if (
                _normalize_email(invite.invitee_email) != normalized
                or invite.status != "pending"
            ):
                continue
            await self.upsert_graph_member(
                graph_id=invite.graph_id,
                user_id=user_id,
                role=invite.role,
            )
            self.kb_invites[key] = KbInviteRecord(
                id=invite.id,
                graph_id=invite.graph_id,
                invitee_email=invite.invitee_email,
                role=invite.role,
                invited_by=invite.invited_by,
                status="accepted",
                created_at=invite.created_at,
                accepted_at=now,
            )
            accepted += 1
        return accepted

    async def list_kb_members(self, graph_id: str) -> list[GraphMemberRecord]:
        members = [
            member
            for member in self.graph_members.values()
            if member.graph_id == graph_id
        ]
        enriched: list[GraphMemberRecord] = []
        for member in sorted(members, key=lambda item: item.joined_at):
            user = self.users.get(member.user_id)
            enriched.append(
                GraphMemberRecord(
                    graph_id=member.graph_id,
                    user_id=member.user_id,
                    role=member.role,
                    joined_at=member.joined_at,
                    email=user.email if user else None,
                    display_name=user.display_name if user else None,
                )
            )
        return enriched

    async def list_pending_invites(self, graph_id: str) -> list[KbInviteRecord]:
        return sorted(
            [
                invite
                for invite in self.kb_invites.values()
                if invite.graph_id == graph_id and invite.status == "pending"
            ],
            key=lambda item: item.created_at,
        )

    async def revoke_kb_access(self, graph_id: str, invitee_email: str) -> bool:
        normalized = _normalize_email(invitee_email)
        revoked = False
        key = f"{graph_id}:{normalized}"
        invite = self.kb_invites.get(key)
        if invite is not None and invite.status in {"pending", "accepted"}:
            self.kb_invites[key] = KbInviteRecord(
                id=invite.id,
                graph_id=invite.graph_id,
                invitee_email=invite.invitee_email,
                role=invite.role,
                invited_by=invite.invited_by,
                status="revoked",
                created_at=invite.created_at,
                accepted_at=invite.accepted_at,
            )
            revoked = True
        user = await self.find_user_by_email(normalized)
        if user is not None:
            member_key = f"{graph_id}:{user.id}"
            if member_key in self.graph_members:
                del self.graph_members[member_key]
                revoked = True
        return revoked


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url.removeprefix("postgres://")
    return url


def _user_from_row(row: Any) -> UserRecord:
    return UserRecord(
        id=row["id"],
        email=row["email"],
        display_name=row["display_name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _graph_from_row(row: Any) -> GraphRecord:
    return GraphRecord(
        id=row["id"],
        user_id=row["user_id"],
        kb_id=str(row["kb_id"]),
        name=row["name"],
        nams_conversation_id=row["nams_conversation_id"],
        created_at=row["created_at"],
    )


def _memory_from_row(row: Any) -> MemoryWrite:
    return MemoryWrite(
        idempotency_key=row["idempotency_key"],
        user_id=row["user_id"],
        graph_id=row["graph_id"],
        nams_message_id=row["nams_message_id"],
        client_id=row["client_id"],
        content_hash=row["content_hash"],
        status=row["status"],
        accepted_at=row["accepted_at"],
        completed_at=row["completed_at"],
    )


def _invite_from_row(row: Any) -> KbInviteRecord:
    return KbInviteRecord(
        id=row["id"],
        graph_id=row["graph_id"],
        invitee_email=row["invitee_email"],
        role=row["role"],
        invited_by=row["invited_by"],
        status=row["status"],
        created_at=row["created_at"],
        accepted_at=row["accepted_at"],
    )


def _member_from_row(row: Any) -> GraphMemberRecord:
    return GraphMemberRecord(
        graph_id=row["graph_id"],
        user_id=row["user_id"],
        role=row["role"],
        joined_at=row["joined_at"],
        email=row.get("email"),
        display_name=row.get("display_name"),
    )


def _normalize_email(email: str) -> str:
    return email.strip().lower()
