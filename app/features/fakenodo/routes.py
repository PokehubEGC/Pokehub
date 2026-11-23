from flask import jsonify, render_template, request

from app.features.fakenodo import fakenodo_bp
from app.features.fakenodo.services import FakenodoService

fakenodo_service = FakenodoService()


def _jsonify_deposition(deposition):
    return jsonify({"id": deposition.id, "doi": deposition.doi})


@fakenodo_bp.route("/fakenodo", methods=["GET"])
def index():
    return render_template("fakenodo/index.html")


@fakenodo_bp.route("/fakenodo/<int:deposition_id>", methods=["GET"])
def get_deposition_by_id(deposition_id):
    deposition = fakenodo_service.get_or_404(deposition_id)
    return _jsonify_deposition(deposition), 200


@fakenodo_bp.route("/fakenodo", methods=["POST"])
def create_deposition():
    """
    A request to create a deposition must include a dictionary for the metadata,
    even if it's empty. If it doesn't, the response status code must be 400.
    """
    try:
        request.get_json()
    except Exception as exc:
        return jsonify({"error": f"Error creating deposition: {str(exc)}"}), 400
    deposition = fakenodo_service.create(doi="fakenodo-DOI-1")
    return _jsonify_deposition(deposition), 201
