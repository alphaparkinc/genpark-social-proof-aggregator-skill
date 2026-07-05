"""
social-proof-aggregator-skill: Client SDK
Aggregate social proof signals into display-ready widgets and trust badges.
"""
from __future__ import annotations
from typing import Optional
import re

TRUST_BADGE_RULES = [
    (4.8, None,  None,  "Top Rated Product"),
    (4.5, None,  500,   "Highly Rated"),
    (None,None,  1000,  "Best Seller"),
    (None,None,  5000,  "Community Favorite"),
    (None, 80,   None,  "Loved by Repeat Buyers"),
    (None, None, None,  "Verified Purchases"),
]

RATING_LABELS = {5: "Excellent", 4: "Great", 3: "Good", 2: "Fair", 1: "Poor"}

POSITIVE_SENTIMENT = ["love", "amazing", "excellent", "perfect", "great", "fantastic", "recommend", "best", "quality", "fast", "happy", "wonderful"]
NEGATIVE_SENTIMENT = ["broken", "damaged", "terrible", "awful", "disappointed", "wrong", "missing", "slow", "poor", "waste"]


class SocialProofClient:
    """
    SDK for aggregating social proof signals into display-ready components.
    """

    def aggregate(
        self,
        product_data: dict,
        reviews: Optional[list[dict]] = None,
        display_format: str = "all",
    ) -> dict:
        """
        Aggregate social proof signals.

        Args:
            product_data: {
                total_reviews, avg_rating, units_sold,
                repeat_buyers_pct (0-100), verified_purchase_pct (0-100)
            }
            reviews:        List of {rating, text, verified, date, helpful_votes}.
            display_format: widget / badge / summary / all

        Returns:
            dict with trust_score, widget, trust_badges, featured_reviews
        """
        reviews = reviews or []
        total_reviews = int(product_data.get("total_reviews", len(reviews)))
        avg_rating = float(product_data.get("avg_rating", 0))
        units_sold = int(product_data.get("units_sold", 0))
        repeat_pct = float(product_data.get("repeat_buyers_pct", 0))
        verified_pct = float(product_data.get("verified_purchase_pct", 80))

        # Trust score
        trust_score = self._calc_trust_score(avg_rating, total_reviews, units_sold, repeat_pct, verified_pct)

        # Rating distribution
        dist = self._rating_distribution(reviews, total_reviews, avg_rating)

        # Widget
        widget = {
            "avg_rating": avg_rating,
            "avg_rating_label": RATING_LABELS.get(round(avg_rating), "Good"),
            "total_reviews": total_reviews,
            "stars_display": self._star_display(avg_rating),
            "rating_distribution": dist,
            "units_sold": units_sold,
            "units_sold_display": self._format_count(units_sold),
            "repeat_buyers_pct": repeat_pct,
            "verified_pct": verified_pct,
            "trust_score": trust_score,
        }

        # Trust badges
        badges = self._build_badges(avg_rating, units_sold, repeat_pct, verified_pct, total_reviews)

        # Featured reviews (highest rated + most helpful)
        featured = self._select_featured(reviews)

        result = {"trust_score": trust_score}
        if display_format in ("widget", "all"):
            result["widget"] = widget
        if display_format in ("badge", "all"):
            result["trust_badges"] = badges
        if display_format in ("summary", "all"):
            result["featured_reviews"] = featured
            result["sentiment_summary"] = self._sentiment_summary(reviews)

        return result

    def _calc_trust_score(self, rating, reviews, sold, repeat, verified) -> float:
        score = 0.0
        # Rating (35 pts)
        score += min(rating / 5, 1) * 35
        # Review volume (20 pts)
        score += min(reviews / 1000, 1) * 20
        # Sales volume (20 pts)
        score += min(sold / 5000, 1) * 20
        # Repeat buyers (15 pts)
        score += min(repeat / 100, 1) * 15
        # Verified purchases (10 pts)
        score += min(verified / 100, 1) * 10
        return round(score, 1)

    @staticmethod
    def _rating_distribution(reviews, total, avg) -> list[dict]:
        counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        for r in reviews:
            rating = int(r.get("rating", 3))
            if rating in counts:
                counts[rating] += 1
        if not reviews and total > 0:
            # Estimate from avg
            counts[5] = int(total * max(0, avg - 4) * 2)
            counts[4] = int(total * max(0, min(avg - 3, 1)) * 0.6)
            counts[3] = int(total * 0.1)
            counts[2] = int(total * 0.05)
            counts[1] = max(0, total - counts[5] - counts[4] - counts[3] - counts[2])
        return [
            {"stars": s, "count": counts[s], "pct": round(counts[s] / max(total, 1) * 100, 1)}
            for s in [5, 4, 3, 2, 1]
        ]

    @staticmethod
    def _star_display(rating: float) -> str:
        full = int(rating)
        half = 1 if rating - full >= 0.5 else 0
        empty = 5 - full - half
        return "*" * full + ("~" if half else "") + "." * empty

    @staticmethod
    def _format_count(n: int) -> str:
        if n >= 1000000: return f"{n/1000000:.1f}M+ sold"
        if n >= 1000: return f"{n//1000}K+ sold"
        return f"{n}+ sold"

    @staticmethod
    def _build_badges(rating, sold, repeat, verified, reviews) -> list[str]:
        badges = []
        if rating >= 4.8: badges.append("Top Rated")
        elif rating >= 4.5: badges.append("Highly Rated")
        if sold >= 5000: badges.append("Community Favorite")
        elif sold >= 1000: badges.append("Best Seller")
        if repeat >= 60: badges.append("Loved by Repeat Buyers")
        if verified >= 85: badges.append("Verified Purchases")
        if reviews >= 500: badges.append("500+ Reviews")
        return badges[:5]

    @staticmethod
    def _select_featured(reviews: list[dict]) -> list[dict]:
        good = [r for r in reviews if int(r.get("rating", 0)) >= 4]
        good.sort(key=lambda x: (x.get("helpful_votes", 0), x.get("rating", 0)), reverse=True)
        return good[:3]

    @staticmethod
    def _sentiment_summary(reviews: list[dict]) -> dict:
        pos, neg, total = 0, 0, len(reviews)
        for r in reviews:
            text = str(r.get("text", "")).lower()
            if any(w in text for w in POSITIVE_SENTIMENT): pos += 1
            if any(w in text for w in NEGATIVE_SENTIMENT): neg += 1
        return {
            "positive_reviews": pos,
            "negative_reviews": neg,
            "neutral_reviews": total - pos - neg,
            "positive_pct": round(pos / max(total, 1) * 100, 1),
        }
