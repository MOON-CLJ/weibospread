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
import base62

app = Flask(__name__)
mongo = PyMongo(app)
"""
#prod
APP_KEY = '4131380600'
APP_SECRET = 'df544af4a9e30abe16e715cb4d0be423'
CALLBACK_URL = 'http://idec.buaa.edu.cn:8080/callback'
"""
#dev
APP_KEY = '1966311272'
APP_SECRET = '57d36e0eaef033593f4bb6f745a67c5f'
CALLBACK_URL = 'http://127.0.0.1:8080/callback'


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


class Count:
    def __init__(self, count=0):
        self.count = count


def add_node_edge(drawtree, graph, ct, parent=None, max_width=0):
    length = len(drawtree.children)
    size = math.log((math.pow(length, 0.3) + math.sqrt(4)), 4)
    b, r, g = "217", "254", "240"
    if length > 6:
        b = str(random.randint(0, 255))
        r = str(random.randint(100, 255))
        g = str(random.randint(0, 255))

    scale_y = max_width / 200 + 1
    node = graph.addNode(drawtree.tree.wid, drawtree.tree.node,
                b=b, r=r, g=g, x=str(drawtree.x), y=str(drawtree.y * scale_y * 10), z="0.0",
                size=str(size))
    node.addAttribute("img_url", drawtree.tree.img_url)
    node.addAttribute("name", drawtree.tree.node)
    node.addAttribute("repost_num", str(length))
    node.addAttribute("weibo_url", drawtree.tree.weibo_url)

    if parent is not None:
        ct.count += 1
        graph.addEdge(ct.count, str(drawtree.tree.wid), str(parent.tree.wid))

    for child in drawtree.children:
        add_node_edge(child, graph, ct, drawtree, max_width)


@app.route('/status')
def status():

    user = mongo.db.users.find_one_or_404({"uid": session["uid"]})
    client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
    client.set_access_token(user["access_token"], user["expires_in"])

    id = request.args.get('id', '')
    try:
        source_weibo = client.statuses__show(id=int(id))
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
        return ""

    print "actual:", len(reposts)

    #root
    tree_nodes = []
    node = source_weibo["user"]["name"]
    img_url = source_weibo["user"]["profile_image_url"]
    weibo_url = "http://weibo.com/" + \
        str(source_weibo["user"]["id"]) + \
        "/" + base62.mid_to_str(source_weibo["mid"])

    tree_nodes.append(Tree(node, int(id), img_url, weibo_url))

    for repost in reposts[::-1]:
        try:
            node = repost["user"]["screen_name"]
            wid = repost["id"]
            img_url = repost["user"]["profile_image_url"]

            weibo_url = "http://weibo.com/" + \
                str(repost["user"]["id"]) + \
                "/" + base62.mid_to_str(repost["mid"])
            tree_nodes.append(Tree(node, wid, img_url, weibo_url))
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

    dt, max_width = buchheim.buchheim(tree_nodes[0])

    gexf = Gexf("MOON_CLJ", "haha")
    graph = gexf.addGraph("directed", "static", "weibo graph")
    graph.addNodeAttribute("img_url", type="URI", force_id="img_url")
    graph.addNodeAttribute("name", type="string", force_id="name")
    graph.addNodeAttribute("repost_num", type="integer", force_id="repost_num")
    graph.addNodeAttribute("weibo_url", type="URI", force_id="weibo_url")
    add_node_edge(dt, graph, Count(), max_width=max_width)

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
    app.run(host='0.0.0.0', port=8080)
