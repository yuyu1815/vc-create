"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
説明:
🐍 独自のパーソナライズされたDiscordボットをPythonでコーディングするためのシンプルなテンプレート

バージョン: 6.4.0
"""

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context


class Owner(commands.Cog, name="owner"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.command(
        name="sync",
        description="スラッシュコマンドを同期します。",
    )
    @app_commands.describe(scope="同期のスコープ。`global`または`guild`のいずれか")
    @commands.is_owner()
    async def sync(self, context: Context, scope: str) -> None:
        """
        スラッシュコマンドを同期します。

        :param context: コマンドのコンテキスト。
        :param scope: 同期のスコープ。`global`または`guild`のいずれか。
        """

        if scope == "global":
            await context.bot.tree.sync()
            embed = discord.Embed(
                description="スラッシュコマンドがグローバルに同期されました。",
                color=0xBEBEFE,
            )
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.copy_global_to(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(
                description="スラッシュコマンドがこのギルドで同期されました。",
                color=0xBEBEFE,
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description="スコープは`global`または`guild`である必要があります。", color=0xE02B2B
        )
        await context.send(embed=embed)

    @commands.command(
        name="unsync",
        description="スラッシュコマンドの同期を解除します。",
    )
    @app_commands.describe(
        scope="同期のスコープ。`global`、`current_guild`または`guild`のいずれか"
    )
    @commands.is_owner()
    async def unsync(self, context: Context, scope: str) -> None:
        """
        スラッシュコマンドの同期を解除します。

        :param context: コマンドのコンテキスト。
        :param scope: 同期のスコープ。`global`、`current_guild`または`guild`のいずれか。
        """

        if scope == "global":
            context.bot.tree.clear_commands(guild=None)
            await context.bot.tree.sync()
            embed = discord.Embed(
                description="スラッシュコマンドのグローバル同期が解除されました。",
                color=0xBEBEFE,
            )
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.clear_commands(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(
                description="このギルドでのスラッシュコマンドの同期が解除されました。",
                color=0xBEBEFE,
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description="スコープは`global`または`guild`である必要があります。", color=0xE02B2B
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="load",
        description="Cogをロードします",
    )
    @app_commands.describe(cog="ロードするCogの名前")
    @commands.is_owner()
    async def load(self, context: Context, cog: str) -> None:
        """
        ボットは指定されたCogをロードします。

        :param context: ハイブリッドコマンドのコンテキスト。
        :param cog: ロードするCogの名前。
        """
        try:
            await self.bot.load_extension(f"cogs.{cog}")
        except Exception:
            embed = discord.Embed(
                description=f"モジュール`{cog}`をロードできませんでした。", color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"モジュール`{cog}`を正常にロードしました。", color=0xBEBEFE
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="unload",
        description="Cogをアンロードします。",
    )
    @app_commands.describe(cog="アンロードするCogの名前")
    @commands.is_owner()
    async def unload(self, context: Context, cog: str) -> None:
        """
        ボットは指定されたCogをアンロードします。

        :param context: ハイブリッドコマンドのコンテキスト。
        :param cog: アンロードするCogの名前。
        """
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
        except Exception:
            embed = discord.Embed(
                description=f"モジュール`{cog}`をアンロードできませんでした。", color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"モジュール`{cog}`を正常にアンロードしました。", color=0xBEBEFE
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="reload",
        description="Cogを再ロードします。",
    )
    @app_commands.describe(cog="再ロードするCogの名前")
    @commands.is_owner()
    async def reload(self, context: Context, cog: str) -> None:
        """
        ボットは指定されたCogを再ロードします。

        :param context: ハイブリッドコマンドのコンテキスト。
        :param cog: 再ロードするCogの名前。
        """
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
        except Exception:
            embed = discord.Embed(
                description=f"モジュール`{cog}`を再読み込みできませんでした。", color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"モジュール`{cog}`を正常に再読み込みしました。", color=0xBEBEFE
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="shutdown",
        description="ボットをシャットダウンさせます。",
    )
    @commands.is_owner()
    async def shutdown(self, context: Context) -> None:
        """
        ボットをシャットダウンします。

        :param context: ハイブリッドコマンドのコンテキスト。
        """
        embed = discord.Embed(description="シャットダウン中です。さようなら！ :wave:", color=0xBEBEFE)
        await context.send(embed=embed)
        await self.bot.close()

    @commands.hybrid_command(
        name="say",
        description="ボットがあなたの望むものを何でも言います。",
    )
    @app_commands.describe(message="ボットが繰り返すべきメッセージ")
    @commands.is_owner()
    async def say(self, context: Context, *, message: str) -> None:
        """
        ボットがあなたの望むものを何でも言います。

        :param context: ハイブリッドコマンドのコンテキスト。
        :param message: ボットが繰り返すべきメッセージ。
        """
        await context.send(message)

    @commands.hybrid_command(
        name="embed",
        description="ボットがあなたの望むものを何でも言いますが、埋め込みメッセージ内で言います。",
    )
    @app_commands.describe(message="ボットが繰り返すべきメッセージ")
    @commands.is_owner()
    async def embed(self, context: Context, *, message: str) -> None:
        """
        ボットがあなたの望むものを何でも言いますが、埋め込みメッセージを使用して言います。

        :param context: ハイブリッドコマンドのコンテキスト。
        :param message: ボットが繰り返すべきメッセージ。
        """
        embed = discord.Embed(description=message, color=0xBEBEFE)
        await context.send(embed=embed)


async def setup(bot) -> None:
    await bot.add_cog(Owner(bot))
