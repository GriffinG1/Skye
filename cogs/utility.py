import discord
import functools
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
            if not func_self.bot.going_live_channel.permissions_for(ctx.author).send_messages:
                return await ctx.send("You don't have permission to use this command.")
            await func(*args, **kwargs)
        return wrapper
    
    @commands.command(aliases=["streamnotify", "golive"])
    @check_stream_perms
    async def going_live(self, ctx, *, stream_location: str):
        """Sends a message to the #going-live channel. Only works if you have send messages perms in that channel."""
        if stream_location.lower() == "twitch":
             url = f"https://www.twitch.tv/gpg5"
        elif stream_location.lower() == "tiktok":
            url = f"https://www.tiktok.com/@gpgrocker/live"
        elif stream_location.lower() == "both":
            embed = discord.Embed(title=f"{ctx.author.display_name} is going live!", description=f"Check out the stream on [Twitch](https://www.twitch.tv/gpg5) and [TikTok](https://www.tiktok.com/@gpgrocker/live)!", colour=discord.Colour.purple())
            embed.set_thumbnail(url=str(ctx.author.display_avatar))
            await self.bot.going_live_channel.send(embed=embed)
            return await ctx.send(f"✅ Successfully sent a message to {self.bot.going_live_channel.mention}.")
        else:
            return await ctx.send("Please specify a valid stream location. Valid options are: `twitch`, `tiktok`.")
        embed = discord.Embed(title=f"{ctx.author.display_name} is going live!", description=f"Check out the stream on [{stream_location.title()}]({url})!", colour=discord.Colour.purple())
        embed.set_thumbnail(url=str(ctx.author.display_avatar))
        await self.bot.going_live_channel.send(embed=embed)
        await ctx.send(f"✅ Successfully sent a message to {self.bot.going_live_channel.mention}.")

async def setup(bot: commands.Bot) -> None:
	await bot.add_cog(Utility(bot))

