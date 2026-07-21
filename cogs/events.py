import discord
from discord.ext import commands
import asyncio


class Events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        print(f"Loaded {self.__class__.__name__} cog.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Log joins
        embed = discord.Embed(title="Member Joined", colour=discord.Colour.green())
        embed.add_field(name="Member", value=f"{member.mention} | {member}", inline=False)
        embed.add_field(name="Joined At", value=discord.utils.format_dt(member.joined_at, style="F"), inline=False)
        await self.bot.join_logs_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Log leaves
        embed = discord.Embed(title="Member Left", colour=discord.Colour.red())
        embed.add_field(name="Member", value=f"{member.mention} | {member}", inline=False)
        embed.add_field(name="Joined At", value=discord.utils.format_dt(member.joined_at, style="F"), inline=False)
        embed.add_field(name="Left At", value=discord.utils.format_dt(discord.utils.utcnow(), style="F"), inline=False)
        await self.bot.join_logs_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Log member nickname changes
        if before.nick != after.nick:
            embed = discord.Embed(title="Member Nickname Changed", colour=discord.Colour.blue())
            embed.add_field(name="Member", value=f"{after.mention} | {after}", inline=False)
            embed.add_field(name="Before", value=f"`{before.nick if before.nick else 'None'}`", inline=False)
            embed.add_field(name="After", value=f"`{after.nick if after.nick else 'None'}`", inline=False)
            embed.add_field(name="Changed At", value=discord.utils.format_dt(discord.utils.utcnow(), style="F"), inline=False)
            await self.bot.mod_logs_channel.send(embed=embed)
        
        # Log member role changes (likely triggered by Onboarding)
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]

            if added_roles or removed_roles:
                embed = discord.Embed(title="Member Roles Updated", colour=discord.Colour.blue())
                embed.add_field(name="Member", value=f"{after.mention} | {after}", inline=False)
                if added_roles:
                    embed.add_field(name="Roles Added", value=", ".join([role.mention for role in added_roles]), inline=False)
                if removed_roles:
                    embed.add_field(name="Roles Removed", value=", ".join([role.mention for role in removed_roles]), inline=False)
                embed.add_field(name="Updated At", value=discord.utils.format_dt(discord.utils.utcnow(), style="F"), inline=False)
                await self.bot.mod_logs_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        # This is very gross handling for me to be lazy and not pass attachments to the listener
        await asyncio.sleep(5)  # Wait to see if a ban is logged via command
        async for message in self.bot.mod_logs_channel.history(limit=5):
            if message.author == self.bot.user and message.embeds:
                description = message.embeds[0].description
                if description and str(user) in description:
                    return  # If the user is already in the log, don't log again

        # Log bans
        embed = discord.Embed(title="Member Banned", colour=discord.Colour.red())
        embed.add_field(name="Member", value=f"{user.mention} | {user}", inline=False)
        embed.add_field(name="Banned At", value=discord.utils.format_dt(discord.utils.utcnow(), style="F"), inline=False)
        await self.bot.mod_logs_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if isinstance(message.channel, discord.DMChannel):
            embed = discord.Embed(title="DM Received")
            embed.add_field(name="Author", value=f"{message.author} ({message.author.mention})")
            msg_content = message.content
            if len(msg_content) > 1024:
                msg_content = f"{msg_content[:1021]}..."
            embed.add_field(name="Message", value=msg_content, inline=False)
            await self.bot.dm_logs_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.id == self.bot.user.id:
            return
        if not isinstance(message.channel, (discord.abc.GuildChannel, discord.threads.Thread)):
            return
        if not message.content or message.type == discord.MessageType.pins_add:
            return
        embed = discord.Embed(title="Message Deleted")
        if message.reference is not None:
            ref = message.reference.resolved
            if ref is not None:
                replied_to = f"[{'@' if len(message.mentions) > 0 and ref.author in message.mentions else ''}{ref.author}]({ref.jump_url}) ({ref.author.id})"
                if len(replied_to) > 1024:
                    replied_to = f"{replied_to[:1021]}..."
                embed.add_field(name="Replied To", value=replied_to)
        if isinstance(message.channel, discord.threads.Thread):
            embed.add_field(name="Thread Location", value=f"{message.channel.parent.mention} ({message.channel.parent.id})", inline=False)
        embed.add_field(name="Author", value=f"{message.author} ({message.author.mention})")
        embed.add_field(name="Channel", value=f"{message.channel.mention}")
        msg_content = message.content
        if len(msg_content) > 1024:
            msg_content = f"{msg_content[:1021]}..."
        embed.add_field(name="Message", value=msg_content, inline=False)
        await self.bot.deleted_logs_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Events(bot))
