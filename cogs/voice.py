"""
VC 自動作成・コピー・自動移動・自動削除 機能
- /vc create で作成した「ベースVC」にユーザーが入室したとき、その設定をコピーした新VCを生成し、入室したユーザーを新VCへ移動。
- 完全コピー: 名前/カテゴリ/ビットレート/ユーザー上限/NSFW/パーミッションオーバーライド
- 同時入室: ユーザーごとに別々のVCを作成
- 自動削除: Botが生成したVCのみ、無人になってから設定秒数後に削除（確認なし）
- 設定はDBに保存（ギルド既定の設定 + ベースVCごとの個別テンプレート）

コマンド:
- /vc create [チャンネル名?]
- /vc help
- /vc setting channel_name <ベースVC> <テンプレート>
   - ベースVC: `/vc create` で作成したVCのみ指定可能（それ以外は拒否してメッセージを返します）。
   - テンプレート: `{user_name}`, `{count}` を使用可能（`count`はギルドごとの0始まり連番）。
- /vc setting max_channels <数値>
- /vc setting delete_delay <秒>
- /vc log_channel <チャンネル>

名前の決定ロジック:
- 複製VC作成時、指定ベースVCに個別テンプレートがあればそれを優先。
- 個別テンプレートが未設定の場合は、ギルド既定 `base_name_template` を使用。
"""

from __future__ import annotations

import asyncio
from typing import Optional, Dict, Set

import discord
from discord import app_commands
from discord.ext import commands


def _safe_format_name(template: str, user: discord.abc.User, count: int) -> str:
    # 使用可能なトークンのみ置換
    name = template.replace("{user_name}", user.name).replace("{count}", str(count))
    # Discordの名前長制限（100文字程度）を軽くケア
    return name[:100]


class Voice(commands.Cog, name="voice"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # 削除スケジュール: channel_id -> asyncio.Task
        self._delete_tasks: Dict[int, asyncio.Task] = {}
        # 入室イベントの重複防止: (user_id, channel_id) 単発ロック
        self._processing_joins: Set[tuple[int, int]] = set()


    # -------------------------
    # アプリコマンド（スラッシュ）グループ
    # -------------------------
    vc = app_commands.Group(name="vc", description="VCを作成・管理します。")
    setting = app_commands.Group(name="setting", description="VCの設定を行います。", parent=vc)

    @vc.command(name="help", description="VC機能の使い方を表示します。")
    async def vc_help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="/vc コマンド一覧", color=0xBEBEFE)
        embed.add_field(
            name="/vc create [チャンネル名]",
            value="ベースVCを作成します。入室すると元VC設定をコピーした専用VCが自動生成され移動します。",
            inline=False,
        )
        embed.add_field(
            name="/vc setting channel_name <ベースVC> <テンプレート>",
            value="/vc create で作成した各ベースVCごとに名前テンプレートを設定します（{user_name}, {count}）。",
            inline=False,
        )
        embed.add_field(
            name="/vc setting max_channels <数>",
            value="同時に存在できる自動生成VCの上限（デフォルト50）。",
            inline=False,
        )
        embed.add_field(
            name="/vc setting delete_delay <秒>",
            value="自動生成VCが無人になってから削除するまでの秒数（デフォルト30）。",
            inline=False,
        )
        embed.add_field(
            name="/vc log_channel <チャンネル>",
            value="ログ出力先のテキストチャンネルを設定します（任意）。",
            inline=False,
        )
        # 現在設定のサマリ
        if interaction.guild is not None and getattr(self.bot, "database", None):
            try:
                settings = await self.bot.database.get_or_create_guild_vc_settings(interaction.guild.id)
                summary = (
                    f"テンプレート: `{settings['base_name_template']}`\n"
                    f"上限: {settings['max_channels']}\n"
                    f"削除遅延: {settings['delete_delay']} 秒\n"
                    f"ログ: {'設定あり' if settings.get('log_channel_id') else '未設定'}"
                )
                embed.add_field(name="現在の設定", value=summary, inline=False)
            except Exception:
                pass
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @vc.command(name="create", description="ベースVCを作成します。")
    @app_commands.describe(channel_name="作成するチャンネル名（省略時はテンプレート適用）")
    async def vc_create(
        self, interaction: discord.Interaction, channel_name: Optional[str] = None
    ) -> None:
        if interaction.guild is None:
            return await interaction.response.send_message(
                "サーバー内で実行してください。", ephemeral=True
            )

        guild = interaction.guild
        author = interaction.user

        # 設定取得（なければ作成）
        settings = await self.bot.database.get_or_create_guild_vc_settings(guild.id)

        # チャンネル名決定
        if channel_name is None or channel_name.strip() == "":
            next_count = await self.bot.database.increment_and_get_name_counter(guild.id)
            channel_name = _safe_format_name(settings["base_name_template"], author, next_count)

        # 作成カテゴリ: ユーザーが現在いるVCのカテゴリを優先、なければギルド直下
        category = None
        if isinstance(author, discord.Member) and author.voice and author.voice.channel:
            category = author.voice.channel.category

        # 実際にVC作成
        try:
            # ベースVCはテンプレートではなく通常作成。overwritesは指定しない（NoneはTypeErrorになるため）。
            new_vc = await guild.create_voice_channel(
                name=channel_name,
                category=category,
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "権限不足のためチャンネルを作成できません。", ephemeral=True
            )
        except discord.HTTPException as e:
            return await interaction.response.send_message(
                f"チャンネル作成に失敗しました: {e}", ephemeral=True
            )

        # ベースVCとして記録
        await self.bot.database.add_base_channel(new_vc.id, guild.id, author.id)

        await interaction.response.send_message(
            f"ベースVCを作成しました: {new_vc.mention}\nこのチャンネルに入室すると、設定をコピーした専用VCが自動生成されます。",
            ephemeral=True,
        )

    # ---- 設定コマンド ----
    @vc.command(name="log_channel", description="ログ出力先チャンネルを設定します。")
    @app_commands.describe(channel="ログ出力先のテキストチャンネル")
    async def vc_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if interaction.guild is None:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        await self.bot.database.update_log_channel_id(interaction.guild.id, channel.id)
        await interaction.response.send_message(f"ログチャンネルを {channel.mention} に設定しました。", ephemeral=True)

    @setting.command(name="channel_name", description="ベース/複製VCの名前テンプレートを設定します。")
    @app_commands.describe(base_channel="/vc create で作成したベースVCを指定してください。", template="{user_name}, {count} が使用できます。")
    async def vc_setting_channel_name(self, interaction: discord.Interaction, base_channel: discord.VoiceChannel, template: str) -> None:
        """指定したベースVCに対して複製VCの名前テンプレートを設定します。

        - 指定可能なのは `/vc create` で作成したベースVCのみです（それ以外は拒否）。
        - 使用可能なトークン: `{user_name}`, `{count}`（ギルド単位の0始まり連番）。
        - 入力は100文字に制限します（Discordの上限に配慮）。
        """
        if interaction.guild is None:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        if base_channel.guild.id != interaction.guild.id:
            return await interaction.response.send_message("同じサーバーのチャンネルを指定してください。", ephemeral=True)
        # /vc create で作られたベースVCかチェック
        if not await self.bot.database.is_base_channel(base_channel.id):
            return await interaction.response.send_message("そのチャンネルは /vc create で作成されたベースVCではないため設定できないよ。", ephemeral=True)
        # 簡単な検証（未知の波括弧は許容するが長過ぎるのはカット）
        template = template[:100]
        await self.bot.database.set_base_channel_template(base_channel.id, template)
        await interaction.response.send_message(f"{base_channel.mention} のベースVC名テンプレートを更新しました: `{template}`", ephemeral=True)

    @vc.command(name="setting_max_channels", description="自動生成VCの同時上限数を設定します。")
    async def vc_setting_max_channels(self, interaction: discord.Interaction, limit: app_commands.Range[int, 1, 500]) -> None:
        if interaction.guild is None:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        await self.bot.database.update_max_channels(interaction.guild.id, int(limit))
        await interaction.response.send_message(f"同時上限数を {int(limit)} に設定しました。", ephemeral=True)

    @vc.command(name="setting_delete_delay", description="無人削除までの秒数を設定します。")
    async def vc_setting_delete_delay(self, interaction: discord.Interaction, seconds: app_commands.Range[int, 5, 3600]) -> None:
        if interaction.guild is None:
            return await interaction.response.send_message("サーバー内で実行してください。", ephemeral=True)
        await self.bot.database.update_delete_delay(interaction.guild.id, int(seconds))
        await interaction.response.send_message(f"削除遅延を {int(seconds)} 秒に設定しました。", ephemeral=True)

    # -------------------------
    # イベントハンドラ
    # -------------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # ユーザーがどこかに入室した
        if after.channel and (before.channel is None or before.channel.id != after.channel.id):
            await self._handle_join(member, after.channel)
        # ユーザーがどこかから退出した
        if before.channel and (after.channel is None or after.channel.id != before.channel.id):
            await self._handle_leave(before.channel)
        # ユーザーが生成VCに再入室した場合は削除スケジュールを解除
        if after.channel:
            await self._cancel_delete_if_generated(after.channel)

    async def _handle_join(self, member: discord.Member, channel: discord.VoiceChannel) -> None:
        key = (member.id, channel.id)
        if key in self._processing_joins:
            return
        self._processing_joins.add(key)
        try:
            # ベースVCでなければ無視
            if not await self.bot.database.is_base_channel(channel.id):
                return

            # 上限チェック
            settings = await self.bot.database.get_or_create_guild_vc_settings(channel.guild.id)
            active = await self.bot.database.count_active_generated_channels(channel.guild.id)
            if active >= int(settings["max_channels"]):
                try:
                    await member.send(f"現在、自動生成VCの上限 ({settings['max_channels']}) に達しています。しばらくしてからお試しください。")
                except Exception:
                    pass
                await self._log(channel.guild, f"上限超過のため {member.display_name} の複製VC作成をスキップしました（{active}/{settings['max_channels']}）。")
                return

            # 元VCの設定をコピー
            try:
                new_name = await self._compute_clone_name(channel, member)
                new_channel = await self._clone_voice_channel(channel, new_name)
            except discord.Forbidden:
                await self._log(channel.guild, "権限不足のためVCを複製できませんでした。")
                return
            except discord.HTTPException as e:
                await self._log(channel.guild, f"VCの複製に失敗しました: {e}")
                return

            # DBに登録（生成VC）
            await self.bot.database.add_generated_channel(new_channel.id, channel.guild.id, channel.id, member.id)
            await self._log(channel.guild, f"複製VCを作成しました: {new_channel.name}（元: {channel.name} / ユーザー: {member.display_name}）")

            # ユーザーを移動
            try:
                await member.move_to(new_channel)
                await self._log(channel.guild, f"{member.display_name} を {new_channel.name} に移動しました。")
            except discord.Forbidden:
                await self._log(channel.guild, f"{member.display_name} を移動できません（権限不足）。")
            except discord.HTTPException as e:
                await self._log(channel.guild, f"{member.display_name} の移動に失敗: {e}")
        finally:
            # ほんの僅かな待機で連続イベントを緩和
            await asyncio.sleep(0.5)
            self._processing_joins.discard(key)

    async def _handle_leave(self, channel: discord.VoiceChannel) -> None:
        # Botが生成したVCのみ対象
        if not await self.bot.database.is_generated_channel(channel.id):
            return
        # 無人なら削除スケジュール
        if len(channel.members) == 0:
            settings = await self.bot.database.get_or_create_guild_vc_settings(channel.guild.id)
            delay = int(settings["delete_delay"]) if settings else 30
            await self._schedule_delete(channel, delay)

    async def _cancel_delete_if_generated(self, channel: discord.VoiceChannel) -> None:
        if not await self.bot.database.is_generated_channel(channel.id):
            return
        task = self._delete_tasks.pop(channel.id, None)
        if task and not task.done():
            task.cancel()

    async def _schedule_delete(self, channel: discord.VoiceChannel, delay: int) -> None:
        # 既存のスケジュールがあればキャンセル
        old = self._delete_tasks.pop(channel.id, None)
        if old and not old.done():
            old.cancel()

        async def _job():
            try:
                await asyncio.sleep(delay)
                # 再確認（存在＆無人）
                if channel and len(channel.members) == 0:
                    await channel.delete(reason="自動生成VCの自動削除")
                    await self.bot.database.mark_generated_channel_deleted(channel.id)
                    # すべての生成VC（このベース由来）が消えたらカウンタを1に戻す
                    try:
                        base_id = await self.bot.database.get_base_channel_id_for_generated(channel.id)
                        if base_id is not None:
                            remain = await self.bot.database.count_active_generated_channels_for_base(base_id)
                            if remain == 0:
                                await self.bot.database.reset_base_counter(base_id)
                    except Exception:
                        pass
                    await self._log(channel.guild, f"{channel.name} を自動削除しました。")
            except asyncio.CancelledError:
                return
            except discord.Forbidden:
                await self._log(channel.guild, f"{channel.name} を削除できません（権限不足）。")
            except discord.HTTPException as e:
                await self._log(channel.guild, f"{channel.name} の削除に失敗: {e}")
            finally:
                self._delete_tasks.pop(channel.id, None)

        self._delete_tasks[channel.id] = asyncio.create_task(_job())

    async def _compute_clone_name(self, source: discord.VoiceChannel, member: discord.Member | None = None) -> str:
        """複製VCの名前を決める。ベースVCにテンプレートがあればそれを、なければギルド既定を使用。"""
        guild = source.guild
        settings = await self.bot.database.get_or_create_guild_vc_settings(guild.id)
        # {count} はベースVC単位の連番（テンプレで作成されたVCに連動）
        # ベースVCでない場合はギルド全体のカウンタを使うフォールバック
        if await self.bot.database.is_base_channel(source.id):
            next_count = await self.bot.database.get_next_base_counter(source.id)
        else:
            next_count = await self.bot.database.increment_and_get_name_counter(guild.id)
        user = member or guild.me  # フォールバックでBot自身
        # ベースVCが個別テンプレートを持っていれば優先
        base_tpl = None
        try:
            if await self.bot.database.is_base_channel(source.id):
                base_tpl = await self.bot.database.get_base_channel_template(source.id)
        except Exception:
            base_tpl = None
        template = base_tpl or settings["base_name_template"]
        name = _safe_format_name(template, user, next_count)
        # 同名存在は許容（Discordは同名チャンネルを許すため）
        return name

    async def _clone_voice_channel(self, source: discord.VoiceChannel, name: str) -> discord.VoiceChannel:
        guild = source.guild
        # パーミッションオーバーライドのコピー
        overwrites = {target: overwrite for target, overwrite in source.overwrites.items()}
        return await guild.create_voice_channel(
            name=name,
            category=source.category,
            bitrate=source.bitrate,
            user_limit=source.user_limit,
            overwrites=overwrites,
        )

    async def _log(self, guild: discord.Guild, message: str) -> None:
        try:
            settings = await self.bot.database.get_or_create_guild_vc_settings(guild.id)
            channel_id = settings.get("log_channel_id") if settings else None
            if channel_id:
                ch = guild.get_channel(int(channel_id))
                if isinstance(ch, discord.TextChannel):
                    await ch.send(message)
        except Exception:
            # ログ送信に失敗してもボットの動作は継続
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Voice(bot))
