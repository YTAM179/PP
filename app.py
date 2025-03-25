from flask import Flask, render_template, request, jsonify
import requests
import time

# Caching to store API results for a short time (e.g., 1 hour)
cache = {}
CACHE_DURATION = 3600  # Cache duration (1 hour)
STEAM_API_KEY = "99883BDAA0AF7A49009D3D88C386AAE4"

# Example of static featured games
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

# Fetch Steam game price using Steam API key
def get_cached_game_data(game_name):
    """Retrieve game data from cache if it's not expired."""
    if game_name in cache:
        cache_entry = cache[game_name]
        if time.time() - cache_entry['timestamp'] < CACHE_DURATION:
            print(f"Using cached data for {game_name}")
            return cache_entry['data']
    return None

# Store data in cache
def cache_game_data(game_name, data):
    if data:  # Only cache if we have valid results
        cache[game_name] = {
            'data': data,
            'timestamp': time.time()
        }

def get_steam_game_price(game_name):
    """Fetch game price from Steam API, with caching and rate-limiting."""
    cached_data = get_cached_game_data(game_name)
    if cached_data:
        return cached_data

    try:
        print(f"Searching for game: {game_name}")

        # Ensure we respect rate limits
        time.sleep(1)  # Small delay to avoid hitting rate limits

        # Fetch all Steam apps
        search_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
        response = requests.get(search_url)
        response.raise_for_status()
        data = response.json()

        app_list = data.get("applist", {}).get("apps", [])

        # Prioritize exact matches, then fallback to partial matches
        exact_matches = [game for game in app_list if game["name"].lower() == game_name.lower()]
        partial_matches = [game for game in app_list if game_name.lower() in game["name"].lower()]

        # Debugging the results of exact and partial matches
        print(f"Exact matches for '{game_name}': {[game['name'] for game in exact_matches]}")
        print(f"Partial matches for '{game_name}': {[game['name'] for game in partial_matches]}")
        
        matches = exact_matches if exact_matches else partial_matches

        # Exclude the specific game (Balatro Soundtrack) by App ID
        matches = [game for game in matches if game["appid"] != 2834460]

        print(f"Found {len(matches)} matches for {game_name} after exclusion.")
        for match in matches:
            print(f"Match: {match['name']} (App ID: {match['appid']})")

        if not matches:
            print(f"Game {game_name} not found.")
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

                # Process price and other data
                original_price = data.get("price_overview", {}).get("initial_formatted", "Price not available")
                sale_price = data.get("price_overview", {}).get("final_formatted", original_price)

                image = data.get("header_image", "")
                game_url = f"https://store.steampowered.com/app/{game_id}"

                results.append({
                    "price": sale_price,
                    "original_price": original_price if sale_price != original_price else None,
                    "image": image,
                    "game_url": game_url,
                    "name": game["name"]
                })

        # Cache the results only if valid
        cache_game_data(game_name, results)
        return results

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Steam data: {e}")
        return None

# Fetch Steam data only
def get_game_prices_concurrently(game_name):
    game_results = get_steam_game_price(game_name)
    return game_results

def get_game_suggestions(query):
    """Get game suggestions based on query input."""
    search_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    response = requests.get(search_url)
    response.raise_for_status()
    data = response.json()
    app_list = data.get("applist", {}).get("apps", [])
    
    # Return matching games based on the query
    suggestions = [game["name"] for game in app_list if query.lower() in game["name"].lower()]
    return suggestions[:5]  # Limit to 5 suggestions

# Initialize Flask app
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    # Serve the homepage with the form and no search results by default
    if request.method == "POST":
        game_name = request.form.get("game_name")
        game_results = get_game_prices_concurrently(game_name)
        return render_template("index.html", game_name=game_name, game_results=game_results, featured_games=FEATURED_GAMES)

    return render_template("index.html", featured_games=FEATURED_GAMES)

@app.route("/search")
def search_game():
    game_name = request.args.get('game_name')
    game_results = get_game_prices_concurrently(game_name)

    # Return a JSON response for AJAX requests
    return jsonify(game_results)

@app.route("/featured")
def featured_games():
    # Return featured games as a JSON response for the front-end
    return jsonify(FEATURED_GAMES)

@app.route("/suggestions")
def suggestions():
    query = request.args.get("query")
    suggestions = get_game_suggestions(query)
    return jsonify(suggestions)

if __name__ == "__main__":
    app.run(debug=True)
