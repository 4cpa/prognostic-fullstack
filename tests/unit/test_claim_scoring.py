from app.core.claim_scoring import score_claims


def _claim(
    *,
    claim_text: str,
    claim_type: str,
    source_url: str,
    source_title: str,
    source_type: str = "other",
    claim_confidence: float = 0.6,
    time_relevance: float = 0.7,
    relevance_score: float = 0.5,
    freshness_score: float = 0.5,
):
    return {
        "claim_text": claim_text,
        "claim_type": claim_type,
        "source_url": source_url,
        "source_title": source_title,
        "source_type": source_type,
        "claim_confidence": claim_confidence,
        "time_relevance": time_relevance,
        "relevance_score": relevance_score,
        "freshness_score": freshness_score,
    }


def test_score_claims_empty_input():
    result = score_claims([])

    assert result["scored_claims"] == []
    assert result["top_pro_claims"] == []
    assert result["top_contra_claims"] == []
    assert result["top_uncertainties"] == []
    assert result["top_background"] == []
    assert result["net_signal"] == 0.0
    assert result["diagnostics"]["claim_count_input"] == 0
    assert result["diagnostics"]["claim_count_scored"] == 0


def test_official_and_wire_sources_score_higher_than_other_when_claims_equal():
    claims = [
        _claim(
            claim_text="Official statement confirms continuity.",
            claim_type="contra",
            source_url="https://ec.europa.eu/news/statement",
            source_title="EU Commission statement",
            source_type="official",
        ),
        _claim(
            claim_text="Wire report confirms continuity.",
            claim_type="contra",
            source_url="https://www.reuters.com/world/europe/item",
            source_title="Reuters report",
            source_type="wire",
        ),
        _claim(
            claim_text="Aggregator report confirms continuity.",
            claim_type="contra",
            source_url="https://www.msn.com/news/item",
            source_title="MSN report",
            source_type="other",
        ),
    ]

    result = score_claims(claims)
    scored = {item["source_title"]: item for item in result["scored_claims"]}

    assert scored["EU Commission statement"]["final_weight"] > scored["MSN report"]["final_weight"]
    assert scored["Reuters report"]["final_weight"] > scored["MSN report"]["final_weight"]


def test_duplicate_claim_texts_are_merged():
    claims = [
        _claim(
            claim_text="Ceasefire talks resumed between the parties.",
            claim_type="contra",
            source_url="https://www.reuters.com/world/middle-east/a",
            source_title="Reuters A",
            source_type="wire",
        ),
        _claim(
            claim_text="Ceasefire talks resumed between the parties.",
            claim_type="contra",
            source_url="https://www.apnews.com/article/b",
            source_title="AP B",
            source_type="wire",
        ),
    ]

    result = score_claims(claims)

    assert result["diagnostics"]["claim_count_input"] == 2
    assert result["diagnostics"]["claim_count_merged"] == 1
    assert len(result["scored_claims"]) == 1

    merged = result["scored_claims"][0]
    assert merged["supporting_source_count"] == 2
    assert merged["supporting_domain_count"] == 2


def test_same_domain_claims_get_limited_independence():
    claims = [
        _claim(
            claim_text="Diplomatic channel remains open.",
            claim_type="contra",
            source_url="https://www.reuters.com/world/item-1",
            source_title="Reuters 1",
            source_type="wire",
        ),
        _claim(
            claim_text="Indirect talks continue.",
            claim_type="contra",
            source_url="https://www.reuters.com/world/item-2",
            source_title="Reuters 2",
            source_type="wire",
        ),
        _claim(
            claim_text="Backchannel diplomacy continues.",
            claim_type="contra",
            source_url="https://www.reuters.com/world/item-3",
            source_title="Reuters 3",
            source_type="wire",
        ),
    ]

    result = score_claims(claims)

    assert len(result["scored_claims"]) == 3
    for item in result["scored_claims"]:
        assert item["independence_weight"] < 1.0


def test_support_boost_rewards_multi_domain_support_for_identical_claim():
    claims = [
        _claim(
            claim_text="Talks with Iran continue through intermediaries.",
            claim_type="contra",
            source_url="https://www.reuters.com/world/item",
            source_title="Reuters item",
            source_type="wire",
        ),
        _claim(
            claim_text="Talks with Iran continue through intermediaries.",
            claim_type="contra",
            source_url="https://www.dw.com/en/item",
            source_title="DW item",
            source_type="major_media",
        ),
        _claim(
            claim_text="Military activity continues in the region.",
            claim_type="uncertainty",
            source_url="https://www.cfr.org/global-conflict-tracker/item",
            source_title="CFR tracker",
            source_type="research",
        ),
    ]

    result = score_claims(claims)
    scored = result["scored_claims"]

    merged_contra = next(item for item in scored if item["claim_type"] == "contra")
    uncertainty = next(item for item in scored if item["claim_type"] == "uncertainty")

    assert merged_contra["supporting_domain_count"] == 2
    assert merged_contra["support_boost"] > 0.0
    assert merged_contra["final_weight"] >= merged_contra["support_boost"]
    assert uncertainty["support_boost"] == 0.0


def test_uncertainty_claims_reduce_effective_net_signal():
    claims = [
        _claim(
            claim_text="Major powers are preparing for direct war.",
            claim_type="pro",
            source_url="https://www.reuters.com/world/item-pro",
            source_title="Reuters pro",
            source_type="wire",
            claim_confidence=0.8,
            time_relevance=0.8,
        ),
        _claim(
            claim_text="Regional escalation continues without clear major-power entry.",
            claim_type="uncertainty",
            source_url="https://www.cfr.org/analysis/item-1",
            source_title="CFR 1",
            source_type="research",
            claim_confidence=0.8,
            time_relevance=0.8,
        ),
        _claim(
            claim_text="Shipping disruption risk remains elevated.",
            claim_type="uncertainty",
            source_url="https://www.reuters.com/world/item-unc-2",
            source_title="Reuters unc 2",
            source_type="wire",
            claim_confidence=0.8,
            time_relevance=0.8,
        ),
    ]

    result = score_claims(claims)

    raw_net = (
        result["diagnostics"]["pro_weight_sum"]
        - result["diagnostics"]["contra_weight_sum"]
    )

    assert raw_net > 0
    assert result["diagnostics"]["uncertainty_weight_sum"] > 0
    assert result["diagnostics"]["uncertainty_drag"] > 0
    assert result["net_signal"] < raw_net


def test_top_bucket_outputs_match_claim_types():
    claims = [
        _claim(
            claim_text="Direct conflict between major powers becomes more plausible.",
            claim_type="pro",
            source_url="https://www.reuters.com/a",
            source_title="Reuters A",
            source_type="wire",
        ),
        _claim(
            claim_text="Ceasefire talks remain active.",
            claim_type="contra",
            source_url="https://www.reuters.com/b",
            source_title="Reuters B",
            source_type="wire",
        ),
        _claim(
            claim_text="Regional escalation continues.",
            claim_type="uncertainty",
            source_url="https://www.cfr.org/c",
            source_title="CFR C",
            source_type="research",
        ),
        _claim(
            claim_text="Background context on historical conflict patterns.",
            claim_type="background",
            source_url="https://example.com/d",
            source_title="Example D",
            source_type="other",
        ),
    ]

    result = score_claims(claims)

    assert len(result["top_pro_claims"]) == 1
    assert len(result["top_contra_claims"]) == 1
    assert len(result["top_uncertainties"]) == 1
    assert len(result["top_background"]) == 1

    assert result["top_pro_claims"][0]["claim_type"] == "pro"
    assert result["top_contra_claims"][0]["claim_type"] == "contra"
    assert result["top_uncertainties"][0]["claim_type"] == "uncertainty"
    assert result["top_background"][0]["claim_type"] == "background"
