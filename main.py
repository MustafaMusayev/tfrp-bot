import os
import discord
from discord.ext import commands
from discord import app_commands

# Bot Tanımlamaları
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# SİZİN GÖNDERDİĞİNİZ ROL ID'LERİ
KAYIT_YETKILISI_ID = 1553693092975083562
KAYITSIZ_ID = 1553695585423466516
UYE_ID = 1553695726276714537
TEKNIK_DIREKTOR_ID = 1553695258490052638
FUTBOLCU_ID = 1553695512903946303

# TAKIM ID'LERİ
TAKIM_ROLLER = {
    "Real Madrid": 1553694284425855117,
    "Barcelona": 1553693436991905792,
    "Manchester United": 1553693737190817872,
    "Manchester City": 1553694567466012722,
    "Liverpool": 1553694684482633728,
    "Bayern Munich": 1553694682742267904,
    "PSG": 1553694837121876038,
    "Juventus": 1553694837855883324,
    "Galatasaray": 1553695020203380777,
    "Fenerbahçe": 1553695019440017490
}

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'{bot.user} başarıyla aktif oldu!')

# Yetki Kontrol Fonksiyonu
def yetkili_mi(interaction: discord.Interaction) -> bool:
    yetkili_rol = interaction.guild.get_role(KAYIT_YETKILISI_ID)
    return yetkili_rol in interaction.user.roles

# 1. STANDART KAYIT (Futbolcu / Üye)
@bot.tree.command(name="kayit", description="Kullanıcıyı Futbolcu veya Üye olarak kaydeder.")
@app_commands.choices(rol_tipi=[
    app_commands.Choice(name="Futbolcu", value="futbolcu"),
    app_commands.Choice(name="Üye", value="uye")
])
async def kayit(interaction: discord.Interaction, üye: discord.Member, isim: str, rol_tipi: app_commands.Choice[str]):
    if not yetkili_mi(interaction):
        await interaction.response.send_message("❌ Bu komutu kullanmak için **Kayıt Yetkilisi** rolüne sahip olmalısınız!", ephemeral=True)
        return

    kayitsiz_rol = interaction.guild.get_role(KAYITSIZ_ID)
    verilecek_rol = interaction.guild.get_role(FUTBOLCU_ID if rol_tipi.value == "futbolcu" else UYE_ID)

    try:
        # İsim aynen girildiği gibi ayarlanıyor (Hiçbir değer eklenmez)
        await üye.edit(nick=isim)
        
        if kayitsiz_rol in üye.roles:
            await üye.remove_roles(kayitsiz_rol)
            
        await üye.add_roles(verilecek_rol)
        
        await interaction.response.send_message(f"✅ {üye.mention} başarıyla **{rol_tipi.name}** olarak kaydoldu!\n👤 **Yeni İsmi:** `{isim}`")
    except Exception as e:
        await interaction.response.send_message(f"❌ Kayıt yapılırken bir hata oluştu: {e}", ephemeral=True)

# 2. TEKNİK DİREKTÖR KAYDI (İsim + Takım Rolü)
@bot.tree.command(name="td_kayit", description="Kullanıcıyı Teknik Direktör olarak kaydeder ve takım rolü verir.")
@app_commands.choices(takim=[
    app_commands.Choice(name="Real Madrid", value="Real Madrid"),
    app_commands.Choice(name="Barcelona", value="Barcelona"),
    app_commands.Choice(name="Manchester United", value="Manchester United"),
    app_commands.Choice(name="Manchester City", value="Manchester City"),
    app_commands.Choice(name="Liverpool", value="Liverpool"),
    app_commands.Choice(name="Bayern Munich", value="Bayern Munich"),
    app_commands.Choice(name="PSG", value="PSG"),
    app_commands.Choice(name="Juventus", value="Juventus"),
    app_commands.Choice(name="Galatasaray", value="Galatasaray"),
    app_commands.Choice(name="Fenerbahçe", value="Fenerbahçe")
])
async def td_kayit(interaction: discord.Interaction, üye: discord.Member, isim: str, takim: app_commands.Choice[str]):
    if not yetkili_mi(interaction):
        await interaction.response.send_message("❌ Bu komutu kullanmak için **Kayıt Yetkilisi** rolüne sahip olmalısınız!", ephemeral=True)
        return

    kayitsiz_rol = interaction.guild.get_role(KAYITSIZ_ID)
    td_rol = interaction.guild.get_role(TEKNIK_DIREKTOR_ID)
    
    takim_rol_id = TAKIM_ROLLER.get(takim.value)
    takim_rol = interaction.guild.get_role(takim_rol_id)

    try:
        await üye.edit(nick=isim)
        
        if kayitsiz_rol in üye.roles:
            await üye.remove_roles(kayitsiz_rol)
            
        # Hem TD Rolünü hem de Takım Rolünü verir
        await üye.add_roles(td_rol, takim_rol)
        
        await interaction.response.send_message(
            f"👔 {üye.mention} başarıyla **{takim.name}** Teknik Direktörü olarak kaydedildi!\n"
            f"👤 **Yeni İsmi:** `{isim}`\n"
            f"🏆 **Verilen Takım:** {takim_rol.mention}"
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Kayıt yapılırken hata oluştu: {e}", ephemeral=True)

bot.run(os.getenv("DISCORD_TOKEN"))
