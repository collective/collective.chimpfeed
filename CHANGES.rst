Changes
=======

1.5 (2012-04-11)
----------------

Features:

- Plone 3 compatibility.

Bugfixes:

- Fixed issue where subscription using first name only (single name,
  when split on space) would cause an exception.

1.4 (2012-03-27)
----------------

Features:

- Bump schedule date to today's date on moderation, if date is in the
  past. This ensures that the item will be shown on the moderation
  screen.

Bugfixes:

- Fixed issue with custom schema mutator which would not function
  correctly with schema caching; we are able to work around it using
  Archetypes' storage API directly.

- Fixed incorrect package dependency.


1.3 (2012-03-26)
----------------

Features:

- Add support for configuring an RSS summary display of included
  items.

- Add support for Dexterity-based content.

- Make content moderation requirement optional.


1.2 (2012-03-09)
----------------

Features:

- Add link to content for moderation.

Bugfixes:

- The moderation portlet now correctly gets the class
  ``'portletModeration'``.

1.1 (2012-03-08)
----------------

- Added simple approval system where items are explicitly made
  available after some date, and separately approved (guarded by a
  custom permission).

  To upgrade, you must run the "catalog" setup step and perform the
  require indexing.

1.0 (2012-01-18)
----------------

- Initial public release.
