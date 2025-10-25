"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
説明:
🐍 独自のパーソナライズされたDiscordボットをPythonでコーディングするためのシンプルなテンプレート

バージョン: 6.4.0
"""

import platform

import discord
from discord.ext import commands
from discord.ext.commands import Context


class General(commands.Cog, name="general"):
    def __init__(self, bot) -> None:
        self.bot = bot



    @commands.hybrid_command(
        name="help", description="ボットが読み込んだすべてのコマンドを一覧表示します。"
    )
    async def help(self, context: Context) -> None:
        embed = discord.Embed(
            title="ヘルプ", description="利用可能なコマンドの一覧：", color=0xBEBEFE
        )
        for i in self.bot.cogs:
            if i == "owner" and not (await self.bot.is_owner(context.author)):
                continue
            cog = self.bot.get_cog(i.lower())
            commands = cog.get_commands()
            data = []
            for command in commands:
                description = command.description.partition("\n")[0]
                data.append(f"{command.name} - {description}")
            help_text = "\n".join(data)
            embed.add_field(
                name=i.capitalize(), value=f"```{help_text}```", inline=False
            )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="botinfo",
        description="ボットに関する便利な（またはそうでない）情報を取得します。",
    )
    async def botinfo(self, context: Context) -> None:
        """
        ボットに関する便利な（またはそうでない）情報を取得します。

        :param context: ハイブリッドコマンドのコンテキスト。
        """
        embed = discord.Embed(
            description="[Krypton](https://krypton.ninja) のテンプレートを使用しています。",
            color=0xBEBEFE,
        )
        embed.set_author(name="ボット情報")
        embed.add_field(name="所有者:", value="Krypton#7331", inline=True)
        embed.add_field(
            name="Pythonバージョン:", value=f"{platform.python_version()}", inline=True
        )
        embed.add_field(
            name="プレフィックス:",
            value=f"/ (スラッシュコマンド) または 通常コマンドの場合は {self.bot.bot_prefix}",
            inline=False,
        )
        embed.set_footer(text=f"{context.author} によるリクエスト")
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="serverinfo",
        description="サーバーに関する便利な（またはそうでない）情報を取得します。",
    )
    async def serverinfo(self, context: Context) -> None:
        """
        サーバーに関する便利な（またはそうでない）情報を取得します。

        :param context: ハイブリッドコマンドのコンテキスト。
        """
        roles = [role.name for role in context.guild.roles]
        num_roles = len(roles)
        if num_roles > 50:
            roles = roles[:50]
            roles.append(f">>>> ロールを表示中 [50/{num_roles}] 件")
        roles = ", ".join(roles)

        embed = discord.Embed(
            title="**サーバー名:**", description=f"{context.guild}", color=0xBEBEFE
        )
        if context.guild.icon is not None:
            embed.set_thumbnail(url=context.guild.icon.url)
        embed.add_field(name="サーバーID", value=context.guild.id)
        embed.add_field(name="メンバー数", value=context.guild.member_count)
        embed.add_field(
            name="テキスト/ボイスチャンネル", value=f"{len(context.guild.channels)}"
        )
        embed.add_field(name=f"ロール ({len(context.guild.roles)})", value=roles)
        embed.set_footer(text=f"作成日時: {context.guild.created_at}")
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="ping",
        description="ボットが稼働しているかを確認します。",
    )
    async def ping(self, context: Context) -> None:
        """
        ボットが稼働しているかを確認します。

        :param context: ハイブリッドコマンドのコンテキスト。
        """
        embed = discord.Embed(
            title="🏓 ポン！",
            description=f"ボットの遅延は{round(self.bot.latency * 1000)}msです。",
            color=0xBEBEFE,
        )
        await context.send(embed=embed)












async def setup(bot) -> None:
    await bot.add_cog(General(bot))
