---
name: test-provider
description: Procedure for running contract and resilience test suites for AniBatch providers
---

# Test Provider Skill

1. **Contract Verification**: Run `pytest tests/unit/test_providers/ -k <provider_name>` to verify provider contract compliance.
2. **Error Resilience**:
   - Verify handling of 404/500 HTTP responses.
   - Verify behavior under network timeouts.
   - Verify behavior when streams or subtitles are missing.
   - Verify rate-limit backoff logic.
3. **Domain Normalization**: Verify that all output objects conform strictly to AniBatch domain models.
