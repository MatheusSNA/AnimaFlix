from flask import Flask, render_template, request, redirect, url_for
import requests
import json

app = Flask(__name__)

API_BASE_URL = "http://127.0.0.1:5001"

@app.route("/")
def index():
    try:
        response = requests.get(f"{API_BASE_URL}/api/latest_episodes")
        response.raise_for_status()  # Levanta um erro para códigos de status HTTP ruins (4xx ou 5xx)
        latest_episodes = response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao conectar com a API: {e}")
        latest_episodes = []
    return render_template("index.html", latest_episodes=latest_episodes)

@app.route("/catalog")
def catalog():
    try:
        response = requests.get(f"{API_BASE_URL}/api/catalog")
        response.raise_for_status()
        catalog_list = response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao conectar com a API de catálogo: {e}")
        catalog_list = []
    return render_template("catalog.html", catalog=catalog_list)


@app.route("/watch")
def watch():
    episode_url = request.args.get("url")
    if not episode_url:
        return "URL do episódio não fornecida", 400
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/video_link?url={episode_url}")
        response.raise_for_status()
        video_data = response.json()
        video_proxy_link = video_data.get("video_link")
        if not video_proxy_link:
            return "Erro ao obter o link do player.", 500
        # A URL do proxy deve ser a URL completa do api_server.py
        # para que o navegador do cliente possa fazer a requisição diretamente a ele.
        # O app.py não deve atuar como proxy para o stream de vídeo, apenas o api_server.py.
        return render_template("watch.html", video_proxy_link=f"{API_BASE_URL}/api/stream_video?url={video_proxy_link}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao conectar com a API: {e}")
        return "Erro ao obter o link do player.", 500

@app.route("/search")
def search():
    query = request.args.get("q")
    if not query:
        return redirect(url_for("index"))
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/search?q={query}")
        response.raise_for_status()
        search_results = response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao conectar com a API de busca: {e}")
        search_results = []
    
    return render_template("search_results.html", query=query, search_results=search_results)

# --- ROTA DE PERFIL DO ANIME ADICIONADA ---
@app.route("/anime_profile")
def anime_profile():
    anime_url = request.args.get("url")
    if not anime_url:
        return "URL do anime não fornecida", 400

    try:
        response = requests.get(f"{API_BASE_URL}/api/anime_profile?url={anime_url}")
        response.raise_for_status()
        anime_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao conectar com a API de perfil de anime: {e}")
        return "Erro ao carregar o perfil do anime.", 500

    return render_template("anime_profile.html", anime=anime_data)

if __name__ == "__main__":
    app.run(debug=True)