from app.features.fakenodo.repositories import FakenodoRepository
from splent_framework.services.BaseService import BaseService


class FakenodoService(BaseService):
    def __init__(self):
        super().__init__(FakenodoRepository())
