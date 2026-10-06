# AniBatch Engineering Rules

## Architecture

Use clean layered architecture.

CLI code must not perform scraping, database access,
FFmpeg execution, or direct HTTP downloads itself.

Provider-specific logic must exist exclusively inside
src/anibatch/providers/.

No provider-specific types may leak into downloader,
metadata, storage, naming, or CLI layers.

All network operations must be asynchronous unless
there is a documented reason otherwise.

## Providers

Every provider must implement the Provider interface.

Never modify core downloader behavior to accommodate
one provider unless the behavior is genuinely generic.

Every provider requires contract tests.

Do not implement mechanisms designed to defeat DRM,
CAPTCHA, authentication, paywalls, or other access
controls.

## Downloads

Downloads must be resumable where the server supports
HTTP ranges.

Never write directly to final destination filenames.
Use temporary .part files followed by atomic finalization.

Queue state must survive program restart.

## Database

Database writes must go through the storage/repository
layer.

Schema changes require migrations.

## FFmpeg

All FFmpeg execution must go through FFmpegService.

Never invoke shell=True for media filenames.

## Testing

Every bug fix requires a regression test.

Network-based tests must not depend on public websites.

Provider behavior should be mocked or tested against
controlled fixtures.

Run the full test suite before declaring a task complete.

## Scope

Do not redesign unrelated modules while completing
a feature.

Prefer small, reviewable commits.

## Documentation

Any user-facing CLI option requires:
- help text
- README documentation
- at least one test
