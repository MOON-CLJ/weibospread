# -*- coding: utf-8 -*-

from flask import Flask
from flask import render_template, request, session, redirect, url_for, escape, flash
from flask.ext.pymongo import PyMongo
from weibo import APIClient
import simplejson as json


app = Flask(__name__)
mongo = PyMongo(app)
APP_KEY = '1966311272'
APP_SECRET = '57d36e0eaef033593f4bb6f745a67c5f'
CALLBACK_URL = 'http://127.0.0.1:5000/callback'


@app.route('/')
def index():
    if "uid" in session:
        user = mongo.db.users.find_one_or_404({"uid": session["uid"]})
        return render_template('simple.html', btnuserpicvisible='inline', btnloginvisible='none', user=user)

    return redirect(url_for('login'))


@app.route('/search')
def search():
    if "uid" in session:
        user = mongo.db.users.find_one_or_404({"uid": session["uid"]})
        client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
        client.set_access_token(user["access_token"], user["expires_in"])

        screen_name = request.args.get('q', '')
        screen_name = screen_name.lstrip("@")
        try:
            target_user = client.users__show(screen_name=screen_name)
        except:
            flash(u"您输入的昵称不存在,请重新输入")
            return redirect(url_for('index'))
        try:
            statuses = client.statuses__user_timeline(uid=target_user["id"], count=10)["statuses"]
        except:
            statuses = []
        #return json.dumps(statuses)
        return render_template('weibolist.html', btnuserpicvisible='inline', btnloginvisible='none', user=user, statuses=statuses)

    return redirect(url_for('login'))


@app.route('/callback')
def callback():
    code = request.args.get('code', '')
    client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
    try:
        r = client.request_access_token(code)
        access_token = r.access_token
        expires_in = r.expires_in
        # TODO: 在此可保存access token
        client.set_access_token(access_token, expires_in)
    except:
        flash(u'微博登录没有成功')
        return redirect(url_for('login'))

    try:
        uid = client.account__get_uid()['uid']
        userinfo = client.get.users__show(uid=uid)
        screen_name = userinfo["screen_name"]
        profile_image_url = userinfo["profile_image_url"]
        mongo.db.users.update({"uid": str(uid)}, {"$set": {"uid": str(uid), "access_token": access_token, "expires_in": expires_in, "screen_name": screen_name, "profile_image_url": profile_image_url}}, upsert=True, safe=True)
        session['uid'] = str(uid)
        return redirect(url_for('index'))
    except Exception:
        flash(u'获取用户微博信息没有成功')
        return redirect(url_for('login'))


@app.route('/login', methods=['GET'])
def login():
    client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
    url = client.get_authorize_url()
    flash(u'请用新浪微博登录')
    return render_template('simple.html', btnuserpicvisible='none', btnloginvisible='inline', url=url)


app.secret_key = 'youknowwhat,iamsocute'
if __name__ == '__main__':
    app.debug = True
    app.run()
