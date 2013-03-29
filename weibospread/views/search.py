# -*- coding: utf-8 -*-

from flask import Blueprint, session, render_template, redirect, url_for, request, flash
from weibospread.utils import require_login, login_user, get_client, items2mongo, mongo
from utils4scrapy.utils import resp2item_v2
from utils4scrapy import base62

search = Blueprint('search', __name__)


@search.route('/')
@require_login
def index():
    user = login_user(session)
    q = request.args.get('q', '')
    q = q.strip('@ \r\n\t')

    client = get_client(user['access_token'], user['expires_in'])
    try:
        target_user = client.get('users/show', screen_name=q)
        mongo.db.all_visited_users.update({'id': target_user['id']}, target_user, upsert=True)
        items2mongo(resp2item_v2(target_user))

        return redirect(url_for('search.weibos_by_uid_and_page', uid=target_user['id']))
    except:
        flash(u'您输入的昵称不存在,请重新输入')
        return redirect(url_for('simple.index'))


@search.route('/u/<int:uid>/')
@search.route('/u/<int:uid>/<int:page>/')
@require_login
def weibos_by_uid_and_page(uid, page=1):
    user = login_user(session)
    client = get_client(user['access_token'], user['expires_in'])

    target_user = mongo.db.all_visited_users.find_one({'id': uid})
    tar_screen_name = target_user['screen_name']
    tar_profile_image_url = target_user['profile_image_url']
    tar_location = target_user['location']

    try:
        statuses = client.get('statuses/user_timeline', uid=uid, count=50, page=page)['statuses']
        items = []
        for status in statuses:
            items.extend(resp2item_v2(status))
        items2mongo(items)
    except:
        flash(u'获取微博信息失败,请刷新')
        statuses = []

    for i in xrange(len(statuses)):
        weibo_url = base62.weiboinfo2url(statuses[i]['user']['id'], statuses[i]['mid'])
        statuses[i]['weibo_url'] = weibo_url

    screen_name = session['screen_name']
    profile_image_url = session['profile_image_url']

    has_prev = True if page > 1 else False
    has_next = True  # 默认始终有下一页
    page_url = lambda page: url_for('search.weibos_by_uid_and_page', uid=uid,
                                    page=page)

    return render_template('weibolist.html', btnuserpicvisible='inline',
                           btnloginvisible='none',
                           screen_name=screen_name, profile_image_url=profile_image_url,
                           tar_screen_name=tar_screen_name,
                           tar_profile_image_url=tar_profile_image_url,
                           tar_location=tar_location,
                           statuses=statuses,
                           page=page,
                           has_prev=has_prev,
                           has_next=has_next,
                           page_url=page_url
                           )
