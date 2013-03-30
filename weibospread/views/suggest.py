# -*- coding: utf-8 -*-

from flask import Blueprint, session, request, jsonify
from weibospread.utils import login_user, get_client

suggest = Blueprint('suggest', __name__)


@suggest.route('/', methods=['GET'])
def index():
    user = login_user(session)
    query = request.args.get('query', '')
    if user:
        client = get_client(user['access_token'], user['expires_in'])

        results = []
        for s in client.get('search/suggestions/at_users', q=query, type=0, count=10):
            results.append(s['nickname'])
        return jsonify(query=query, suggestions=results)

    return jsonify(query=query, suggestions=[])
