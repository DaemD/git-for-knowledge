"""SQLite ledger for NAMS write provenance and idempotency."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MemoryWrite:
    idempotency_key: str
    workspace_id: str
    nams_message_id: str | None
    client_id: str | None
    content_hash: str
    status: str
    accepted_at: str
    completed_at: str | None


@dataclass(frozen=True)
class BeginWriteResult:
    """Result of reserving an idempotency key before a NAMS call."""

    should_submit: bool
    write: MemoryWrite


class MemoryWriteStore:
    """Small, process-safe SQLite store for a single service deployment."""

    def __init__(self, path: Path | str = "data/memory_writes.db") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def begin_write(
        self,
        *,
        idempotency_key: str,
        workspace_id: str,
        client_id: str,
        content_hash: str,
        accepted_at: str,
    ) -> BeginWriteResult:
        """Reserve a key, or return the state from an earlier attempt.

        A failed write is explicitly made pending again. Its original
        ``accepted_at`` remains the time the service first accepted that key.
        """
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    INSERT INTO memory_writes (
                        idempotency_key, workspace_id, client_id, content_hash,
                        status, accepted_at
                    ) VALUES (?, ?, ?, ?, 'pending', ?)
                    """,
                    (
                        idempotency_key,
                        workspace_id,
                        client_id,
                        content_hash,
                        accepted_at,
                    ),
                )
            except sqlite3.IntegrityError:
                write = self._get_by_key(connection, idempotency_key)
                if write is None:  # Defensive: the primary-key conflict vanished.
                    connection.rollback()
                    raise RuntimeError("Could not read the existing memory write")

                if write.status == "failed":
                    connection.execute(
                        """
                        UPDATE memory_writes
                        SET status = 'pending', nams_message_id = NULL,
                            completed_at = NULL
                        WHERE idempotency_key = ?
                        """,
                        (idempotency_key,),
                    )
                    write = self._get_by_key(connection, idempotency_key)
                    if write is None:
                        connection.rollback()
                        raise RuntimeError("Could not reset the failed memory write")
                    connection.commit()
                    return BeginWriteResult(should_submit=True, write=write)

                connection.commit()
                return BeginWriteResult(should_submit=False, write=write)

            write = self._get_by_key(connection, idempotency_key)
            if write is None:
                connection.rollback()
                raise RuntimeError("Could not read the new memory write")
            connection.commit()
            return BeginWriteResult(should_submit=True, write=write)

    def mark_completed(
        self,
        idempotency_key: str,
        nams_message_id: str,
        completed_at: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE memory_writes
                SET nams_message_id = ?, status = 'completed', completed_at = ?
                WHERE idempotency_key = ?
                """,
                (nams_message_id, completed_at, idempotency_key),
            )

    def mark_failed(self, idempotency_key: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE memory_writes
                SET status = 'failed'
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            )

    def get_by_message_ids(
        self,
        workspace_id: str,
        message_ids: set[str],
    ) -> dict[str, MemoryWrite]:
        if not message_ids:
            return {}

        placeholders = ", ".join("?" for _ in message_ids)
        query = f"""
            SELECT idempotency_key, workspace_id, nams_message_id, client_id,
                   content_hash, status, accepted_at, completed_at
            FROM memory_writes
            WHERE workspace_id = ?
              AND nams_message_id IN ({placeholders})
        """
        with self._connect() as connection:
            rows = connection.execute(query, (workspace_id, *message_ids)).fetchall()
        return {
            str(row["nams_message_id"]): self._row_to_write(row)
            for row in rows
            if row["nams_message_id"] is not None
        }

    def get_by_key(self, idempotency_key: str) -> MemoryWrite | None:
        with self._connect() as connection:
            return self._get_by_key(connection, idempotency_key)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_writes (
                    idempotency_key TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    nams_message_id TEXT,
                    client_id TEXT,
                    content_hash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    accepted_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_writes_nams_message_id
                ON memory_writes(nams_message_id)
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _get_by_key(
        connection: sqlite3.Connection,
        idempotency_key: str,
    ) -> MemoryWrite | None:
        row = connection.execute(
            """
            SELECT idempotency_key, workspace_id, nams_message_id, client_id,
                   content_hash, status, accepted_at, completed_at
            FROM memory_writes
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
        return MemoryWriteStore._row_to_write(row) if row else None

    @staticmethod
    def _row_to_write(row: sqlite3.Row) -> MemoryWrite:
        return MemoryWrite(
            idempotency_key=str(row["idempotency_key"]),
            workspace_id=str(row["workspace_id"]),
            nams_message_id=(
                str(row["nams_message_id"])
                if row["nams_message_id"] is not None
                else None
            ),
            client_id=(
                str(row["client_id"]) if row["client_id"] is not None else None
            ),
            content_hash=str(row["content_hash"]),
            status=str(row["status"]),
            accepted_at=str(row["accepted_at"]),
            completed_at=(
                str(row["completed_at"])
                if row["completed_at"] is not None
                else None
            ),
        )
