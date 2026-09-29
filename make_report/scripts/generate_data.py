#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate plausible experimental data with uncertainties.

Reads a small JSON config describing one or more quantities, samples them
with Gaussian/quantized noise, and emits a JSON blob ready to paste into
report.json (data_processing.tables).

Usage:
    python generate_data.py --config data_config.json --out data.json
"""
import argparse
import json
import math
import random
import sys


def _sample_normal(mu, sigma, n, rng):
    return [rng.gauss(mu, sigma) for _ in range(n)]


def _round_sig(x, sig):
    if x == 0:
        return 0.0
    d = sig - int(math.floor(math.log10(abs(x)))) - 1
    return round(x, d)


def analyze(values, delta_ins, resolution, k=2):
    """Type A / Type B / combined uncertainty for a set of readings."""
    n = len(values)
    mean = sum(values) / n
    if n > 1:
        var = sum((v - mean) ** 2 for v in values) / (n - 1)
        s = math.sqrt(var)
        u_a = s / math.sqrt(n)
    else:
        u_a = 0.0
    u_b_ins = delta_ins / math.sqrt(3.0)
    u_b_res = resolution / (2.0 * math.sqrt(3.0))
    u_b = math.sqrt(u_b_ins ** 2 + u_b_res ** 2)
    u_c = math.sqrt(u_a ** 2 + u_b ** 2)
    u_exp = k * u_c
    return {
        "n": n,
        "mean": mean,
        "std": s if n > 1 else 0.0,
        "u_a": u_a,
        "u_b_ins": u_b_ins,
        "u_b_res": u_b_res,
        "u_b": u_b,
        "u_c": u_c,
        "U": u_exp,
        "k": k,
    }


def build(config):
    rng = random.Random(config.get("seed", 20260920))
    out = {"quantities": {}, "tables": []}
    for q in config["quantities"]:
        values = _sample_normal(q["true"], q.get("sigma", 0.01),
                                q.get("n", 10), rng)
        res = q.get("resolution", 0.001)
        values = [round(v / res) * res for v in values]
        stats = analyze(values, q.get("delta_ins", res), res,
                        q.get("k", 2))
        rec = {
            "name": q["name"],
            "unit": q.get("unit", ""),
            "values": values,
            "stats": stats,
        }
        out["quantities"][q["name"]] = rec

        cols = ["次数 $i$", q["name"] + (f" /{q['unit']}" if q.get("unit") else "")]
        rows = [[str(i + 1), f"{v:g}"] for i, v in enumerate(values)]
        rows.append(["$\\bar{x}$", f"{stats['mean']:.6g}"])
        out["tables"].append({
            "caption": f"表  {q['name']} 测量数据",
            "columns": cols,
            "rows": rows,
            "note": (f"仪器误差限 $\\Delta={q.get('delta_ins', res):g}$，"
                     f"分辨力 $\\delta={res:g}$，$k={stats['k']}$。"),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    with open(args.config, "r", encoding="utf-8-sig") as f:
        config = json.load(f)
    result = build(config)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    sys.stdout.write("wrote " + args.out + "\n")


if __name__ == "__main__":
    main()
