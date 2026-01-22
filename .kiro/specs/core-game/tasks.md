# Implementation Plan

- [x] 1. Harden Gemini validation and fallback pipeline  
  - Enforce choice counts (2–3), unique IDs, and required text for events; validate effects against allowed resources and catalog items.  
  - Integrate fallback monitor and last-reason tracking for event/resolution generation; short-circuit Gemini calls when offline/quota exhausted.  
  - Guard resource/item mutations with validation before apply; ensure invalid LLM payloads trigger fallback paths.  
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 5.1, 5.2, 5.3_

- [x] 2. Improve UI/runner observability for fallback and status  
  - Surface fallback/offline status via `gemini_online` flag and log entries to the player; annotate fallback source (prefetch vs deck, reason).  
  - Log timeout-triggered fallback and choice availability reasons; keep status in sync after each event/resolution.  
  - _Requirements: 1.4, 2.2, 4.1, 4.2, 4.3, 4.4, 5.1, 5.3_

- [x] 3. Add deterministic tests for validation and resilience  
  - Unit tests for choice count enforcement, effect validation against catalog/resources, and modify_resource guard rails.  
  - Tests for fallback-only mode when Gemini offline/quota exhausted and timeout-to-fallback logging behavior.  
  - _Requirements: 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2, 5.1_

- [x] 4. Maintain ontology traceability  
  - Create/update `ontology/conestoga.ttl` with requirements/design/component/task/test nodes and SHACL constraints for traceability.  
  - Link new validator/fallback monitor, design elements, tasks, and tests back to requirement IDs.  
  - _Requirements: 5.1, 5.3_
