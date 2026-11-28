from app import db


class Deposition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doi = db.Column(db.String(50), nullable=True)
    conceptdoi = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="draft")
    files_changed = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"Deposition<{self.id}>"
