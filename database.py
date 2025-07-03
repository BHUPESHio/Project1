from flask import Flask
from flask_pymongo import PyMongo


def ConnectDB(app:Flask):
    try:
        app.config["MONGO_URI"]="mongodb+srv://examplep489:bait1783@fitrackdb.o4yvman.mongodb.net/"
        mongo=PyMongo(app)
        return mongo
    except Exception as error:
        print(error)
