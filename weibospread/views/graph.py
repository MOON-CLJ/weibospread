# -*- coding: utf-8 -*-

from flask import Blueprint, session, redirect, url_for
from weibospread.utils import require_login, login_user, get_client, items2mongo, mongo
from utils4scrapy.utils import resp2item_v2
from utils4scrapy.items import WeiboItem
from utils4scrapy import base62
from gexf import Gexf
from lxml import etree
from weibospread.gen import Tree
from weibospread import buchheim
import math
import re
import random
import datetime

graph = Blueprint('graph', __name__)


def reposts2tree(source_weibo, reposts, per_page, page_count):
    # root
    tree_nodes = []
    tree_stats = {}
    node = source_weibo['user']['name']
    extra_infos = {
        'location': source_weibo['user']['location'],
        'datetime': source_weibo['created_at'],
        'wid': source_weibo['id'],
        'img_url': source_weibo['user']['profile_image_url'],
        'weibo_url': base62.weiboinfo2url(source_weibo['user']['id'], source_weibo['mid'])
    }

    tree_nodes.append(Tree(node, extra_infos))
    created_at = source_weibo['created_at']
    created_at = datetime.datetime.strptime(created_at, '%a %b %d %H:%M:%S +0800 %Y')
    tree_stats['spread_begin'] = created_at
    tree_stats['spread_end'] = created_at
    tree_stats['reposts_count'] = source_weibo['reposts_count']
    tree_stats['repost_peoples'] = set([source_weibo['user']['id']])

    # sort reposts
    reposts = sorted(reposts, key=lambda x: x['id'])
    reposts = reposts[: per_page * page_count]

    # genarate tree
    for repost in reposts:
        node = repost['user']['name']
        extra_infos = {
            'location': repost['user']['location'],
            'datetime': repost['created_at'],
            'wid': repost['id'],
            'img_url': repost['user']['profile_image_url'],
            'weibo_url': base62.weiboinfo2url(repost['user']['id'], repost['mid'])
        }

        tree_nodes.append(Tree(node, extra_infos))

        repost_users = re.findall(u'/@([a-zA-Z-_\u0391-\uFFE5]+)', repost['text'])
        parent_idx = 0
        while parent_idx < len(repost_users):
            flag = False
            for node in tree_nodes[-2::-1]:
                if node.node == repost_users[parent_idx]:
                    node.append_child(tree_nodes[-1])
                    flag = True
                    break

            if flag:
                break
            parent_idx += 1
        else:
            tree_nodes[0].append_child(tree_nodes[-1])

        created_at = repost['created_at']
        created_at = datetime.datetime.strptime(created_at, '%a %b %d %H:%M:%S +0800 %Y')
        if created_at > tree_stats['spread_end']:
            tree_stats['spread_end'] = created_at
        tree_stats['repost_peoples'].add(repost['user']['id'])

    tree_stats['repost_people_count'] = len(tree_stats['repost_peoples'])
    del tree_stats['repost_peoples']

    return tree_nodes, tree_stats


class Count:
    def __init__(self, count=0):
        self.count = count


def add_node_and_edge(drawtree, graph, ct, parent=None, max_width=0):
    length = len(drawtree.children)
    size = math.log((math.pow(length, 0.3) + math.sqrt(4)), 4)
    b, r, g = '217', '254', '240'
    if length > 6:
        b = str(random.randint(0, 255))
        r = str(random.randint(100, 255))
        g = str(random.randint(0, 255))

    scale_y = max_width / 200 + 1
    node = graph.addNode(drawtree.tree.extra_infos['wid'], drawtree.tree.node,
                         b=b, r=r, g=g, x=str(drawtree.x), y=str(drawtree.y * scale_y * 10), z='0.0',
                         size=str(size))

    node.addAttribute('img_url', drawtree.tree.extra_infos['img_url'])
    node.addAttribute('name', drawtree.tree.node)
    node.addAttribute('location', drawtree.tree.extra_infos['location'])
    node.addAttribute('datetime', drawtree.tree.extra_infos['datetime'])
    node.addAttribute('repost_num', str(length))
    node.addAttribute('weibo_url', drawtree.tree.extra_infos['weibo_url'])

    if parent is not None:
        ct.count += 1
        graph.addEdge(ct.count, str(drawtree.tree.extra_infos['wid']), str(parent.tree.extra_infos['wid']))

    for child in drawtree.children:
        add_node_and_edge(child, graph, ct, drawtree, max_width)


def tree2graph(tree_nodes):
    dt, max_depth, max_width = buchheim.buchheim(tree_nodes[0])

    gexf = Gexf('MOON_CLJ', 'simple')
    graph = gexf.addGraph('directed', 'static', 'weibo graph')
    graph.addNodeAttribute('img_url', type='URI', force_id='img_url')
    graph.addNodeAttribute('name', type='string', force_id='name')
    graph.addNodeAttribute('location', type='string', force_id='location')
    graph.addNodeAttribute('datetime', type='string', force_id='datetime')
    graph.addNodeAttribute('repost_num', type='integer', force_id='repost_num')
    graph.addNodeAttribute('weibo_url', type='URI', force_id='weibo_url')

    add_node_and_edge(dt, graph, Count(), max_width=max_width)

    return etree.tostring(gexf.getXML(), pretty_print=False, encoding='utf-8', xml_declaration=True), max_depth, max_width


@graph.route('/<int:mid>/')
@graph.route('/<int:mid>/<int:page>/')
@require_login
def index(mid, page=None):
    user = login_user(session)
    client = get_client(user['access_token'], user['expires_in'])

    per_page = 200
    total_page = 0
    reposts_count = 0
    source_weibo = None
    if page is None:
        source_weibo = client.get('statuses/show', id=mid)
        mongo.db.all_source_weibos.update({'id': source_weibo['id']}, source_weibo, upsert=True)

        items2mongo(resp2item_v2(source_weibo))

        reposts_count = source_weibo['reposts_count']
        total_page = int(math.ceil(reposts_count * 1.0 / per_page))
        page = total_page
    else:
        source_weibo = mongo.db.all_source_weibos.find_one({'id': mid})
        if source_weibo is None:
            return ''
        reposts_count = source_weibo['reposts_count']
        total_page = int(math.ceil(reposts_count * 1.0 / per_page))

    try:
        reposts = client.get('statuses/repost_timeline', id=mid,
                             count=200, page=page)['reposts']

        # 如果reposts为空，且是最开始访问的一页，有可能是页数多算了一页,直接将页数减一页跳转
        if reposts == [] and total_page > 1 and page == total_page:
            return redirect(url_for('graph.index', mid=mid, page=page - 1))

        items = []
        for repost in reposts:
            items.extend(resp2item_v2(repost))
        items2mongo(items)
        for item in items:
            if isinstance(item, WeiboItem) and item['id'] != source_weibo['id']:
                item = item.to_dict()
                item['source_weibo'] = source_weibo['id']
                mongo.db.all_repost_weibos.update({'id': item['id']}, item, upsert=True)
    except RuntimeError:
        pass

    reposts = list(mongo.db.all_repost_weibos.find({'source_weibo': source_weibo['id']}))
    if reposts == []:
        return ''

    page_count = total_page - page + 1 if total_page >= page else 0
    tree, tree_stats = reposts2tree(source_weibo, reposts, per_page, page_count)
    graph, max_depth, max_width = tree2graph(tree)
    tree_stats['max_depth'] = max_depth
    tree_stats['max_width'] = max_width

    # 存储转发状态
    tree_stats['id'] = mid
    tree_stats['page'] = page
    mongo.db.tree_stats.update({'id': mid, 'page': page}, tree_stats, upsert=True, w=1)
    return graph
