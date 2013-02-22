# -*- coding: utf-8 -*-

from repost_status import RepostStatus
from scrapy.exceptions import DropItem
from utils4scrapy.items import WeiboItem, UserItem
from utils4scrapy.utils import local2unix
import math


def reposts2tree(reposts):
    pass


def tree2graph(tree):
    pass


def resp2item(resp):
    """ /statuses/show  api structured data to item"""

    weibo = WeiboItem()
    user = UserItem()

    if 'deleted' in resp:
        raise DropItem('deleted')

    if 'reposts_count' not in resp:
        raise DropItem('reposts_count')

    for k in WeiboItem.RESP_ITER_KEYS:
        weibo[k] = resp[k]

    weibo['timestamp'] = local2unix(weibo['created_at'])

    for k in UserItem.RESP_ITER_KEYS:
        user[k] = resp['user'][k]

    weibo['user'] = user

    retweeted_user = None
    if 'retweeted_status' in resp and 'deleted' not in resp['retweeted_status']:
        retweeted_status = WeiboItem()
        retweeted_user = UserItem()

        for k in WeiboItem.RESP_ITER_KEYS:
            retweeted_status[k] = resp['retweeted_status'][k]
        retweeted_status['timestamp'] = local2unix(retweeted_status['created_at'])

        for k in UserItem.RESP_ITER_KEYS:
            retweeted_user[k] = resp['retweeted_status']['user'][k]

        retweeted_status['user'] = retweeted_user
        weibo['retweeted_status'] = retweeted_status

    return user, weibo, retweeted_user


def load_last_page(app, weibo2db, client, id, since_id, reposts_count):
    before_reposts_count = weibo2db.before_reposts_count(id, since_id)
    page = int(math.ceil((reposts_count - before_reposts_count) / 200.0)) + 1
    retry = 0
    while retry < 4:
        retry += 1
        if retry > 1:
            page -= 1
            if page < 1:
                return
        try:
            reposts = client.get('statuses/repost_timeline', id=int(id),
                                 count=200, page=page, since_id=since_id)
            if len(reposts['reposts']) > 0:
                weibo2db.reposts(id, reposts['reposts'])
                return reposts['reposts'][0]['id']
        except Exception, e:
            app.logger.error(e)


def load_reposts(app, weibo2db, redis, client, id, since_id):
    repost_status = RepostStatus(redis, id)

    redis_since_id = repost_status.get_sinceid()
    if redis_since_id is None:
        redis_since_id = 0
    else:
        redis_since_id = int(redis_since_id)

    if since_id < redis_since_id:
        since_id = redis_since_id
    count = repost_status.get_repostcount()
    if count is None:
        try:
            count = reposts_count(app, weibo2db, client, id)
            repost_status.set_repostcount(count)
        except:
            return [], None, 0
    count = int(count)

    new_since_id = load_last_page(app, weibo2db, client, id, since_id, count)
    if new_since_id is not None:
        since_id = new_since_id
        repost_status.set_sinceid(new_since_id)

    reposts, source_weibo = weibo2db.before_reposts(id, since_id)

    return reposts, source_weibo, since_id


def reposts_count(app, weibo2db, client, id):
    retry = 0
    while retry < 3:
        retry += 1
        try:
            source_weibo = client.get('statuses/show', id=int(id))
            weibo2db.status(source_weibo)

            reposts_count = int(source_weibo["reposts_count"])
            if reposts_count > 0:
                return reposts_count
        except Exception, e:
            app.logger.error(e)
    else:
        app.logger.error("get reposts count of %s fail" % id)
        raise Exception("get reposts count of %s fail" % id)
