"""
Модуль для шаблона проекта FastAPI
"""

import re
from pathlib import Path
from typing import Optional

import pytz
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from fastapi_accelerator.db.dbsession import MainDatabaseManager
from fastapi_accelerator.exception import custom_http_exception_handler
from fastapi_accelerator.middleware import log_request_response


def base_pattern(
    app: FastAPI,
    routers: tuple[APIRouter, ...],
    timezone: pytz.timezone,
    cache_status: bool,
    debug: bool,
    base_dir: Path,
    database_manager: MainDatabaseManager,
    secret_key: str,
    origins: Optional[list] = None,
):
    """Паттерн построения проекта по умолчанию"""
    # Установка временной зоны для проекта
    app.state.TIMEZONE = timezone
    # Установить режим работы
    # Включает режим отладки. Используется в основном для разработки.
    app.debug = debug
    # Установить использования кеша
    app.state.CACHE_STATUS = cache_status
    # Менеджер для взаимодействия с БД
    app.state.DATABASE_MANAGER = database_manager
    # Секретный ключ
    app.state.SECRET_KEY = secret_key
    # Подключить middleware
    if app.debug:
        # Логировать время выполение API запроса
        app.middleware("http")(log_request_response)
    # Подключить обработчик ошибок
    app.exception_handler(StarletteHTTPException)(custom_http_exception_handler)
    # Брать версию из файла version.toml
    version = re.search(
        r'version=\"([^\"]+)"\n', (base_dir / "version.toml").read_text()
    ).group(1)
    app.version = version
    # Описание проекта
    app.description = (base_dir / "README.md").read_text().strip()

    # Подключение роутер
    if routers:
        app.openapi_tags = app.openapi_tags or []
        for router in routers:
            app.include_router(router)
            # Получить views из router
            if views := getattr(router, "views", None):
                # Добавить информацию в описание тегов
                app.openapi_tags.extend([view.openapi_tag for view in views])
        app.openapi_tags.append({"name": "common", "description": "Методы из common"})
    # Добавить CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],  # Список разрешённых источников
        allow_credentials=True,  # Разрешение на использование куков
        allow_methods=["*"],  # Разрешение всех методов (GET, POST и т.д.)
        allow_headers=["*"],  # Разрешение всех заголовков
    )

    # Добавить метод HealthCheck для API
    @app.get("/healthcheck", summary="Проверить состояние приложения", tags=["common"])
    async def healthcheck() -> HealthcheckResponse:
        return {"status": True, "version": version}


class HealthcheckResponse(BaseModel):
    status: bool
    version: str