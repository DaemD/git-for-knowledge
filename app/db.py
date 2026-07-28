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


@dataclass
class InMemoryControlStore:
    """Test double mirroring PostgreSQL control-plane semantics."""

    users: dict[str, UserRecord] = field(default_factory=dict)
    graphs: dict[str, GraphRecord] = field(default_factory=dict)
    memory_writes: dict[str, MemoryWrite] = field(default_factory=dict)

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
