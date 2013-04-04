# -*- coding: utf-8 -*-

from flask import Blueprint, session, render_template, redirect, url_for
from weibospread.utils import require_login, get_client, login_user, items2mongo, mongo
from utils4scrapy.utils import resp2item_v2
import math

show_graph = Blueprint('show_graph', __name__)


@show_graph.route('/<int:mid>/')
@show_graph.route('/<int:mid>/<int:page>/')
@require_login
def index(mid, page=None):
    if page is None:
        per_page = 200
        user = login_user(session)
        client = get_client(user['access_token'], user['expires_in'])

        source_weibo = client.get('statuses/show', id=mid)
        mongo.db.all_source_weibos.update({'id': source_weibo['id']}, source_weibo, upsert=True)

        items2mongo(resp2item_v2(source_weibo))

        reposts_count = source_weibo['reposts_count']
        total_page = int(math.ceil(reposts_count * 1.0 / per_page))
        page = total_page

        return redirect(url_for('show_graph.index', mid=mid, page=page))

    screen_name = session['screen_name']
    profile_image_url = session['profile_image_url']
    return render_template('graph.html', btnuserpicvisible='inline',
                           btnloginvisible='none',
                           screen_name=screen_name, profile_image_url=profile_image_url,
                           mid=mid,
                           page=page)
