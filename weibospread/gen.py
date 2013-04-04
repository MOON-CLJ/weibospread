# -*- coding: utf-8 -*-


class Tree:
    def __init__(self, node='', extra_infos={}, location='', datetime='', wid=0, img_url='', weibo_url='', *children):
        self.node = node
        self.extra_infos = extra_infos
        if children:
            self.children = children
        else:
            self.children = []

    def __str__(self):
        return '%s' % (self.node)

    def __repr__(self):
        return '%s' % (self.node)

    def __getitem__(self, key):
        if isinstance(key, int) or isinstance(key, slice):
            return self.children[key]
        if isinstance(key, str):
            for child in self.children:
                if child.node == key:
                    return child

    def __iter__(self):
        return self.children.__iter__()

    def __len__(self):
        return len(self.children)

    @property
    def width(self):
        return len(self)

    def append_child(self, tree):
        self.children.append(tree)
