from keep_alive import keep_alive

import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

TOKEN = os.environ["DISCORD_TOKEN"]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix="m",
    intents=intents,
    heartbeat_timeout=60.0
)

ytdl_format_options = {
    'format': 'bestaudio',
    'noplaylist': True,
    'quiet': True,
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

queue = []
current_song = None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

async def play_next(ctx):
    global current_song

    if queue:
        data = queue.pop(0)
        current_song = data

        source = await discord.FFmpegOpusAudio.from_probe(
            data['url'], **ffmpeg_options
        )

        ctx.voice_client.play(
            source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx), bot.loop
            )
        )

        embed = discord.Embed(
            title="กำลังเล่นเพลงนี้อยู่นะ",
            description=data['title'],
            color=0x370a05
        )
        #embed.set_thumbnail(url=data['thumbnail'])
        await ctx.send(embed=embed)

    else:
        current_song = None

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("คุณต้องอยู่ใน Voice Channel ก่อน")

"""
@bot.command()
async def play(ctx, url):
    if not ctx.voice_client:
        await ctx.invoke(join)

    loop = asyncio.get_event_loop()

    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
    audio_url = data['url']

    source = await discord.FFmpegOpusAudio.from_probe(
        audio_url,
        **ffmpeg_options
    )

    ctx.voice_client.play(source)
    await ctx.send("ก็ได้ๆจะเอามาเปิดให้ก็ได้นะ")
"""

@bot.command()
async def play(ctx, *, query):
    global current_song

    if not ctx.voice_client:
        await ctx.invoke(join)

    loop = asyncio.get_event_loop()

    # ถ้าเป็นลิงก์ ให้ใช้ตรง ๆ
    if query.startswith("http"):
        search = query
    else:
        # ถ้าไม่ใช่ลิงก์ ให้ค้นหาใน YouTube
        search = f"ytsearch:{query}"

    data = await loop.run_in_executor(
        None,
        lambda: ytdl.extract_info(search, download=False)
    )

    # ถ้าเป็นการค้นหา จะได้ results เป็น list
    if 'entries' in data:
        data = data['entries'][0]

    song = {
        'title': data.get('title', 'Unknown'),
        'url': data['url']
    }

    queue.append(song)

    await ctx.send(
        f"เห็นว่าเธอขอให้ฉันเปิดหรอกนะ! ฉันเลยเอา {song['title']} มาใส่คิวให้ ฮึ\n"
        f"ตอนนี้มี {len(queue)} เพลงในคิวแล้วนะ"
    )

    # ถ้าไม่มีเพลงกำลังเล่น ให้เริ่มเล่นเลย
    if not ctx.voice_client.is_playing() and not current_song:
        await play_next(ctx)

@bot.command()
async def search(ctx, *, query):
    global current_song

    if not ctx.voice_client:
        await ctx.invoke(join)

    loop = asyncio.get_event_loop()
    search_query = f"ytsearch5:{query}"

    data = await loop.run_in_executor(
        None,
        lambda: ytdl.extract_info(search_query, download=False)
    )

    results = data['entries']

    desc = "\n".join(
        [f"**{i+1}.** {entry['title']}"
         for i, entry in enumerate(results)]
    )

    embed = discord.Embed(
        title="ดูสิว่าชั้นเจออะไรมา",
        description=desc,
        color=0x370a05
    )

    embed.set_footer(text="พิมพ์เลข 1-5 เพื่อเลือกเพลง (30 วิ)")

    await ctx.send(embed=embed)

    def check(m):
        return (
            m.author == ctx.author and
            m.channel == ctx.channel and
            m.content.isdigit() and
            1 <= int(m.content) <= 5
        )

    try:
        reply = await bot.wait_for("message", timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("หมดเวลาแล้ว! เลือกอะไรง่ายๆแค่นี้ก็ทำไม่ได้")
        return

    selected = int(reply.content) - 1
    chosen = results[selected]

    song = {
        'title': chosen.get('title', 'Unknown'),
        'url': chosen['url']
    }

    queue.append(song)

    await ctx.send(
        f"เลือกได้ซักทีนะ หืม **{song['title']}** สินะ\n"
        f"ใส่คิวให้แล้ว ตอนนี้มี {len(queue)} เพลงในคิว"
    )

    if not ctx.voice_client.is_playing() and not current_song:
        await play_next(ctx)


@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("ข้ามอันนี้ไปละน้า")

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("อะๆ หยุดไว้ก่อนก็ได้อะ")

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("มาๆ มาฟังกันต่อ")

@bot.command()
async def list(ctx):
    if queue:
        desc = "\n".join(
            [f"{i+1}. {song['title']}" for i, song in enumerate(queue)]
        )
    else:
        desc = "ไม่มีเพลงในคิว"

    embed = discord.Embed(
        title="ตอนนี้ในคิวมีตามนี้ล่ะ",
        description=desc,
        color=0x370a05
    )
    await ctx.send(embed=embed)

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


bot.run(TOKEN, reconnect=True)
