REPOSTCOUNT = 'simple:{id}:repostcount'
SINCEID = 'simple:{id}:sinceid'


class RepostStatus(object):
    """Redis-based reposts status"""

    def __init__(self, server, id):
        self.server = server
        self.repostcount = REPOSTCOUNT.format(id=id)
        self.sinceid = SINCEID.format(id=id)

    def get_repostcount(self):
        return self.server.get(self.repostcount)

    def get_sinceid(self):
        return self.server.get(self.sinceid)

    def set_repostcount(self, count):
        self.server.set(self.repostcount, count)
        self.server.expire(self.repostcount, 3600)

    def set_sinceid(self, count):
        self.server.set(self.sinceid, count)
        self.server.expire(self.sinceid, 3600)
