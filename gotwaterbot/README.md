# Water Fountain Telegram Bot

A Telegram bot that finds nearby water fountains using OpenStreetMap data and provides both map images and Google Maps navigation links.

## Features

- 🚰 Finds water fountains within 1000m of your location
- 🗺️ Generates static map images showing your location and nearby fountains
- 🔗 Provides Google Maps navigation links for each fountain
- 📍 Supports both manual location sharing and location requests
- 🏠 Accepts street addresses for users who don't want to share GPS location (supports US and UK formats)
- ⚡ Fast response times with error handling

## Setup

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd gotwaterbot
pip install -r requirements.txt
```

### 2. Get API Keys

**Telegram Bot Token:**
1. Talk to [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token

**Google Maps API Key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable "Maps Static API" and "Geocoding API"
4. Create an API key with proper restrictions

### 3. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
SEARCH_RADIUS_METERS=1000
```

### 4. Run the Bot

```bash
python bot.py
```

## Deployment on Railway

1. Create a new Railway project
2. Connect your GitHub repository
3. Set environment variables in Railway dashboard:
   - `TELEGRAM_BOT_TOKEN`
   - `GOOGLE_MAPS_API_KEY`
   - `SEARCH_RADIUS_METERS=1000`
4. Deploy!

## Usage

1. Start the bot with `/start`
2. **Option A**: Share your GPS location using the 📍 button
3. **Option B**: Type a street address:
   - US format: `816 S Highland St, Arlington, VA 22204`
   - UK format: `221B Baker Street, London NW1 6XE`
4. Receive a map with nearby water fountains
5. Click on links for navigation directions

## Commands

- `/start` - Start the bot and see welcome message
- `/help` - Show help information
- `/location` - Request location sharing
- `/radius <meters>` - Set custom search radius (100-5000m)

## API Usage

- **OpenStreetMap Overpass API**: Queries for `amenity=drinking_water`
- **Google Static Maps API**: Generates map images with markers
- **Telegram Bot API**: Handles user interactions and location sharing

## Project Structure

```
gotwaterbot/
├── bot.py              # Main bot logic and handlers
├── osm_client.py       # OpenStreetMap API integration
├── map_generator.py    # Map image and link generation
├── geocoding_client.py # Address geocoding functionality
├── config.py          # Configuration management
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variables template
└── README.md          # Project documentation
```

## Contributing

Feel free to submit issues and pull requests to improve the bot!

## License

MIT License
