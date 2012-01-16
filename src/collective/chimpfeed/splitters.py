import os

from plone.memoize.instance import memoizedproperty

module_path = os.path.dirname(__file__)


class GenericNameSplitter:
    @staticmethod
    def split_name(name):
        names = filter(None, name.split(u' '))

        if len(names) < 2:
            return name, u''

        if len(names) == 2:
            return names

        last = names[-1]
        return u' '.join(names[:-2]), '%s %s' % (names[-2], last)


class DanishNameSplitter(object):
    @memoizedproperty
    def given_names(self):
        path = os.path.join(module_path, 'names', 'da')
        return open(os.path.join(path, 'male.txt'), 'r').read().\
               decode('utf-8').split(u'\n') + \
               open(os.path.join(path, 'female.txt'), 'r').read().\
               decode('utf-8').split(u'\n')

    def split_name(self, name):
        names = filter(None, name.split(u' '))

        if len(names) < 2:
            return name

        last = names[-1]

        if len(names) == 2 or not last.endswith(u'sen') or \
               names[-2] in self.given_names:
            return u" ".join(names[:-1]), last

        return u" ".join(names[:-2]), u"%s %s" % (names[-2], last)
