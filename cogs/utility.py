import discord
import functools
import asyncio
import os
import sys
import json
from discord.ext import commands


class Utility(commands.Cog):
    """Various utility commands."""

    def __init__(self, bot):
        self.bot = bot
        print(f"Loaded {self.__class__.__name__} cog.")

    def check_stream_perms(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_self = args[0]  # assume self is at args[0]
            ctx = args[1]  # and assume ctx is at args[1]
            channel = getattr(func_self.bot, "going_live_channel", None)
            if channel is None:
                return await ctx.send("Going-live channel is not configured yet.")
            if not channel.permissions_for(ctx.author).send_messages:
                return await ctx.send("You don't have permission to use this command.")
            await func(*args, **kwargs)
        return wrapper
    
    @commands.command(aliases=["streamnotify", "golive"])
    @check_stream_perms
    async def going_live(self, ctx, *, stream_location: str):
        """Sends a message to the #going-live channel. Only works if you have send messages perms in that channel."""
        stream_location = stream_location.lower()
        if stream_location == "twitch":
             url = "https://www.twitch.tv/gpg5"
        elif stream_location == "tiktok":
            url = "https://www.tiktok.com/@gpgrocker/live"
        elif stream_location == "both":
            embed = discord.Embed(title=f"{ctx.author.display_name} is going live!", description=f"Check out the stream on [Twitch](https://www.twitch.tv/gpg5) and [TikTok](https://www.tiktok.com/@gpgrocker/live)!", colour=discord.Colour.purple())
            embed.set_thumbnail(url=str(ctx.author.display_avatar))
            await self.bot.going_live_channel.send(embed=embed)
            return await ctx.send(f"✅ Successfully sent a message to {self.bot.going_live_channel.mention}.")
        else:
            return await ctx.send("Please specify a valid stream location. Valid options are: `twitch`, `tiktok`, `both`.")
        embed = discord.Embed(title=f"{ctx.author.display_name} is going live!", description=f"Check out the stream on [{stream_location.title()}]({url})!", colour=discord.Colour.purple())
        embed.set_thumbnail(url=str(ctx.author.display_avatar))
        await self.bot.going_live_channel.send(content=self.bot.going_live_role.mention, embed=embed)
        await ctx.send(f"✅ Successfully sent a message to {self.bot.going_live_channel.mention}.")

    @commands.command()
    @commands.is_owner()
    async def gitpull(self, ctx):
        message = await ctx.send("Pulling from git...")
        pre_head = ""
        try:
            pre_head_proc = await asyncio.create_subprocess_exec("git", "rev-parse", "HEAD", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            pre_head_stdout, _ = await asyncio.wait_for(pre_head_proc.communicate(), timeout=10)
            pre_head = pre_head_stdout.decode("utf-8", errors="replace").strip()
            proc = await asyncio.create_subprocess_exec("git", "pull", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            return await message.edit(content="Timed out while pulling from git.")
        resp = "\n".join([stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")]).strip()
        if not resp:
            resp = "(no output)"
        short_resp = resp if len(resp) <= 1800 else f"{resp[:1797]}..."
        if proc.returncode != 0:
            return await message.edit(content=f"Git pull failed (exit {proc.returncode}).\n```{short_resp}```")
        if resp.startswith("Already up to date."):
            return await message.edit(content=f"```{short_resp}```")
        await message.edit(content=f"Commits pulled! Restarting...\n```{short_resp}```")
        restart_args = [sys.executable, os.path.abspath(sys.argv[0]), "gitpull", str(ctx.channel.id)]
        if pre_head:
            restart_args.append(pre_head)
            await ctx.send(f"Testing message. Pre-HEAD commit: `{pre_head}`")
        os.execv(sys.executable, restart_args)

    @commands.command(aliases=["configinfo"])
    @commands.is_owner()
    async def check_config(self, ctx):
        """Checks data in the bot's config.json"""
        with open("config.json", "r") as file:
            loaded_config = json.load(file)
        guild_data = loaded_config.get("guild_data", {}) if isinstance(loaded_config.get("guild_data", {}), dict) else {}
        prefixes = loaded_config.get("prefix", [])
        if not isinstance(prefixes, list):
            prefixes = [prefixes]
        prefix_text = ", ".join(f"`{prefix}`" for prefix in prefixes)
        summary_lines = [
            f"`is_beta`: {loaded_config.get('is_beta')}",
            f"`prefix`: {prefix_text}",
            f"`guild_id`: {guild_data.get('guild_id')}",
        ]
        channel_lines = []
        role_lines = []
        other_lines = []
        for attrib in sorted(attr for attr in vars(self.bot) if attr.endswith("_channel") or attr.endswith("_role")):
            value = getattr(self.bot, attrib, None)
            if isinstance(value, discord.abc.GuildChannel):
                channel_lines.append(f"{attrib}: {value.mention} ({value.id})")
            elif isinstance(value, discord.Role):
                role_lines.append(f"{attrib}: {value.mention} ({value.id})")
            else:
                other_lines.append(f"{attrib}: {value}")

        embed = discord.Embed(title="Config Check")
        embed.add_field(name="Summary", value="\n".join(summary_lines), inline=False)
        if channel_lines:
            channels_text = "\n".join(channel_lines)
            if len(channels_text) > 1024:
                channels_text = f"{channels_text[:1021]}..."
            embed.add_field(name=f"Channels ({len(channel_lines)})", value=channels_text, inline=True)
        if role_lines:
            roles_text = "\n".join(role_lines)
            if len(roles_text) > 1024:
                roles_text = f"{roles_text[:1021]}..."
            embed.add_field(name=f"Roles ({len(role_lines)})", value=roles_text, inline=True)
        if other_lines:
            other_text = "\n".join(other_lines)
            if len(other_text) > 1024:
                other_text = f"{other_text[:1021]}..."
            embed.add_field(name="Other", value=other_text, inline=False)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))

