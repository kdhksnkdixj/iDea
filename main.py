import asyncio
import os
import time
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = "YOUR_BOT_TOKEN_HERE"
BYPASS_API = "https://your-bypass-api.com/bypass"  # ضع رابط API الـ bypass هنا

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

cooldowns: dict[int, float] = {}


async def bypass_link(url: str) -> tuple[bool, str]:
    """يرسل الرابط لـ API الـ bypass ويرجع المفتاح"""
    timeout = aiohttp.ClientTimeout(total=120)  # البايباس قد ياخذ وقت
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # هنا نرسل الرابط للـ API. بعض الـ APIs تطلب GET والبعض POST
            async with session.post(BYPASS_API, json={"url": url}) as resp:
                if resp.status != 200:
                    return False, f"فشل الـ API — HTTP {resp.status}"
                data = await resp.json()
                key = data.get("key") or data.get("data", {}).get("key")
                if not key:
                    return False, "الـ API ما رجع مفتاح."
                return True, str(key)
    except asyncio.TimeoutError:
        return False, "انتهى وقت الاتصال بـ API (تجاوز 120 ثانية)."
    except aiohttp.ClientError as e:
        return False, f"خطأ في الاتصال بـ API: {e}"
    except Exception as e:
        return False, f"خطأ غير متوقع: {e}"


class CopyKeyView(discord.ui.View):
    def __init__(self, key: str):
        super().__init__(timeout=300)
        self.key = key

    @discord.ui.button(label="Copy Key", style=discord.ButtonStyle.success, emoji="📋")
    async def copy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # يرسل المفتاح كرسالة ephemeral عشان يقدر ينسخه بسهولة
        await interaction.response.send_message(
            f"`{self.key}`", ephemeral=True
        )


class KeyModal(discord.ui.Modal):
    def __init__(self, kind: str, label: str):
        super().__init__(title=f"{label} — ضع الرابط")
        self.kind = kind
        self.label_text = label
        self.link = discord.ui.TextInput(
            label="رابط المفتاح",
            placeholder="https://auth.platorelay.com/a?d=...",
            required=True,
            max_length=500,
        )
        self.add_item(self.link)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        left = remaining_cooldown(user_id)
        if left > 0:
            await interaction.response.send_message(
                f"انتظر {int(left) + 1} ثانية قبل ما تطلب مرة ثانية.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        cooldowns[user_id] = time.monotonic()

        await asyncio.sleep(5)  # التأخير المطلوب (5 ثواني)

        ok, result = await bypass_link(self.link.value)
        if not ok:
            await interaction.followup.send(f"❌ {result}", ephemeral=True)
            return

        key = result
        bump_stat(self.kind, user_id)

        # تصميم الـ Embed نفسه اللي بالصورة
        embed = discord.Embed(
            title="Bypass Complete",
            description=(
                "Your key has been retrieved successfully.\n\n"
                "✅\n\n"
                "**Key:**\n"
                f"`{key}`\n\n"
                "Tap to copy on mobile."
            ),
            color=0x2b2d31
        )
        # تقدر تحط صورة الـ thumbnail هنا (مثل صورة الكلب اللي بالصورة)
        embed.set_thumbnail(url="https://i.imgur.com/your_image.png")
        embed.set_footer(text="KeyCrusher")  # أو اسم البوت حقك

        view = CopyKeyView(key)

        # 1) الخاص
        dm_note = "✅ وصلك على الخاص."
        try:
            await interaction.user.send(embed=embed, view=view)
        except discord.Forbidden:
            dm_note = "⚠️ ما قدرت أرسل على الخاص — افتح DMs وأعد المحاولة."

        # 2) رسالة ephemeral في الروم (ما يشوفها غير الشخص)
        await interaction.followup.send(content=dm_note, embed=embed, view=view, ephemeral=True)


class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Get Hack Key", style=discord.ButtonStyle.danger, custom_id="btn_hack", emoji="🔑")
    async def hack_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KeyModal("hack", "Hack Key"))

    @discord.ui.button(label="Get Script Key", style=discord.ButtonStyle.primary, custom_id="btn_script", emoji="📜")
    async def script_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KeyModal("script", "Script Key"))


@bot.event
async def on_ready():
    bot.add_view(PanelView())
    synced = await bot.tree.sync()
    print(f"logged in as {bot.user} | synced {len(synced)} commands")


@bot.tree.command(name="panel", description="ينشر لوحة المفاتيح")
@app_commands.checks.has_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔑 Key Panel",
        description="اختر نوع المفتاح — البوت يجيب المفتاح ويرسله لك على الخاص + هنا.",
        color=0x2b2d31,
    )
    await interaction.response.send_message(embed=embed, view=PanelView())


# (دوال الإحصائيات load_stats, save_stats, bump_stat, remaining_cooldown)
# تقدر تحطها كما هي من الكود السابق

bot.run(TOKEN)