from flask import Flask, render_template, request, jsonify
import requests
import time

# Caching to store API results for a short time (1 hour)
cache = {}
CACHE_DURATION = 3600  # Cache duration (1 hour)
STEAM_API_KEY = "99883BDAA0AF7A49009D3D88C386AAE4"

# Featured games
FEATURED_GAMES = [
    {
        "name": "Satisfactory",
        "price": "$40.87",
        "image": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/526870/header.jpg?t=1737364583",
        "game_url": "https://store.steampowered.com/app/526870/Satisfactory/"
    },
    {
        "name": "Persona 3 Reload",
        "price": "$76.05",
        "image": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/2161700/header.jpg?t=1741697885",
        "game_url": "https://store.steampowered.com/app/2161700/Persona_3_Reload/"
    },
    {
        "name": "Call of Duty®: Black Ops 6",
        "price": "$86.95",
        "image": "https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/2933620/header.jpg?t=1740790590",
        "game_url": "https://store.steampowered.com/app/2933620/Call_of_Duty_Black_Ops_6/"
    }
]

# Caching functions
def get_cached_game_data(game_name):
    if game_name in cache and time.time() - cache[game_name]['timestamp'] < CACHE_DURATION:
        return cache[game_name]['data']
    return None

def cache_game_data(game_name, data):
    if data:
        cache[game_name] = {'data': data, 'timestamp': time.time()}

# Fetch Steam game price
def get_steam_game_price(game_name):
    cached_data = get_cached_game_data(game_name)
    if cached_data:
        return cached_data

    try:
        time.sleep(1)
        search_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
        response = requests.get(search_url)
        response.raise_for_status()
        data = response.json()
        app_list = data.get("applist", {}).get("apps", [])

        matches = [game for game in app_list if game["name"].lower() == game_name.lower()] or \
                  [game for game in app_list if game_name.lower() in game["name"].lower()]

        if not matches:
            return None

        results = []
        for game in matches:
            game_id = game["appid"]
            store_url = f"https://store.steampowered.com/api/appdetails?appids={game_id}&key={STEAM_API_KEY}"
            game_data = requests.get(store_url)
            game_data.raise_for_status()
            game_data = game_data.json()

            if str(game_id) in game_data and game_data[str(game_id)]["success"]:
                data = game_data[str(game_id)]["data"]
                price = data.get("price_overview", {}).get("final_formatted", "Price not available")
                image = data.get("header_image", "")
                game_url = f"https://store.steampowered.com/app/{game_id}"

                results.append({
                    "price": price,
                    "image": image,
                    "game_url": game_url,
                    "name": game["name"],
                    "platform": "Steam"
                })

        cache_game_data(game_name, results)
        return results

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Steam data: {e}")
        return None

# Fetch GOG game price
def get_gog_game_price(game_name):
    base_url = "https://www.gog.com/games/ajax/filtered"
    params = {"mediaType": "game", "search": game_name}

    response = requests.get(base_url, params=params)
    if response.status_code != 200:
        return []

    try:
        data = response.json()
        games = data.get("products", []) if isinstance(data, dict) else []

        if not games:
            return []

        game_results = []
        for game in games:
            # Get Steam image if available
            steam_results = get_steam_game_price(game["title"])
            steam_image = steam_results[0]["image"] if steam_results else None

            # Use GOG image if it exists, otherwise use Steam image, otherwise placeholder
            image_url = game.get("image", "")
            if image_url:
                image_url = f"https:{image_url}" if image_url.startswith("//") else image_url
            else:
                image_url = steam_image if steam_image else "https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg"

            game_results.append({
                "name": game["title"],
                "price": f"${game.get('price', {}).get('finalAmount', 'N/A')}",
                "original_price": f"${game.get('price', {}).get('baseAmount', None)}" if game.get('price', {}).get('baseAmount') else None,
                "image": image_url,
                "game_url": f"https://www.gog.com{game['url']}",
                "platform": "GOG"
            })

        return game_results

    except ValueError:
        return []

# Fetch game prices from all sources
def get_game_prices_concurrently(game_name):
    steam_results = get_steam_game_price(game_name)
    gog_results = get_gog_game_price(game_name)

    return (steam_results or []) + (gog_results or [])

# Flask app setup
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        game_name = request.form.get("game_name")
        game_results = get_game_prices_concurrently(game_name)
        return render_template("index.html", game_name=game_name, game_results=game_results, featured_games=FEATURED_GAMES)
    return render_template("index.html", featured_games=FEATURED_GAMES)

@app.route("/search")
def search_game():
    game_name = request.args.get('game_name')
    game_results = get_game_prices_concurrently(game_name)
    return jsonify(game_results)

@app.route("/featured")
def featured_games():
    return jsonify(FEATURED_GAMES)

if __name__ == "__main__":
    app.run(debug=True)
#making sure this is the updated code lol#