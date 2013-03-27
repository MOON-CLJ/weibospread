# -*- coding: utf-8 -*-

from flask import Blueprint, session, render_template, redirect, url_for, request, flash
from weibo import Client

from weibospread.extensions import mongo
from weibospread.utils import login_user

#prod
"""
APP_KEY = '4131380600'
APP_SECRET = 'df544af4a9e30abe16e715cb4d0be423'
CALLBACK_URL = 'http://idec.buaa.edu.cn:8080/callback'
"""

#dev
APP_KEY = '1966311272'
APP_SECRET = '57d36e0eaef033593f4bb6f745a67c5f'
CALLBACK_URL = 'http://127.0.0.1:8080/callback'


simple = Blueprint('simple', __name__)


@simple.route('/')
def index():
    if login_user(session):
        screen_name = session["screen_name"]
        profile_image_url = session["profile_image_url"]
        return render_template('simple.html', btnuserpicvisible='inline',
                               btnloginvisible='none', screen_name=screen_name, profile_image_url=profile_image_url)

    return redirect(url_for('simple.login'))


@simple.route('/callback')
def callback():
    code = request.args.get('code', '')
    client = Client(APP_KEY, APP_SECRET, CALLBACK_URL)
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
        raise
        flash(u'获取用户微博信息没有成功')
        return redirect(url_for('simple.login'))


@simple.route('/login', methods=['GET'])
def login():
    client = Client(APP_KEY, APP_SECRET, CALLBACK_URL)
    url = client.authorize_url
    flash(u'请用新浪微博登录')
    return render_template('simple.html', btnuserpicvisible='none', btnloginvisible='inline', url=url)
