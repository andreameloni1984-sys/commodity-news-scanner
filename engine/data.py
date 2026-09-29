--- a/engine/data.py
+++ b/engine/data.py
@@
 PROVIDER_ORDER = {
@@
 }

@@
 def _fetch_biquote(
     symbol: str,
 ):
@@
-    urls = (
-        f"{BIQUOTE_BASE}/candles",
-        f"{BIQUOTE_BASE}/history",
-        f"{BIQUOTE_BASE}/timeseries",
-    )
+    # Official OHLC endpoint first. Legacy endpoints remain
+    # as compatibility fallbacks.
+    urls = (
+        f"{BIQUOTE_BASE}/{provider_symbol}/ohlc",
+        f"{BIQUOTE_BASE}/candles",
+        f"{BIQUOTE_BASE}/history",
+        f"{BIQUOTE_BASE}/timeseries",
+    )
@@
-    params_variants = (
-        {
-            "symbol": provider_symbol,
-            "interval": "5m",
-            "limit": max(
-                LOOKBACK,
-                120,
-            ),
-        },
-        {
-            "symbol": provider_symbol,
-            "timeframe": "5m",
-            "limit": max(
-                LOOKBACK,
-                120,
-            ),
-        },
-    )
+    params_variants = (
+        {
+            "interval": "5m",
+            "limit": min(
+                max(LOOKBACK, 120),
+                1000,
+            ),
+        },
+        {
+            "symbol": provider_symbol,
+            "interval": "5m",
+            "limit": min(
+                max(LOOKBACK, 120),
+                1000,
+            ),
+        },
+        {
+            "symbol": provider_symbol,
+            "timeframe": "5m",
+            "limit": min(
+                max(LOOKBACK, 120),
+                1000,
+            ),
+        },
+    )
@@
 def load_data(
@@
-        # ----------------------------------------------------
-        # SUCCESS
-        # ----------------------------------------------------
-
-        if candles:
-
-            # Resolve symbol metadata.
+        # ----------------------------------------------------
+        # CANDLES RECEIVED — VALIDATE BEFORE ACCEPTING
+        # ----------------------------------------------------
+
+        if candles:
+
+            # A provider can return valid OHLC candles that are
+            # technically parseable but too old for intraday use.
+            # Do not accept stale data just because HTTP succeeded.
+            validated_probe, validation_probe_error = (
+                _validate_candles(candles)
+            )
+
+            if (
+                validation_probe_error
+                or len(validated_probe) < MIN_CANDLES_REQUIRED
+            ):
+                attempts[-1]["success"] = False
+                attempts[-1]["error"] = (
+                    validation_probe_error
+                    or "INSUFFICIENT_CANDLES"
+                )
+                continue
+
+            latest_probe = validated_probe[-1]["timestamp"]
+            probe_fresh, probe_age, probe_status = _freshness(
+                latest_probe
+            )
+
+            attempts[-1]["fresh_live"] = probe_fresh
+            attempts[-1]["age_seconds"] = round(probe_age, 1)
+            attempts[-1]["freshness_status"] = probe_status
+
+            if not probe_fresh:
+                # If the market is actually closed, keep the data so
+                # _finalize() can classify it as MARKET_CLOSED.
+                closed_status = classify_data_status(
+                    state.commodity,
+                    live=False,
+                    data_ok=True,
+                )
+
+                if closed_status != "MARKET_CLOSED":
+                    attempts[-1]["success"] = False
+                    attempts[-1]["error"] = (
+                        "STALE_PROVIDER:"
+                        f"{round(probe_age, 1)}s"
+                    )
+                    continue
+
+            # Resolve symbol metadata.
