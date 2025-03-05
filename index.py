# Turku Weather Discord Bot - Python Version
import os
import sys
import datetime
import asyncio
import requests
import discord
from discord import app_commands
from discord.ui import View, Button

# Debug environment variables
print("DEBUG: Environment variables check")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Files in current directory: {os.listdir('.')}")
print(f"DISCORD_TOKEN exists: {'Yes' if 'DISCORD_TOKEN' in os.environ else 'No'}")
print(f"CHANNEL_ID exists: {'Yes' if 'CHANNEL_ID' in os.environ else 'No'}")

# Try to load from dotenv if available
try:
    from dotenv import load_dotenv
    print("DEBUG: dotenv module found, attempting to load .env file")
    load_dotenv()
    print("DEBUG: .env file processed (if it exists)")
except ImportError:
    print("DEBUG: dotenv module not found, skipping .env loading")

# Get environment variables with fallbacks and immediate error checking
TOKEN = os.environ.get('DISCORD_TOKEN')
print(f"DEBUG: TOKEN after environment check: {'Found (not showing value)' if TOKEN else 'Not found'}")

if not TOKEN:
    # Try direct access as a fallback
    print("DEBUG: Attempting to read TOKEN directly from .env file")
    try:
        if os.path.exists('.env'):
            with open('.env', 'r') as env_file:
                for line in env_file:
                    if line.startswith('DISCORD_TOKEN='):
                        TOKEN = line.split('=', 1)[1].strip()
                        print("DEBUG: Found TOKEN in .env file")
                        break
    except Exception as e:
        print(f"DEBUG: Error reading .env file: {e}")

# Final check for TOKEN
if not TOKEN:
    print("ERROR: DISCORD_TOKEN is missing. Please set it in Railway variables or .env file.")
    # Don't exit immediately to ensure logs are visible
    # Continue with empty token to produce a clear error message

# Read CHANNEL_ID safely
try:
    CHANNEL_ID = int(os.environ.get('CHANNEL_ID', 0)) if os.environ.get('CHANNEL_ID') else None
    print(f"DEBUG: CHANNEL_ID parsed: {'Found' if CHANNEL_ID else 'Not found'}")
except ValueError:
    print(f"DEBUG: Error parsing CHANNEL_ID - not a valid integer: {os.environ.get('CHANNEL_ID')}")
    CHANNEL_ID = None

# Turku coordinates
CITY = 'Turku'
LAT = 60.45
LON = 22.27

# Initialize Discord client
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Weather code mapping in Finnish
WEATHER_DESCRIPTIONS = {
    0: 'Selkeää',
    1: 'Enimmäkseen selkeää',
    2: 'Osittain pilvistä',
    3: 'Pilvistä',
    45: 'Sumua',
    48: 'Huurresumua',
    51: 'Kevyttä tihkua',
    53: 'Kohtalaista tihkua',
    55: 'Tiheää tihkua',
    56: 'Kevyttä jäätävää tihkua',
    57: 'Tiheää jäätävää tihkua',
    61: 'Kevyttä sadetta',
    63: 'Kohtalaista sadetta',
    65: 'Rankkaa sadetta',
    66: 'Kevyttä jäätävää sadetta',
    67: 'Rankkaa jäätävää sadetta',
    71: 'Kevyttä lumisadetta',
    73: 'Kohtalaista lumisadetta',
    75: 'Rankkaa lumisadetta',
    77: 'Lumijyväsiä',
    80: 'Kevyitä sadekuuroja',
    81: 'Kohtalaisia sadekuuroja',
    82: 'Voimakkaita sadekuuroja',
    85: 'Kevyitä lumikuuroja',
    86: 'Voimakkaita lumikuuroja',
    95: 'Ukkosmyrsky',
    96: 'Ukkosmyrsky ja kevyittä rakeita',
    99: 'Ukkosmyrsky ja voimakkaita rakeita'
}

# Function to fetch weather data
def get_weather(day_offset=0):
    try:
        # Calculate the date for forecast (today + day_offset)
        target_date = datetime.datetime.now() + datetime.timedelta(days=day_offset)
        
        # Request both current and hourly data for multiple days
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m&hourly=temperature_2m,precipitation_probability,weather_code&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code&timezone=Europe%2FHelsinki&forecast_days=7"
        response = requests.get(url)
        response.raise_for_status()
        return response.json(), day_offset
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None, day_offset

# Function to get color based on temperature
def get_color_by_temp(temp):
    if temp < 0:
        return 0x9EC9FF  # Cold - light blue
    elif temp < 10:
        return 0x33A1FD  # Cool - blue
    elif temp < 20:
        return 0x66BB6A  # Mild - green
    elif temp < 30:
        return 0xFFA726  # Warm - orange
    else:
        return 0xFF5722  # Hot - red

# Function to create forecast graph for a specific day
def create_forecast_graph(weather_data, day_offset=0):
    # Get hourly data
    hourly = weather_data['hourly']
    timestamps = hourly['time']
    temps = hourly['temperature_2m']
    precip_probs = hourly['precipitation_probability'] if 'precipitation_probability' in hourly else [0] * len(timestamps)
    weather_codes = hourly['weather_code']
    
    # Calculate the start and end indices for the target day
    today = datetime.datetime.now().date()
    target_date = (today + datetime.timedelta(days=day_offset)).strftime('%Y-%m-%d')
    
    # Find indices for the target day
    start_idx = None
    end_idx = None
    
    for i, timestamp in enumerate(timestamps):
        if timestamp.startswith(target_date):
            if start_idx is None:
                start_idx = i
            end_idx = i
    
    if start_idx is None or end_idx is None:
        return "```\nEnnustetietoja ei saatavilla tälle päivälle\n```"
    
    # Get data for the target day
    day_timestamps = timestamps[start_idx:end_idx+1]
    day_temps = temps[start_idx:end_idx+1]
    day_precip_probs = precip_probs[start_idx:end_idx+1] if start_idx < len(precip_probs) else [0] * len(day_timestamps)
    day_weather_codes = weather_codes[start_idx:end_idx+1]
    
    # Weather symbols for different conditions
    weather_symbols = {
        0: "☀️",  # Clear
        1: "🌤️",  # Mainly clear
        2: "⛅",  # Partly cloudy
        3: "☁️",  # Overcast
        45: "🌫️", # Fog
        48: "🌫️", # Rime fog
        51: "🌧️", # Light drizzle
        53: "🌧️", # Moderate drizzle
        55: "🌧️", # Dense drizzle
        56: "🌧️", # Light freezing drizzle
        57: "🌧️", # Dense freezing drizzle
        61: "🌧️", # Slight rain
        63: "🌧️", # Moderate rain
        65: "🌧️", # Heavy rain
        66: "🌧️", # Light freezing rain
        67: "🌧️", # Heavy freezing rain
        71: "❄️",  # Light snow
        73: "❄️",  # Moderate snow
        75: "❄️",  # Heavy snow
        77: "❄️",  # Snow grains
        80: "🌦️", # Light rain showers
        81: "🌦️", # Moderate rain showers
        82: "🌦️", # Violent rain showers
        85: "🌨️", # Light snow showers
        86: "🌨️", # Heavy snow showers
        95: "⛈️", # Thunderstorm
        96: "⛈️", # Thunderstorm with hail
        99: "⛈️", # Thunderstorm with heavy hail
    }
    
    # Create forecast text
    forecast = "```\nSääennuste tunneittain:\n"
    forecast += "Aika  | Lämpötila | Sade% | Sää\n"
    forecast += "------+-----------+-------+-----\n"
    
    # Determine step size based on number of entries
    step = 2 if len(day_timestamps) > 12 else 1
    
    for i in range(0, len(day_timestamps), step):
        if i < len(day_timestamps):
            hour = datetime.datetime.fromisoformat(day_timestamps[i]).hour
            temp = day_temps[i]
            precip = day_precip_probs[i] if i < len(day_precip_probs) else 0
            weather_symbol = weather_symbols.get(day_weather_codes[i], "?")
            
            forecast += f"{hour:02}:00 | {temp:5.1f}°C  | {precip:3.0f}%  | {weather_symbol}\n"
    
    forecast += "```"
    return forecast

# Function to create weather embed in Finnish
def create_weather_embed(weather_data, day_offset=0):
    current = weather_data['current']
    
    # Get date for the requested day offset
    target_date = datetime.datetime.now() + datetime.timedelta(days=day_offset)
    
    # Get weather code and description
    if day_offset == 0:
        # Current day: use current weather data
        weather_code = current['weather_code']
        temperature = current['temperature_2m']
        apparent_temp = current['apparent_temperature']
        humidity = current['relative_humidity_2m']
        wind_speed = current['wind_speed_10m']
        wind_gusts = current['wind_gusts_10m']
        pressure = current['pressure_msl']
        cloud_cover = current['cloud_cover']
        precipitation = current['precipitation']
    else:
        # Future/past day: use daily data
        daily = weather_data['daily']
        daily_date_index = None
        
        # Find the index for our target date
        for i, date_str in enumerate(daily['time']):
            if date_str == target_date.strftime('%Y-%m-%d'):
                daily_date_index = i
                break
        
        if daily_date_index is not None:
            weather_code = daily['weather_code'][daily_date_index]
            temperature = (daily['temperature_2m_max'][daily_date_index] + 
                           daily['temperature_2m_min'][daily_date_index]) / 2  # average
            apparent_temp = temperature  # No feels-like for future days
            humidity = None  # Not available for future
            wind_speed = None  # Not available for future
            wind_gusts = None  # Not available for future
            pressure = None  # Not available for future
            cloud_cover = None  # Not available for future
            precipitation = daily['precipitation_sum'][daily_date_index]
        else:
            # Fallback if we can't find the day
            weather_code = 0
            temperature = 0
            apparent_temp = 0
            humidity = None
            wind_speed = None
            wind_gusts = None
            pressure = None
            cloud_cover = None
            precipitation = 0
    
    weather_description = WEATHER_DESCRIPTIONS.get(weather_code, 'Tuntematon sää')
    
    # Format date in Finnish
    days_of_week = ['Maanantai', 'Tiistai', 'Keskiviikko', 'Torstai', 'Perjantai', 'Lauantai', 'Sunnuntai']
    months = ['tammikuuta', 'helmikuuta', 'maaliskuuta', 'huhtikuuta', 'toukokuuta', 'kesäkuuta', 
              'heinäkuuta', 'elokuuta', 'syyskuuta', 'lokakuuta', 'marraskuuta', 'joulukuuta']
    
    weekday = days_of_week[target_date.weekday()]
    month = months[target_date.month - 1]
    formatted_date = f"{weekday}, {target_date.day}. {month} {target_date.year}"
    
    # Set title with indicator if not current day
    if day_offset == 0:
        title = f"Sää Turussa - {formatted_date} (Tänään)"
    elif day_offset < 0:
        title = f"Sää Turussa - {formatted_date} ({abs(day_offset)} päivää sitten)"
    else:
        title = f"Sää Turussa - {formatted_date} ({day_offset} päivää eteenpäin)"
    
    embed = discord.Embed(
        title=title,
        description=weather_description,
        color=get_color_by_temp(temperature)
    )
    
    # Add current weather fields (only for current day or with available data)
    embed.add_field(name="Lämpötila", value=f"{temperature:.1f}°C", inline=True)
    
    if apparent_temp is not None:
        embed.add_field(name="Tuntuu kuin", value=f"{apparent_temp:.1f}°C", inline=True)
    
    if humidity is not None:
        embed.add_field(name="Kosteus", value=f"{humidity}%", inline=True)
        
    if wind_speed is not None:
        embed.add_field(name="Tuuli", value=f"{wind_speed} km/h", inline=True)
        
    if wind_gusts is not None:
        embed.add_field(name="Tuulenpuuskat", value=f"{wind_gusts} km/h", inline=True)
        
    if pressure is not None:
        embed.add_field(name="Ilmanpaine", value=f"{pressure} hPa", inline=True)
        
    if cloud_cover is not None:
        embed.add_field(name="Pilvisyys", value=f"{cloud_cover}%", inline=True)
    
    if precipitation is not None:
        if day_offset == 0:
            embed.add_field(name="Sademäärä", value=f"{precipitation} mm", inline=True)
        else:
            embed.add_field(name="Sademäärä (päivä)", value=f"{precipitation} mm", inline=True)
    
    # Add the forecast graph
    if day_offset >= -1 and day_offset <= 6:  # Only for reasonable forecast range
        forecast_graph = create_forecast_graph(weather_data, day_offset)
        embed.add_field(name="Päivän ennuste", value=forecast_graph, inline=False)
    
    embed.set_footer(text="Tiedot: Open-Meteo API")
    embed.timestamp = datetime.datetime.utcnow()
    
    return embed

# Navigation buttons for forecast days
class WeatherNavigationView(View):
    def __init__(self, weather_data, day_offset=0):
        super().__init__(timeout=120)  # 2 minute timeout
        self.weather_data = weather_data
        self.day_offset = day_offset
    
    @discord.ui.button(label="« Edellinen päivä", style=discord.ButtonStyle.secondary)
    async def previous_day(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.day_offset <= -3:  # Don't go further than 3 days in the past
            await interaction.response.send_message("Historiatietoja ei ole saatavilla pidemmälle taaksepäin.", ephemeral=True)
            return
            
        new_offset = self.day_offset - 1
        new_data, new_offset = get_weather(new_offset)
        embed = create_weather_embed(new_data, new_offset)
        view = WeatherNavigationView(new_data, new_offset)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Nykyinen päivä", style=discord.ButtonStyle.primary)
    async def current_day(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_data, new_offset = get_weather(0)  # Reset to today
        embed = create_weather_embed(new_data, 0)
        view = WeatherNavigationView(new_data, 0)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Seuraava päivä »", style=discord.ButtonStyle.secondary)
    async def next_day(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.day_offset >= 6:  # Don't go further than 6 days in the future
            await interaction.response.send_message("Ennusteita ei ole saatavilla pidemmälle tulevaisuuteen.", ephemeral=True)
            return
            
        new_offset = self.day_offset + 1
        new_data, new_offset = get_weather(new_offset)
        embed = create_weather_embed(new_data, new_offset)
        view = WeatherNavigationView(new_data, new_offset)
        await interaction.response.edit_message(embed=embed, view=view)

# Define slash command (in Finnish)
@tree.command(name="sää", description="Hae Turun tämänhetkinen sää")
async def weather_command(interaction):
    await interaction.response.defer()
    weather_data, day_offset = get_weather(0)
    
    if not weather_data:
        await interaction.followup.send("Valitettavasti en voinut hakea säätietoja Turulle.")
        return
    
    embed = create_weather_embed(weather_data, day_offset)
    view = WeatherNavigationView(weather_data, day_offset)
    await interaction.followup.send(embed=embed, view=view)

# Function to send daily weather update
async def send_weather_update():
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print(f"Kanavaa ID:llä {CHANNEL_ID} ei löydy!")
        return
    
    weather_data, day_offset = get_weather(0)
    if not weather_data:
        await channel.send("Valitettavasti en voinut hakea tämän päivän säätietoja Turulle.")
        return
    
    embed = create_weather_embed(weather_data, day_offset)
    view = WeatherNavigationView(weather_data, day_offset)
    await channel.send(embed=embed, view=view)

# Function to schedule the daily weather update at 8:00 AM
async def schedule_daily_update():
    while True:
        now = datetime.datetime.now()
        target_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
        
        # If it's already past 8 AM, schedule for the next day
        if now >= target_time:
            target_time = target_time + datetime.timedelta(days=1)
        
        # Calculate seconds until the target time
        seconds_until_target = (target_time - now).total_seconds()
        print(f"Seuraava sääpäivitys ajastettu {seconds_until_target/60:.1f} minuutin päähän")
        
        await asyncio.sleep(seconds_until_target)
        
        # Send the weather update
        await send_weather_update()
        
        # Sleep a bit to avoid sending twice if execution takes time
        await asyncio.sleep(60)

@client.event
async def on_ready():
    print(f'Kirjauduttu sisään käyttäjänä {client.user.name}')
    print('Aloitetaan päivittäisen sääpäivityksen ajastus kello 8:00')
    
    # Register slash commands
    await tree.sync()
    print('Slash-komennot rekisteröity onnistuneesti')
    
    # Start the daily update scheduler
    if CHANNEL_ID:
        asyncio.create_task(schedule_daily_update())
    else:
        print("VAROITUS: CHANNEL_ID puuttuu, automaattisia päivityksiä ei lähetetä")

# Print final debug info before running
print(f"DEBUG: Final TOKEN check: {'Present' if TOKEN else 'Missing'}")
print(f"DEBUG: Final CHANNEL_ID check: {CHANNEL_ID}")

# Run the bot
if TOKEN:
    print("DEBUG: Starting Discord client")
    try:
        client.run(TOKEN)
    except Exception as e:
        print(f"ERROR: Failed to start Discord client: {e}")
else:
    print("CRITICAL ERROR: Cannot start bot without DISCORD_TOKEN. Please set it in Railway variables.")
    # Add an artificial delay to ensure logs are visible
    import time
    time.sleep(30)
