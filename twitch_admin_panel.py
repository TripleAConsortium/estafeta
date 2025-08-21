from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
from urllib.parse import urlencode
import subprocess
import json
import os
from dotenv import load_dotenv

load_dotenv()
twitch_client_id = os.getenv('TWITCH_CLIENT_ID')
twitch_client_secret = os.getenv('TWITCH_CLIENT_SECRET')
twitch_redirect_uri = os.getenv('TWITCH_REDIRECT_URI')

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

def create_twitch_app():
    app = FastAPI()

    @app.get("/twitch_admin", response_class=HTMLResponse)
    async def twitch_admin_panel(request: Request):
        # Check if user is logged in to Twitch
        twitch_credentials = await get_twitch_credentials(request)
        is_twitch_logged_in = twitch_credentials is not None
        twitch_user_name = request.cookies.get("twitch_user_name", "")
        
        twitch_section = ""
        if is_twitch_logged_in:
            twitch_section = f"""
            <div class="form-container">
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
                <div class="button-group">
                    <button onclick="updateStreamInfo()">Update Stream Info</button>
                    <button class="delete-button" onclick="logoutTwitch()">Logout from Twitch</button>
                    <button class="open-source-button" onclick="goBack()">← Back to Main</button>
                </div>
            </div>
            """
        else:
            twitch_section = """
            <div class="form-container">
                <h2>Twitch Integration</h2>
                <div class="button-group">
                    <button class="twitch-button" onclick="loginTwitch()">Login with Twitch</button>
                    <button class="open-source-button" onclick="goBack()">← Back to Main</button>
                </div>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Twitch Admin Panel</title>
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
            {twitch_section}

            <script>
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

                function loginTwitch() {{
                    window.location.href = '/auth/twitch';
                }}

                function logoutTwitch() {{
                    window.location.href = '/logout';
                }}

                function goBack() {{
                    window.location.href = '/';
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
            response = RedirectResponse("/twitch_admin")
            response.set_cookie("twitch_access_token", access_token, httponly=True, max_age=3600)
            response.set_cookie("twitch_refresh_token", refresh_token, httponly=True, max_age=2592000)  # 30 days
            response.set_cookie("twitch_user_id", user_info['id'], max_age=3600)
            response.set_cookie("twitch_user_login", user_info['login'], max_age=3600)
            response.set_cookie("twitch_user_name", user_info['display_name'], max_age=3600)
            
            return response

    @app.get("/logout")
    async def logout(response: Response):
        """Logout from Twitch"""
        response = RedirectResponse("/twitch_admin")
        response.delete_cookie("twitch_access_token")
        response.delete_cookie("twitch_refresh_token")
        response.delete_cookie("twitch_user_id")
        response.delete_cookie("twitch_user_login")
        response.delete_cookie("twitch_user_name")
        return response

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

    @app.get("/search")
    async def search(query: str):
        command = f"/root/twitch_cli/twitch api get 'search/categories?query={query}'"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        try:
            data = json.loads(result.stdout)
            return data['data']
        except json.JSONDecodeError:
            return {"data": []}

    return app