from flask import Flask, make_response, jsonify, request
from pymongo import MongoClient
from bson import ObjectId


app = Flask(__name__)


#Mongo connection
#client = MongoClient("mongodb://localhost:27017")
#db = client.bizDB
#businesses = db.biz







#This a welcome route
@app.route("/", methods=["GET"])
def index():
    return make_response("<h1>App for Assignment</h1>", 200)








if __name__== "__main__":
    app.run(debug=True)