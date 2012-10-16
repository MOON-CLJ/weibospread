# -*- coding: utf-8 -*-

from flask import Flask
from flask import render_template, request, session, redirect, url_for, flash
from flask.ext.pymongo import PyMongo
from weibo import Client
from gexf import Gexf
from lxml import etree
from gen import Tree
from utils4scrapy.weibo2db import Weibo2Db
from utils4scrapy.utils import load_reposts
from utils4scrapy import base62
import buchheim
import math
import random
import time
import redis
import simplejson as json
import re


app = Flask(__name__)
mongo = PyMongo(app)
weibo2db = Weibo2Db()
r = redis.Redis('localhost', 6379)

#prod
APP_KEY = '4131380600'
APP_SECRET = 'df544af4a9e30abe16e715cb4d0be423'
CALLBACK_URL = 'http://idec.buaa.edu.cn:8080/callback'


def login_user(session):
    if 'uid' in session:
        user = mongo.db.users.find_one_or_404({"uid": session["uid"]})
        if user["expires_in"] > time.time():
            return user
    return None


@app.route('/')
def index():
    if login_user(session):
        screen_name = session["screen_name"]
        profile_image_url = session["profile_image_url"]
        return render_template('simple.html', btnuserpicvisible='inline',
                               btnloginvisible='none', screen_name=screen_name, profile_image_url=profile_image_url)

    return redirect(url_for('login'))


@app.route('/search')
def search():
    user = login_user(session)
    if user:
        client = Client(APP_KEY, APP_SECRET, CALLBACK_URL)
        client.set_token(user["access_token"])

        t = request.args.get('t', '')
        q = request.args.get('q', '')
        p = request.args.get('p', 1)
        u = request.args.get('u', 0)

        q = q.strip("@ \r\n\t")
        t = t.strip("@ \r\n\t")
        p = int(p)

        if t != '':
            retry = 0
            page = p
            n_page = p + 3
            t_statuses = []
            tar_screen_name = None
            tar_profile_image_url = None
            tar_location = None

            while 1:
                try:
                    if retry > 5:
                        break
                    statuses = client.get('statuses/user_timeline', uid=u, count=100, page=page)["statuses"]
                    weibo2db.statuses(statuses)
                    if tar_screen_name is None and len(statuses) > 0:
                        tar_profile_image_url = statuses[0]["user"]["profile_image_url"]
                        tar_screen_name = statuses[0]["user"]["name"]
                        tar_location = statuses[0]["user"]["location"]
                    for status in statuses:
                        if t in status["text"] or [t in status["retweeted_status"]["text"]
                                                   if "retweeted_status" in status else False][0]:
                            t_statuses.append(status)

                    if page == n_page:
                        break
                    else:
                        page += 1
                except Exception, e:
                    app.logger.error(e)
                    retry += 1

            if len(t_statuses) == 0:
                flash(u"没有搜索到相关微博,请尝试下一页或者采用其他关键词")

            statuses = t_statuses
            p = page
        else:
            try:
                target_user = client.get('users/show', screen_name=q)
            except:
                flash(u"您输入的昵称不存在,请重新输入")
                return redirect(url_for('index'))

            u = target_user["id"]
            page = p
            tar_screen_name = target_user["screen_name"]
            tar_profile_image_url = target_user["profile_image_url"]
            tar_location = target_user["location"]

            try:
                statuses = client.get('statuses/user_timeline', uid=u, count=50, page=page)["statuses"]
                weibo2db.statuses(statuses)
            except:
                flash(u"获取微博信息失败,请刷新")
                statuses = []

        for i in xrange(len(statuses)):
            weibo_url = "http://weibo.com/" \
                + str(statuses[i]["user"]["id"]) \
                + "/" + base62.mid_to_str(statuses[i]["mid"])
            statuses[i]["weibo_url"] = weibo_url

        screen_name = session["screen_name"]
        profile_image_url = session["profile_image_url"]
        return render_template('weibolist.html', btnuserpicvisible='inline',
                               btnloginvisible='none', t=t, q=q, p=int(p), u=u,
                               screen_name=screen_name, profile_image_url=profile_image_url,
                               tar_screen_name=tar_screen_name,
                               tar_profile_image_url=tar_profile_image_url,
                               tar_location=tar_location,
                               statuses=statuses)

    return redirect(url_for('login'))


class Count:
    def __init__(self, count=0):
        self.count = count


def node_rank(root):
    import Queue
    q = Queue.Queue()
    q.put(root)
    node_length = {}
    while not q.empty():
        node = q.get()
        node_length[node] = len(node.children)
        for n in node.children:
            q.put(n)
    node_length = sorted(node_length.iteritems(), key=lambda(x, y): y, reverse=True)
    if len(node_length) > 5:
        node_length = node_length[:5]
    rank_node = []
    for node, value in node_length:
        if value > 5:
            rank_node.append(node)
    return rank_node


def add_node_edge(drawtree, graph, rank, ct, parent=None, max_width=0):
    length = len(drawtree.children)
    size = math.log((math.pow(length, 0.3) + math.sqrt(4)), 4)
    b, r, g = "217", "254", "240"
    if length > 6 and drawtree not in rank:
        b = str(random.randint(0, 255))
        r = str(random.randint(100, 255))
        g = str(random.randint(0, 255))
    if drawtree in rank:
        b = '0'
        r = '255'
        g = '0'

    scale_y = max_width / 200 + 1
    node = graph.addNode(drawtree.tree.wid, drawtree.tree.node,
                         b=b, r=r, g=g, x=str(drawtree.x), y=str(drawtree.y * scale_y * 10), z="0.0",
                         size=str(size))
    node.addAttribute("img_url", drawtree.tree.img_url)
    node.addAttribute("name", drawtree.tree.node)
    node.addAttribute("location", drawtree.tree.location)
    node.addAttribute("datetime", drawtree.tree.datetime)
    node.addAttribute("repost_num", str(length))
    node.addAttribute("weibo_url", drawtree.tree.weibo_url)

    if parent is not None:
        ct.count += 1
        graph.addEdge(ct.count, str(drawtree.tree.wid), str(parent.tree.wid))

    for child in drawtree.children:
        add_node_edge(child, graph, rank, ct, drawtree, max_width)


@app.route('/status')
def status():
    user = login_user(session)
    if user is None:
        return ""

    client = Client(APP_KEY, APP_SECRET, CALLBACK_URL)
    client.set_token(user["access_token"])

    id = request.args.get('id', '')
    since_id = request.args.get('since_id', 0)

    reposts, source_weibo, since_id = load_reposts(app, weibo2db, r, client, id, since_id)
    if len(reposts) == 0:
        return ""

    for repost in reposts:
        print "-- " * 10
        print repost['user']['name']
        print repost['text']
    #root
    tree_nodes = []
    node = source_weibo["user"]["name"]
    location = source_weibo["user"]["location"]
    datetime = source_weibo["created_at"]
    img_url = source_weibo["user"]["profile_image_url"]
    url_user_str = str(source_weibo["user"]["id"])
    url_weibo_str = base62.mid_to_str(source_weibo["mid"])
    if url_weibo_str.startswith("z"):
        url_weibo_str = "z0" + url_weibo_str[1:]

    weibo_url = "http://weibo.com/" + url_user_str + "/" + url_weibo_str

    tree_nodes.append(Tree(node, location, datetime, int(id), img_url, weibo_url))

    for repost in reposts:
        try:
            node = repost["user"]["name"]
            wid = repost["id"]
            img_url = repost["user"]["profile_image_url"]
            location = repost["user"]["location"]
            datetime = repost['created_at']
            url_user_str = str(repost["user"]["id"])
            url_weibo_str = base62.mid_to_str(repost["mid"])
            if url_weibo_str.startswith("z"):
                url_weibo_str = "z0" + url_weibo_str[1:]

            weibo_url = "http://weibo.com/" + url_user_str + "/" + url_weibo_str

            tree_nodes.append(Tree(node, location, datetime, wid, img_url, weibo_url))
        except:
            app.logger.error(repost)
            continue

        repost_users = re.findall(u'/@([a-zA-Z-_\u0391-\uFFE5]+)', repost["text"])
        parent = 0
        while parent < len(repost_users):
            flag = False
            for node in tree_nodes[-2::-1]:
                if node.node == repost_users[parent]:
                    node.append_child(tree_nodes[-1])
                    flag = True
                    break
            if flag:
                break
            parent += 1
        else:
            tree_nodes[0].append_child(tree_nodes[-1])

    dt, max_width = buchheim.buchheim(tree_nodes[0])

    gexf = Gexf("MOON_CLJ", "haha")
    graph = gexf.addGraph("directed", "static", "weibo graph")
    graph.addNodeAttribute("img_url", type="URI", force_id="img_url")
    graph.addNodeAttribute("name", type="string", force_id="name")
    graph.addNodeAttribute("location", type="string", force_id="location")
    graph.addNodeAttribute("datetime", type="string", force_id="datetime")
    graph.addNodeAttribute("repost_num", type="integer", force_id="repost_num")
    graph.addNodeAttribute("weibo_url", type="URI", force_id="weibo_url")

    rank = node_rank(tree_nodes[0])
    add_node_edge(dt, graph, rank, Count(), max_width=max_width)

    return etree.tostring(gexf.getXML(), pretty_print=True, encoding='utf-8', xml_declaration=True)


@app.route('/graph')
def graph():
    if "uid" in session:
        id = request.args.get('id', '')

        screen_name = session["screen_name"]
        profile_image_url = session["profile_image_url"]
        return render_template('graph.html', btnuserpicvisible='inline',
                               btnloginvisible='none', screen_name=screen_name, profile_image_url=profile_image_url, id=id)

    return redirect(url_for('login'))


@app.route('/suggest', methods=['GET'])
def suggest():
    user = login_user(session)
    if user:
        query = request.args.get('query', '')
        client = Client(APP_KEY, APP_SECRET, CALLBACK_URL)
        client.set_token(user["access_token"])
        try:
            results = []
            for s in client.get('search/suggestions/at_users', q=query, type=0, count=10):
                results.append(s['nickname'])
            return json.dumps({'query': query, 'suggestions': results})
        except:
            raise

    return json.dumps({'query': query, 'suggestions': []})


@app.route('/callback')
def callback():
    code = request.args.get('code', '')
    client = Client(APP_KEY, APP_SECRET, CALLBACK_URL)
    try:
        client.set_code(code)
        r = client.token_info
        uid = r['uid']
        access_token = r['access_token']
        expires_in = r['expires_in']
    except:
        flash(u'微博登录没有成功')
        return redirect(url_for('login'))

    try:
        userinfo = client.get('users/show', uid=uid)
        screen_name = userinfo["screen_name"]
        profile_image_url = userinfo["profile_image_url"]

        mongo.db.users.update({"uid": uid},
                              {"$set": {"uid": uid, "access_token": access_token,
                              "expires_in": expires_in, "screen_name": screen_name,
                              "profile_image_url": profile_image_url}}, upsert=True, safe=True)

        session['uid'] = uid
        session['screen_name'] = screen_name
        session["profile_image_url"] = profile_image_url
        return redirect(url_for('index'))
    except Exception:
        flash(u'获取用户微博信息没有成功')
        return redirect(url_for('login'))


@app.route('/login', methods=['GET'])
def login():
    client = Client(APP_KEY, APP_SECRET, CALLBACK_URL)
    url = client.authorize_url
    flash(u'请用新浪微博登录')
    return render_template('simple.html', btnuserpicvisible='none', btnloginvisible='inline', url=url)


app.secret_key = 'youknowwhat,iamsocute'
if __name__ == '__main__':
    #dev
    APP_KEY = '1966311272'
    APP_SECRET = '57d36e0eaef033593f4bb6f745a67c5f'
    CALLBACK_URL = 'http://127.0.0.1:8080/callback'

    app.debug = True
    app.run(host='0.0.0.0', port=8080)
