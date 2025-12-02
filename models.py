from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.schema import UniqueConstraint
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    votes = db.relationship("Vote", backref="user", cascade="all,delete")

class Poll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(300), nullable=False)
    options = db.relationship("PollOption", backref="poll", cascade="all,delete")
    votes = db.relationship("Vote", backref="poll", cascade="all,delete")
    # start_time and end_time control poll lifetime (UTC)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)

    def is_active(self):
        """Return True if now (UTC) is within poll window (inclusive)."""
        now = datetime.utcnow()
        if self.start_time and now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        return True

class PollOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("poll.id"))
    text = db.Column(db.String(200))
    votes = db.relationship("Vote", backref="option", cascade="all,delete")

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("poll.id"))
    option_id = db.Column(db.Integer, db.ForeignKey("poll_option.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    encrypted_vote = db.Column(db.LargeBinary)
    ip_address = db.Column(db.String(50))

    __table_args__ = (UniqueConstraint("poll_id", "user_id", name="unique_user_vote"),)