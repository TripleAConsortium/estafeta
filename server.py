from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
port = os.getenv('PORT')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    current_year = datetime.now().year
    current_month = datetime.now().month
    
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
            }}
            .suggestion-item:hover {{
                background-color: #f0f0f0;
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
        </div>

        <script>
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
                    div.innerText = item.name;
                    div.onclick = () => {{
                        document.getElementById('search').value = item.name;
                        suggestionsDiv.style.display = 'none';
                    }};
                    suggestionsDiv.appendChild(div);
                }});

                suggestionsDiv.style.display = data.length ? 'block' : 'none';
            }}
        </script>
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
