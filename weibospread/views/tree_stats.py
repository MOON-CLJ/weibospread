# -*- coding: utf-8 -*-

from flask import Blueprint, jsonify
from weibospread.utils import require_login, mongo

tree_stats = Blueprint('tree_stats', __name__)


@tree_stats.route('/<int:mid>/<int:page>/')
@require_login
def index(mid, page):
    tree_stats = mongo.db.tree_stats.find_one({'id': mid, 'page': page})
    del tree_stats['_id']
    tree_stats['spread_begin'] = tree_stats['spread_begin'].strftime('%Y-%m-%d %H:%M:%S')
    tree_stats['spread_end'] = tree_stats['spread_end'].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify(stats=tree_stats)
