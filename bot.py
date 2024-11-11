import discord
from discord.ext import commands
import sqlite3
import re
import os
import subprocess
import asyncio
from discord import app_commands

# Veritabanı bağlantısı
conn = sqlite3.connect("owo_data.db")
cursor = conn.cursor()

# Veritabanı tablolarını oluştur
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    discord_id INTEGER PRIMARY KEY,
    kar_zarar INTEGER DEFAULT 0,  -- Kullanıcının kâr/zarar durumu
    message_count INTEGER DEFAULT 0,  -- Kullanıcının mesaj sayısı
    pray_status INTEGER DEFAULT 0,  -- Otomatik pray durumu
    random_status INTEGER DEFAULT 0,  -- Random mesaj durumu
    captcha_status INTEGER DEFAULT 0,  -- CAPTCHA koruma durumu
    captcha_limit INTEGER DEFAULT 10  -- CAPTCHA mesaj limiti
)''')
conn.commit()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

CAPTCHA_LIMIT = 10  # Varsayılan CAPTCHA limit
is_bot_paused = False  # Botun duraklatılma durumu
prefix = "!"  # Başlangıç prefix'i

# GitHub Repo bilgileri
GITHUB_REPO_DIR = "/path/to/your/repo"  # GitHub repo dizininizin yolu
GITHUB_REPO_URL = "https://github.com/username/repository.git"  # GitHub repo URL'si

# Slash komutlarını senkronize et
@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı.')
    await bot.tree.sync()

# Kullanıcı ID'sini kaydetme komutu
@bot.command()
async def kayit(ctx):
    discord_id = ctx.author.id
    cursor.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
    if cursor.fetchone():
        await ctx.send(f"{ctx.author.name}, zaten kayıtlısınız.")
    else:
        cursor.execute("INSERT INTO users (discord_id) VALUES (?)", (discord_id,))
        conn.commit()
        await ctx.send(f"{ctx.author.name}, başarıyla kaydoldunuz!")

# Kâr-Zarar Durumunu Gösterme
@bot.command()
async def kar_zarar(ctx):
    discord_id = ctx.author.id
    cursor.execute("SELECT kar_zarar FROM users WHERE discord_id = ?", (discord_id,))
    result = cursor.fetchone()
    if result:
        await ctx.send(f"{ctx.author.name}, toplam kâr-zarar durumun: {result[0]}")
    else:
        await ctx.send("Öncelikle kaydolmanız gerekiyor.")

# Kâr/Zarar Verilerini OwO Botundan Alma
@bot.event
async def on_message(message):
    owo_bot_id = 408785106942164992 # OwO botunun ID'sini buraya yazın
    
    if message.author.id == owo_bot_id:  # Eğer mesaj OwO botundan geldiyse
        # Mesajın içeriğini kontrol et
        match = re.search(r'(Kazandınız|Zarar ettiniz)\s+(\d+)', message.content)
        
        if match:
            sonuc = match.group(1)  # Kazandınız veya Zarar ettiniz
            miktar = int(match.group(2))  # Kazanılan veya kaybedilen miktar
            
            user_id = message.mentions[0].id  # Mesajdaki kullanıcıyı alıyoruz

            cursor.execute("SELECT * FROM users WHERE discord_id = ?", (user_id,))
            result = cursor.fetchone()

            if result:  # Eğer kullanıcı veritabanında varsa
                if sonuc == "Kazandınız":
                    kar_zarar = result[1] + miktar  # Kazanç
                else:
                    kar_zarar = result[1] - miktar  # Zarar
                cursor.execute("UPDATE users SET kar_zarar = ? WHERE discord_id = ?", (kar_zarar, user_id))
                conn.commit()
                await message.channel.send(f"{message.mentions[0].mention}, kâr-zarar durumu güncellendi: {kar_zarar}")
            else:
                await message.channel.send(f"{message.mentions[0].mention}, öncelikle kaydolmanız gerekiyor.")
    
    if is_bot_paused:
        return

    await bot.process_commands(message)

# Randoms Özelliğini Açma/Kapama
@bot.command()
async def randoms(ctx, status: str):
    if status.lower() == "aç":
        cursor.execute("UPDATE users SET random_status = 1 WHERE discord_id = ?", (ctx.author.id,))
        conn.commit()
        await ctx.send(f"{ctx.author.name}, random mesajlar açıldı.")
    elif status.lower() == "kapa":
        cursor.execute("UPDATE users SET random_status = 0 WHERE discord_id = ?", (ctx.author.id,))
        conn.commit()
        await ctx.send(f"{ctx.author.name}, random mesajlar kapatıldı.")
    else:
        await ctx.send("Geçersiz komut. Lütfen 'aç' veya 'kapa' yazın.")

# CAPTCHA Koruması
@bot.command()
async def captchaprotect(ctx, *args):
    if len(args) == 1 and args[0].lower() == "aç":
        cursor.execute("UPDATE users SET captcha_status = 1 WHERE discord_id = ?", (ctx.author.id,))
        conn.commit()
        await ctx.send(f"{ctx.author.name}, CAPTCHA koruması açıldı.")
    elif len(args) == 1 and args[0].lower() == "kapa":
        cursor.execute("UPDATE users SET captcha_status = 0 WHERE discord_id = ?", (ctx.author.id,))
        conn.commit()
        await ctx.send(f"{ctx.author.name}, CAPTCHA koruması kapatıldı.")
    elif len(args) == 2 and args[0].lower() == "cf_limit":
        limit = int(args[1])
        cursor.execute("UPDATE users SET captcha_limit = ? WHERE discord_id = ?", (limit, ctx.author.id))
        conn.commit()
        await ctx.send(f"{ctx.author.name}, CAPTCHA mesaj limiti {limit} olarak ayarlandı.")
    else:
        await ctx.send("Geçersiz komut.")

# Pray Özelliğini Açma/Kapama
@bot.command()
async def pray(ctx, status: str):
    if status.lower() == "aç":
        cursor.execute("UPDATE users SET pray_status = 1 WHERE discord_id = ?", (ctx.author.id,))
        conn.commit()
        await ctx.send(f"{ctx.author.name}, otomatik pray özelliği açıldı.")
    elif status.lower() == "kapa":
        cursor.execute("UPDATE users SET pray_status = 0 WHERE discord_id = ?", (ctx.author.id,))
        conn.commit()
        await ctx.send(f"{ctx.author.name}, otomatik pray özelliği kapatıldı.")
    else:
        await ctx.send("Geçersiz komut. Lütfen 'aç' veya 'kapa' yazın.")

# Başlangıç Miktarını Gösterme veya Değiştirme
@bot.command()
async def miktar(ctx, amount: int = None):
    if amount is None:
        cursor.execute("SELECT kar_zarar FROM users WHERE discord_id = ?", (ctx.author.id,))
        result = cursor.fetchone()
        if result:
            await ctx.send(f"{ctx.author.name}, başlangıç miktarınız: {result[0]}")
        else:
            await ctx.send("Öncelikle kaydolmanız gerekiyor.")
    else:
        cursor.execute("UPDATE users SET kar_zarar = ? WHERE discord_id = ?", (amount, ctx.author.id))
        conn.commit()
        await ctx.send(f"{ctx.author.name}, başlangıç miktarınız {amount} olarak ayarlandı.")

# Botu Dondurma ve Başlatma
@bot.command()
async def durdur(ctx):
    global is_bot_paused
    is_bot_paused = True
    await ctx.send(f"{ctx.author.name}, bot durduruldu.")

@bot.command()
async def başlat(ctx):
    global is_bot_paused
    is_bot_paused = False
    await ctx.send(f"{ctx.author.name}, bot başlatıldı.")

# Prefix Değiştirme
@bot.command()
async def prefix(ctx, new_prefix: str):
    global prefix
    prefix = new_prefix
    await ctx.send(f"Prefix başarıyla {new_prefix} olarak değiştirildi.")

# Yardım Komutu
@bot.command()
async def yardım(ctx):
    yardım_mesajı = (
        "**!randoms aç/kapa** - Random mesajları açar veya kapatır.\n"
        "**!durdur** - Botu dondurur.\n"
        "**!başlat** - Botu devam ettirir.\n"
        "**!captchaprotect aç/kapa/cf_limit** - CAPTCHA korumasını açar, kapatır veya mesaj limitini ayarlar.\n"
        "**!pray aç/kapa** - Otomatik pray özelliğini açar veya kapatır.\n"
        "**!miktar başlangıç_miktarı** - Başlangıç miktarını gösterir veya değiştirir.\n"
        "**!kar_zarar** - Kar-zarar durumunuzu gösterir.\n"
        "**!yardım** - Mevcut komutların listesini gösterir.\n"
    )
    await ctx.send(yardım_mesajı)

# GitHub Repo Güncelleme Komutu
@bot.command()
async def repo_guncelle(ctx):
    await ctx.send("GitHub reposu güncelleniyor...")
    try:
        # GitHub repo klasörüne git
        subprocess.run(["git", "pull", "origin", "main"], cwd=GITHUB_REPO_DIR, check=True)
        await ctx.send("GitHub reposu başarıyla güncellendi.")
    except subprocess.CalledProcessError:
        await ctx.send("GitHub repo güncellenirken bir hata oluştu.")

# Botu çalıştırma
bot.run("")
