from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy 
from pymongo import MongoClient
from bson.objectid import ObjectId
from elasticsearch import Elasticsearch
from bson import json_util
import certifi

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://sql9226142:2AaSYlHJVz@sql9.freemysqlhosting.net/sql9226142'
db = SQLAlchemy(app)

client = MongoClient('mongodb://sgruggy:root@ds013221.mlab.com:13221/enerknol')
mongodb = client['enerknol']
name_and_stats = mongodb['countries']

es = Elasticsearch(['https://search-enerknol-bv47orjv3nd23ehdxwy275gl2u.us-east-2.es.amazonaws.com'])

# for player in name_and_stats.find():
#     if player['_id']:
#         player['mongoId'] = str(player['_id'])
#         player.pop('_id', None)
#         es.index(index = "my_index", doc_type = "user", id = player['mongoId'], body = json_util.dumps(player))

# for hit in res['hits']['hits']:
#     hit['_id'] = hit['_source']['mongoId']
#     # print(hit)
# print(len(res['hits']['hits']))

class Users(db.Model):
    __tablename__ = 'Users'
    user_id = db.Column('user_id', db.Integer, primary_key = True)
    user_name = db.Column('user_name', db.Unicode)
    user_username = db.Column('user_username', db.Unicode)
    user_password = db.Column('user_password', db.Unicode)

    def __init__(self, user_id, user_name, user_username, user_password):
        self.user_id = user_id
        self.user_name = user_name
        self.user_username = user_username
        self.user_password = user_password

authenticated = False
currentUser = None

@app.route('/', methods = ['GET', 'POST'])
def hello_world():
    if not authenticated:
        return redirect('/login', code = 302)
    else:
        return render_template('index.html', user = currentUser.user_name)

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Users.query.filter_by(user_username = request.form['username']).first()
        if user is None:
            return "incorrect"
        else:
            global authenticated
            authenticated = True

            global currentUser
            currentUser = user
            return redirect('/');
    else:
        return render_template('login.html')

@app.route('/register', methods = ['GET', 'POST'])
def register(error = ''):
    if request.method == 'POST':
        if request.form['password'] == '' or request.form['username'] == '' or request.form['name'] == '':
            return render_template('register.html', error="Please enter all the fields")
        else:
            newUser = Users(None, request.form['name'], request.form['username'], request.form['password'])
            db.session.add(newUser)
            db.session.commit()
            return redirect('/login')
    else:
        return render_template('register.html')

@app.route('/search/page/<int:page>', methods = ['GET'])
def search(page):
    searchQuery = request.args['country']
    page = page or 1
    if searchQuery == '':
        res = es.search(index="my_index",
            size = 50, from_ = (page * 50),
            body={"query": {"match_all": {}}},
            preference = '_primary')
    else:
        res = es.search(index="my_index", size = 50, from_ = (page * 50), body={"query": {"match": {'country': searchQuery}}}, preference = '_primary')
    
    hasNext = int(res['hits']['total']) > (page+1) * 50
    return render_template('search.html', countries = res['hits']['hits'], start = 1 + (page-1) * 50, next = page+1, hasNext = hasNext)

@app.route('/search/<objectId>')
def mongoSearch(objectId):
    test = name_and_stats.find_one({'_id': ObjectId(objectId)})
    return render_template('item.html', city = test)

if __name__ == '__main__':
    app.run()