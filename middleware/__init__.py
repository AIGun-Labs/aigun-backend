from .request import Request, RequestMiddleware
from .security import SecurityData, SecurityStatus
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import settings



# Register middleware
def register_middleware(app: FastAPI):
    # Add custom middleware
    app.add_middleware(RequestMiddleware, public_key=open(settings.JWT_PUBLIC_FILE_PATH).read())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )