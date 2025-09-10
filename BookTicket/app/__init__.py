from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
import cloudinary
from flask_login import LoginManager


app = Flask(__name__)

app.secret_key = 'your_secret_name'
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@your_MySQL_user/flight?charset=utf8mb4" % quote("your_password")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["NUMBER_ROWS"] = 6


db = SQLAlchemy(app)

cloudinary.config(
    cloud_name='your_cloud_name',
    api_key='your_api_key',
    api_secret='your_api_secret'
)

login = LoginManager(app)
