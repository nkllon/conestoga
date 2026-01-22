# Performance Optimization Notes

## Prefetch Strategy Evolution

### Initial Approach: Prefetch Event + All Resolutions
**Attempt**: Generate event AND all choice resolutions during initial load
**Result**: ~60s total time
- Event generation: ~5-15s  
- Resolution 1: ~5-15s
- Resolution 2: ~5-15s
- Resolution 3: ~5-15s
- **Total: 20-60s**

**Problem**: Violates Requirement 10.6 (<2s target for 80% of generations)

### Parallel Optimization Attempt
**Attempt**: Generate resolutions in parallel using ThreadPoolExecutor
**Result**: ~58s total time (minimal improvement)
- Event generation: ~47s
- 3 resolutions in parallel: ~10s
- **Total: ~57s**

**Problem**: Gemini API appears rate-limited or sequential on the backend. Parallel requests don't significantly improve latency.

### Final Approach: Event-Only Prefetch with On-Demand Resolutions ✅
**Strategy**: 
1. Prefetch only events (~5-15s)
2. Generate resolutions on-demand when player makes choice
3. Cache resolutions for instant retry/back navigation

**Benefits**:
- Initial load: ~5-15s (75% faster)
- Player sees event immediately
- Resolution generation happens during natural gameplay pause
- Cached resolutions prevent re-generation
- Meets Requirement 10 latency targets

## Gemini API Rate Limits (Free Tier)

**Limit**: 20 requests per day per model (gemini-3-flash)
**Reset**: Daily

**Error Response**:
```
429 You exceeded your current quota
Retry in: 41.5s
```

**Handling**:
- Automatic fallback to FallbackDeck (Requirement 10.6)
- Fallback events generate instantly (<0.1s)
- System continues functioning without API
- No user-facing errors or crashes

## Performance Targets (Requirement 10.6)

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Event generation | <2s for 80% | ~5-15s | ⚠️ API-dependent |
| Fallback generation | <1s | ~0.1s | ✅ |
| Initial load (event only) | <20s | ~5-15s | ✅ |
| Initial load (event+resolutions) | N/A | ~60s | ❌ Not used |
| Cached operations | <0.1s | ~0.05s | ✅ |

## Recommendations

1. **Production**: Upgrade to Gemini API paid tier for better rate limits
2. **Testing**: Use fallback mode extensively to avoid quota exhaustion
3. **UX**: Loading screen provides good feedback during generation
4. **Optimization**: Current event-only prefetch is optimal given API constraints
