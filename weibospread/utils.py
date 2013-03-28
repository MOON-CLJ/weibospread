# -*- coding: utf-8 -*-

from weibospread.extensions import mongo
from utils4scrapy.pipelines import MongodbPipeline
from flask import session, redirect, url_for
from functools import wraps
from weibo import Client
import time


def login_user(session):
    if 'uid' in session:
        user = mongo.db.users.find_one_or_404({'uid': session['uid']})
        if user['expires_in'] > time.time():
            return user
    return None


def require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if login_user(session):
            return f(*args, **kwargs)
        else:
            return redirect(url_for('simple.login'))

    return decorated

#prod
'''
APP_KEY = '4131380600'
APP_SECRET = 'df544af4a9e30abe16e715cb4d0be423'
CALLBACK_URL = 'http://idec.buaa.edu.cn:8080/callback'
'''

#dev
APP_KEY = '1966311272'
APP_SECRET = '57d36e0eaef033593f4bb6f745a67c5f'
CALLBACK_URL = 'http://127.0.0.1:8080/callback'


def get_client(access_token=None, expires_at=None):
    if access_token and expires_at:
        return Client(APP_KEY, APP_SECRET, CALLBACK_URL, access_token=access_token, expires_at=expires_at)
    else:
        return Client(APP_KEY, APP_SECRET, CALLBACK_URL)


def items2mongo(items):
    pipeline = MongodbPipeline()
    for item in items:
        pipeline.process_item(item, spider=None)
