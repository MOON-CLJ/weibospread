from scrapy.exceptions import DropItem
from utils import resp2item
from utils4scrapy.pipelines import MongodbPipeline
import time


class Weibo2Db(object):
    def __init__(self):
        self.pipeline = MongodbPipeline()

    def update_reposts(self, id, reposts):
        old_weibo = self.pipeline.db.master_timeline_weibo.find_one({'_id': int(id)})

        updates = {}

        flag = False
        for more_repost in reposts:
            if more_repost not in old_weibo['reposts']:
                old_weibo['reposts'].append(more_repost)
                flag = True
        updates['reposts'] = old_weibo['reposts']

        updates['last_modify'] = time.time()

        if flag:
            self.pipeline.db.master_timeline_weibo.update({'_id': int(id)},
                                                          {"$set": updates})

    def statuses(self, statuses):
        for status in statuses:
            try:
                user, weibo, retweeted_user = resp2item(status)
            except DropItem:
                continue

            self.pipeline.process_item(user, None)
            self.pipeline.process_item(weibo, None)
            if retweeted_user is not None:
                self.pipeline.process_item(retweeted_user, None)

    def reposts(self, id, statuses):
        reposts = []
        for status in statuses:
            try:
                user, weibo, retweeted_user = resp2item(status)
            except DropItem:
                continue

            reposts.append(weibo['id'])

            self.pipeline.process_item(user, None)
            self.pipeline.process_item(weibo, None)
            if retweeted_user is not None:
                self.pipeline.process_item(retweeted_user, None)
        self.update_reposts(id, reposts)

    def status(self, status):
        try:
            user, weibo, retweeted_user = resp2item(status)
        except DropItem:
            return

        self.pipeline.process_item(user, None)
        self.pipeline.process_item(weibo, None)
        if retweeted_user is not None:
            self.pipeline.process_item(retweeted_user, None)

    def before_reposts_count(self, id, since_id):
        status = self.pipeline.db.master_timeline_weibo.find_one({'_id': int(id)})
        count = 0
        if status:
            for repost in status['reposts']:
                if repost <= since_id:
                    count += 1
        return count

    def before_reposts(self, id, since_id):
        reposts = []
        status = self.pipeline.db.master_timeline_weibo.find_one({'_id': int(id)})
        if status:
            reposts_id = [repost for repost in status['reposts'] if repost <= since_id]
            reposts_id.sort()
            for repost_id in reposts_id:
                repost = self.pipeline.db.master_timeline_weibo.find_one({'_id': repost_id})
                del repost['reposts']
                reposts.append(repost)

            del status['reposts']

        return reposts, status
