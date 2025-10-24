import asyncio
import time
from fastapi import FastAPI, Depends
from app.dependencies import request_init
from middleware.request import Request
from utils.status_checker import status_checker
from views.render import Text
from data.logger import create_logger





