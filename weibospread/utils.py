# -*- coding: utf-8 -*-

from weibospread.extensions import mongo
import time


def login_user(session):
    if 'uid' in session:
        user = mongo.db.users.find_one_or_404({"uid": session["uid"]})
        if user["expires_in"] > time.time():
            return user
    return None
