# Unit Converter Bot

A Telegram bot that converts between units. Send a message in the format `[value] [unit] to [unit]` and get an instant answer.

## Usage

```
100 kg to lbs
32 fahrenheit to celsius
60 mph to kph
5 feet to meters
1 gallon to liters
500 ml to cups
3pm EST to PST
15:30 GMT to JST
now UTC to America/New_York
```

## Supported Units

### Weight
| From | To | Example |
|------|----|---------|
| kg | lbs | `70 kg to lbs` |
| lbs | kg | `150 lbs to kg` |
| oz | grams | `8 oz to grams` |
| grams | oz | `250 grams to oz` |
| stone | kg | `12 stone to kg` |
| kg | stone | `80 kg to stone` |
| metric tons | lbs | `1 metric_ton to lbs` |

### Temperature
| From | To | Example |
|------|----|---------|
| Celsius | Fahrenheit | `100 celsius to fahrenheit` |
| Fahrenheit | Celsius | `72 fahrenheit to celsius` |
| Celsius | Kelvin | `25 celsius to kelvin` |
| Kelvin | Celsius | `300 kelvin to celsius` |

### Distance
| From | To | Example |
|------|----|---------|
| miles | km | `26.2 miles to km` |
| km | miles | `42 km to miles` |
| feet | meters | `6 feet to meters` |
| meters | feet | `1.8 meters to feet` |
| inches | cm | `12 inches to cm` |
| cm | inches | `30 cm to inches` |
| yards | meters | `100 yards to meters` |
| nautical miles | km | `10 nautical_miles to km` |
| light years | km | `1 light_year to km` |

### Speed
| From | To | Example |
|------|----|---------|
| mph | kph | `60 mph to kph` |
| kph | mph | `100 kph to mph` |
| knots | mph | `20 knots to mph` |
| m/s | mph | `10 m/s to mph` |
| mach | mph | `1 mach to mph` |

### Volume
| From | To | Example |
|------|----|---------|
| liters | gallons | `2 liters to gallons` |
| gallons | liters | `5 gallons to liters` |
| ml | cups | `500 ml to cups` |
| cups | ml | `2 cups to ml` |
| fl oz | ml | `8 fl_oz to ml` |
| ml | fl oz | `250 ml to fl_oz` |
| pints | liters | `4 pints to liters` |
| quarts | liters | `1 quart to liters` |
| tablespoons | ml | `3 tablespoons to ml` |
| teaspoons | ml | `1 teaspoon to ml` |
| cubic feet | liters | `1 cubic_foot to liters` |

### Area
| From | To | Example |
|------|----|---------|
| acres | hectares | `10 acres to hectares` |
| hectares | acres | `5 hectares to acres` |
| sq ft | sq meters | `1000 ft² to m²` |
| sq meters | sq ft | `100 m² to ft²` |
| sq miles | sq km | `1 mi² to km²` |

### Energy & Power
| From | To | Example |
|------|----|---------|
| calories | joules | `200 calories to joules` |
| kcal | kJ | `500 kcal to kJ` |
| kWh | joules | `1 kWh to joules` |
| BTU | joules | `1000 BTU to joules` |
| horsepower | watts | `100 horsepower to watts` |
| watts | horsepower | `750 watts to horsepower` |

### Pressure
| From | To | Example |
|------|----|---------|
| psi | bar | `30 psi to bar` |
| bar | psi | `2 bar to psi` |
| atm | psi | `1 atm to psi` |
| mmHg | kPa | `120 mmHg to kPa` |

### Data
| From | To | Example |
|------|----|---------|
| GB | MB | `2 GB to MB` |
| TB | GB | `1 TB to GB` |
| MB | KB | `100 MB to KB` |

### Time
| From | To | Example |
|------|----|---------|
| hours | minutes | `2.5 hours to minutes` |
| minutes | seconds | `90 minutes to seconds` |
| days | hours | `7 days to hours` |
| weeks | days | `4 weeks to days` |
| years | days | `1 year to days` |

### Time Zone Conversion
| From | To | Example |
|------|----|---------|
| EST | PST | `3pm EST to PST` |
| GMT | JST | `15:30 GMT to JST` |
| UTC | US/Eastern | `now UTC to US/Eastern` |
| PST | CET | `9am PST to CET` |

**Supported timezone formats:**
- Common abbreviations: EST, PST, GMT, UTC, JST, IST, CET, BST, AEST
- Full timezone names: America/New_York, Europe/London, Asia/Tokyo
- Time formats: `3pm`, `3:30pm`, `15:30`, `15`
- Current time: `now UTC to PST`

## Deployment (Railway)

1. Push this repo to GitHub
2. Create a new Railway project and connect the repo
3. Add environment variable: `TELEGRAM_BOT_TOKEN=<your token>`
4. Railway will use the `Procfile` to start the bot as a worker

## Local Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # add your token
export TELEGRAM_BOT_TOKEN=your_token
python bot.py
```

Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram.
