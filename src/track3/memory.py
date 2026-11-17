"""What the agent remembers between rounds, saved as JSON so a restart does not forget."""
import json
from collections import defaultdict
from pathlib import Path


class Memory:
    def __init__(self, path: str):
        self.path = Path(path)
        data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.sent: dict = data.get("sent", {})         # round_id -> offers we sent (with markup and buyer type)
        self.rounds: list = data.get("rounds", [])     # results of cleared rounds, oldest first
        self.policy_state: dict = data.get("policy_state", {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"sent": self.sent, "rounds": self.rounds, "policy_state": self.policy_state}, ensure_ascii=False, indent=1),
                             encoding="utf-8")

    def record_sent(self, round_id: str, offers: list[dict], state: dict, tv: dict) -> None:
        buyers = {r["rfq_id"]: (r["buyer"], r["buyer_type"]) for r in state["rfqs"]}
        specs = {r['rfq_id']: dict(r['spec']) for r in state['rfqs']}
        self.sent[round_id] = [{**o, "buyer": buyers[o["rfq_id"]][0], "buyer_type": buyers[o["rfq_id"]][1],
                                "spec": specs[o['rfq_id']],
                                "markup": round(o["price_per_kg"] / tv[o["lot_id"]], 3)} for o in offers]
        self.save()

    def record_results(self, results: dict | None) -> None:
        if not results or not results.get("round_id") or any(r["round_id"] == results["round_id"] for r in self.rounds):
            return
        self.rounds.append(results)
        self.save()

    def summary(self, last: int = 3) -> str:
        """A few short lines for the LLM prompt."""
        # TODO: this only looks at the last few rounds. Trends over the whole game, per buyer persona,
        #       may tell you more (ผู้ซื้อแต่ละรายมีนิสัยต่างกัน)
        lines = []
        for rnd in self.rounds[-last:]:
            sent = {(o["rfq_id"], o["lot_id"]): o for o in self.sent.get(rnd["round_id"], [])}
            mine = []
            for o in rnd["my_offers"]:
                s = sent.get((o["rfq_id"], o["lot_id"]), {})
                mine.append(f"{s.get('buyer_type', '?')} x{s.get('markup', '?')} {o['status']}")
            by_type = defaultdict(lambda: [0, 0])
            for row in rnd["market_summary"]:
                by_type[row["buyer_type"]][0] += row["wanted_kg"]
                by_type[row["buyer_type"]][1] += row["bought_kg"]
            market = ", ".join(f"{t} bought {b * 100 // max(w, 1)}% of wanted" for t, (w, b) in by_type.items())
            lines.append(f"{rnd['round_id']}: my offers [{'; '.join(mine) or 'none'}]; market: {market}")
        return "\n".join(lines) or "none yet"

    def _observations(self, buyer: str | None, buyer_type: str) -> list[dict]:
        """Join sent offers to their market outcomes.  Unknown outcomes are ignored."""
        observations = []
        for rnd in self.rounds:
            sent = {(o["rfq_id"], o["lot_id"]): o for o in self.sent.get(rnd["round_id"], [])}
            for result in rnd.get("my_offers", []):
                offer = sent.get((result.get("rfq_id"), result.get("lot_id")))
                if not offer or offer.get("buyer_type") != buyer_type:
                    continue
                if buyer is not None and offer.get("buyer") != buyer:
                    continue
                if result.get("status") in {"ACCEPTED", "PARTIAL", "OUTBID", "ABOVE_LIMIT"}:
                    observations.append({"markup": offer["markup"], "status": result["status"]})
        return observations

    def markup_for(self, buyer: str, buyer_type: str, default: float) -> float:
        """Recommend the next markup from observed outcomes.

        Buyer-specific evidence is preferred.  If there are fewer than two useful
        observations, use the buyer type as a small prior instead of overreacting
        to one lucky or unlucky round.
        """
        own = self._observations(buyer, buyer_type)
        evidence = own if len(own) >= 2 else self._observations(None, buyer_type)
        if not evidence:
            return default

        accepted = [o["markup"] for o in evidence if o["status"] == "ACCEPTED"]
        partial = [o["markup"] for o in evidence if o["status"] == "PARTIAL"]
        too_high = [o["markup"] for o in evidence if o["status"] == "ABOVE_LIMIT"]
        outbid = [o["markup"] for o in evidence if o["status"] == "OUTBID"]

        # A known ceiling is stronger evidence than a general outbid.  Keep a
        # margin below it; the market's hidden ceiling can vary round to round.
        if too_high:
            target = min(min(too_high) - 0.02, default - 0.005)
        elif accepted:
            # Test a little higher than the best full sale.  Partial fills are
            # treated as near-clearing evidence, not a reason for a sharp move.
            target = max(accepted) + 0.01
            if partial:
                target = min(target, max(partial) + 0.005)
        elif outbid:
            target = min(min(outbid) - 0.015, default - 0.005)
        else:
            target = default

        # Blend with the prior while data is scarce, then cap the change per
        # decision.  This is the real-time learning layer used even without LLM.
        weight = min(len(evidence) / 6, 1.0)
        target = default * (1 - weight) + target * weight
        return round(max(0.85, min(1.30, target)), 3)

    def buyer_summary(self, buyer: str, buyer_type: str) -> str:
        observations = self._observations(buyer, buyer_type)
        if not observations:
            return "no direct evidence"
        counts = defaultdict(int)
        for item in observations:
            counts[item["status"]] += 1
        return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))

    def evidence_count(self, buyer: str, buyer_type: str) -> int:
        """How much direct evidence is available for a bounded price test."""
        return len(self._observations(buyer, buyer_type))

    def market_signal(self, buyer: str, buyer_type: str) -> tuple[float, str]:
        """Return a small RFQ-priority adjustment from public market summaries.

        An unfilled RFQ with few offers is worth pursuing; a completely filled RFQ
        with many offers is likely crowded.  This ranks RFQs, rather than claiming
        that the public price fields reveal competitors' value-normalised prices.
        """
        rows = []
        for rnd in self.rounds:
            for row in rnd.get("market_summary", []):
                if row.get("buyer") == buyer:
                    rows.append(row)
        if not rows:
            for rnd in self.rounds:
                rows.extend(row for row in rnd.get("market_summary", []) if row.get("buyer_type") == buyer_type)
        if not rows:
            return 0.0, "no market history"
        fill = sum(row["bought_kg"] / max(row["wanted_kg"], 1) for row in rows) / len(rows)
        offers = sum(row.get("offers", 0) for row in rows) / len(rows)
        signal = max(-0.5, min(0.75, (1 - fill) - max(0, offers - 4) * .08))
        return signal, f"fill={fill:.0%}, offers={offers:.1f}"
