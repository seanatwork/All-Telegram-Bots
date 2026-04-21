import logging
import asyncio
import re
from telegram import Update, Location
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from gotwater_config import Config
from osm_client import OSMClient
from map_generator import MapGenerator
from geocoding_client import GeocodingClient
import io

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class WaterFountainBot:
    def __init__(self):
        self.osm_client = OSMClient()
        self.map_generator = MapGenerator()
        self.geocoding_client = GeocodingClient()
        
        # Pattern to detect addresses (supports US and UK formats)
        self.address_pattern = re.compile(
            r'^\d+[A-Za-z]*\s+.*\s+(?:St|Ave|Avenue|Street|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Place|Pl|Close|Cl|Gardens|Gdns|Square|Sq|Terrace|Tce|Crescent|Cres|Hill|Circus|Park|Pk|Mews|Row|Wynd|Vale|End|Green|Grove|Gr|Manor|Wood|Woods|Field|Fields|Meadow|Meadows|Bank|Banks|Side|Approach|Gate|Gates|Walk|Passage|Path|Alley|Broadway|Brwy|Causeway|Cw|Chase|Ch|Circle|Cir|Common|Cross|Xing|Crossing|Crest|Cr|Dale|Div|Estate|Es|Expressway|Expy|Extension|Ext|Field|Fld|Ford|Frd|Forest|Frst|Forge|Frg|Forks|Frks|Fort|Ft|Freeway|Fwy|Garden|Gdn|Gardens|Gdns|Gateway|Gatewy|Glens|Gln|Green|Grn|Grove|Grv|Harbor|Hbr|Haven|Hvn|Heights|Hts|Highway|Hwy|Hollow|Hol|Inlet|Inlt|Island|Is|Islands|Iss|Junction|Jct|Key|Ky|Knob|Knb|Lake|Lk|Lakes|Lks|Land|Lnd|Landing|Lndg|Lane|Ln|Light|Lgt|Lights|Lgts|Loaf|Lf|Lock|Lcks|Lodge|Ldg|Loop|Lp|Mall|Manor|Mnr|Meadows|Mdw|Mill|Ml|Mills|Mls|Mission|Msn|Motorway|Mtwy|Mount|Mnt|Mountain|Mtn|Mountains|Mtns|Neck|Nck|Orchard|Orch|Oval|Ovl|Overpass|Opas|Park|Pk|Parkway|Pkwy|Passage|Psge|Path|Pike|Pines|Pnes|Place|Pl|Plain|Pln|Plains|Plns|Plaza|Plz|Point|Pt|Points|Pts|Port|Prt|Ports|Prts|Prairie|Prr|Radial|Rad|Ramp|Rmp|Ranch|Rnch|Rapid|Rpd|Rapids|Rpds|Rest|Rst|Ridge|Rdg|Ridges|Rdgs|River|Rvr|Road|Rd|Roads|Rds|Route|Rte|Row|Rue|Run|Shoal|Shls|Shoals|Shls|Shore|Shr|Shores|Shrs|Skyway|Skwy|Spring|Spg|Springs|Spgs|Spur|Spurs|Sqr|Squares|Sqrs|Station|Stn|Stravenue|Straven|Stream|Strm|Street|St|Streets|Sts|Summit|Smt|Terrace|Ter|Throughway|Trwy|Track|Trk|Trafficway|Trfy|Trail|Trl|Trailer|Trlr|Tunnel|Tunl|Turnpike|Tpke|Underpass|Upas|Union|Un|Valleys|Vlys|Village|Vlg|Villages|Vlgs|Ville|Vl|Vista|Vis|Walk|Walks|Wall|Walls|Way|Ways|Well|Wl|Wells|Wls)\s*.*\d{5,6}?', 
            re.IGNORECASE
        )
        
        # Fallback pattern for UK addresses and other formats
        self.uk_address_pattern = re.compile(
            r'(?:\d+[A-Za-z]*\s+)?(?:[A-Za-z]+\s+)?(?:St|Ave|Avenue|Street|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Place|Pl|Close|Cl|Gardens|Gdns|Square|Sq|Terrace|Tce|Crescent|Cres|Hill|Circus|Park|Pk|Mews|Row|Wynd|Vale|End|Green|Grove|Gr|Manor|Wood|Woods|Field|Fields|Meadow|Meadows|Bank|Banks|Side|Approach|Gate|Gates|Walk|Passage|Path|Alley|Broadway|Brwy|Causeway|Cw|Chase|Ch|Circle|Cir|Common|Cross|Xing|Crossing|Crest|Cr|Dale|Div|Estate|Es|Expressway|Expy|Extension|Ext|Field|Fld|Ford|Frd|Forest|Frst|Forge|Frg|Forks|Frks|Fort|Ft|Freeway|Fwy|Garden|Gdn|Gardens|Gdns|Gateway|Gatewy|Glens|Gln|Green|Grn|Grove|Grv|Harbor|Hbr|Haven|Hvn|Heights|Hts|Highway|Hwy|Hollow|Hol|Inlet|Inlt|Island|Is|Islands|Iss|Junction|Jct|Key|Ky|Knob|Knb|Lake|Lk|Lakes|Lks|Land|Lnd|Landing|Lndg|Lane|Ln|Light|Lgt|Lights|Lgts|Loaf|Lf|Lock|Lcks|Lodge|Ldg|Loop|Lp|Mall|Manor|Mnr|Meadows|Mdw|Mill|Ml|Mills|Mls|Mission|Msn|Motorway|Mtwy|Mount|Mnt|Mountain|Mtn|Mountains|Mtns|Neck|Nck|Orchard|Orch|Oval|Ovl|Overpass|Opas|Park|Pk|Parkway|Pkwy|Passage|Psge|Path|Pike|Pines|Pnes|Place|Pl|Plain|Pln|Plains|Plns|Plaza|Plz|Point|Pt|Points|Pts|Port|Prt|Ports|Prts|Prairie|Prr|Radial|Rad|Ramp|Rmp|Ranch|Rnch|Rapid|Rpd|Rapids|Rpds|Rest|Rst|Ridge|Rdg|Ridges|Rdgs|River|Rvr|Road|Rd|Roads|Rds|Route|Rte|Row|Rue|Run|Shoal|Shls|Shoals|Shls|Shore|Shr|Shores|Shrs|Skyway|Skwy|Spring|Spg|Springs|Spgs|Spur|Spurs|Sqr|Squares|Sqrs|Station|Stn|Stravenue|Straven|Stream|Strm|Street|St|Streets|Sts|Summit|Smt|Terrace|Ter|Throughway|Trwy|Track|Trk|Trafficway|Trfy|Trail|Trl|Trailer|Trlr|Tunnel|Tunl|Turnpike|Tpke|Underpass|Upas|Union|Un|Valleys|Vlys|Village|Vlg|Villages|Vlgs|Ville|Vl|Vista|Vis|Walk|Walks|Wall|Walls|Way|Ways|Well|Wl|Wells|Wls|Palace|Castle|Bridge|Tower|Abbey|Cathedral|Church|Hall|Market|Square|Circus)', 
            re.IGNORECASE
        )
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = (
            "🚰 Welcome to Water Fountain Bot!\n\n"
            "I can help you find nearby water fountains and restrooms using your location or an address!\n\n"
            "How to use:\n"
            "• Send me your location (📍) or\n"
            "• Type /location to request location access\n"
            "• Or type an address like: 816 S Highland St, Arlington, VA 22204 or 221B Baker Street, London NW1 6XE\n"
            "• Set custom radius: /radius 2000 (search within 2km)\n\n"
            "I'll find water fountains and restrooms (default 1000m) and show you a map with directions!"
        )
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "🚰 Water Fountain Bot Help\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/location - Request location sharing\n"
            "/radius <meters> - Set custom search radius (100-5000m)\n\n"
            "How to use:\n"
            "• Share your location using the 📍 button\n"
            "• Type an address like: 816 S Highland St, Arlington, VA 22204 or 221B Baker Street, London NW1 6XE\n"
            "• Set custom radius: /radius 2000 (search within 2km)\n\n"
            "I'll find water fountains and restrooms within your search radius!"
        )
        await update.message.reply_text(help_message)
    
    async def set_radius(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /radius command to set custom search radius"""
        if not context.args:
            await update.message.reply_text(
                "📏 Usage: /radius <meters>\n\n"
                "Examples:\n"
                "/radius 500 - Search within 500m\n"
                "/radius 2000 - Search within 2km\n"
                "/radius 1000 - Reset to default (1000m)"
            )
            return
        
        try:
            radius = int(context.args[0])
            if radius < 100 or radius > 5000:
                await update.message.reply_text(
                    "❌ Radius must be between 100m and 5000m (5km).\n"
                    "Please try again with a valid radius."
                )
                return
            
            # Store radius in user context (for this session)
            context.user_data['search_radius'] = radius
            
            await update.message.reply_text(
                f"📏 Search radius set to {radius}m.\n"
                f"This will apply to your next search."
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid radius. Please use a number like:\n"
                "/radius 1000 or /radius 500"
            )
    
    async def request_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /location command - send location request button"""
        location_request = (
            "📍 Please share your location to find nearby water fountains.\n\n"
            "Tap the 📍 (location) button below and select 'Send Location'"
        )
        
        reply_markup = {
            'keyboard': [[{'text': '📍 Send Location', 'request_location': True}]],
            'resize_keyboard': True,
            'one_time_keyboard': True
        }
        
        await update.message.reply_text(location_request, reply_markup=reply_markup)
    
    async def handle_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE, address: str):
        """Handle address messages"""
        # Send geocoding message
        geocoding_msg = await update.message.reply_text(f"🔍 Geocoding address: {address}")
        
        try:
            # Geocode the address
            coordinates = self.geocoding_client.geocode_address(address)
            
            if not coordinates:
                await geocoding_msg.edit_text(
                    "❌ Could not find that address. Please check the address format and try again.\n\n"
                    "Examples:\n"
                    "• US: 816 S Highland St, Arlington, VA 22204\n"
                    "• UK: 221B Baker Street, London NW1 6XE"
                )
                return
            
            latitude, longitude = coordinates
            
            # Update message to show geocoding was successful
            address_info = self.geocoding_client.format_address_response(address, coordinates)
            await geocoding_msg.edit_text(f"{address_info}\n\n🔍 Searching for water fountains nearby...")
            
            # Find water fountains with custom radius or default
            search_radius = context.user_data.get('search_radius', Config.SEARCH_RADIUS_METERS)
            fountains = self.osm_client.find_water_fountains(
                latitude, longitude, search_radius
            )
            
            if not fountains:
                await geocoding_msg.edit_text(
                    f"{address_info}\n\n"
                    f"❌ No water fountains found within {search_radius}m of this location.\n\n"
                    "Try searching in a different area or check if you're in a location "
                    "with public water facilities."
                )
                return
            
            # Generate map image
            map_image = self.map_generator.generate_static_map(latitude, longitude, fountains)
            
            # Generate Google Maps links
            links = self.map_generator.generate_google_maps_links(latitude, longitude, fountains)
            search_area_link = self.map_generator.generate_search_area_link(latitude, longitude)
            
            # Prepare response message
            response_text = f"🚰 Found {len(fountains)} water sources and restrooms within {search_radius}m of:\n{address_info}\n\n"
            response_text += "\n".join(links) + f"\n\n[🗺️ View search area on Google Maps]({search_area_link})"
            
            # Send map image if generated successfully
            if map_image:
                await geocoding_msg.delete()
                await update.message.reply_photo(
                    photo=io.BytesIO(map_image),
                    caption=response_text,
                    parse_mode='Markdown'
                )
            else:
                await geocoding_msg.edit_text(response_text, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error handling address: {e}")
            await geocoding_msg.edit_text(
                "❌ Sorry, something went wrong while processing that address. "
                "Please try again later."
            )
    
    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle location messages"""
        if not update.message.location:
            await update.message.reply_text("❌ Please send a valid location.")
            return
        
        location = update.message.location
        latitude = location.latitude
        longitude = location.longitude
        
        # Send searching message
        searching_msg = await update.message.reply_text("🔍 Searching for water fountains nearby...")
        
        try:
            # Find water fountains with custom radius or default
            search_radius = context.user_data.get('search_radius', Config.SEARCH_RADIUS_METERS)
            fountains = self.osm_client.find_water_fountains(
                latitude, longitude, search_radius
            )
            
            if not fountains:
                await searching_msg.edit_text(
                    f"❌ No water fountains found within {search_radius}m of your location.\n\n"
                    "Try searching in a different area or check if you're in a location "
                    "with public water facilities."
                )
                return
            
            # Generate map image
            map_image = self.map_generator.generate_static_map(latitude, longitude, fountains)
            
            # Generate Google Maps links
            links = self.map_generator.generate_google_maps_links(latitude, longitude, fountains)
            search_area_link = self.map_generator.generate_search_area_link(latitude, longitude)
            
            # Prepare response message
            response_text = f"🚰 Found {len(fountains)} water sources and restrooms within {search_radius}m:\n\n"
            response_text += "\n".join(links) + f"\n\n[🗺️ View search area on Google Maps]({search_area_link})"
            
            # Send map image if generated successfully
            if map_image:
                await searching_msg.delete()
                await update.message.reply_photo(
                    photo=io.BytesIO(map_image),
                    caption=response_text,
                    parse_mode='Markdown'
                )
            else:
                await searching_msg.edit_text(response_text, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error handling location: {e}")
            await searching_msg.edit_text(
                "❌ Sorry, something went wrong while searching for water fountains. "
                "Please try again later."
            )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages that aren't commands"""
        text = update.message.text.strip()
        
        # Check if the text looks like an address
        if self.address_pattern.match(text) or self.uk_address_pattern.search(text):
            await self.handle_address(update, context, text)
        else:
            await update.message.reply_text(
                "📍 Please share your location or type an address to find water fountains.\n\n"
                "Examples:\n"
                "• Share location using the 📍 button\n"
                "• US address: 816 S Highland St, Arlington, VA 22204\n"
                "• UK address: 221B Baker Street, London NW1 6XE\n\n"
                "Use /help for more information."
            )

def build_app():
    Config.validate()
    bot = WaterFountainBot()
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("location", bot.request_location))
    application.add_handler(CommandHandler("radius", bot.set_radius))
    application.add_handler(MessageHandler(filters.LOCATION, bot.handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text))
    return application


def main():
    logger.info("Starting Water Fountain Bot...")
    build_app().run_polling()

if __name__ == '__main__':
    main()
