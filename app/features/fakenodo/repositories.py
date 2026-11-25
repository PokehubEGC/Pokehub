from splent_framework.repositories.BaseRepository import BaseRepository

from app.features.fakenodo.models import Deposition


class FakenodoRepository(BaseRepository):
    def __init__(self):
        super().__init__(Deposition)

    def get_all(self):
        return self.model.query.all()
