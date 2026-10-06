from datetime import UTC, datetime

import aiosqlite

MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS anime (
            id TEXT PRIMARY KEY,
            metadata_source TEXT NOT NULL,
            metadata_id TEXT,
            title TEXT NOT NULL,
            english_title TEXT,
            romaji_title TEXT,
            native_title TEXT,
            aliases TEXT,
            year INTEGER,
            season TEXT,
            episode_count INTEGER,
            status TEXT NOT NULL,
            cover_url TEXT
        );

        CREATE TABLE IF NOT EXISTS provider_series (
            id TEXT PRIMARY KEY,
            anime_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            provider_series_id TEXT NOT NULL,
            url TEXT,
            FOREIGN KEY(anime_id) REFERENCES anime(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS episodes (
            id TEXT PRIMARY KEY,
            anime_id TEXT NOT NULL,
            number REAL NOT NULL,
            absolute_number INTEGER,
            title TEXT,
            air_date TEXT,
            provider_episode_id TEXT,
            FOREIGN KEY(anime_id) REFERENCES anime(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS download_jobs (
            id TEXT PRIMARY KEY,
            anime_id TEXT NOT NULL,
            episode_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            state TEXT NOT NULL,
            selected_quality TEXT NOT NULL,
            selected_audio TEXT NOT NULL,
            selected_subtitle TEXT,
            destination TEXT NOT NULL,
            temporary_path TEXT NOT NULL,
            bytes_total INTEGER NOT NULL DEFAULT 0,
            bytes_downloaded INTEGER NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS completed_files (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            episode_id TEXT NOT NULL,
            destination TEXT NOT NULL,
            size INTEGER NOT NULL,
            checksum TEXT,
            completed_at TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES download_jobs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_state ON download_jobs(state);
        CREATE INDEX IF NOT EXISTS idx_episodes_anime ON episodes(anime_id);
        CREATE INDEX IF NOT EXISTS idx_prov_series_anime ON provider_series(anime_id);
        """,
    )
]


async def run_migrations(db: aiosqlite.Connection) -> None:
    """Run all unapplied database migrations."""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        """
    )
    async with db.execute("SELECT version FROM schema_migrations") as cursor:
        rows = await cursor.fetchall()
        applied = {row[0] for row in rows}

    for version, sql in MIGRATIONS:
        if version not in applied:
            await db.executescript(sql)
            now_iso = datetime.now(UTC).isoformat()
            await db.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                (version, now_iso),
            )
            await db.commit()
