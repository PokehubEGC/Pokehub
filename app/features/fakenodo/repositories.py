from app.features.fakenodo.models import Fakenodo
from splent_framework.repositories.BaseRepository import BaseRepository


class FakenodoRepository(BaseRepository):
    def __init__(self):
        super().__init__(Fakenodo)
