import discord
import functools
import asyncio
import os
import sys
import json
import urllib.parse
import urllib.request
import config_handler
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

    def _fetch_oembed_metadata(self, target_url, provider):
        encoded_url = urllib.parse.quote(target_url, safe=":/")
        request_url = f"https://www.{provider}.com/oembed?url={encoded_url}"
        headers = {"User-Agent": "SkyeBot/1.0"}
        request = urllib.request.Request(request_url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.load(response)
            if isinstance(payload, dict) and payload:
                return payload
        except Exception:
            pass
        return {}

    async def _get_stream_metadata(self, target_url, provider):
        return await asyncio.to_thread(self._fetch_oembed_metadata, target_url, provider)

    @property
    def pingable_roles(self):
        if config_handler.config is None:
            return {}

        roles = {}
        for key, bot_attr in config_handler.config.get_public_notif_roles().items():
            role_obj = getattr(self.bot, bot_attr, None)
            if role_obj is not None:
                short_key = key.split("_", 1)[0]
                roles[short_key] = role_obj
        return roles
    
    @commands.command(aliases=["streamnotify", "golive"])
    @check_stream_perms
    async def going_live(self, ctx, *, stream_location: str):
        """Sends a message to the #going-live channel. Only works if you have send messages perms in that channel."""
        stream_location = stream_location.lower()
        twitch_url = "https://www.twitch.tv/gpg5"
        tiktok_url = "https://www.tiktok.com/@gpgrocker/live"
        if stream_location == "twitch":
            metadata = await self._get_stream_metadata(twitch_url, "twitch.tv")
            stream_title = metadata.get("title") if isinstance(metadata, dict) else None
            thumb_url = metadata.get("thumbnail_url") if isinstance(metadata, dict) else None
            embed = discord.Embed(title=f"{ctx.author.display_name} is going live!", description=f"Check out the stream on [Twitch]({twitch_url})!", colour=discord.Colour.purple())
            if stream_title:
                embed.add_field(name="Stream Title", value=stream_title[:1024], inline=False)
            embed.set_thumbnail(url=thumb_url or str(ctx.author.display_avatar))
        elif stream_location == "tiktok":
            metadata = await self._get_stream_metadata(tiktok_url, "tiktok.com")
            stream_title = metadata.get("title") if isinstance(metadata, dict) else None
            thumb_url = metadata.get("thumbnail_url") if isinstance(metadata, dict) else None
            embed = discord.Embed(title=f"{ctx.author.display_name} is going live!", description=f"Check out the stream on [TikTok]({tiktok_url})!", colour=discord.Colour.purple())
            if stream_title:
                embed.add_field(name="Stream Title", value=stream_title[:1024], inline=False)
            embed.set_thumbnail(url=thumb_url or str(ctx.author.display_avatar))
        elif stream_location == "both":
            twitch_metadata = await self._get_stream_metadata(twitch_url, "twitch.tv")
            stream_title = twitch_metadata.get("title") if isinstance(twitch_metadata, dict) else None
            thumb_url = twitch_metadata.get("thumbnail_url") if isinstance(twitch_metadata, dict) else None
            embed = discord.Embed(
                title=f"{ctx.author.display_name} is going live!",
                description=f"Check out the stream on [Twitch]({twitch_url}) and [TikTok]({tiktok_url})!",
                colour=discord.Colour.purple(),
            )
            if stream_title:
                embed.add_field(name="Stream Title", value=stream_title[:1024], inline=False)
            embed.set_thumbnail(url=thumb_url or str(ctx.author.display_avatar))
            await self.bot.going_live_channel.send(embed=embed)
            return await ctx.send(f"✅ Successfully sent a message to {self.bot.going_live_channel.mention}.")
        else:
            return await ctx.send("Please specify a valid stream location. Valid options are: `twitch`, `tiktok`, `both`.")
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

    @commands.command(aliases=['notify'])
    async def safe_notify(self, ctx, role: str = None):
        """Allows for safe pinging of a role without exposing role mentions to everyone"""
        pingable_roles = self.pingable_roles
        if role is None:
            return await ctx.send(f"Please specify a role to ping. Valid options are: {', '.join(pingable_roles.keys())}", delete_after=10)
        elif role.lower() not in pingable_roles:
            return await ctx.send(f"Invalid role specified. Valid options are: {', '.join(pingable_roles.keys())}", delete_after=10)
        await ctx.message.delete()
        role_to_ping = pingable_roles[role.lower()]
        if role_to_ping is None:
            return await ctx.send(f"The role for '{role}' is not configured yet.")
        await ctx.send(f"{ctx.author.mention}: {role_to_ping.mention}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))

