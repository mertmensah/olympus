# Advanced Model Selection Guide

## Overview

The Olympus platform supports intelligent routing of reconstruction requests to different adapters based on input characteristics. This enables:

- **Quality-based routing**: Use fast models for low-quality inputs, premium models for high-quality inputs
- **Fallback chains**: Gracefully handle adapter failures
- **A/B testing**: Compare different models on production traffic
- **Cost optimization**: Route expensive operations strategically

## Selection Strategies

### 1. Fixed Strategy (Default)
Always uses one adapter regardless of input characteristics.

**Configuration**:
```bash
OLYMPUS_MODEL_SELECTION_STRATEGY=fixed
OLYMPUS_PRIMARY_ADAPTER=mock_v1
```

**Use case**: Development, testing, or when you want consistent behavior.

---

### 2. Quality-Based Strategy
Selects adapter based on input quality metrics and asset count.

**Logic**:
- High quality (>threshold) + adequate assets → premium adapter (hf_api_v1)
- Low quality (<threshold) or sparse assets → fast adapter (mock_v1)
- Threshold adjusts based on asset count for confidence weighting

**Configuration**:
```bash
OLYMPUS_MODEL_SELECTION_STRATEGY=quality_based
OLYMPUS_QUALITY_THRESHOLD=0.7
OLYMPUS_HIGH_QUALITY_ADAPTER=hf_api_v1
OLYMPUS_LOW_QUALITY_ADAPTER=mock_v1
```

**Example decisions**:
| Quality | Assets | Decision | Reason |
|---------|--------|----------|--------|
| 0.85 | 6 | hf_api_v1 | High quality, enough inputs |
| 0.50 | 2 | mock_v1 | Low quality, too few inputs |
| 0.72 | 1 | mock_v1 | Single asset, insufficient confidence |
| 0.75 | 8 | hf_api_v1 | Good quality, many inputs |

**Use case**: Production environments where you want to optimize cost and latency.

---

### 3. Fallback Strategy
Tries primary adapter, falls back to secondary on failure.

**Configuration**:
```bash
OLYMPUS_MODEL_SELECTION_STRATEGY=fallback
OLYMPUS_PRIMARY_ADAPTER=hf_api_v1
OLYMPUS_SECONDARY_ADAPTER=mock_v1
```

**Behavior**:
1. Attempt reconstruction with `hf_api_v1`
2. If timeout/error → automatically retry with `mock_v1`
3. Returns error artifact if both fail

**Use case**: Critical jobs where some output is better than none.

---

### 4. A/B Test Strategy
Randomly selects between two adapters for experimentation.

**Configuration**:
```bash
OLYMPUS_MODEL_SELECTION_STRATEGY=ab_test
OLYMPUS_PRIMARY_ADAPTER=mock_v1
OLYMPUS_SECONDARY_ADAPTER=hf_api_v1
OLYMPUS_AB_SPLIT=0.5  # 50% to primary, 50% to secondary
```

**Example with 30/70 split**:
```bash
OLYMPUS_AB_SPLIT=0.3  # 30% to primary, 70% to secondary
```

**Use case**: Compare models on real traffic, measure quality/performance differences.

---

## Environment Variables

### Selection Strategy
| Variable | Default | Values | Description |
|----------|---------|--------|-------------|
| `OLYMPUS_MODEL_SELECTION_STRATEGY` | `fixed` | `fixed`, `quality_based`, `fallback`, `ab_test` | Strategy to use |

### Adapters
| Variable | Default | Description |
|----------|---------|-------------|
| `OLYMPUS_PRIMARY_ADAPTER` | `mock_v1` | Primary adapter name |
| `OLYMPUS_SECONDARY_ADAPTER` | `mock_v1` | Secondary adapter (fallback/A/B test) |

### Quality-Based Strategy
| Variable | Default | Range | Description |
|----------|---------|-------|-------------|
| `OLYMPUS_QUALITY_THRESHOLD` | `0.7` | 0.0-1.0 | Quality score threshold |
| `OLYMPUS_HIGH_QUALITY_ADAPTER` | `hf_api_v1` | adapter name | Used for high-quality jobs |
| `OLYMPUS_LOW_QUALITY_ADAPTER` | `mock_v1` | adapter name | Used for low-quality jobs |

### A/B Testing
| Variable | Default | Range | Description |
|----------|---------|-------|-------------|
| `OLYMPUS_AB_SPLIT` | `0.5` | 0.0-1.0 | Fraction of traffic to primary |

---

## Usage Examples

### Example 1: Development (Fixed to mock_v1)
```bash
docker-compose -f docker-compose.yml \
  -e OLYMPUS_MODEL_SELECTION_STRATEGY=fixed \
  -e OLYMPUS_PRIMARY_ADAPTER=mock_v1 \
  up
```

### Example 2: Production with Cost Optimization
```bash
# Expensive model only for good-quality inputs
OLYMPUS_MODEL_SELECTION_STRATEGY=quality_based
OLYMPUS_QUALITY_THRESHOLD=0.75
OLYMPUS_HIGH_QUALITY_ADAPTER=hf_api_v1
OLYMPUS_LOW_QUALITY_ADAPTER=mock_v1
```

With this config:
- Users with high-quality inputs get premium HF API reconstruction
- Users with low-quality inputs get fast mock_v1
- Saves API costs on low-confidence jobs

### Example 3: Reliability with Fallback
```bash
# Always try to get best result, fall back gracefully
OLYMPUS_MODEL_SELECTION_STRATEGY=fallback
OLYMPUS_PRIMARY_ADAPTER=hf_api_v1
OLYMPUS_SECONDARY_ADAPTER=mock_v1
```

Behavior:
- 90% of time: HF API succeeds, user gets premium result
- 10% of time: HF API times out → fallback to mock_v1
- User always gets some reconstruction

### Example 4: Model Comparison (A/B Testing)
```bash
# Compare mock_v1 vs hf_api_v1 on 50/50 traffic split
OLYMPUS_MODEL_SELECTION_STRATEGY=ab_test
OLYMPUS_PRIMARY_ADAPTER=mock_v1
OLYMPUS_SECONDARY_ADAPTER=hf_api_v1
OLYMPUS_AB_SPLIT=0.5
```

**Tracking**:
- Each job artifact includes `model_selection` metadata
- Compare metrics across both groups in your analytics
- Decide which model to keep long-term

---

## Monitoring Selection Decisions

Each job's reconstruct artifact includes selection metadata:

```json
{
  "model_selection": {
    "strategy": "quality_based",
    "selected_adapter": "hf_api_v1",
    "quality_score": 0.85,
    "asset_count": 6,
    "quality_threshold": 0.7,
    "primary_adapter": "mock_v1",
    "secondary_adapter": "hf_api_v1"
  },
  "adapter": {
    "name": "hf_api_v1",
    "version": "1.0.0"
  },
  "runtime": {
    "latency_ms": 2350.5,
    "peak_memory_kb": 512.3,
    "output_size_bytes": 125640
  }
}
```

### Analytics Queries

**With quality-based routing:**
```sql
-- Average latency per adapter
SELECT 
  model_selection.selected_adapter,
  AVG(runtime.latency_ms) as avg_latency,
  COUNT(*) as job_count
FROM artifacts
WHERE stage = 'reconstruct'
GROUP BY model_selection.selected_adapter;
```

**A/B test comparison:**
```sql
-- Compare user satisfaction by adapter
SELECT 
  model_selection.selected_adapter,
  AVG(user_rating) as avg_rating,
  COUNT(*) as n
FROM artifacts 
WHERE strategy = 'ab_test'
GROUP BY model_selection.selected_adapter;
```

---

## Implementation Details

The selection happens in `run_reconstruct_stage()`:

```python
# Pipeline calls model selector
selector = get_model_selector()
adapter, adapter_name = selector.select_adapter(
    quality_score=quality_score,
    asset_count=len(selected_assets)
)

# Then uses selected adapter
adapter_output = adapter.run(adapter_input)

# Artifact includes selection metadata for tracking
payload["model_selection"] = selector.get_selection_metadata(...)
```

### Adding Custom Selection Logic

Extend `ModelSelector` in `backend/app/services/model_selector.py`:

```python
class ModelSelector:
    def select_adapter(self, quality_score, asset_count):
        # Your custom logic here
        if some_condition:
            return get_reconstruct_adapter("custom_adapter"), "custom_adapter"
        else:
            return get_reconstruct_adapter("fallback_adapter"), "fallback_adapter"
```

---

## Best Practices

1. **Start with fixed strategy** for initial validation
2. **Use quality-based for production** to optimize costs
3. **Monitor selection metadata** to understand traffic patterns
4. **Run A/B tests** before committing to new adapters
5. **Set appropriate thresholds** based on your business metrics
6. **Document your strategy** in deployment notes

---

## Troubleshooting

**Q: Why is my high-quality adapter never selected?**  
A: Check that:
- `OLYMPUS_QUALITY_THRESHOLD` is low enough for your data
- `OLYMPUS_HIGH_QUALITY_ADAPTER` is configured correctly
- Asset count is >= 3 (the default threshold adjusts for low counts)

**Q: A/B split isn't 50/50?**  
A: The split is probabilistic and smooths out over many requests. Run more tests to see convergence.

**Q: How do I switch strategies without restarting?**  
A: Stop the container, update environment, restart:
```bash
docker-compose down
# Edit .env or docker-compose.yml
docker-compose up
```

**Q: Can I mix strategies?**  
A: Not in one selector, but you can:
- Deploy multiple backend instances with different strategies
- Use a load balancer to route traffic differently
- Switch strategies via deployment/reconfig cycle
