"""
FastAPI server for Guardian AI Companion
Handles user authentication, chat, and profile management
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from guardian.core.orchestrator.pulse_orchestrator import orchestrate
from guardian.imprint_zero_onboarding import ImprintZero
from guardian.core.user_manager import UserManager

# Initialize FastAPI app
app = FastAPI(title="Guardian AI Companion API")
security = HTTPBearer()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
user_manager = UserManager()
imprint_zero = ImprintZero()

# JWT Configuration
JWT_SECRET = "your-secret-key"  # In production, use secure environment variable
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


# Request/Response Models
class UserRegisterRequest(BaseModel):
    username: str
    password: str
    narrative_style: str
    communication_preferences: Dict[str, Any]
    accessibility_needs: Dict[str, Any]


class UserLoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    message: str
    is_onboarding: Optional[bool] = False


class UserSettingsUpdate(BaseModel):
    narrative_style: Optional[str]
    communication_preferences: Optional[Dict[str, Any]]
    accessibility_needs: Optional[Dict[str, Any]]


def create_jwt_token(user_id: int, username: str) -> str:
    """Create a JWT token for the user"""
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    return jwt.encode(
        {"user_id": user_id, "username": username, "exp": expiration},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Validate JWT token and return user information"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/api/register")
async def register(request: UserRegisterRequest):
    """Register a new user with Imprint Zero process"""
    result = imprint_zero.create_initial_profile(
        username=request.username,
        password=request.password,
        narrative_style=request.narrative_style,
        communication_preferences=request.communication_preferences,
        accessibility_needs=request.accessibility_needs,
    )

    if result["status"] != "success":
        raise HTTPException(status_code=400, detail=result["message"])

    # Create JWT token
    token = create_jwt_token(result["user_id"], result["username"])

    return {
        "status": "success",
        "token": token,
        "user": {"id": result["user_id"], "username": result["username"]},
    }


@app.post("/api/login")
async def login(request: UserLoginRequest):
    """Authenticate user and return JWT token"""
    result = user_manager.authenticate_user(request.username, request.password)

    if result["status"] != "success":
        raise HTTPException(status_code=401, detail=result["message"])

    token = create_jwt_token(result["user_id"], result["username"])

    return {
        "status": "success",
        "token": token,
        "user": {"id": result["user_id"], "username": result["username"]},
    }


@app.post("/api/chat")
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """Process chat message and return AI response"""
    try:
        if request.is_onboarding:
            return StreamingResponse(
                imprint_zero.process_onboarding_message(
                    current_user["user_id"], request.message
                ),
                media_type="text/event-stream",
            )

        # Regular chat processing
        profile = user_manager.get_user_profile(current_user["user_id"])

        command = {
            "action": "run_model",
            "params": {
                "prompt": request.message,
                "user_id": current_user["user_id"],
                "profile": profile.get("profile_data", {}),
            },
        }

        result = orchestrate(command)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {"status": "success", "message": result["response"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/imprint-zero")
async def imprint_zero_chat(
    request: ChatRequest, current_user: dict = Depends(get_current_user)
):
    """Process onboarding chat message and stream AI response"""
    try:

        async def generate_response():
            async for chunk in imprint_zero.process_onboarding_message(
                current_user["user_id"], request.message
            ):
                yield f"data: {chunk}\n\n"
                await asyncio.sleep(0.1)  # Small delay for natural feeling

        return StreamingResponse(generate_response(), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/settings")
async def get_user_settings(current_user: dict = Depends(get_current_user)):
    """Get user's current settings"""
    result = user_manager.get_user_profile(current_user["user_id"])

    if result["status"] != "success":
        raise HTTPException(status_code=404, detail=result["message"])

    return {
        "status": "success",
        "settings": {
            "narrative_style": result["profile_data"].get("narrative_style"),
            "communication_preferences": result["profile_data"].get(
                "communication_preferences", {}
            ),
            "accessibility_needs": result["profile_data"].get(
                "accessibility_needs", {}
            ),
        },
    }


@app.put("/api/user/settings")
async def update_user_settings(
    settings: UserSettingsUpdate, current_user: dict = Depends(get_current_user)
):
    """Update user's settings"""
    result = user_manager.update_user_profile(
        current_user["user_id"],
        {
            "profile_data": {
                "narrative_style": settings.narrative_style,
                "communication_preferences": settings.communication_preferences,
                "accessibility_needs": settings.accessibility_needs,
            }
        },
    )

    if result["status"] != "success":
        raise HTTPException(status_code=400, detail=result["message"])

    return {"status": "success", "message": "Settings updated successfully"}


# Mount static files
import os
from fastapi.staticfiles import StaticFiles

frontend_dir = os.path.join(os.path.dirname(__file__), "../../../frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
async def read_root():
    return FileResponse("frontend/index.html")


@app.get("/{path:path}")
async def catch_all(path: str):
    file_path = f"frontend/{path}"
    if Path(file_path).is_file():
        return FileResponse(file_path)
    # If the file doesn't exist, return index.html for client-side routing
    return FileResponse("frontend/index.html")


# Explicitly handle dashboard routes
@app.get("/dashboard-new")
async def dashboard_new():
    return FileResponse("frontend/dashboard-new.html")


@app.get("/dashboard")
async def dashboard():
    # Redirect old dashboard to new one
    return RedirectResponse(url="/dashboard-new.html", status_code=308)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
