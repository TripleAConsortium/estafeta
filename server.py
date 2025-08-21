from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from declaration import create_declaration_app
from twitch_admin_panel import create_twitch_app

load_dotenv()
port = os.getenv('PORT')

# Create main app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create sub-applications
declaration_app = create_declaration_app()
twitch_app = create_twitch_app()

# Add routes from both apps to main app
for route in declaration_app.routes:
    app.router.routes.append(route)

for route in twitch_app.routes:
    app.router.routes.append(route)

# Debug: print all routes
print("Available routes:")
for route in app.routes:
    print(f"  {route.methods} {route.path}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(port))
