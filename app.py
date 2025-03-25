from flask import Flask, render_template, request
import requests
import concurrent.futures
import time

# Caching to store API results for a short time (e.g., 5 minutes)
cache = {}

# Fetch Steam game price
def get_steam_game_price(game_name):
    # Check cache first
    if game_name in cache and time.time() - cache[game_name]["timestamp"] < 300:
        print("Returning cached Steam data.")
        return cache[game_name]["steam"]
    
    steam_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    response = requests.get(steam_url).json()

    app_list = response.get("applist", {}).get("apps", [])
    game_id = None

    for game in app_list:
        if game_name.lower() in game["name"].lower():
            game_id = game["appid"]
            break

    if not game_id:
        print("Steam game not found")
        return None, None, None

    store_url = f"https://store.steampowered.com/api/appdetails?appids={game_id}"
    game_data = requests.get(store_url).json()

    if str(game_id) in game_data and game_data[str(game_id)]["success"]:
        data = game_data[str(game_id)]["data"]
        price = data.get("price_overview", {}).get("final_formatted", "Price not available")
        image = data.get("header_image", "")
        game_url = f"https://store.steampowered.com/app/{game_id}"

        # Cache the result
        cache[game_name] = {
            "steam": (price, image, game_url),
            "timestamp": time.time()
        }

        print("Steam Data:", price, game_url, image)
        return price, image, game_url

    print("Steam price not found")
    return None, None, None

# Fetch Epic Games price using Store Catalog API
def get_epic_game_price(game_name):
    epic_url = "https://store-site-backend-static.ak.epicgames.com/store/api/content/products"
    response = requests.get(epic_url).json()

    print("Epic API Response:", response)
    games = response.get("elements", [])

    if not games:
        print("Epic API returned no games.")
        return None, None, None  # Avoid KeyError

    for game in games:
        print("Checking game:", game.get("title"))  # Debug: Print each game name
        if game_name.lower() in game.get("title", "").lower():
            price_info = game.get("price", {}).get("totalPrice", {}).get("fmtPrice", {}).get("originalPrice", "Price not available")
            image = game.get("keyImages", [{}])[0].get("url", "")
            game_url = f"https://store.epicgames.com/p/{game.get('productSlug', '')}"

            print("Epic Data Found:", price_info, game_url, image)  # Debug: Confirm found data

            return price_info, image, game_url

    print("Epic game not found")
    return None, None, None

# Fetch both Steam and Epic data concurrently
def get_game_prices_concurrently(game_name):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Call both functions concurrently
        future_steam = executor.submit(get_steam_game_price, game_name)
        future_epic = executor.submit(get_epic_game_price, game_name)

        # Measure the time taken by each request
        start_time_steam = time.time()
        price_steam, image_steam, game_url_steam = future_steam.result()
        print(f"Steam API call took {time.time() - start_time_steam} seconds.")
        
        start_time_epic = time.time()
        price_epic, image_epic, game_url_epic = future_epic.result()
        print(f"Epic API call took {time.time() - start_time_epic} seconds.")
    
    return price_steam, image_steam, game_url_steam, price_epic, image_epic, game_url_epic

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    price_steam, image_steam, game_url_steam = None, None, None
    price_epic, image_epic, game_url_epic = None, None, None
    
    if request.method == "POST":
        game_name = request.form.get("game_name")
        price_steam, image_steam, game_url_steam, price_epic, image_epic, game_url_epic = get_game_prices_concurrently(game_name)
        
        print("Sending to HTML:", price_steam, image_steam, game_url_steam, price_epic, image_epic, game_url_epic)
    
    return render_template("index.html", game_name=request.form.get("game_name"),
                           price_steam=price_steam, image_steam=image_steam, game_url_steam=game_url_steam,
                           price_epic=price_epic, image_epic=image_epic, game_url_epic=game_url_epic)

if __name__ == "__main__":
    # Run the app in production mode to improve performance (disable debug)
    app.run(debug=False)
