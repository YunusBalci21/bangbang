import os
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging
import urllib.parse
import re
from collections import deque
import asyncio
from flask import Flask
from threading import Thread

# Description of the bot
description = '''A bot for playing music from Spotify, YouTube, and SoundCloud with queue support.'''

# Setup logging
logging.basicConfig(level=logging.INFO)

# Define Discord intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize bot with command prefix and intents
bot = commands.Bot(command_prefix='!',
                   description=description,
                   intents=intents)

# Queue to manage music tracks
song_queue = deque()

# Flask app to keep Replit instance awake
app = Flask('')


@app.route('/')
def home():
    return "Bot is running"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()


# Event listener for when the bot is ready
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


# Join voice channel command
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
    else:
        await ctx.send("You need to be in a voice channel to use this command."
                       )


# Play YouTube links by streaming
async def play_youtube(url, voice_client, ctx):
    ydl_opts = {
        'format': 'bestaudio',
        'noplaylist': 'True',
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)  # Get streaming URL
            audio_url = info['url']
            source = discord.FFmpegPCMAudio(
                audio_url,
                executable="ffmpeg",
                before_options=
                "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn")
            voice_client.play(source,
                              after=lambda e: asyncio.run_coroutine_threadsafe(
                                  on_audio_end(e, ctx), ctx.bot.loop))
            await ctx.send(f"Now playing: {info['title']}")
    except Exception as e:
        await ctx.send(f"Error playing YouTube URL: {str(e)}")


# Callback function to play next song in queue
async def on_audio_end(error, ctx):
    if error:
        print(f"Error: {error}")
    if song_queue:
        next_song = song_queue.popleft()
        await play(next_song['ctx'], next_song['url'])


# Play SoundCloud links by streaming
async def play_soundcloud(url, voice_client, ctx):
    ydl_opts = {
        'format': 'bestaudio',
        'noplaylist': 'True',
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)  # Get streaming URL
            audio_url = info['url']
            source = discord.FFmpegPCMAudio(
                audio_url,
                executable="ffmpeg",
                before_options=
                "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn")
            voice_client.play(source,
                              after=lambda e: asyncio.run_coroutine_threadsafe(
                                  on_audio_end(e, ctx), ctx.bot.loop))
            await ctx.send(f"Now playing: {info['title']}")
    except Exception as e:
        await ctx.send(f"Error playing SoundCloud URL: {str(e)}")


# Play Spotify tracks by searching on YouTube
async def play_spotify(url, voice_client, ctx):
    try:
        sp = spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id='78f1e87c28124a6b8bccd9bb7842571e',
                client_secret='c1806f10a1c24a98921242d0926e57a7'))
        track = sp.track(url)
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        search_query = f"{track_name} {artist_name} official audio"
        query_string = urllib.parse.urlencode({'search_query': search_query})
        html_content = requests.get(
            f'https://www.youtube.com/results?{query_string}').text
        search_results = re.findall(r'/watch\?v=(.{11})', html_content)
        if search_results:
            video_url = f'https://www.youtube.com/watch?v={search_results[0]}'
            await play_youtube(video_url, voice_client, ctx)
        else:
            await ctx.send(
                "No results found on YouTube for the given Spotify track.")
    except Exception as e:
        await ctx.send(f"Error retrieving Spotify track: {str(e)}")


# Main play command with Spotify, YouTube, and SoundCloud support
@bot.command()
async def play(ctx, url):
    voice_client = ctx.voice_client
    if not voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
            voice_client = ctx.voice_client
        else:
            await ctx.send(
                "You need to be in a voice channel to use this command.")
            return

    if voice_client.is_playing() or voice_client.is_paused():
        # Add song to queue if something is currently playing
        song_queue.append({'ctx': ctx, 'url': url})
        await ctx.send(
            f"Track added to queue. Position in queue: {len(song_queue)}")
    else:
        # Play the song immediately if nothing is playing
        if "youtube.com" in url or "youtu.be" in url:
            await play_youtube(url, voice_client, ctx)
        elif "spotify" in url:
            await play_spotify(url, voice_client, ctx)
        elif "soundcloud.com" in url:
            await play_soundcloud(url, voice_client, ctx)
        else:
            await ctx.send(
                "Unsupported link. Please use a YouTube, Spotify, or SoundCloud link."
            )


# Skip the currently playing track
@bot.command()
async def skip(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.send("Skipped the current track.")
    else:
        await ctx.send("No track is currently playing.")


# Leave voice channel command
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


# Run the bot
keep_alive()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError(
        "No DISCORD_TOKEN found. Please set it as an environment variable.")

bot.run(TOKEN)
