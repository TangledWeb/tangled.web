1.0a13 (unreleased)
===================

- No changes yet


1.0a12 (2017-12-10)
===================

- Fix borked 1.0a11 release.


1.0a11 (2017-12-10)
===================

- Removed `Request.reset_resource_config()`. It's no longer needed since
  properties created via `@cached_property` can now always be safely deleted.
- Changed the default for `Reprensentation.quality` to `0.5`. This makes all
  content types equal instead of favoring HTML.
- Added `quality` field to default resource config options. This allows
  resources to set a preferred content type.
- Changed how the response content type is selected: it's now selected based on
  what the resource is configured to handle.
- Moved first evaluation of `Application._handlers` to `Application.created()`
  in order to shake out more errors during application startup instead of
  waiting for the first request.
- Added `Application.handle_request(request)`, which takes a request and passes
  it into the handler chain. This allows for easier testing of request handling
  and also for overriding how handling is initiated.
- Added default implementation of `Resouce.OPTIONS()` instead of having it be
  disallowed by default (I think `OPTIONS` should always be allowed?). It
  returns a response with the `Allow` header set.
- Added `Resource.PATCH()`. It's disallowed by default.
- Added initial CORS handler. This initial version only supports development
  use cases with a permissive setting that allows requests from any origin.


0.1a10 (2016-01-03)
===================

- Store mounted resource paths in a tree instead of a list. Do lookups via the
  tree instead of doing a linear regex search through a list. For most apps,
  the performance difference probably won't matter, but it could be significant
  for apps that have a lot of resources.
- Improve how converters can be specified in URL vars. Ensure any valid Python
  identifier is accepted, and allow `package:callable` paths.
- When an error is encountered when running the dev server, wait until a change
  is made to some file before attempting to restart (instead of blindly
  attempting to restart every
  5 seconds).
- StringRepresentation now accepts any kind of data being returned from
  a resource method.
- Ditto for HTMLRepresentation. The data will be `str`-ified.
- Add default app `factory` setting, which points at `tangled.web:Application`,
  naturally. I don't see any point in *requiring* an app factory to be
  specified in every app when the default will be used in most cases. At the
  very least, simplifying getting up-and-running is a good thing.
- When using the `tangled.app.resources` setting, allow paths to resources to
  be relative to a package. The `tangled.app.resources.package` setting can be
  used to specify the package; if that's not set, the `package` setting will be
  used if present.
- Provide a way to defer firing the `ApplicationCreated`` event. Normally, it's
  always called at the end of `Application.__init__`, but there are cases where
  this might not be desirable. The `tangled.app.defer_created` setting can be
  used to control this (in which case, the event has to be fired manually).
- Change the basic scaffold so the app is configured via the `include`
  mechanism rather than using an app factory. The latter approach shouldn't be
  recommended in the general case.


0.1a9 (2014-08-05)
==================

- Tidy up generated `application.wsgi` scripts: don't pass `parse_settings` to
  `Application` since `Application` no longer has a `parse_settings` arg.
- Replace `@reify` with `@cached_property` throughout. `@reify` was removed
  from `tangled`.
- Remove venusian dependency; use tangled's deferred decorator action system
  instead.
- Add a safe method for resetting a request's resource config:
  `request.reset_resource_config()`. This ensures `request.resource_config` has
  been accessed before attempting to delete it.


0.1a8 (2014-03-22)
==================

- Simplify and improve settings parsing. In particular, move settings parsing
  logic from `Application.__init__()` to a new `settings.make_app_settings()`
  function. The purpose of this is to make it easy for apps to do custom
  settings parsing by calling `make_app_settings()` and passing the result to
  `Application`. In simple cases, though, this can be ignored, and a plain
  dict or settings file name can be passed to `Application` as before.
- As part of the above, `Application` no longer accepts a `parse_settings` arg;
  `make_app_settings()` has a `parse` arg instead that serves the same purpose
  (disabling parsing, since it's enabled by default).
- Also part of the above: the `parse_settings()` and `parse_settings_file()`
  functions were removed from `settings` and the corresponding static methods
  were removed from `Application`. They weren't very useful in the first place
  and are less so now.
- Fix generation of application.wsgi via wsgi_application recipe: pass extra
  settings to `Application` via `**` instead of passing the extra settings dict
  as a single keyword arg.
- In quick start doc, install dependencies via PyPI rather than git (now that
  releases have been made of the relevant packages).
- Upgrade tangled from 0.1a6 to 0.1a7. 0.1a7 contains some fixes and
  improvements to settings parsing.


0.1a7 (unreleased)
==================

- The Accept header can now be set via a file name extension in URL. For
  example, the URL /users.json will cause the Accept header to be set to
  application/json, and the .json extension will remove from the request's path
  before the request is passed down to the application. This functionality is
  enabled via the tangled.app.set_accept_from_ext setting (it defaults to on).
- Encode date and datetime objects as timestamps in JSON responses (only if
  custom encoding hasn't been configured).
- Make exception log messages configurable. The
  tangled.app.exc_log_message_factory setting can be pointed at a function that
  accepts an app, request, and exception and returns a string.
- Start adding "main" (i.e., prose) documentation.
- Slightly improve package metadata.


0.1a6 (2014-02-10)
==================

- Add download_url to setup().
- Make app factory configurable in WSGI app recipe. Previously, it was hard
  coded as `tangled.web.Application`.


0.1a5 (2014-02-09)
==================

- Fix more packaging issues

  - Include package data (i.e., include scaffolds)
  - Add .template extension to .py files in basic scaffold that use ${var}s

- Require released version of tangled 0.1a5 or newer

- Update trove classifiers

  - Declare package to be Alpha status
  - Declare support for Python 3.3 and 3.4 specifically (instead of generic
    Python 3)


0.1a4 (2014-02-06)
==================

- Include tangled in packages list. Not sure this is strictly necessary, but
  it's more correct in the sense that a namespace package may include Python
  modules.
- Include package data (ensure defaults.ini and scaffolds get installed).


0.1a3 (2014-02-06)
==================

- Fix packaging issues.
- Reimplement the `tangled shell` command as a subclass of
  `tangled.scripts.ShellCommand`.


0.1a2 (2014-02-05)
==================

- Fix packaging issues.


0.1a1 (2014-02-05)
==================

First release.
