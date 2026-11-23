from app import db


class Deposition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doi = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"Deposition<{self.id}>"
