import uuid

from splent_framework.services.BaseService import BaseService

from app.features.fakenodo.repositories import FakenodoRepository


class FakenodoService(BaseService):
    def __init__(self):
        super().__init__(FakenodoRepository())

    def get_all(self):
        return self.repository.get_all()

    def get_or_404(self, deposition_id: int):
        return self.repository.get_or_404(deposition_id)

    def delete(self, deposition_id: int):
        self.get_or_404(deposition_id)
        return self.repository.delete(deposition_id)

    def publish(self, deposition_id: int):
        deposition = self.get_or_404(deposition_id)
        conceptdoi = deposition.conceptdoi or f"10.5281/fakenodo.concept.{deposition.id}"
        if not deposition.doi or deposition.files_changed:
            unique_suffix = uuid.uuid4().hex[:6]
            doi = f"10.5281/fakenodo.{deposition.id}.{unique_suffix}"
        else:
            doi = deposition.doi
        return self.repository.update(
            deposition_id,
            doi=doi,
            conceptdoi=conceptdoi,
            status="published",
            files_changed=False,
        )

    def upload_file(self, deposition_id: int):
        self.get_or_404(deposition_id)
        self.repository.update(deposition_id, files_changed=True)
