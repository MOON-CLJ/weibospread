# -*- coding: utf-8 -*-

from flask import Blueprint, session, render_template, redirect, url_for, request, flash
from weibospread.extensions import mongo
from weibospread.utils import require_login, get_client

simple = Blueprint('simple', __name__)


@simple.route('/')
@require_login
def index():
    screen_name = session['screen_name']
    profile_image_url = session['profile_image_url']
    return render_template('simple.html', btnuserpicvisible='inline',
                           btnloginvisible='none', screen_name=screen_name, profile_image_url=profile_image_url)


@simple.route('/callback')
def callback():
    code = request.args.get('code', '')
    client = get_client()
    try:
        client.set_code(code)
        r = client.token_info
        uid = r['uid']
        access_token = r['access_token']
        expires_in = r['expires_at']
    except:
        flash(u'微博登录没有成功')
        return redirect(url_for('simple.login'))

    try:
        userinfo = client.get('users/show', uid=uid)
        screen_name = userinfo['screen_name']
        profile_image_url = userinfo['profile_image_url']

        mongo.db.users.update({'uid': uid},
                              {'$set': {'uid': uid, 'access_token': access_token,
                              'expires_in': expires_in, 'screen_name': screen_name,
                              'profile_image_url': profile_image_url}}, upsert=True, safe=True)

        session['uid'] = uid
        session['screen_name'] = screen_name
        session['profile_image_url'] = profile_image_url
        return redirect(url_for('simple.index'))
    except Exception:
        flash(u'获取用户微博信息没有成功')
        return redirect(url_for('simple.login'))


@simple.route('/login', methods=['GET'])
def login():
    client = get_client()
    url = client.authorize_url
    flash(u'请用新浪微博登录')
    return render_template('simple.html', btnuserpicvisible='none', btnloginvisible='inline', url=url)
