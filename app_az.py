#!/usr/bin/python
from flask import Flask, render_template, flash, request,Response
from googletrans import Translator
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField,RadioField,HiddenField
import sqlite3
import numpy as np
from functools import wraps
import re
from flask import g
import wptools
 
# App config.
DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = '7d441f27d441f27567d441f2b6176a'
DATABASE = 'db_itc_upd.db'
TABLE = "italian"
wordlist = ['agenzia','informazione','quotidiano','stampa','blog' ]
USERNAME = 'astrazeneca'
PASSWORD = 'astrazeneca'
HOST = '127.0.0.1'
PORT = 8080

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == USERNAME and password == PASSWORD

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated
    

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close() 

def query_db(query, args=(), one=False, commit = False):
    db = get_db()
    cur = db.execute(query, args)
    rv = cur.fetchall()
    
    if(commit):
        db.commit()
    cur.close()
    
    return rv[0] if rv else None

def getTitles(site,url_content):
    allRes = [""]

    if(url_content):
        url_content = url_content.replace("www.","")
        url_content = url_content.replace("http://","")
        allRes =[""]
        for result in site.search(url_content):
            print(result["title"])
            allRes.append(result["title"])
    return allRes[0]

def getSiteDescription(title):
    candidate = wptools.page(title,silent=True).get_query()

    return candidate.extext.split("\n")[0]
 
def getScore(description,following_count,followers_count,tweet_count):
    ## get  a score for a user (higher most likely press)
    words = wordlist
    rr = []
    for r in words:
        rr.append(".*%s.*"%(r))
    rex = "|".join(rr)
    score = 0
    if(len(description) > 40):
        score += 1

    score += np.log10(int(followers_count) +1)
    score = "%.1f"%(score*0.5)
    
    if(re.match(rex,description.lower())):
        score = float(score)
        score += 5 
    return float(score)
    
    
 
 
class ReusableForm(Form):
    org = RadioField('org', choices =['press','user', 'undef'])
    hid = HiddenField('org_id')

 
 
@app.route("/", methods=['GET', 'POST'])
@requires_auth
def index():
    
    if( request.args.get('language')):
        TABLE = request.args.get('language')
    else:
        TABLE = 'italian'
        
    form = ReusableForm(request.form)
    translator = Translator()

    query0 = "SELECT count(id) FROM %s WHERE user_classification <> ?"%(TABLE)
    
    aa = (-1,)
    results0 = query_db(query0, aa, True)

    classified_num = results0[0] 
    
    
    query = "SELECT id,description,followers_count,following_count,location,tweet_count,name,user_classification, AZ_counts FROM %s  ORDER BY RANDOM() LIMIT 1;"%(TABLE)
    
    results = query_db(query)
    
    
    iddi = results[0]
    hidden_id = iddi
    description = results[1]
    if(TABLE != 'english'):
        description_trans = translator.translate(description, dest='en') ## added translation
        description_trans_text = description_trans.text
    else:
        description_trans_text = " ...  "
    followers_count = results[2]
    following_count = results[3]
    location = results[4]
    tweet_count = results[5]
    name = results[6]
    
    checkd = results[7]
    AZ_counts = results[8]
    score = getScore(description,following_count,followers_count,tweet_count)

    if request.method == 'POST':

        org=request.form['org']
        hid = request.form['org_id']

        
        sql = "UPDATE %s SET user_classification=? WHERE id = ?"%(TABLE)
        aa = (org,hid)
        results = query_db(sql, aa, True,True)


        query0 = "SELECT count(id) FROM %s WHERE user_classification <> ?"%(TABLE)
    
        aa = (-1,)
        results0 = query_db(query0, aa, True)

        classified_num = results0[0] 

        
        if org :
            # Save the comment here.
            flash('Saved ' + org)
        else:
            flash('Error: All the form fields are required. ')
 

    return render_template('index.html', testo = description, translated = description_trans_text, language = TABLE.capitalize(),
                    hidden_id = iddi, score = score, checkd = checkd, 
                    ourl = 'url', followers_count  = followers_count,
                    following_count =  following_count ,
                    tweet_count = tweet_count,
                    AZ_counts = AZ_counts, name=name,
                    classified_num = classified_num, form=form)
 
if __name__ == "__main__":
    app.run(host=HOST, port = PORT)
