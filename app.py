import requests
from flask import Flask, render_template, request

app = Flask(__name__)

def get_steam_game_price(game_name):
    """Fetch game price, description, and image from Steam API."""
    steam_app_list_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
    steam_store_url = "https://store.steampowered.com/api/appdetails?appids={}"

    # Get the list of Steam games
    response = requests.get(steam_app_list_url).json()
    
    if "applist" not in response or "apps" not in response["applist"]:
        return None, None, None  # No game list found

    app_list = response["applist"]["apps"]

    # Find the game ID
    game_id = None
    for game in app_list:
        if game["name"].lower() == game_name.lower():
            game_id = game["appid"]
            break

    if not game_id:
        return None, None, None  # Game not found

    # Get game details
    details_response = requests.get(steam_store_url.format(game_id)).json()
    if str(game_id) not in details_response or not details_response[str(game_id)]["success"]:
        return None, None, None  # Invalid response

    game_data = details_response[str(game_id)]["data"]
    
    # Extract price
    price = game_data.get("price_overview", {}).get("final_formatted", "Price not available")

    # Extract game image
    image_url = game_data.get("header_image", "")

    # Extract description
    game_info = game_data.get("short_description", "No description available")

    return price, game_info, image_url

@app.route("/", methods=["GET", "POST"])
def index():
    price, game_info, image_url = None, None, None
    if request.method == "POST":
        game_name = request.form["game_name"]
        price, game_info, image_url = get_steam_game_price(game_name)
    return render_template("index.html", price=price, game_info=game_info, image_url=image_url, game_name=game_name)

if __name__ == "__main__":
    app.run(debug=True)

