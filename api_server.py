from flask import Flask, jsonify, request, Response
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
import re
import time
import json
import os

app = Flask(__name__)

# URL do site-fonte
SOURCE_URL = "https://animefire.plus/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Caminho para o arquivo de cache
CACHE_FILE = 'video_link_cache.json'

# Cache em memória para armazenar links de vídeo
video_link_cache = {}

def load_cache():
    """
    Carrega o cache de links de vídeo de um arquivo JSON.
    """
    global video_link_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                video_link_cache = json.load(f)
            print(f"✅ Cache de links de vídeo carregado de {CACHE_FILE}")
        except json.JSONDecodeError:
            print(f"⚠️ Erro ao decodificar o cache de {CACHE_FILE}. Iniciando com cache vazio.")
            video_link_cache = {}
    else:
        print(f"ℹ️ Arquivo de cache {CACHE_FILE} não encontrado. Iniciando com cache vazio.")

def save_cache():
    """
    Salva o cache de links de vídeo em um arquivo JSON.
    """
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(video_link_cache, f, indent=4)
    print(f"💾 Cache de links de vídeo salvo em {CACHE_FILE}")

def get_player_url_selenium(episode_url):
    """
    Usa Selenium para extrair a URL do player do vídeo, simulando um clique com JavaScript.
    """
    driver = None
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        options.add_argument("--enable-unsafe-swiftshader")
        options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.0")

        driver = webdriver.Chrome(options=options)
        driver.get(episode_url)

        # Seletor para o botão de play.
        PLAY_BUTTON_SELECTOR = ".vjs-big-play-button"
        
        # Espera o botão de play aparecer
        play_button = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, PLAY_BUTTON_SELECTOR))
        )
        
        # Clica no botão de play usando JavaScript para contornar o overlay
        driver.execute_script("arguments[0].click();", play_button)
        
        time.sleep(2) # Pequena pausa para o vídeo carregar

        # Espera o elemento de vídeo aparecer e pega a URL dele
        VIDEO_ELEMENT_SELECTOR = "#my-video_html5_api"
        video_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, VIDEO_ELEMENT_SELECTOR))
        )
        
        player_url = video_element.get_attribute('src')
        return player_url

    except Exception as e:
        print(f"❌ Erro ao extrair o link do player para {episode_url}: {e}")
        return None

    finally:
        if driver:
            driver.quit()

def scrape_latest_episodes():
    """
    Busca os últimos episódios e seus links usando BeautifulSoup para ser rápido.
    """
    try:
        response = requests.get(SOURCE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        EPISODE_CARD_SELECTOR = "div.divCardUltimosEpsHome"
        animes = soup.select(EPISODE_CARD_SELECTOR)
        
        scraped_animes = []
        for anime in animes:
            try:
                link_element = anime.find('a')
                title_element = anime.find('h3', class_='animeTitle')
                image_element = anime.find('img', class_='imgAnimesUltimosEps')
                episode_number_element = anime.find('span', class_='numEp')

                if all([link_element, title_element, image_element, episode_number_element]):
                    title = title_element.text.strip().split(' - Episódio')[0].strip()
                    episode_number = episode_number_element.text.strip()
                    episode_link = link_element.get('href')
                    relative_path = image_element.get('data-src')
                    image_url = urljoin(SOURCE_URL, relative_path)
                    
                    scraped_animes.append({
                        'title': title,
                        'episode_number': episode_number,
                        'link': episode_link,
                        'image_url': image_url
                    })
            except Exception as e:
                print(f"Erro ao processar um card de anime, pulando para o próximo: {e}")
                continue
        return scraped_animes
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao buscar os dados da página: {e}")
        return []

def scrape_anime_catalog():
    """Busca o catálogo completo de animes na URL correta."""
    try:
        response = requests.get(f"{SOURCE_URL}lista-de-animes-legendados", headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Seletor ajustado com base na sua amostra de código HTML
        ANIME_CARD_SELECTOR = "div.divCardUltimosEps"
        animes = soup.select(ANIME_CARD_SELECTOR)

        catalog_data = []
        for anime in animes:
            try:
                link_element = anime.find('a')
                title_element = anime.find('h3', class_='animeTitle')
                image_element = anime.find('img', class_='imgAnimes')
                
                if all([link_element, title_element, image_element]):
                    title = title_element.text.strip()
                    anime_link = link_element.get('href')
                    
                    # Pega a URL da imagem do atributo 'data-src' que contém o caminho real
                    relative_path = image_element.get('data-src') or image_element.get('src')
                    image_url = urljoin(SOURCE_URL, relative_path)

                    catalog_data.append({
                        'title': title,
                        'link': anime_link,
                        'image_url': image_url
                    })
            except Exception as e:
                print(f"Erro ao processar um card de anime no catálogo: {e}")
                continue
        
        return catalog_data
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao buscar o catálogo de animes: {e}")
        return []

def scrape_search_results(query):
    """
    Busca animes no site AnimeFire.plus e retorna os resultados.
    """
    search_url = f"{SOURCE_URL}pesquisar/{query}"
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        SEARCH_CARD_SELECTOR = "div.divCardContainer"
        animes = soup.select(SEARCH_CARD_SELECTOR)

        search_results = []
        for anime in animes:
            try:
                link_element = anime.find('a')
                title_element = anime.find('h3', class_='animeTitle')
                image_element = anime.find('img', class_='imgAnimesUltimosEps')

                if all([link_element, title_element, image_element]):
                    title = title_element.text.strip()
                    link = link_element.get('href')
                    relative_path = image_element.get('data-src')
                    image_url = urljoin(SOURCE_URL, relative_path)

                    search_results.append({
                        'title': title,
                        'link': link,
                        'image_url': image_url
                    })
            except Exception as e:
                print(f"Erro ao processar um card de busca, pulando para o próximo: {e}")
                continue
        return search_results
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao buscar resultados para '{query}': {e}")
        return []

# --- FUNÇÃO DE RASPAGEM DO PERFIL DO ANIME CORRIGIDA ---
def scrape_anime_profile(anime_url):
    """
    Busca informações detalhadas de um anime (sinopse, imagem e lista de episódios)
    a partir da URL do seu perfil.
    """
    try:
        response = requests.get(anime_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        profile_data = {}

        # Título principal
        title_element = soup.find('h1', class_='anime-title')
        profile_data['title'] = title_element.text.strip() if title_element else "Título não encontrado"

        # Nomes adicionais (inglês e japonês)
        # O site mudou a forma de extrair, agora precisa buscar por 'h6' dentro de uma div específica
        div_names = soup.find('div', class_='div_anime_names')
        if div_names:
            h6_elements = div_names.find_all('h6')
            profile_data['english_title'] = h6_elements[0].text.strip() if len(h6_elements) > 0 else None
            profile_data['japanese_title'] = h6_elements[1].text.strip() if len(h6_elements) > 1 else None
        else:
            profile_data['english_title'] = None
            profile_data['japanese_title'] = None


        # Imagem de capa
        image_element = soup.find('div', class_='anime-cover-poster').find('img')
        relative_path = image_element.get('src') or image_element.get('data-src')
        profile_data['image_url'] = urljoin(SOURCE_URL, relative_path) if image_element else "Imagem não encontrada"

        # Sinopse
        synopsis_element = soup.find('p', class_='anime-synopsis')
        profile_data['synopsis'] = synopsis_element.text.strip() if synopsis_element else "Sinopse não encontrada"

        # Lista de Episódios
        episode_elements = soup.select('div.div_video_list a.lEp')
        episodes_list = []
        for ep in episode_elements:
            try:
                episode_number = ep.text.strip().replace('Episódio ', '')
                episode_link = urljoin(SOURCE_URL, ep.get('href'))
                episodes_list.append({
                    'episode_number': episode_number,
                    'link': episode_link
                })
            except Exception as e:
                print(f"Erro ao processar um episódio: {e}")
                continue
        profile_data['episodes'] = episodes_list
        
        return profile_data
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao buscar o perfil do anime em {anime_url}: {e}")
        return None

@app.route('/api/latest_episodes', methods=['GET'])
def latest_episodes():
    episodes = scrape_latest_episodes()
    return jsonify(episodes)

@app.route('/api/catalog', methods=['GET'])
def get_catalog():
    catalog = scrape_anime_catalog()
    return jsonify(catalog)

@app.route('/api/search', methods=['GET'])
def search_animes():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Termo de busca não fornecido'}), 400
    
    results = scrape_search_results(query)
    return jsonify(results)

# --- ROTA DA API DO PERFIL DO ANIME CORRIGIDA ---
@app.route("/api/anime_profile")
def api_anime_profile():
    anime_url = request.args.get("url")
    if not anime_url:
        return jsonify({"error": "URL do anime não fornecida"}), 400

    print(f"Buscando dados do perfil para: {anime_url}")

    profile_data = scrape_anime_profile(anime_url)

    if profile_data:
        print("✅ Dados do perfil extraídos com sucesso!")
        return jsonify(profile_data)
    else:
        return jsonify({"error": "Erro ao extrair dados do perfil"}), 500


@app.route('/api/video_link', methods=['GET'])
def video_link():
    episode_url = request.args.get('url')
    if not episode_url:
        return jsonify({'error': 'URL do episódio não fornecida'}), 400
    
    # Tenta obter o link do cache primeiro
    if episode_url in video_link_cache:
        print(f"✅ Link do vídeo encontrado no cache para {episode_url}")
        return jsonify({'video_link': video_link_cache[episode_url]})

    # Se não estiver no cache, usa Selenium para extrair
    player_url = get_player_url_selenium(episode_url)
    
    if player_url:
        # Armazena no cache antes de retornar
        video_link_cache[episode_url] = player_url
        save_cache() # Salva o cache após adicionar um novo item
        print(f"✅ Link do vídeo extraído e armazenado no cache para {episode_url}")
        return jsonify({'video_link': player_url})
    else:
        return jsonify({'error': 'Erro ao extrair o link do vídeo'}), 500

@app.route('/api/stream_video')
def stream_video():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({'error': 'URL do vídeo não fornecida'}), 400

    # Define o cabeçalho Referer para simular a origem do AnimeFire.plus
    headers = {
        'Referer': 'https://animefire.plus/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # Faz a requisição ao servidor de streaming com o Referer modificado
        r = requests.get(video_url, headers=headers, stream=True)
        r.raise_for_status()

        # Cria uma resposta de streaming para o frontend
        def generate():
            for chunk in r.iter_content(chunk_size=8192):
                yield chunk

        return Response(generate(), mimetype=r.headers.get('Content-Type', 'video/mp4'))

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao fazer proxy do vídeo: {e}")
        return jsonify({'error': 'Erro ao fazer proxy do vídeo'}), 500

if __name__ == '__main__':
    load_cache() # Carrega o cache ao iniciar o servidor
    app.run(port=5001, debug=True)