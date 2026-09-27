import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
from datetime import datetime, timezone

# Intents (İcazələr)
intents = discord.Intents.default()
intents.members = True          # Anında rol və təhlükəsizlik analizi üçün mütləqdir
intents.message_content = True  # .k komandası üçün

bot = commands.Bot(command_prefix=".", intents=intents)

# === BURAYA ÖZ ID-LƏRİNİ YAZ ===
CONFIG = {
    "ROLES": {
        "KAYITSIZ": 1553695585423466516,            # Kayıtsız Rol ID
        "KAYITLI_UYE": 1553695726276714537,        # Kayıtlı Üye Rol ID
        "PROFESYONEL_FUTBOLCU": 1553695512903946303, # Profesyonel Futbolcu Rol ID
        "TEKNIK_DIREKTOR": 1553695258490052638,     # Kulüp Menajeri Rol ID
        "KAYIT_YETKILISI": 1553693092975083562     # Kayıt Yetkilisi Rol ID
    },
    "CHANNELS": {
        "KAYIT_SALONU": 1553684536859037727         # kayıt-salonu Kanal ID
    }
}

# Üstələnilən qeydiyyatları yaddaşda saxlamaq üçün dict (TargetUserID -> ClaimerUserID)
claimed_registrations = {}

# -------------------------------------------------------------
# 1. GİRİŞDƏ: ANINDA KAYITSIZ ROLU + TƏHLÜKƏSİZLİK ANALİZİ
# -------------------------------------------------------------
@bot.event
async def on_member_join(member: discord.Member):
    # Saniyəsində Kayıtsız Rolu verir
    kayitsiz_rol = member.guild.get_role(CONFIG["ROLES"]["KAYITSIZ"])
    if kayitsiz_rol:
        await member.add_roles(kayitsiz_rol)

    # Hesabın yaşını hesablamaq (30 gündən kiçikdirsə Şübhəli)
    now = datetime.now(timezone.utc)
    account_age_days = (now - member.created_at).days
    is_trusted = account_age_days >= 30
    security_status = "🟢 Güvenilir" if is_trusted else "⚠️ Şüpheli (Yeni Hesap)"
    color = discord.Color.green() if is_trusted else discord.Color.red()

    embed = discord.Embed(
        title="📥 Yeni Üye Katıldı!",
        color=color,
        timestamp=now
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 Kullanıcı:", value=f"{member.mention} (`{member.name}`)", inline=True)
    embed.add_field(name="🆔 ID:", value=f"`{member.id}`", inline=True)
    embed.add_field(name="🛡️ Güvenlik Durumu:", value=security_status, inline=True)
    
    created_timestamp = int(member.created_at.timestamp())
    embed.add_field(name="📅 Hesap Kuruluş Tarihi:", value=f"<t:{created_timestamp}:R> ({account_age_days} gün önce)", inline=False)
    embed.set_footer(text="Kayıt işlemini başlatmak için aşağıdaki butona tıklayın.")

    # "Kayıtı Üstlen" Düyməsi
    view = View(timeout=None)
    btn_ustlen = Button(label="📌 Kayıtı Üstlen", style=discord.ButtonStyle.primary, custom_id=f"ustlen_{member.id}")
    view.add_item(btn_ustlen)

    kayit_kanal = member.guild.get_channel(CONFIG["CHANNELS"]["KAYIT_SALONU"])
    if kayitKanal := kayit_kanal:
        yetkili_rol = member.guild.get_role(CONFIG["ROLES"]["KAYIT_YETKILISI"])
        await kayitKanal.send(content=f"{yetkili_rol.mention} Hoş Geldin {member.mention}!", embed=embed, view=view)

# -------------------------------------------------------------
# 2. DÜYMƏ VƏ MODAL İDARƏSİ (INTERACTION)
# -------------------------------------------------------------
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if not interaction.type == discord.InteractionType.component:
        return

    custom_id = interaction.data.get("custom_id", "")

    # A) KAYITI ÜSTLEN DÜYMƏSİ
    if custom_id.startswith("ustlen_"):
        member_roles = [role.id for role in interaction.user.roles]
        if CONFIG["ROLES"]["KAYIT_YETKILISI"] not in member_roles and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Bu kaydı yalnızca Kayıt Yetkilileri üstlenebilir!", ephemeral=True)

        target_id = int(custom_id.split("_")[1])

        if target_id in claimed_registrations:
            claimer_id = claimed_registrations[target_id]
            return await interaction.response.send_message(f"❌ Bu kaydı zaten <@{claimer_id}> üstlendi!", ephemeral=True)

        claimed_registrations[target_id] = interaction.user.id

        disabled_view = View()
        disabled_btn = Button(label=f"📌 Üstlenen: {interaction.user.name}", style=discord.ButtonStyle.success, disabled=True)
        disabled_view.add_item(disabled_btn)

        await interaction.response.edit_message(view=disabled_view)
        await interaction.followup.send(f"✅ <@{target_id}> kullanıcısının kaydını **{interaction.user.mention}** üstlendi! Artık `.k @etiket` komutu ile kayıt edebilirsiniz.")

    # B) KAYSIT TÜRÜ SEÇİM MENÜSÜ
    elif custom_id.startswith("select_kayit_tur_"):
        target_id = custom_id.split("_")[3]
        selected_type = interaction.data["values"][0]

        # Modal (Ad yazma penceresi)
        modal = KayitIsimModal(target_id=target_id, kayit_turu=selected_type)
        await interaction.response.send_modal(modal)

# -------------------------------------------------------------
# 3. MODAL FORMU (AD YAZMA PƏNCƏRƏSİ)
# -------------------------------------------------------------
class KayitIsimModal(Modal, title="Kayıt İsim Formu"):
    def __init__(self, target_id, kayit_turu):
        super().__init__()
        self.target_id = int(target_id)
        self.kayit_turu = kayit_turu

        self.isim_input = TextInput(
            label="Kullanıcının Kayıt Adı ve Soyadı",
            placeholder="Örn: Arda Güler",
            style=discord.TextStyle.short,
            required=True
        )
        self.add_item(self.isim_input)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        target_member = guild.get_member(self.target_id)

        if not target_member:
            return await interaction.response.send_message("❌ Kullanıcı sunucuda bulunamadı!", ephemeral=True)

        girilen_isim = self.isim_input.value

        # Kayıtsız rolünü alırıq
        kayitsiz_rol = guild.get_role(CONFIG["ROLES"]["KAYITSIZ"])
        if kayitsiz_rol in target_member.roles:
            await target_member.remove_roles(kayitsiz_rol)

        verilen_roller = []
        kayitli_uye_rol = guild.get_role(CONFIG["ROLES"]["KAYITLI_UYE"])

        # Seçilən növə görə rollar veriliri
        if self.kayit_turu == "kayitli_uye":
            if kayitli_uye_rol:
                await target_member.add_roles(kayitli_uye_rol)
                verilen_roller.append("Kayıtlı Üye")

        elif self.kayit_turu == "futbolcu":
            prof_rol = guild.get_role(CONFIG["ROLES"]["PROFESYONEL_FUTBOLCU"])
            roles_to_add = [r for r in [kayitli_uye_rol, prof_rol] if r]
            await target_member.add_roles(*roles_to_add)
            verilen_roller.extend(["Kayıtlı Üye", "Profesyonel Futbolcu"])

        elif self.kayit_turu == "teknik_direktor":
            td_rol = guild.get_role(CONFIG["ROLES"]["TEKNIK_DIREKTOR"])
            roles_to_add = [r for r in [kayitli_uye_rol, td_rol] if r]
            await target_member.add_roles(*roles_to_add)
            verilen_roller.extend(["Kayıtlı Üye", "Teknik Direktör (Kulüp Menajeri)"])

        # Adı dəyişdirilir: Ad | €1M
        try:
            await target_member.edit(nick=f"{girilen_isim} | €1M")
        except Exception:
            pass

        # Üstələnməyə son verilir
        claimed_registrations.pop(self.target_id, None)

        embed_result = discord.Embed(
            title="🎉 Kayıt Tamamlandı!",
            color=discord.Color.blue()
        )
        embed_result.add_field(name="👤 Kullanıcı:", value=target_member.mention, inline=False)
        embed_result.add_field(name="🏷️ Yeni İsim:", value=f"`{girilen_isim} | €1M`", inline=False)
        embed_result.add_field(name="🎭 Verilen Rol(ler):", value=f"`{', '.join(verilen_roller)}`", inline=False)
        embed_result.add_field(name="✍️ Kayıt Eden:", value=interaction.user.mention, inline=False)

        await interaction.response.send_message(embed=embed_result)

# -------------------------------------------------------------
# 4. KOMANDA İLƏ QEYDİYYAT: .k @etiket
# -------------------------------------------------------------
@bot.command(name="k")
async def kayit_et(ctx, member: discord.Member = None):
    # Yetkili Kontrolü
    user_roles = [r.id for r in ctx.author.roles]
    if CONFIG["ROLES"]["KAYIT_YETKILISI"] not in user_roles and not ctx.author.guild_permissions.administrator:
        return await ctx.reply("❌ Bu komut sadece Kayıt Yetkilileri içindir.")

    if not member:
        return await ctx.reply("⚠️ Lütfen kayıt edilecek kullanıcıyı etiketleyin! Örn: `.k @kullanıcı`")

    # Üstələnmə kontrolü
    if member.id not in claimed_registrations:
        return await ctx.reply("⚠️ Bu kullanıcının kaydı henüz kimse tarafından üstlenilmedi! Önce **Kayıtı Üstlen** butonuna tıklayın.")

    if claimed_registrations[member.id] != ctx.author.id:
        claimer_id = claimed_registrations[member.id]
        return await ctx.reply(f"❌ Bu kaydı <@{claimer_id}> üstlendi. Sadece o kayıt edebilir!")

    # Rol Seçim Menusü (Select Menu)
    select = Select(
        custom_id=f"select_kayit_tur_{member.id}",
        placeholder="Kayıt Türünü Seçiniz...",
        options=[
            discord.SelectOption(label="Kayıtlı Üye", description="Sadece Kayıtlı Üye rolü verir.", value="kayitli_uye", emoji="👤"),
            discord.SelectOption(label="Futbolcu", description="Profesyonel Futbolcu rolü verir.", value="futbolcu", emoji="⚽"),
            discord.SelectOption(label="Teknik Direktör", description="Kulüp Menajeri rolü verir.", value="teknik_direktor", emoji="👔"),
        ]
    )

    view = View()
    view.add_item(select)

    await ctx.reply(content=f"📋 {member.mention} kullanıcısı için **Kayıt Türünü** seçiniz:", view=view)

# Botu Başlatmaq
import os

bot.run(os.getenv("DISCORD_TOKEN"))
