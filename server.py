from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.reg_routers import __routers__
from services.llm_agent import LLMManager
from services.smtp import EmailService
from core.config import Settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    llm_manager = LLMManager()
    llm_manager.initialize()

    smtp_manager = EmailService(
        smtp_server=app.state.settings.SMTP_SERVER,
        smtp_port=app.state.settings.SMTP_PORT,
        smtp_user=app.state.settings.SMTP_USERNAME,
        smtp_password=app.state.settings.SMTP_PASSWORD,
        sender_email=app.state.settings.SENDER_EMAIL,
    )
    smtp_manager.set_up_default_signature("signature.html")

    app.state.get_llm_client_invoke = llm_manager
    app.state.get_smtp_client_invoke = smtp_manager

    yield


class Server:
    __slots__ = ["__app"]

    def __init__(self):

        self.__app = FastAPI(
            lifespan=lifespan, title="Knowledge Graph Server", debug=True
        )
        self.__app.state.settings = Settings()
        # configure routers
        self.include_routers(__routers__)

    @property
    def app(self) -> FastAPI:
        return self.__app

    def include_routers(self, routers: list):
        for router in routers:
            self.__app.include_router(router)
