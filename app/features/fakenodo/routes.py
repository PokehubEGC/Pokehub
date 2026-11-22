from flask import jsonify, render_template

from app.features.fakenodo import fakenodo_bp
from app.features.fakenodo.models import Fakenodo
from app.features.fakenodo.services import FakenodoService

fakenodo_service = FakenodoService()


@fakenodo_bp.route("/fakenodo", methods=["GET"])
def index():
    return render_template("fakenodo/index.html")


@fakenodo_bp.route("/fakenodo/<int:deposition_id>", methods=["GET"])
def get_deposition_by_id(deposition_id) -> Fakenodo:
    deposition = fakenodo_service.get_or_404(deposition_id)
    return (jsonify({"id": deposition.id, "doi": deposition.doi}), 200)
