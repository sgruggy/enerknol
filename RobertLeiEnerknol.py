from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy 
from pymongo import MongoClient
from bson.objectid import ObjectId      #This is for translating a string to a mongo ObjectId
from elasticsearch import Elasticsearch
from bson import json_util              #This was used to create ElasticSearch indexes
import re
import certifi                          #This is required for connecting to AWS

'''
Configuring MySQL connection using a free mysql hosting site
'''
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://sql9226142:2AaSYlHJVz@sql9.freemysqlhosting.net/sql9226142'
db = SQLAlchemy(app)

'''
Configuring MongoDB Connection using a free MongoDB hosting site
'''
client = MongoClient('mongodb://sgruggy:root@ds013221.mlab.com:13221/enerknol')
mongodb = client['enerknol']
name_and_stats = mongodb['countries']


'''
Configuring ElasticSearch using AWS
Has around 50,000 documents using a public cities json data file

This only works locally. When I try to access it on PythonAnywhere, it refused connection
I think this is because ElasticSearch is configured to only accept localhost connections, and
there are settings you can change on the client itself to acccept remote connections.
Since I do not have the actual ElasticSearch engine itself, I have no way to access this and
I do not know how to do so otherwise. 

I also tried Heroku's Bonsai service using this setup:

bonsai = 'https://iws348lmlq:vp4rbh6cmo@enerknol-7245164056.us-east-1.bonsaisearch.net'
auth = re.search('https\:\/\/(.*)\@', bonsai).group(1).split(':')
host = bonsai.replace('https://%s:%s@' % (auth[0], auth[1]), '')

es_header = [{
  'host': host,
  'port': 443,
  'use_ssl': True,
  'http_auth': (auth[0],auth[1])
}]

es = Elasticsearch(es_header)

Again, this only worked locally, so I was out of ideas.
'''
es = Elasticsearch(['https://search-enerknol-bv47orjv3nd23ehdxwy275gl2u.us-east-2.es.amazonaws.com'])

'''
I used this to dump the MongoDB collection into an ES Index
for player in name_and_stats.find():
    if player['_id']:
        player['mongoId'] = str(player['_id'])
        player.pop('_id', None)
        es.index(index = "my_index", 
            doc_type = "user", 
            id = player['mongoId'], 
            body = json_util.dumps(player))
'''

'''
This is the ORM model used to communicate with the MySQL databse
'''
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

'''
This app has soft authentication.
If the user isn't authenticated, he/she will be redirected to the login page from the homepage
Once authenticated, the currentUser will be populated with the User object
Would never use in production, but it was good for testing
'''
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
            return render_template('login.html', error = "Username/Password does not exist in database")
        else:
            global authenticated
            authenticated = True

            global currentUser
            currentUser = user
            return redirect('/');
    else:
        return render_template('login.html', error = "")

@app.route('/register', methods = ['GET', 'POST'])
def register(error = ''):
    if request.method == 'POST':
        #If fields are empty
        if request.form['password'] == '' or request.form['username'] == '' or request.form['name'] == '':
            return render_template('register.html', error="Please enter all the fields")
        else:
            #Creates the ORM model to add
            newUser = Users(None,
                request.form['name'],
                request.form['username'],
                request.form['password'])

            db.session.add(newUser)
            db.session.commit()
            return redirect('/login')
    else:
        return render_template('register.html')

'''
Pagination is done here, using a page size of 50 entries
Pages can be navigated using the "Next Page" button or modifying the URL
Going to a page that exceeds the number of the available documents will return no results
'''
@app.route('/search/page/<int:page>', methods = ['GET'])
def search(page):
    searchQuery = request.args['country']
    page = page or 1
    if searchQuery == '':
        #If blank search, return all
        res = es.search(index="my_index",
            size = 50, from_ = (page * 50),
            body={"query": {"match_all": {}}},
            preference = '_primary')
    else:
        res = es.search(index="my_index", size = 50, from_ = (page * 50), body={"query": {"match": {'country': searchQuery}}}, preference = '_primary')

    #Checking the total to see if there are more pages to display
    hasNextPage = int(res['hits']['total']) > (page+1) * 50
    return render_template('search.html', countries = res['hits']['hits'], start = 1 + (page-1) * 50, next = page+1, hasNext = hasNextPage)

'''
Clicking the city anchor will take you to this page
Shows a mongo info page for the mongo document object clicked
'''
@app.route('/search/<objectId>')
def mongoSearch(objectId):
    city = name_and_stats.find_one({'_id': ObjectId(objectId)})
    return render_template('item.html', city = city)

if __name__ == '__main__':
    app.run()