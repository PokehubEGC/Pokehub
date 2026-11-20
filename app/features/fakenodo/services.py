from splent_framework.services.BaseService import BaseService

from app.features.fakenodo.repositories import FakenodoRepository


class FakenodoService(BaseService):
    def __init__(self):
        super().__init__(FakenodoRepository())
