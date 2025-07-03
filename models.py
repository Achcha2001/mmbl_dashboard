# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80), unique=True, nullable=False)
    password   = db.Column(db.String(128), nullable=False)
    is_admin   = db.Column(db.Boolean, default=False)

class Upload(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    filename   = db.Column(db.String(256), nullable=False)
    uploaded_at= db.Column(db.DateTime, default=datetime.utcnow)
