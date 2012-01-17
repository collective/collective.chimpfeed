import os
from setuptools import setup, find_packages


def read(*pathnames):
    return open(os.path.join(os.path.dirname(__file__), *pathnames)).read()

version = '1.0-beta3'

setup(name='collective.chimpfeed',
      version=version,
      description="Plone-integration for MailChimp RSS-campaigns.",
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
          'plone.app.registry',
          'plone.app.controlpanel',
          'greatape',
          'simplejson',
      ],
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
