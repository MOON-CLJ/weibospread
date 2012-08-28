# -*- coding: utf-8 -*-

from flask import Flask
from flask import render_template, request, session, redirect, url_for, flash, jsonify
from flask.ext.pymongo import PyMongo
from weibo import APIClient
import simplejson as json
import re
from gexf import Gexf
from lxml import etree
from gen import Tree
import buchheim
import math
import random

app = Flask(__name__)
mongo = PyMongo(app)
APP_KEY = '1966311272'
APP_SECRET = '57d36e0eaef033593f4bb6f745a67c5f'
CALLBACK_URL = 'http://127.0.0.1:5000/callback'


@app.route('/')
def index():
    if "uid" in session:
        screen_name = session["screen_name"]
        profile_image_url = session["profile_image_url"]
        return render_template('simple.html', btnuserpicvisible='inline', btnloginvisible='none', screen_name=screen_name, profile_image_url=profile_image_url)

    return redirect(url_for('login'))


@app.route('/search')
def search():
    if "uid" in session:
        user = mongo.db.users.find_one_or_404({"uid": session["uid"]})
        client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
        client.set_access_token(user["access_token"], user["expires_in"])

        screen_name = request.args.get('q', '')
        screen_name = screen_name.strip("@ \r\n\t")
        try:
            target_user = client.users__show(screen_name=screen_name)
        except:
            flash(u"您输入的昵称不存在,请重新输入")
            return redirect(url_for('index'))
        try:
            statuses = client.statuses__user_timeline(uid=target_user["id"], count=50)["statuses"]
        except:
            statuses = []

        screen_name = session["screen_name"]
        profile_image_url = session["profile_image_url"]
        return render_template('weibolist.html', btnuserpicvisible='inline', btnloginvisible='none', screen_name=screen_name, profile_image_url=profile_image_url, statuses=statuses)

    return redirect(url_for('login'))


def add_node(drawtree, graph):
    length = len(drawtree.children)
    size = math.log((math.pow(length, 0.3) + math.sqrt(4)), 4)
    b, r, g = "0", "179", "0"
    if length > 3:
        b = str(random.randint(0, 255))
        r = str(random.randint(100, 255))
        g = str(random.randint(0, 255))

    graph.addNode(drawtree.tree.wid, drawtree.tree.node,
            b=b, r=r, g=g, x=str(drawtree.x), y=str(drawtree.y * 10), z="0.0",
            size=str(size))
    for child in drawtree.children:
        add_node(child, graph)


@app.route('/status')
def status():

    user = mongo.db.users.find_one_or_404({"uid": session["uid"]})
    client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
    client.set_access_token(user["access_token"], user["expires_in"])

    id = request.args.get('id', '')
    try:
        source_user = client.statuses__show(id=int(id))["user"]
        reposts = client.statuses__repost_timeline(id=int(id), count=200)
        total_number = reposts["total_number"]
        print "expect:", total_number
        reposts = reposts["reposts"]
        if total_number > 200:
            for i in xrange(total_number / 200):
                print "more about", id, "page", i + 2
                more_reposts = client.statuses__repost_timeline(id=int(id), count=200, page=i + 2)
                reposts.extend(more_reposts["reposts"])
    except:
        flash(u"获取微博的转发信息失败")

    print "actual:", len(reposts)

    #root
    tree_nodes = []
    tree_nodes.append(Tree(source_user["name"], int(id)))

    for repost in reposts[::-1]:
        try:
            tree_nodes.append(Tree(repost["user"]["screen_name"], repost["id"]))
        except:
            print "weibo deleted"
            continue

        repost_users = re.findall(r'//@(\S+?):', repost["text"])
        if len(repost_users):
            flag = True
            for node in tree_nodes[::-1]:
                if node.node == repost_users[0]:
                    node.append_child(tree_nodes[-1])
                    flag = False
                    break

            if flag:
                tree_nodes[0].append_child(tree_nodes[-1])
        else:
            tree_nodes[0].append_child(tree_nodes[-1])

    dt = buchheim.buchheim(tree_nodes[0])

    gexf = Gexf("MOON_CLJ", "haha")
    graph = gexf.addGraph("directed", "static", "weibo graph")
    graph.addNodeAttribute("Authority", type="float", force_id="Authority")
    graph.addNodeAttribute("Hub", type="float", force_id="hub")
    add_node(dt, graph)

    #node.addAttribute("Authority", "1.1")

    return etree.tostring(gexf.getXML(), pretty_print=True, encoding='utf-8', xml_declaration=True)

#    print json.dumps(json.loads(json.dumps(reposts)), indent=4)


@app.route('/graph')
def graph():
    if "uid" in session:
        id = request.args.get('id', '')

        screen_name = session["screen_name"]
        profile_image_url = session["profile_image_url"]
        return render_template('graph.html', btnuserpicvisible='inline', btnloginvisible='none', screen_name=screen_name, profile_image_url=profile_image_url, id=id)

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
        session['screen_name'] = screen_name
        session["profile_image_url"] = profile_image_url
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
    app.run(host='0.0.0.0')
