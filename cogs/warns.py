import discord
import json
import io
from discord.ext import commands


class Warning(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            with open("data/warns.json", "r") as file:
                self.warns_dict = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as exception:
            print(f"No warns file found, or file was corrupt. Not loading warns.py\n{exception}")
            for command in self.get_commands():
                command.enabled = False
        else:
            print(f'Loaded {self.__class__.__name__} cog with {len(self.warns_dict)} entries.')

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, target: discord.Member, *, reason="No reason was given"):
        """Warns a user. Kicks at 3 and 4 warnings, bans at 5"""
        has_attch = bool(ctx.message.attachments)
        if target == ctx.message.author:
            return await ctx.send("You can't warn yourself, obviously.")
        elif ctx.author.top_role.position < target.top_role.position + 1:
            return await ctx.send("That person has a role higher than or equal to yours, you can't kick them.")
        self.warns_dict.setdefault(str(target.id), [])
        self.warns_dict[str(target.id)].append(
            {
                "reason": reason,
                "date": discord.utils.format_dt(target.created_at),
                "warned_by": f"{ctx.author}",
            })
        warns = self.warns_dict[str(target.id)]
        dm_msg = f"You were warned on {ctx.guild}.\nThe reason provided was: `{reason}`.\nThis is warn #{len(warns)}."
        log_msg = ""
        if len(warns) >= 5:
            dm_msg += "\nYou were banned for this warn."
            log_msg += "They were banned as a result of this warn."
        elif len(warns) >= 3:
            dm_msg += "\nYou were kicked for this warn."
            if len(warns) == 4:
                dm_msg += "\nYou will be automatically banned if you are warned again."
            log_msg += "They were kicked as a result of this warn."
        elif len(warns) == 2:
            dm_msg += "You will be automatically kicked if you are warned again."
        embed = discord.Embed(title=f"{target} warned")
        embed.description = f"{target} | {target.id} was warned in {ctx.channel.mention} by {ctx.author} for `{reason}`. This is warn #{len(warns)}. {log_msg}"
        if len(embed.description) > 4096:
            embed.description = f"{embed.description[:4093]}..."
        try:
            if has_attch:
                img_bytes = await ctx.message.attachments[0].read()
                warn_img = discord.File(io.BytesIO(img_bytes), 'image.png')
                log_img = discord.File(io.BytesIO(img_bytes), 'warn_image.png')
                await target.send(dm_msg, file=warn_img)
            else:
                await target.send(dm_msg)
        except discord.Forbidden:
            embed.description = f"{embed.description}\n**Could not DM user.**"
            if len(embed.description) > 4096:
                embed.description = f"{embed.description[:4093]}..."
        with open("data/warns.json", "w") as file:
            json.dump(self.warns_dict, file, indent=4)
        if len(warns) >= 5:
            await target.ban(reason=f"Warn #{len(warns)}", delete_message_days=0)
        elif len(warns) >= 3:
            await target.kick(reason=f"Warn #{len(warns)}")
        if has_attch:
            embed.set_thumbnail(url="attachment://warn_image.png")
            await self.bot.logs_channel.send(embed=embed, file=log_img)
        else:
            await self.bot.logs_channel.send(embed=embed)
        if len(warns) >= 5:
            return await ctx.send(f"Warned {target}. This is warn #{len(warns)}. {log_msg}", embed=embed)
        await ctx.send(f"Warned {target}. This is warn #{len(warns)}. {log_msg}")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def delwarn(self, ctx, target: discord.User, *, warn):
        """Deletes a users warn. Can take the warn number, or the warn reason"""
        try:
            target_warns = self.warns_dict[str(target.id)]
            warnings = len(target_warns)
            if warnings == 0:
                return await ctx.send(f"{target} doesn't have any warnings!")
        except KeyError:
            return await ctx.send(f"{target} hasn't been warned before!")
        if warn.isdigit():
            warn_index = int(warn) - 1
            if warn_index < 0 or warn_index >= len(target_warns):
                return await ctx.send(f"{target} doesn't have a warn with that number.")
            warn = target_warns.pop(warn_index)
        else:
            warn_match = next((warn_entry for warn_entry in target_warns if warn_entry.get("reason") == warn), None)
            if warn_match is None:
                return await ctx.send(f"{target} doesn't have a warn matching `{warn}`.")
            target_warns.remove(warn_match)
            warn = warn_match
        with open("data/warns.json", "w") as file:
            json.dump(self.warns_dict, file, indent=4)
        await ctx.send(f"Removed warn from {target}.")
        warns_count = len(self.warns_dict[str(target.id)])
        embed = discord.Embed(title=f"Warn removed from {target}")
        warn_reason = warn["reason"]
        if len(warn_reason) > 1024:
            warn_reason = f"{warn_reason[:1021]}..."
        embed.add_field(name="Warn Reason:", value=warn_reason)
        embed.add_field(name="Warned By:", value=warn["warned_by"])
        embed.add_field(name="Warned On:", value=warn["date"])
        embed.set_footer(text=f"{target.name} now has {warns_count} warn(s).")
        try:
            await target.send(f"Warn `{warn['reason']}` was removed on {ctx.guild}. You now have {warns_count} warn(s).")
        except discord.Forbidden:
            embed.description = "\n**Could not DM user.**"
        await self.bot.logs_channel.send(f"{target} had a warn removed:", embed=embed)

    @commands.command()
    async def listwarns(self, ctx, target: discord.User = None):
        """Allows a user to list their own warns, or a staff member to list a user's warns"""
        if not target or target == ctx.author:
            target = ctx.author
        elif target and not ctx.author.guild_permissions.kick_members:
            raise commands.errors.CheckFailure()
        try:
            warns = self.warns_dict[str(target.id)]
        except KeyError:
            return await ctx.send(f"{target} has no warns.")
        embed = discord.Embed(title=f"Warns for {target}")
        count = 0
        for warn in warns:
            count += 1
            field_value = f"**Reason**: {warn['reason']}\n**Issued By**: {warn['warned_by']}"
            if len(field_value) > 1024:
                field_value = f"{field_value[:1021]}..."
            embed.add_field(name=f"#{count}: {warn['date']}", value=field_value)
        if count == 0:
            return await ctx.send(f"{target} has no warns.")
        embed.set_footer(text=f"Total warns: {count}")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def clearwarns(self, ctx, target: discord.User):
        """Clears all of a users warns"""
        try:
            warns = self.warns_dict[str(target.id)]
            if len(warns) == 0:
                return await ctx.send(f"{target} doesn't have any warnings!")
            self.warns_dict[str(target.id)] = []
        except KeyError:
            return await ctx.send(f"{target} already has no warns.")
        await ctx.send(f"Cleared warns for {target}.")
        with open("data/warns.json", "w") as file:
            json.dump(self.warns_dict, file, indent=4)
        embed = discord.Embed(title=f"Warns for {target} cleared")
        embed.description = f"{target} | {target.id} had their warns cleared by {ctx.author}. Warns can be found below."
        if len(embed.description) > 4096:
            embed.description = f"{embed.description[:4093]}..."
        count = 0
        for warn in warns:
            count += 1
            field_value = f"**Reason**: {warn['reason']}\n**Issued By**: {warn['warned_by']}"
            if len(field_value) > 1024:
                field_value = f"{field_value[:1021]}..."
            embed.add_field(name=f"#{count}: {warn['date']}", value=field_value)
        try:
            await target.send(f"All of your warns were cleared on {ctx.guild}.")
        except discord.Forbidden:
            embed.description = f"{embed.description}\n**Could not DM user.**"
            if len(embed.description) > 4096:
                embed.description = f"{embed.description[:4093]}..."
        await self.bot.logs_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Warning(bot))
