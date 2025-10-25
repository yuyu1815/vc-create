"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
説明:
🐍 独自のパーソナライズされたDiscordボットをPythonでコーディングするためのシンプルなテンプレート

バージョン: 6.4.0
"""

import json
import logging
import os
import platform
import random
import sys

import aiosqlite
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv

from database import DatabaseManager

load_dotenv()

"""	
ボットインテントの設定（イベント制限）
インテントの詳細については、以下のウェブサイトを参照してください：
https://discordpy.readthedocs.io/en/latest/intents.html
https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents


デフォルトインテント:
intents.bans = True
intents.dm_messages = True
intents.dm_reactions = True
intents.dm_typing = True
intents.emojis = True
intents.emojis_and_stickers = True
intents.guild_messages = True
intents.guild_reactions = True
intents.guild_scheduled_events = True
intents.guild_typing = True
intents.guilds = True
intents.integrations = True
intents.invites = True
intents.messages = True # メッセージの内容を取得するには`message_content`が必要です
intents.reactions = True
intents.typing = True
intents.voice_states = True
intents.webhooks = True

特権インテント（Discordの開発者ポータルで有効にする必要があります）、必要な場合のみ使用してください：
intents.members = True
intents.message_content = True
intents.presences = True
"""

intents = discord.Intents.default()

"""
プレフィックス（通常）コマンドを使用する場合は、これをコメント解除してください。
スラッシュコマンドを使用することが推奨されるため、プレフィックスコマンドは使用しないでください。

プレフィックスコマンドを使用する場合は、Discord開発者ポータルで以下のインテントも有効にしてください。
"""
# intents.message_content = True

# 両方のロガーを設定


class LoggingFormatter(logging.Formatter):
    # Colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record):
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(reset)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(LoggingFormatter())
# File handler
file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

# Add the handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(os.getenv("PREFIX")),
            intents=intents,
            help_command=None,
        )
        """
        これによりカスタムボット変数が作成され、cogsでこれらの変数に簡単にアクセスできるようになります。

        例えば、ロガーは以下のコードで利用可能です：
        - self.logger # このクラス内
        - bot.logger # このファイル内
        - self.bot.logger # cogs内
        """
        self.logger = logger
        self.database = None
        self.bot_prefix = os.getenv("PREFIX")
        self.invite_link = os.getenv("INVITE_LINK")

    async def init_db(self) -> None:
        async with aiosqlite.connect(
            f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
        ) as db:
            with open(
                f"{os.path.realpath(os.path.dirname(__file__))}/database/schema.sql",
                encoding = "utf-8"
            ) as file:
                await db.executescript(file.read())
            await db.commit()

    async def load_cogs(self) -> None:
        """
        この関数のコードは、ボットが起動するたびに実行されます。
        """
        for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
            if file.endswith(".py"):
                extension = file[:-3]
                try:
                    await self.load_extension(f"cogs.{extension}")
                    self.logger.info(f"拡張機能 '{extension}' を読み込みました")
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    self.logger.error(
                        f"Failed to load extension {extension}\n{exception}"
                    )

    @tasks.loop(minutes=1.0)
    async def status_task(self) -> None:
        """
        ボットのゲームステータスタスクを設定します。
        """
        statuses = ["with you!", "with Krypton!", "with humans!"]
        await self.change_presence(activity=discord.Game(random.choice(statuses)))

    @status_task.before_loop
    async def before_status_task(self) -> None:
        """
        ステータス変更タスクを開始する前に、ボットが準備完了であることを確認します
        """
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        """
        これはボットが最初に起動したときに実行されます。
        """
        self.logger.info(f"{self.user.name} としてログインしました")
        self.logger.info(f"discord.py APIバージョン: {discord.__version__}")
        self.logger.info(f"Pythonバージョン: {platform.python_version()}")
        self.logger.info(
            f"実行環境: {platform.system()} {platform.release()} ({os.name})"
        )
        self.logger.info("-------------------")
        await self.init_db()
        await self.load_cogs()
        self.status_task.start()
        self.database = DatabaseManager(
            connection=await aiosqlite.connect(
                f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
            )
        )

    async def on_message(self, message: discord.Message) -> None:
        """
        このイベントのコードは、誰かがプレフィックスの有無にかかわらずメッセージを送信するたびに実行されます

        :param message: 送信されたメッセージ。
        """
        if message.author == self.user or message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_completion(self, context: Context) -> None:
        """
        このイベントのコードは、通常のコマンドが*正常に*実行されるたびに実行されます。

        :param context: 実行されたコマンドのコンテキスト。
        """
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        if context.guild is not None:
            self.logger.info(
                f"コマンド '{executed_command}' がサーバー '{context.guild.name}' (ID: {context.guild.id}) でユーザー '{context.author}' (ID: {context.author.id}) によって実行されました"
            )
        else:
            self.logger.info(
                f"コマンド '{executed_command}' がユーザー '{context.author}' (ID: {context.author.id}) によってDMで実行されました"
            )

    async def on_command_error(self, context: Context, error) -> None:
        """
        このイベントのコードは、通常の有効なコマンドがエラーをキャッチするたびに実行されます。

        :param context: 実行に失敗した通常のコマンドのコンテキスト。
        :param error: 発生したエラー。
        """
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            time_parts = []
            if round(hours) > 0:
                time_parts.append(f"{round(hours)}時間")
            if round(minutes) > 0:
                time_parts.append(f"{round(minutes)}分")
            if round(seconds) > 0 or not time_parts:
                time_parts.append(f"{round(seconds)}秒")
            remaining_time = " ".join(time_parts)
            embed = discord.Embed(
                description=f"**少し待ってください** - このコマンドはあと{remaining_time}で再度使用できます。",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(
                description="あなたはボットの所有者ではありません！", color=0xE02B2B
            )
            await context.send(embed=embed)
            if context.guild:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is not an owner of the bot."
                )
            else:
                self.logger.warning(
                    f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the bot's DMs, but the user is not an owner of the bot."
                )
        elif isinstance(error, commands.MissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            embed = discord.Embed(
                description="次の権限が不足しているため、このコマンドを実行できません: `"
                + missing_perms
                + "`",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            embed = discord.Embed(
                description="ボットに次の権限がないため、コマンドを完全に実行できません: `"
                + missing_perms
                + "`",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            missing_param = (
                error.param.name if hasattr(error, "param") and error.param else None
            )
            embed = discord.Embed(
                title="エラー!",
                description=
                f"必須の引数`{missing_param}`が指定されていません。"
                if missing_param
                else "必須の引数が不足しています。コマンドの使い方を確認してください。",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        else:
            raise error


bot = DiscordBot()
bot.run(os.getenv("TOKEN"))
