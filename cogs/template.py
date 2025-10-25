"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
説明:
🐍 独自のパーソナライズされたDiscordボットをPythonでコーディングするためのシンプルなテンプレート

バージョン: 6.4.0
"""

from discord.ext import commands
from discord.ext.commands import Context


# ここでCogに名前を付け、Cogの新しいクラスを作成します。
class Template(commands.Cog, name="template"):
    def __init__(self, bot) -> None:
        self.bot = bot

    # ここで独自のコマンドを追加できます。常に最初のパラメータとして"self"を提供する必要があります。

    @commands.hybrid_command(
        name="testcommand",
        description="これは何もしないテスト用コマンドです。",
    )
    async def testcommand(self, context: Context) -> None:
        """
        これは何もしないテスト用コマンドです。

        :param context: アプリケーションコマンドのコンテキスト。
        """
        # ここで独自の処理を行ってください

        # "pass"を削除することを忘れないでください。メソッドに内容がないため追加しただけです。
        pass


# 最後にCogをボットに追加して、ロード、アンロード、再ロードし、その内容を使用できるようにします。
async def setup(bot) -> None:
    await bot.add_cog(Template(bot))
