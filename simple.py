# -*- coding: utf-8 -*-

from flask import Flask
from flask import render_template, request, session, redirect, url_for, escape, flash
from flask.ext.pymongo import PyMongo
from weibo import APIClient
import simplejson as json
import re


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
        screen_name = screen_name.strip("@ ")
        try:
            target_user = client.users__show(screen_name=screen_name)
        except:
            flash(u"您输入的昵称不存在,请重新输入")
            return redirect(url_for('index'))
        try:
            statuses = client.statuses__user_timeline(uid=target_user["id"], count=10)["statuses"]
        except:
            statuses = []
        return render_template('weibolist.html', btnuserpicvisible='inline', btnloginvisible='none', user=user, statuses=statuses)

    return redirect(url_for('login'))


def dps_graph(simple_graph, relation_links, repost_users, now, now_node):
    if now_node == None:
        simple_graph = {"name": repost_users[0]["name"], "id": repost_users[0]["id"], "repost_users": []}
        now_node = simple_graph["repost_users"]
    for link in relation_links[now]:
        now_node.append({"name": repost_users[link["index"]]["name"], "id": repost_users[link["index"]]["id"], "repost_users": []})
        simple_graph, relation_links, repost_users = dps_graph(simple_graph, relation_links, repost_users, link["index"], now_node[-1]["repost_users"])

    return simple_graph, relation_links, repost_users


@app.route('/graph')
def graph():
    if "uid" in session:
        user = mongo.db.users.find_one_or_404({"uid": session["uid"]})
        client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
        client.set_access_token(user["access_token"], user["expires_in"])

        id = request.args.get('id', '')
        try:
            reposts = client.statuses__repost_timeline(id=int(id), count=200)
            source_user = client.statuses__show(id=int(id))["user"]
        except:
            flash(u"获取微博的转发信息失败")
            return redirect(url_for('index'))

        #print json.dumps(json.loads(json.dumps(reposts)), indent=4)
        #        for username in re.findall(r'//@(\S+?):', text):
        total_number = reposts["total_number"]
        repost_users = []
        repost_users.append({"name": source_user["name"], "id": source_user["id"]})
        relation_links = [[]]
        """
        print total_number
        print source_user["name"]
        print source_user["id"]
        """

        reposts["reposts"].reverse()
        for index in xrange(len(reposts["reposts"])):
            repost = reposts["reposts"][index]
            """
            print "<-------------------------------------------------------->"
            print repost["text"]
            print repost["user"]["id"]
            print repost["user"]["screen_name"]
            """
            repost_userinfo = {"id": repost["user"]["id"], "name": repost["user"]["screen_name"]}
            repost_info = {"index": index + 1}

            relation_links.append([])

            repost_user = re.findall(r'//@(\S+?):', repost["text"])
            if len(repost_user):
                flag = True
                temp_len = len(repost_users)
                for i in xrange(temp_len):
                    if repost_users[temp_len - 1 - i]["name"] == repost_user[0]:
#                        print repost['text']
                        flag = False
                        relation_links[temp_len - 1 - i].append(repost_info)
                        break
                if not flag:
                    repost_users.append(repost_userinfo)
                    continue

            relation_links[0].append(repost_info)
            repost_users.append(repost_userinfo)
        """
        print "relation_links", json.dumps(relation_links, indent=4)
        print "repost_users", json.dumps(repost_users, indent=4)
        """

        simple_graph = {}
        simple_graph, relation_links, repost_users = dps_graph(simple_graph, relation_links, repost_users, 0, None)
        print json.dumps(simple_graph, indent=4)

        return json.dumps(simple_graph, indent=4)

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
