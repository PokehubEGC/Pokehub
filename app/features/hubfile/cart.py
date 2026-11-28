from flask import session
from flask_login import current_user
from sqlalchemy.orm import joinedload

from app import db
from app.features.auth.models import User
from app.features.dataset.models import DataSet
from app.features.hubfile.models import Hubfile, ModelCartItem


class ModelCart:
    session_key = "model_cart"

    def files(self):
        query = Hubfile.query.options(joinedload(Hubfile.dataset).joinedload(DataSet.ds_meta_data))
        if current_user.is_authenticated:
            query = query.join(ModelCartItem).filter(ModelCartItem.user_id == current_user.id)
        else:
            ids = session.get(self.session_key, [])
            if not ids:
                return []
            query = query.filter(Hubfile.id.in_(ids))

        return [file for file in query.order_by(Hubfile.dataset_id, Hubfile.id) if file.is_readable_by(current_user)]

    def set_membership(self, file_id, in_cart):
        if not current_user.is_authenticated:
            ids = set(session.get(self.session_key, []))
            if in_cart:
                ids.add(file_id)
            else:
                ids.discard(file_id)
            session[self.session_key] = sorted(ids)
            return

        user_id = current_user.id
        # Serialize changes to this account's cart, including simultaneous adds.
        db.session.get(User, user_id, with_for_update=True)
        item = db.session.get(ModelCartItem, (user_id, file_id), with_for_update=True)
        if in_cart and item is None:
            db.session.add(ModelCartItem(user_id=user_id, file_id=file_id))
        elif not in_cart and item is not None:
            db.session.delete(item)
        db.session.commit()
