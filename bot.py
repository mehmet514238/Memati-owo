import discord
from discord.ext import commands
import sqlite3
import os
from dotenv import load_dotenv
import subprocess

# .env dosyasındaki bot token'ını yükleyin
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Veritabanı bağlantısını başlatın
conn = sqlite3.connect("owo_data.db")
cursor = conn.cursor()

# Veritabanında 'users' tablosu oluşturun (eğer yoksa)
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    discord_id INTEGER PRIMARY KEY,
    kar_zarar INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    pray_status INTEGER DEFAULT 0,
    random_status INTEGER DEFAULT 0,
    captcha_status INTEGER DEFAULT 0,
    captcha_limit INTEGER DEFAULT 10
)''')
conn.commit()

# Bot için gerekli ayarlar
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Komutlar burada devam eder...
@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı.')

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

@bot.command()
async def kar_zarar(ctx):
    discord_id = ctx.author.id
    cursor.execute("SELECT kar_zarar FROM users WHERE discord_id = ?", (discord_id,))
    result = cursor.fetchone()
    if result:
        await ctx.send(f"{ctx.author.name}, toplam kâr-zarar durumun: {result[0]}")
    else:
        await ctx.send("Öncelikle kaydolmanız gerekiyor.")

# OwO botundan kar-zarar verilerini alma
@bot.event
async def on_message(message):
    owo_bot_id = 408785106942164992  # OwO bot ID'si
    
    if message.author.id == owo_bot_id:
        match = re.search(r'(Kazandınız|Zarar ettiniz)\s+(\d+)', message.content)
        
        if match:
            sonuc = match.group(1)
            miktar = int(match.group(2))
            user_id = message.mentions[0].id

            cursor.execute("SELECT * FROM users WHERE discord_id = ?", (user_id,))
            result = cursor.fetchone()

            if result:
                kar_zarar = result[1] + miktar if sonuc == "Kazandınız" else result[1] - miktar
                cursor.execute("UPDATE users SET kar_zarar = ? WHERE discord_id = ?", (kar_zarar, user_id))
                conn.commit()
                await message.channel.send(f"{message.mentions[0].mention}, kâr-zarar durumu güncellendi: {kar_zarar}")
            else:
                await message.channel.send(f"{message.mentions[0].mention}, öncelikle kaydolmanız gerekiyor.")
    
    await bot.process_commands(message)

@bot.command()
async def randoms(ctx, status: str):
    if status.lower() in ["aç", "kapa"]:
        new_status = 1 if status.lower() == "aç" else 0
        cursor.execute("UPDATE users SET random_status = ? WHERE discord_id = ?", (new_status, ctx.author.id))
        conn.commit()
        await ctx.send(f"{ctx.author.name}, random mesajlar {'açıldı' if new_status else 'kapandı'}.")
    else:
        await ctx.send("Geçersiz komut. Lütfen 'aç' veya 'kapa' yazın.")

@bot.command()
async def captchaprotect(ctx, *args):
    if len(args) == 1:
        status = 1 if args[0].lower() == "aç" else 0
        cursor.execute("UPDATE users SET captcha_status = ? WHERE discord_id = ?", (status, ctx.author.id))
        conn.commit()
        await ctx.send(f"{ctx.author.name}, CAPTCHA koruması {'açıldı' if status else 'kapandı'}.")
    elif len(args) == 2 and args[0].lower() == "cf_limit":
        try:
            limit = int(args[1])
            cursor.execute("UPDATE users SET captcha_limit = ? WHERE discord_id = ?", (limit, ctx.author.id))
            conn.commit()
            await ctx.send(f"{ctx.author.name}, CAPTCHA mesaj limiti {limit} olarak ayarlandı.")
        except ValueError:
            await ctx.send("Lütfen geçerli bir sayı girin.")
    else:
        await ctx.send("Geçersiz komut.")

@bot.command()
async def repo_guncelle(ctx):
    await ctx.send("GitHub reposu güncelleniyor...")
    try:
        subprocess.run(["git", "pull", "origin", "main"], check=True)
        await ctx.send("GitHub reposu başarıyla güncellendi.")
    except subprocess.CalledProcessError:
        await ctx.send("GitHub repo güncellenirken bir hata oluştu.")

bot.run(TOKEN)
