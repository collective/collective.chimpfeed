from zope.component import getMultiAdapter
from Products.Five.browser import BrowserView
from ZODB.POSException import ConflictError

# This code is "stolen" from singing and dancing, see https://svn.plone.org/svn/collective/collective.dancing/

import logging
logger = logging.getLogger("Plone")

try:
    from BeautifulSoup import BeautifulSoup
    HAS_SOUP = True
except:
    HAS_SOUP = False

plone_html_strip_not_likey = [
    {'id': 'review-history'},
    {'class':'documentActions'},
    {'class':'portalMessage'},
    {'id':'plone-document-byline'},
    {'id':'portlets-below'},
    {'id':'portlets-above'},
    {'class': 'newsletterExclude'},
    ]

def plone_html_strip(html, not_likey=plone_html_strip_not_likey):

    r"""Tries to strip the relevant parts from a Plone HTML page.

    Looks for ``<div id="content">`` and ``<div id="region-content">`` as
    a fallback.

      >>> html = (
      ...     '<html><body><div id="content"><h1 class="documentFirstHeading">'
      ...     'Hi, it\'s me!</h1><p>Wannabe the son of Frankenstein</p>'
      ...     '</div></body></html>')
      >>> plone_html_strip(html)
      u'<h1 class="documentFirstHeading">Hi, it\'s me!</h1><p>Wannabe the son of Frankenstein</p>'
      >>> plone_html_strip('<div id="region-content">Hello, World!</div>')
      u'Hello, World!'

    Will also strip away any ``<div id="review-history">``:

      >>> html = (
      ...     '<div id="region-content">'
      ...     '<div id="review-history">Yesterday</div>Tomorrow</div>')
      >>> plone_html_strip(html)
      u'Tomorrow'

    """

    if not isinstance(html, unicode):
        html = unicode(html, 'UTF-8')

    soup = BeautifulSoup(html)
    content = soup.find('div', attrs={'id': 'content'})
    if content is None:
        content = soup.find('div', attrs=dict({'id': 'region-content'}))

    for attrs in not_likey:
        for item in content.findAll(attrs=attrs):
            item.extract() # meaning: item.bye()
    return content.renderContents(encoding=None) # meaning: as unicode

class Newsletter(BrowserView):
    def title(self):
        return self.context.aq_parent.Title()

    def template(self):
        if not HAS_SOUP:
            logger.info("BeautifulSoup is not installed, not processing of contents is done.")
            return ''

        if hasattr(self.context, 'REQUEST'):
            context = self.context
        else:
            context = self.context.aq_parent

        # Hack to avoid infinite loop due to request parameters
        context.REQUEST.set('restricted_traverse', True)

        try:
            html = context()
        except ConflictError:
            raise
        except:
            # Simple calling does not work if layout
            # is a view, we can try a little harder...
            html = context.restrictedTraverse(context.getLayout())()

        if 'kss' in html:
            return plone_html_strip(html)
        else:
            return html


