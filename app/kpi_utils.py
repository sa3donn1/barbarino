from datetime import datetime, timedelta
from models import db, Barber, Haircut, Client
from sqlalchemy import func, and_, case
from sqlalchemy.orm import aliased


def get_barbers_overview():
    """
    Returns rows with:
      barber_id,
      barber_name,
      total_clients,
      total_haircuts (the total number of Haircut rows for this barber)
    """
    query = (
        db.session.query(
            Barber.id.label("barber_id"),
            Barber.name.label("barber_name"),
            func.count(Client.id.distinct()).label("total_clients"),
            func.count(Haircut.id).label("total_haircuts")
        )
        .outerjoin(Client, Client.barber_id == Barber.id)
        .outerjoin(Haircut, Haircut.barber_id == Barber.id)
        .group_by(Barber.id, Barber.name)
    )
    return query.all()
