"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
説明:
🐍 独自のパーソナライズされたDiscordボットをPythonでコーディングするためのシンプルなテンプレート

バージョン: 6.4.0
"""

import aiosqlite


class DatabaseManager:
    def __init__(self, *, connection: aiosqlite.Connection) -> None:
        self.connection = connection

    async def migrate(self) -> None:
        """Run lightweight migrations to keep DB schema up-to-date at startup.
        This will auto-add any missing columns used by the bot, with safe defaults.
        Idempotent and safe to run multiple times.
        Limitations: SQLite cannot easily add NOT NULL constraints retroactively; we add columns
        with defaults where possible and backfill NULLs.
        """
        # Helper: get existing column names for a table
        async def _get_columns(table: str) -> set[str]:
            async with self.connection.execute(f"PRAGMA table_info('{table}')") as cur:
                rows = await cur.fetchall()
                return {row[1] for row in rows}

        # Helper: ensure column exists; if missing, run provided ALTER and optional backfill
        async def _ensure_column(table: str, column: str, add_column_sql: str, backfill_sql: str | None = None) -> None:
            cols = await _get_columns(table)
            if column not in cols:
                await self.connection.execute(add_column_sql)
                await self.connection.commit()
                if backfill_sql:
                    await self.connection.execute(backfill_sql)
                    await self.connection.commit()

        # guild_vc_settings expected columns
        await _ensure_column(
            "guild_vc_settings",
            "base_name_template",
            "ALTER TABLE guild_vc_settings ADD COLUMN base_name_template TEXT NOT NULL DEFAULT '{user_name}のVC'",
            "UPDATE guild_vc_settings SET base_name_template = COALESCE(base_name_template, '{user_name}のVC')",
        )
        await _ensure_column(
            "guild_vc_settings",
            "name_counter",
            "ALTER TABLE guild_vc_settings ADD COLUMN name_counter INTEGER NOT NULL DEFAULT 0",
            "UPDATE guild_vc_settings SET name_counter = COALESCE(name_counter, 0)",
        )
        await _ensure_column(
            "guild_vc_settings",
            "max_channels",
            "ALTER TABLE guild_vc_settings ADD COLUMN max_channels INTEGER NOT NULL DEFAULT 50",
            "UPDATE guild_vc_settings SET max_channels = COALESCE(max_channels, 50)",
        )
        await _ensure_column(
            "guild_vc_settings",
            "delete_delay",
            "ALTER TABLE guild_vc_settings ADD COLUMN delete_delay INTEGER NOT NULL DEFAULT 30",
            "UPDATE guild_vc_settings SET delete_delay = COALESCE(delete_delay, 30)",
        )
        await _ensure_column(
            "guild_vc_settings",
            "log_channel_id",
            "ALTER TABLE guild_vc_settings ADD COLUMN log_channel_id TEXT",
            None,
        )

        # vc_base_channels expected columns
        await _ensure_column(
            "vc_base_channels",
            "creator_id",
            "ALTER TABLE vc_base_channels ADD COLUMN creator_id TEXT",
            None,
        )
        await _ensure_column(
            "vc_base_channels",
            "name_template",
            "ALTER TABLE vc_base_channels ADD COLUMN name_template TEXT",
            None,
        )
        await _ensure_column(
            "vc_base_channels",
            "name_counter",
            "ALTER TABLE vc_base_channels ADD COLUMN name_counter INTEGER NOT NULL DEFAULT 1",
            "UPDATE vc_base_channels SET name_counter = COALESCE(name_counter, 1)",
        )
        await _ensure_column(
            "vc_base_channels",
            "created_at",
            "ALTER TABLE vc_base_channels ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "UPDATE vc_base_channels SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)",
        )

        # vc_generated_channels expected columns
        await _ensure_column(
            "vc_generated_channels",
            "creator_id",
            "ALTER TABLE vc_generated_channels ADD COLUMN creator_id TEXT",
            None,
        )
        await _ensure_column(
            "vc_generated_channels",
            "created_at",
            "ALTER TABLE vc_generated_channels ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "UPDATE vc_generated_channels SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)",
        )
        await _ensure_column(
            "vc_generated_channels",
            "deleted_at",
            "ALTER TABLE vc_generated_channels ADD COLUMN deleted_at TIMESTAMP",
            None,
        )

    # -----------------
    # 既存のテンプレ機能
    # -----------------
    async def add_warn(
        self, user_id: int, server_id: int, moderator_id: int, reason: str
    ) -> int:
        """
        この関数はデータベースに警告を追加します。

        :param user_id: 警告されるべきユーザーのID。
        :param reason: ユーザーが警告される理由。
        """
        rows = await self.connection.execute(
            "SELECT id FROM warns WHERE user_id=? AND server_id=? ORDER BY id DESC LIMIT 1",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            warn_id = result[0] + 1 if result is not None else 1
            await self.connection.execute(
                "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                (
                    warn_id,
                    user_id,
                    server_id,
                    moderator_id,
                    reason,
                ),
            )
            await self.connection.commit()
            return warn_id

    async def remove_warn(self, warn_id: int, user_id: int, server_id: int) -> int:
        """
        この関数はデータベースから警告を削除します。

        :param warn_id: 警告のID。
        :param user_id: 警告されたユーザーのID。
        :param server_id: ユーザーが警告されたサーバーのID
        """
        await self.connection.execute(
            "DELETE FROM warns WHERE id=? AND user_id=? AND server_id=?",
            (
                warn_id,
                user_id,
                server_id,
            ),
        )
        await self.connection.commit()
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0

    async def get_warnings(self, user_id: int, server_id: int) -> list:
        """
        この関数はユーザーのすべての警告を取得します。

        :param user_id: チェックされるべきユーザーのID。
        :param server_id: チェックされるべきサーバーのID。
        :return: ユーザーのすべての警告のリスト。
        """
        rows = await self.connection.execute(
            "SELECT user_id, server_id, moderator_id, reason, strftime('%s', created_at), id FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            result_list = []
            for row in result:
                result_list.append(row)
            return result_list

    # -----------------
    # VC機能: 設定・トラッキング
    # -----------------
    async def get_or_create_guild_vc_settings(self, guild_id: int) -> dict:
        rows = await self.connection.execute(
            "SELECT guild_id, base_name_template, name_counter, max_channels, delete_delay, log_channel_id FROM guild_vc_settings WHERE guild_id=?",
            (str(guild_id),),
        )
        async with rows as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "guild_id": row[0],
                    "base_name_template": row[1],
                    "name_counter": row[2],
                    "max_channels": row[3],
                    "delete_delay": row[4],
                    "log_channel_id": row[5],
                }
        # 作成
        await self.connection.execute(
            "INSERT OR IGNORE INTO guild_vc_settings(guild_id) VALUES (?)",
            (str(guild_id),),
        )
        await self.connection.commit()
        return {
            "guild_id": str(guild_id),
            "base_name_template": "{user_name}のVC",
            "name_counter": 0,
            "max_channels": 50,
            "delete_delay": 30,
            "log_channel_id": None,
        }

    async def increment_and_get_name_counter(self, guild_id: int) -> int:
        """ギルドの連番カウンタを原子的に払い出す（現在値を返しつつ +1）。"""
        # まずは既存行に対して UPDATE ... RETURNING を試みる
        async with self.connection.execute(
            """
            UPDATE guild_vc_settings
            SET name_counter = name_counter + 1
            WHERE guild_id = ?
            RETURNING name_counter - 1
            """,
            (str(guild_id),),
        ) as cursor:
            row = await cursor.fetchone()
            if row is not None:
                await self.connection.commit()
                return int(row[0])
        # 行が存在しない場合は作成してから再試行
        await self.connection.execute(
            "INSERT OR IGNORE INTO guild_vc_settings(guild_id, name_counter) VALUES(?, 0)",
            (str(guild_id),),
        )
        await self.connection.commit()
        async with self.connection.execute(
            """
            UPDATE guild_vc_settings
            SET name_counter = name_counter + 1
            WHERE guild_id = ?
            RETURNING name_counter - 1
            """,
            (str(guild_id),),
        ) as cursor:
            row = await cursor.fetchone()
            await self.connection.commit()
            return int(row[0]) if row and row[0] is not None else 0

    async def update_base_name_template(self, guild_id: int, template: str) -> None:
        await self.connection.execute(
            "INSERT INTO guild_vc_settings(guild_id, base_name_template) VALUES(?, ?) ON CONFLICT(guild_id) DO UPDATE SET base_name_template=excluded.base_name_template",
            (str(guild_id), template),
        )
        await self.connection.commit()

    async def update_max_channels(self, guild_id: int, limit: int) -> None:
        await self.connection.execute(
            "INSERT INTO guild_vc_settings(guild_id, max_channels) VALUES(?, ?) ON CONFLICT(guild_id) DO UPDATE SET max_channels=excluded.max_channels",
            (str(guild_id), limit),
        )
        await self.connection.commit()

    async def update_delete_delay(self, guild_id: int, seconds: int) -> None:
        await self.connection.execute(
            "INSERT INTO guild_vc_settings(guild_id, delete_delay) VALUES(?, ?) ON CONFLICT(guild_id) DO UPDATE SET delete_delay=excluded.delete_delay",
            (str(guild_id), seconds),
        )
        await self.connection.commit()

    async def update_log_channel_id(self, guild_id: int, channel_id: int | None) -> None:
        await self.connection.execute(
            "INSERT INTO guild_vc_settings(guild_id, log_channel_id) VALUES(?, ?) ON CONFLICT(guild_id) DO UPDATE SET log_channel_id=excluded.log_channel_id",
            (str(guild_id), str(channel_id) if channel_id else None),
        )
        await self.connection.commit()

    # --- ベースVC単位のテンプレート ---
    async def set_base_channel_template(self, base_channel_id: int, template: str) -> None:
        """/vc create で作成したベースVCごとにテンプレートを設定します。

        :param base_channel_id: ベースVCのチャンネルID（`/vc create` で作成されたもの）。
        :param template: 名前テンプレート（例: "{user_name}の部屋 #{count}"）。
        :return: なし
        """
        await self.connection.execute(
            "UPDATE vc_base_channels SET name_template=? WHERE channel_id=?",
            (template, str(base_channel_id)),
        )
        await self.connection.commit()

    async def get_base_channel_template(self, base_channel_id: int) -> str | None:
        """指定したベースVCに設定された名前テンプレートを取得します。

        優先順位は以下の通りです（この関数はベースVC個別のみを返します）：
        1) ベースVCごとの `name_template`（存在すればその文字列）
        2) 未設定の場合は ``None`` を返します（呼び出し側でギルド既定にフォールバックしてください）。

        :param base_channel_id: `/vc create` で作成されたベースVCのチャンネルID。
        :return: 個別テンプレート文字列、または未設定時は ``None``。
        """
        rows = await self.connection.execute(
            "SELECT name_template FROM vc_base_channels WHERE channel_id=?",
            (str(base_channel_id),),
        )
        async with rows as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            return None

    async def add_base_channel(self, channel_id: int, guild_id: int, creator_id: int | None) -> None:
        await self.connection.execute(
            "INSERT OR IGNORE INTO vc_base_channels(channel_id, guild_id, creator_id) VALUES (?, ?, ?)",
            (str(channel_id), str(guild_id), str(creator_id) if creator_id else None),
        )
        await self.connection.commit()

    async def is_base_channel(self, channel_id: int) -> bool:
        rows = await self.connection.execute(
            "SELECT 1 FROM vc_base_channels WHERE channel_id=?",
            (str(channel_id),),
        )
        async with rows as cursor:
            return (await cursor.fetchone()) is not None

    async def add_generated_channel(self, channel_id: int, guild_id: int, base_channel_id: int, creator_id: int | None) -> None:
        await self.connection.execute(
            "INSERT OR IGNORE INTO vc_generated_channels(channel_id, guild_id, base_channel_id, creator_id) VALUES (?, ?, ?, ?)",
            (str(channel_id), str(guild_id), str(base_channel_id), str(creator_id) if creator_id else None),
        )
        await self.connection.commit()

    async def is_generated_channel(self, channel_id: int) -> bool:
        rows = await self.connection.execute(
            "SELECT 1 FROM vc_generated_channels WHERE channel_id=? AND deleted_at IS NULL",
            (str(channel_id),),
        )
        async with rows as cursor:
            return (await cursor.fetchone()) is not None

    async def count_active_generated_channels(self, guild_id: int) -> int:
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM vc_generated_channels WHERE guild_id=? AND deleted_at IS NULL",
            (str(guild_id),),
        )
        async with rows as cursor:
            row = await cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

    async def mark_generated_channel_deleted(self, channel_id: int) -> None:
        await self.connection.execute(
            "UPDATE vc_generated_channels SET deleted_at=CURRENT_TIMESTAMP WHERE channel_id=?",
            (str(channel_id),),
        )
        await self.connection.commit()

    # ---- New per-base counters ----
    async def get_next_base_counter(self, base_channel_id: int) -> int:
        """Atomically get current count for base channel and increment it.
        Returns the current value before increment. If row missing, defaults to 1 and then increments to 2.
        """
        # Ensure base channel row exists
        await self.connection.execute(
            "INSERT OR IGNORE INTO vc_base_channels(channel_id, guild_id) VALUES(?, '')",
            (str(base_channel_id),),
        )
        await self.connection.commit()
        async with self.connection.execute(
            """
            UPDATE vc_base_channels
            SET name_counter = COALESCE(name_counter, 1) + 1
            WHERE channel_id = ?
            RETURNING name_counter - 1
            """,
            (str(base_channel_id),),
        ) as cursor:
            row = await cursor.fetchone()
            await self.connection.commit()
            # If somehow no row, return 1
            return int(row[0]) if row and row[0] is not None else 1

    async def reset_base_counter(self, base_channel_id: int) -> None:
        await self.connection.execute(
            "UPDATE vc_base_channels SET name_counter = 1 WHERE channel_id = ?",
            (str(base_channel_id),),
        )
        await self.connection.commit()

    async def get_base_channel_id_for_generated(self, generated_channel_id: int) -> int | None:
        async with self.connection.execute(
            "SELECT base_channel_id FROM vc_generated_channels WHERE channel_id=?",
            (str(generated_channel_id),),
        ) as cursor:
            row = await cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else None

    async def count_active_generated_channels_for_base(self, base_channel_id: int) -> int:
        async with self.connection.execute(
            "SELECT COUNT(*) FROM vc_generated_channels WHERE base_channel_id=? AND deleted_at IS NULL",
            (str(base_channel_id),),
        ) as cursor:
            row = await cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else 0
