from app import db


class Fakenodo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doi = db.Column(db.String(50), nullable=False, unique=True)

    def __repr__(self):
        return f"Fakenodo<{self.id}>"
