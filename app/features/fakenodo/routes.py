from flask import jsonify, request

from app.features.fakenodo import fakenodo_bp
from app.features.fakenodo.services import FakenodoService

fakenodo_service = FakenodoService()


def _serialize_deposition(deposition):
    return {
        "id": deposition.id,
        "doi": deposition.doi,
        "conceptdoi": deposition.conceptdoi,
        "status": deposition.status,
    }


def _jsonify_deposition(deposition):
    return jsonify(_serialize_deposition(deposition))


@fakenodo_bp.route("/fakenodo", methods=["GET"])
def list_depositions():
    depositions = fakenodo_service.get_all()
    return jsonify([_serialize_deposition(d) for d in depositions]), 200


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


@fakenodo_bp.route("/fakenodo/<int:deposition_id>/actions/publish", methods=["POST"])
def publish_deposition(deposition_id):
    deposition = fakenodo_service.publish(deposition_id)
    return _jsonify_deposition(deposition), 202


@fakenodo_bp.route("/fakenodo/<int:deposition_id>", methods=["DELETE"])
def delete_deposition(deposition_id):
    fakenodo_service.delete(deposition_id)
    return "", 204
