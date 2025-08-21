from fastapi import FastAPI, Request, Response, Cookie, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import httpx
from urllib.parse import urlencode

load_dotenv()
port = os.getenv('PORT')
github_token = os.getenv('GITHUB_TOKEN')
github_owner = os.getenv('GITHUB_OWNER')
github_repo = os.getenv('GITHUB_REPO')
twitch_client_id = os.getenv('TWITCH_CLIENT_ID')
twitch_client_secret = os.getenv('TWITCH_CLIENT_SECRET')
twitch_redirect_uri = os.getenv('TWITCH_REDIRECT_URI')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Twitch OAuth endpoints
TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/authorize"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
TWITCH_API_URL = "https://api.twitch.tv/helix"

async def get_twitch_user_info(access_token: str):
    """Get user info from Twitch using access token"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Client-Id': twitch_client_id
    }
    
    async with httpx.AsyncClient() as client:
        # First validate the token
        validate_response = await client.get(TWITCH_VALIDATE_URL, headers=headers)
        if validate_response.status_code != 200:
            return None
            
        validate_data = validate_response.json()
        user_id = validate_data['user_id']
        
        # Get user info
        user_response = await client.get(f'{TWITCH_API_URL}/users?id={user_id}', headers=headers)
        if user_response.status_code != 200:
            return None
            
        user_data = user_response.json()
        return user_data['data'][0] if user_data['data'] else None

@app.get("/auth/twitch")
async def auth_twitch():
    """Redirect to Twitch authentication"""
    params = {
        'client_id': twitch_client_id,
        'redirect_uri': twitch_redirect_uri,
        'response_type': 'code',
        'scope': 'channel:manage:broadcast',
        'force_verify': 'false'
    }
    
    auth_url = f"{TWITCH_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(auth_url)

@app.get("/auth/twitch/callback")
async def auth_twitch_callback(code: str, response: Response):
    """Handle Twitch authentication callback"""
    # Exchange code for access token
    data = {
        'client_id': twitch_client_id,
        'client_secret': twitch_client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': twitch_redirect_uri
    }
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(TWITCH_TOKEN_URL, data=data)
        if token_response.status_code != 200:
            return {"error": "Failed to get access token"}
            
        token_data = token_response.json()
        access_token = token_data['access_token']
        refresh_token = token_data['refresh_token']
        
        # Get user info
        user_info = await get_twitch_user_info(access_token)
        if not user_info:
            return {"error": "Failed to get user info"}
            
        # Set cookies with user info and tokens
        response = RedirectResponse("/")
        response.set_cookie("twitch_access_token", access_token, httponly=True, max_age=3600)
        response.set_cookie("twitch_refresh_token", refresh_token, httponly=True, max_age=2592000)  # 30 days
        response.set_cookie("twitch_user_id", user_info['id'], max_age=3600)
        response.set_cookie("twitch_user_login", user_info['login'], max_age=3600)
        response.set_cookie("twitch_user_name", user_info['display_name'], max_age=3600)
        
        return response

@app.get("/logout")
async def logout(response: Response):
    """Logout from Twitch"""
    response = RedirectResponse("/")
    response.delete_cookie("twitch_access_token")
    response.delete_cookie("twitch_refresh_token")
    response.delete_cookie("twitch_user_id")
    response.delete_cookie("twitch_user_login")
    response.delete_cookie("twitch_user_name")
    return response

async def get_twitch_credentials(request: Request):
    """Get Twitch credentials from cookies"""
    access_token = request.cookies.get("twitch_access_token")
    user_id = request.cookies.get("twitch_user_id")
    user_login = request.cookies.get("twitch_user_login")
    
    if access_token and user_id:
        return {
            "access_token": access_token,
            "user_id": user_id,
            "user_login": user_login
        }
    return None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Check if user is logged in to Twitch
    twitch_credentials = await get_twitch_credentials(request)
    is_twitch_logged_in = twitch_credentials is not None
    twitch_user_name = request.cookies.get("twitch_user_name", "")
    
    twitch_section = ""
    if is_twitch_logged_in:
        twitch_section = f"""
        <div class="form-container" style="margin-top: 20px;">
            <h2>Twitch Integration (Logged in as {twitch_user_name})</h2>
            <div class="form-group">
                <label for="stream-title">Stream Title:</label>
                <input type="text" id="stream-title" placeholder="Enter stream title">
            </div>
            <div class="form-group">
                <label for="stream-game">Game Name:</label>
                <input type="text" id="stream-game" placeholder="Enter game name" oninput="fetchGameSuggestions()">
                <div id="game-suggestions" class="suggestions" style="display: none;"></div>
            </div>
            <div class="form-group">
                <label for="stream-language">Language:</label>
                <input type="text" id="stream-language" value="ru" placeholder="Stream language">
            </div>
            <div class="form-group">
                <label for="stream-tags">Tags (comma separated):</label>
                <input type="text" id="stream-tags" placeholder="Enter tags">
            </div>
            <button onclick="updateStreamInfo()">Update Stream Info</button>
            <button class="delete-button" onclick="logoutTwitch()" style="margin-top: 10px;">Logout from Twitch</button>
        </div>
        """
    else:
        twitch_section = """
        <div class="form-container" style="margin-top: 20px;">
            <h2>Twitch Integration</h2>
            <button onclick="loginTwitch()" style="background-color: #6441a5;">Login with Twitch</button>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Форма ввода игры</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f0f0f0;
            }}
            .form-container {{
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .form-group {{
                margin-bottom: 15px;
            }}
            label {{
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }}
            input[type="text"], select, textarea {{
                padding: 10px;
                font-size: 16px;
                width: 100%;
                border: 1px solid #ccc;
                border-radius: 4px;
                box-sizing: border-box;
            }}
            .date-picker {{
                display: flex;
                gap: 10px;
            }}
            .date-picker select {{
                flex: 1;
            }}
            .suggestions {{
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
                position: absolute;
                z-index: 1000;
                width: calc(100% - 2px);
                max-width: 578px;
            }}
            .suggestion-item {{
                padding: 10px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .suggestion-item:hover {{
                background-color: #f0f0f0;
            }}
            .suggestion-item img {{
                width: 26px;
                height: 36px;
                object-fit: cover;
            }}
            button {{
                background-color: #4CAF50;
                color: white;
                padding: 10px 15px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                width: 100%;
            }}
            button:hover {{
                background-color: #45a049;
            }}
            .delete-button {{
                background-color: #f44336;
                color: white;
            }}

            .delete-button:hover {{
                background-color: #e53935;
            }}

            .open-source-button {{
                background-color: #2196F3;
                color: white;
            }}

            .open-source-button:hover {{
                background-color: #1976D2;
            }}

            .twitch-button {{
                background-color: #6441a5;
                color: white;
            }}

            .twitch-button:hover {{
                background-color: #4e3680;
            }}

            .button-group {{
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}

            .notification {{
                position: fixed;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                padding: 15px 25px;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                z-index: 1000;
                opacity: 0;
                transition: opacity 0.3s ease;
            }}

            .notification.show {{
                opacity: 1;
            }}

            .notification.success {{
                background-color: #4CAF50;
            }}

            .notification.error {{
                background-color: #f44336;
            }}

            .notification.warning {{
                background-color: #ff9800;
            }}

        </style>
    </head>
    <body>
        <div class="form-container">
            <div class="form-group">
                <label for="search">Название игры:</label>
                <input type="text" id="search" placeholder="Введите название игры..." oninput="fetchSuggestions()">
                <div id="suggestions" class="suggestions" style="display: none;"></div>
            </div>
            
            <div class="form-group">
                <label for="player">Player:</label>
                <select id="player">
                    <option value="P">P</option>
                    <option value="T">T</option>
                    <option value="R">R</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Дата завершения:</label>
                <div class="date-picker">
                    <select id="month">
                        <option value="1"{' selected' if current_month == 1 else ''}>Январь</option>
                        <option value="2"{' selected' if current_month == 2 else ''}>Февраль</option>
                        <option value="3"{' selected' if current_month == 3 else ''}>Март</option>
                        <option value="4"{' selected' if current_month == 4 else ''}>Апрель</option>
                        <option value="5"{' selected' if current_month == 5 else ''}>Май</option>
                        <option value="6"{' selected' if current_month == 6 else ''}>Июнь</option>
                        <option value="7"{' selected' if current_month == 7 else ''}>Июль</option>
                        <option value="8"{' selected' if current_month == 8 else ''}>Август</option>
                        <option value="9"{' selected' if current_month == 9 else ''}>Сентябрь</option>
                        <option value="10"{' selected' if current_month == 10 else ''}>Октябрь</option>
                        <option value="11"{' selected' if current_month == 11 else ''}>Ноябрь</option>
                        <option value="12"{' selected' if current_month == 12 else ''}>Декабрь</option>
                    </select>
                    <select id="year">
                        {''.join(f'<option value="{year}"{" selected" if year == current_year else ""}>{year}</option>' 
                        for year in range(current_year - 5, current_year + 1))}
                    </select>
                </div>
            </div>

            <div class="form-group">
                <label for="platform">Platform:</label>
                <input type="text" id="platform" list="platforms" placeholder="Выберите или введите платформу">
                <datalist id="platforms">
                    <option value="PC">
                    <option value="macOS">
                    <option value="PS1">
                    <option value="PS2">
                    <option value="PS3">
                    <option value="Nintendo Switch">
                    <option value="X1">
                    <option value="X360">
                    <option value="SMD">
                    <option value="NES">
                    <option value="SNES">
                    <option value="Mobile">
                </datalist>
            </div>

            <div class="form-group">
                <label for="status">Status:</label>
                <select id="status">
                    <option value="completed">Completed</option>
                    <option value="dropped">Dropped</option>
                    <option value="re-completed">Re-completed</option>
                    <option value="frozen">Frozen</option>
                    <option value="started">Started</option>
                </select>
            </div>

            <div class="form-group">
                <label for="co-op">CO-OP:</label>
                <textarea id="co-op" rows="4" placeholder="CO-OP игроки (по одной строке на каждую запись)"></textarea>
            </div>

            <div class="button-group">
                <button onclick="saveData()">Сохранить</button>
                <button class="delete-button" onclick="deleteData()">Удалить по ID</button>
                <button class="open-source-button" onclick="editData()">Изменить по ID</button>
                <button class="open-source-button" onclick="openSourceData()">Открыть исходные данные ↗</button>
                <button class="open-source-button" onclick="openTable()">Открыть таблицу ↗</button>
            </div>
        </div>

        {twitch_section}

        <script>

            function htmlEncode(str) {{
                return str.replace(/&/g, "&amp;")
                          .replace(/</g, "&lt;")
                          .replace(/>/g, "&gt;")
                          .replace(/"/g, "&quot;")
                          .replace(/'/g, "&#39;");
            }}

            async function fetchSuggestions() {{
                const input = document.getElementById('search').value;
                const suggestionsDiv = document.getElementById('suggestions');

                if (input.length < 3) {{
                    suggestionsDiv.style.display = 'none';
                    return;
                }}

                const response = await fetch(`/search?query=${{input}}`);
                const data = await response.json();

                suggestionsDiv.innerHTML = '';
                data.forEach(item => {{
                    const div = document.createElement('div');
                    div.className = 'suggestion-item';
                    
                    if (item.box_art_url) {{
                        const img = document.createElement('img');
                        img.src = item.box_art_url;
                        div.appendChild(img);
                    }}
                    
                    const text = document.createElement('span');
                    text.innerText = item.name;
                    div.appendChild(text);
                    
                    div.onclick = () => {{
                        document.getElementById('search').value = item.name;
                        suggestionsDiv.style.display = 'none';
                    }};
                    suggestionsDiv.appendChild(div);
                }});

                suggestionsDiv.style.display = data.length ? 'block' : 'none';
            }}

            async function fetchGameSuggestions() {{
                const input = document.getElementById('stream-game').value;
                const suggestionsDiv = document.getElementById('game-suggestions');

                if (input.length < 3) {{
                    suggestionsDiv.style.display = 'none';
                    return;
                }}

                const response = await fetch(`/search?query=${{input}}`);
                const data = await response.json();

                suggestionsDiv.innerHTML = '';
                data.forEach(item => {{
                    const div = document.createElement('div');
                    div.className = 'suggestion-item';
                    
                    if (item.box_art_url) {{
                        const img = document.createElement('img');
                        img.src = item.box_art_url;
                        div.appendChild(img);
                    }}
                    
                    const text = document.createElement('span');
                    text.innerText = item.name;
                    div.appendChild(text);
                    
                    div.onclick = () => {{
                        document.getElementById('stream-game').value = item.name;
                        suggestionsDiv.style.display = 'none';
                    }};
                    suggestionsDiv.appendChild(div);
                }});

                suggestionsDiv.style.display = data.length ? 'block' : 'none';
            }}

            async function trigger_html_generation() {{
                try {{
                    const response = await fetch('https://api.github.com/repos/{github_owner}/{github_repo}/actions/workflows/json_to_html_launcher.yml/dispatches', {{
                        method: 'POST',
                        headers: {{
                            'Authorization': `Bearer {github_token}`,
                            'Accept': 'application/vnd.github.v3+json'
                        }},
                        body: JSON.stringify({{
                            ref: 'main',
                            inputs: {{
                                wait_time: "40"
                            }}
                        }})
                    }});
                    return response.ok;
                }} catch (error) {{
                    showNotification(`Ошибка при отправке данных: ${{error}}`, 'error');
                    return false;
                }}
            }}

            async function collectData() {{
                const gameData = {{
                    player: document.getElementById('player').value,
                    game: htmlEncode(document.getElementById('search').value),
                    month: document.getElementById('month').value.padStart(2, '0'),
                    year: document.getElementById('year').value,
                    platform: document.getElementById('platform').value,
                    status: document.getElementById('status').value,
                    "co-op": document.getElementById('co-op').value.split('\\n').filter(line => htmlEncode(line.trim()))
                }};
                return gameData;
            }}

            async function saveWithData(gameData) {{
                if (!gameData.game) {{
                    alert('Пожалуйста, введите название игры');
                    return;
                }}

                try {{
                    const response = await fetch('https://api.github.com/repos/{github_owner}/{github_repo}/actions/workflows/json_editor.yml/dispatches', {{
                        method: 'POST',
                        headers: {{
                            'Authorization': `Bearer {github_token}`,
                            'Accept': 'application/vnd.github.v3+json'
                        }},
                        body: JSON.stringify({{
                            ref: 'main',
                            inputs: {{
                                add_walkthrough_data: JSON.stringify(gameData)
                            }}
                        }})
                    }});

                    if (response.ok) {{
                        const htmlGenSuccess = await trigger_html_generation();
                        showNotification('Данные успешно отправлены! Таблица обновится через пару минут.');
                        document.getElementById('search').value = '';
                        document.getElementById('platform').value = '';
                        document.getElementById('co-op').value = '';
                    }} else {{
                        const error = await response.json();
                        showNotification(`Ошибка: ${{error.message}}`, 'error');
                    }}
                }} catch (error) {{
                    showNotification(`Ошибка при отправке данных: ${{error}}`, 'error');
                }}
            }}

            async function duplicateCoopPlayer(gameData, player) {{
                if (gameData.player == player) {{
                    return null;
                }}
                let copy = {{ ...gameData }};
                for (let i = 0; i < copy["co-op"].length; i++) {{
                    if (copy["co-op"][i] == player) {{
                        copy["co-op"][i] = gameData.player;
                        copy.player = player;
                        return copy;
                    }}
                }}
                return null;
            }}

            async function saveData() {{
                const gameData = await collectData();
                await saveWithData(gameData);

                /*for (const type of ["T", "R", "P"]) {{
                    const dup = await duplicateCoopPlayer(gameData, type);
                    console.log(type)
                    console.log(dup)
                    if (dup) {{
                        await saveWithData(dup);
                    }}
                }}*/
            }}

            async function editWithData(gameData) {{
                if (!gameData.game) {{
                    alert('Пожалуйста, введите название игры');
                    return;
                }}

                const id = prompt('Введите ID для удаления:');
                if (!id) return;

                try {{
                    const response = await fetch('https://api.github.com/repos/{github_owner}/{github_repo}/actions/workflows/json_editor.yml/dispatches', {{
                        method: 'POST',
                        headers: {{
                            'Authorization': `Bearer {github_token}`,
                            'Accept': 'application/vnd.github.v3+json'
                        }},
                        body: JSON.stringify({{
                            ref: 'main',
                            inputs: {{
                                replace_walkthrough_data: JSON.stringify(gameData),
                                replace_walkthrough_id: id
                            }}
                        }})
                    }});
                    console.log(JSON.stringify(gameData))

                    if (response.ok) {{
                        const htmlGenSuccess = await trigger_html_generation();
                        showNotification('Данные успешно отправлены! Таблица обновится через пару минут.');
                        document.getElementById('search').value = '';
                        document.getElementById('platform').value = '';
                        document.getElementById('co-op').value = '';
                    }} else {{
                        const error = await response.json();
                        showNotification(`Ошибка: ${{error.message}}`, 'error');
                    }}
                }} catch (error) {{
                    showNotification(`Ошибка при отправке данных: ${{error}}`, 'error');
                }}
            }}

            async function editData() {{
                await editWithData(await collectData());
            }}

            async function deleteData() {{
                const id = prompt('Введите ID для удаления:');
                if (!id) return;

                const confirmDelete = confirm('Вы уверены, что хотите удалить данные с ID: ' + id + '?');
                if (!confirmDelete) return;

                try {{
                    const response = await fetch('https://api.github.com/repos/{github_owner}/{github_repo}/actions/workflows/json_editor.yml/dispatches', {{
                        method: 'POST',
                        headers: {{
                            'Authorization': `Bearer {github_token}`,
                            'Accept': 'application/vnd.github.v3+json'
                        }},
                        body: JSON.stringify({{
                            ref: 'main',
                            inputs: {{
                                delete_walkthrough_id: id
                            }}
                        }})
                    }});

                    if (response.ok) {{
                        const htmlGenSuccess = await trigger_html_generation();
                        showNotification('Данные успешно удалены! Таблица обновится через пару минут.');
                    }} else {{
                        const error = await response.json();
                        showNotification(`Ошибка: ${{error.message}}`, 'error');
                    }}
                }} catch (error) {{
                    showNotification(`Ошибка при удалении данных: ${{error}}`, 'error');
                }}
            }}

            function openSourceData() {{
                window.open('https://github.com/{github_owner}/{github_repo}/blob/json_data/estafeta_games_data.json', '_blank');
            }}

            function openTable() {{
                window.open('https://{github_owner}.github.io/{github_repo}', '_blank');
            }}

            function loginTwitch() {{
                window.location.href = '/auth/twitch';
            }}

            function logoutTwitch() {{
                window.location.href = '/logout';
            }}

            async function updateStreamInfo() {{
                const title = document.getElementById('stream-title').value;
                const game = document.getElementById('stream-game').value;
                const language = document.getElementById('stream-language').value;
                const tags = document.getElementById('stream-tags').value.split(',').map(tag => tag.trim()).filter(tag => tag);

                if (!title || !game) {{
                    showNotification('Пожалуйста, заполните название стрима и игры', 'error');
                    return;
                }}

                try {{
                    // First search for the game ID
                    const searchResponse = await fetch(`/search?query=${{encodeURIComponent(game)}}`);
                    const searchData = await searchResponse.json();
                    
                    if (!searchData || searchData.length === 0) {{
                        showNotification('Игра не найдена на Twitch', 'error');
                        return;
                    }}

                    const gameId = searchData[0].id;
                    
                    // Update stream info
                    const updateResponse = await fetch('/update_stream', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            title: title,
                            game_id: gameId,
                            broadcaster_language: language,
                            tags: tags
                        }})
                    }});

                    const result = await updateResponse.json();
                    
                    if (updateResponse.ok) {{
                        showNotification('Информация о стриме успешно обновлена!', 'success');
                    }} else {{
                        showNotification(`Ошибка: ${{result.detail || 'Неизвестная ошибка'}}`, 'error');
                    }}
                }} catch (error) {{
                    showNotification(`Ошибка при обновлении информации: ${{error}}`, 'error');
                }}
            }}

            function showNotification(message, type = 'success') {{
                const notification = document.getElementById('notification');
                notification.textContent = message;
                notification.className = `notification ${{type}}`;
                notification.classList.add('show');
                
                setTimeout(() => {{
                    notification.classList.remove('show');
                }}, 8000);
            }}
        </script>
        <div id="notification" class="notification"></div>
    </body>
    </html>
    """

@app.get("/search")
async def search(query: str):
    command = f"/root/twitch_cli/twitch api get 'search/categories?query={query}'"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    try:
        data = json.loads(result.stdout)
        return data['data']
    except json.JSONDecodeError:
        return {"data": []}

@app.post("/update_stream")
async def update_stream(request: Request, twitch_credentials: dict = Depends(get_twitch_credentials)):
    """Update stream information on Twitch"""
    if not twitch_credentials:
        return {"error": "Not authenticated with Twitch"}, 401
        
    data = await request.json()
    
    # Prepare the request to Twitch API
    url = f"{TWITCH_API_URL}/channels?broadcaster_id={twitch_credentials['user_id']}"
    headers = {
        'Authorization': f'Bearer {twitch_credentials["access_token"]}',
        'Client-Id': twitch_client_id,
        'Content-Type': 'application/json'
    }
    
    # Prepare the payload
    payload = {}
    if 'title' in data:
        payload['title'] = data['title']
    if 'game_id' in data:
        payload['game_id'] = data['game_id']
    if 'broadcaster_language' in data:
        payload['broadcaster_language'] = data['broadcaster_language']
    if 'tags' in data:
        payload['tags'] = data['tags']
    
    async with httpx.AsyncClient() as client:
        response = await client.patch(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return {"status": "success", "message": "Stream information updated successfully"}
        else:
            return {"error": f"Twitch API error: {response.status_code}", "details": response.text}, response.status_code

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(port))
