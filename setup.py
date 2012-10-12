import os
from setuptools import setup, find_packages


def read(*pathnames):
    return open(os.path.join(os.path.dirname(__file__), *pathnames)).read()

version = '1.8.1'

setup(name='collective.chimpfeed',
      version=version,
      description="MailChimp-integration for Plone!",
      long_description='\n'.join([
          read('README.rst'),
          read('CHANGES.rst'),
          ]),
      classifiers=[
        "Framework :: Plone",
        "Framework :: Zope2",
        "Programming Language :: Python",
        ],
      keywords='plone rss mailchimp',
      author='Malthe Borch',
      author_email='mborch@gmail.com',
      license='GPL',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'plone.indexer',
          'plone.z3cform',
          'greatape',
          'simplejson',
          'Products.AdvancedQuery',
      ],
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
