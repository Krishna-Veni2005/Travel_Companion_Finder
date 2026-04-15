from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

# Friendship model to track friendships
class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', foreign_keys=[user_id], backref='user_friends')
    friend = db.relationship('User', foreign_keys=[friend_id])

    def __repr__(self):
        return f'<Friendship {self.user_id} - {self.friend_id}>'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(15))
    gender = db.Column(db.String(10))
    dob = db.Column(db.Date)
    destination = db.Column(db.String(150))
    travel_date = db.Column(db.Date)

    # Relationship to get the list of friends (for the user)
    friends = db.relationship('User', secondary='friendship', 
                              primaryjoin='Friendship.user_id == User.id',
                              secondaryjoin='Friendship.friend_id == User.id',
                              backref='friend_of')
