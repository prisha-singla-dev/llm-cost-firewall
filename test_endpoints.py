"""
test_endpoints.py - Manual endpoint validation script
Run this while the server is running: python test_endpoints.py
It shows you exactly what each endpoint returns and whether it's correct.
"""
import os, sys, json, time
os.environ.setdefault("MOCK_MODE", "true")
sys.path.insert(0, ".")

# ── Import app directly and call route logic (no HTTP server needed) ──────────
from app.router import LLMRouter
from app.budget import BudgetExceededError
from app.rate_limiter import RateLimiter
from app.analyzer import compute_complexity, select_model

results = []
def check(name, cond, detail=""):
    results.append(cond)
    icon = "✅" if cond else "❌"
    print(f"  {icon} {name}" + (f"  [{detail}]" if detail else ""))

print("\n" + "═"*58)
print("  LLM COST FIREWALL — COMPLETE SYSTEM VALIDATION")
print("═"*58)


# ════════════════════════════════════════════════════════════
# 1. ANALYZER
# ════════════════════════════════════════════════════════════
print("\n📐 1. Complexity Analyzer")

simple = compute_complexity("What is 2+2?")
check("Simple query scores < 0.30", simple["composite"] < 0.30,
      f"score={simple['composite']}")

hard = compute_complexity(
    "Analyze the architectural trade-offs between microservices and monolithic systems "
    "in distributed ML inference. Compare latency, scalability, operational complexity."
)
check("Complex query scores > 0.35", hard["composite"] > 0.35,
      f"score={hard['composite']}")

check("Complex > simple", hard["composite"] > simple["composite"])
check("All 6 factors present", all(
    k in simple["factors"] for k in ["length","keywords","questions","code","technical","sentence"]
))

model_simple  = select_model(0.10)
model_complex = select_model(0.90)
check("Low complexity → Flash", "flash" in model_simple.lower(), model_simple)
check("High complexity → Pro",  "pro"   in model_complex.lower(), model_complex)


# ════════════════════════════════════════════════════════════
# 2. BUDGET ENFORCER
# ════════════════════════════════════════════════════════════
print("\n💰 2. Budget Enforcement")
from app.budget import BudgetEnforcer
b = BudgetEnforcer(daily_limit=5.0, hourly_limit=1.0)

b.check_budget()  # should not raise
check("No block under limit", True)

b.record_cost(0.50)
s = b.status()
check("Cost recorded correctly", abs(s["total_cost_usd"] - 0.50) < 1e-9,
      f"recorded=${s['total_cost_usd']}")
check("Remaining = limit - spent", abs(s["daily_remaining_usd"] - 4.50) < 1e-6,
      f"remaining=${s['daily_remaining_usd']}")

b2 = BudgetEnforcer(daily_limit=0.001, hourly_limit=100.0)
b2.record_cost(0.002)
try:
    b2.check_budget()
    check("Daily budget blocks when exceeded", False, "should have raised!")
except BudgetExceededError as e:
    check("Daily budget blocks when exceeded", True, f"blocked at ${e.spent:.4f}")


# ════════════════════════════════════════════════════════════
# 3. RATE LIMITER
# ════════════════════════════════════════════════════════════
print("\n🚦 3. Rate Limiter")
rl = RateLimiter(requests_per_hour=3)

for i in range(3):
    rl.check("user_a")
r4 = rl.check("user_a")
check("4th request blocked (limit=3)", not r4["allowed"],
      f"allowed={r4['allowed']}")
check("retry_after > 0", r4.get("retry_after", 0) > 0,
      f"retry_after={r4.get('retry_after')}")

other = rl.check("user_b")
check("Different user unaffected", other["allowed"])

stats = rl.stats()
check("Stats: total_blocked >= 1", stats["total_blocked"] >= 1,
      f"blocked={stats['total_blocked']}")
check("Stats: total_allowed >= 3",  stats["total_allowed"] >= 3,
      f"allowed={stats['total_allowed']}")


# ════════════════════════════════════════════════════════════
# 4. EXACT CACHE
# ════════════════════════════════════════════════════════════
print("\n💾 4. Exact Cache")
from app.cache import ExactCache
c = ExactCache(ttl=60, max_size=10)

miss = c.get("What is Python?", "gemini-1.5-flash")
check("Miss on empty cache", miss is None)

c.set("What is Python?", "gemini-1.5-flash", "Python is a programming language.", 0.001)
hit = c.get("What is Python?", "gemini-1.5-flash")
check("Hit after set", hit is not None)
check("Response matches", hit["response"] == "Python is a programming language.")

wrong_model = c.get("What is Python?", "gemini-1.5-pro")
check("Different model = miss", wrong_model is None)

cstats = c.stats()
check("Hit rate tracked", cstats["hit_rate_pct"] > 0,
      f"hit_rate={cstats['hit_rate_pct']}%")

# TTL expiry
c_short = ExactCache(ttl=0, max_size=10)
c_short.set("expire test", "flash", "val", 0.0)
time.sleep(0.01)
check("Expired entry returns None", c_short.get("expire test", "flash") is None)


# ════════════════════════════════════════════════════════════
# 5. FULL ROUTER PIPELINE
# ════════════════════════════════════════════════════════════
print("\n🔄 5. Full Router Pipeline (Mock Mode)")
router = LLMRouter()

# Basic call
r1 = router.process("What is machine learning?", user_id="prisha")
check("Basic call returns response", len(r1.get("response","")) > 0)
check("Has all metadata fields", all(k in r1 for k in
      ["response","model","cost_usd","cache_hit","complexity_score","latency_ms","tokens"]))
check("cost_usd > 0 for real call", r1["cost_usd"] > 0, f"${r1['cost_usd']}")
check("cache_hit = False first call", r1["cache_hit"] == False)
check("cache_type = none first call", r1["cache_type"] == "none")

# Cache hit on repeat
r2 = router.process("What is machine learning?", user_id="prisha")
check("Exact cache hit on repeat",   r2["cache_hit"] == True,
      f"cache_type={r2['cache_type']}")
check("Cache hit costs $0",          r2["cost_usd"] == 0.0)
check("Cache type = exact",          r2["cache_type"] == "exact")

# Simple query → Flash
r3 = router.process("Hi", user_id="prisha")
check("Simple query uses Flash", "flash" in r3["model"].lower(), r3["model"])

# Force model override
r4 = router.process("Hi", user_id="prisha", force_model="gemini-1.5-pro")
check("Force model override works", "pro" in r4["model"].lower(), r4["model"])

# Budget block
router2 = LLMRouter()
router2.budget.update_limits(daily=0.000001)
router2.budget.record_cost(0.001)
try:
    router2.process("any query", user_id="test")
    check("Budget block raises", False, "should have raised!")
except (BudgetExceededError, ValueError):
    check("Budget block raises", True)

# Rate limit block
router3 = LLMRouter()
router3.rate_limiter = RateLimiter(requests_per_hour=1)
router3.process("first request", user_id="limited")
try:
    router3.process("second request", user_id="limited")
    check("Rate limit block raises", False, "should have raised!")
except ValueError:
    check("Rate limit block raises", True)


# ════════════════════════════════════════════════════════════
# 6. LOGGER
# ════════════════════════════════════════════════════════════
print("\n📝 6. CSV Logger")
from app.logger import RequestLogger
import tempfile, os

with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
    tmpfile = f.name

log = RequestLogger(log_file=tmpfile)
log.log("prisha", "What is AI?", "gemini-1.5-flash", 0.25, 20, 80, 0.00012, False, "none", 145.3)
log.log("prisha", "Same question", "gemini-1.5-flash", 0.25, 0, 0, 0.0, True, "exact", 3.1)
log.log("other_user", "Different query", "gemini-1.5-pro", 0.80, 50, 200, 0.003, False, "none", 890.0)

rows = log.read_all()
check("Rows logged = 3", len(rows) == 3, f"got {len(rows)}")
check("Most recent first", rows[0]["user_id"] == "other_user")

csv_str = log.export_csv_string()
check("CSV export has header", "timestamp" in csv_str)
check("CSV export has all rows", csv_str.count("\n") >= 4)
os.unlink(tmpfile)


# ════════════════════════════════════════════════════════════
# 7. STATS AGGREGATION
# ════════════════════════════════════════════════════════════
print("\n📊 7. Stats / Analytics")
router4 = LLMRouter()
router4.process("test query one",   user_id="u1")
router4.process("test query two",   user_id="u1")
router4.process("test query one",   user_id="u1")  # cache hit

stats = router4.get_full_stats()
check("Stats has exact_cache",    "exact_cache"    in stats)
check("Stats has semantic_cache", "semantic_cache" in stats)
check("Stats has budget",         "budget"         in stats)
check("Stats has rate_limiter",   "rate_limiter"   in stats)

ec = stats["exact_cache"]
check("Cache has 1 hit (3rd call)", ec["hits"] >= 1, f"hits={ec['hits']}")
check("Cache hit_rate_pct > 0",     ec["hit_rate_pct"] > 0)

bud = stats["budget"]
check("Budget tracks total_cost", bud["total_cost_usd"] > 0, f"${bud['total_cost_usd']}")


# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
passed = sum(results)
total  = len(results)
print()
print("═"*58)
print(f"  RESULT: {passed}/{total} checks passed  {'🎉' if passed == total else '⚠️'}")
if passed < total:
    print(f"  {total-passed} checks failed — scroll up for ❌ details")
print("═"*58)