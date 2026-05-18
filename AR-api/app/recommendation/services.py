from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import logging
import math
import re
from typing import Any

import httpx
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.playlist.models import PlaylistModel, PlaylistVideoModel
from app.recommendation.models import (
    UserInterestProfileModel,
    UserSearchEventModel,
    UserVideoEventModel,
)
from app.recommendation.schemas import (
    RecommendationClickEventSchema,
    RecommendationResponseSchema,
    RecommendationResolvedEntitySchema,
    RecommendationSearchEventSchema,
    RecommendationSeedSchema,
)

logger = logging.getLogger(__name__)

_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "at",
    "for",
    "from",
    "how",
    "in",
    "is",
    "me",
    "of",
    "on",
    "or",
    "show",
    "that",
    "the",
    "to",
    "video",
    "videos",
    "with",
}


class RecommendationService:
    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db

    async def ingest_search_event(
        self,
        *,
        user_id: int,
        payload: RecommendationSearchEventSchema,
    ) -> None:
        parsed_intent = payload.parsed_intent if isinstance(payload.parsed_intent, dict) else {}
        event = UserSearchEventModel(
            user_id=user_id,
            query=payload.query.strip(),
            parsed_intent=parsed_intent,
        )
        self.db.add(event)

        profile = await self._get_or_create_profile(user_id)
        self._apply_decay(profile)

        self._boost_weights(
            profile.category_weights,
            self._to_str_list(parsed_intent.get("categories")),
            2.0,
        )
        self._boost_weights(
            profile.tag_weights,
            self._to_str_list(parsed_intent.get("tags")),
            1.6,
        )
        self._boost_weights(
            profile.entity_weights,
            self._to_str_list(parsed_intent.get("entities")),
            2.0,
        )
        self._boost_weights(profile.entity_weights, self._extract_terms(payload.query), 0.6)

    async def ingest_video_event(
        self,
        *,
        user_id: int,
        payload: RecommendationClickEventSchema,
    ) -> None:
        context = payload.event_context if isinstance(payload.event_context, dict) else {}
        event = UserVideoEventModel(
            user_id=user_id,
            video_id=payload.video_id.strip(),
            event_type=payload.event_type.strip().lower(),
            event_context=context,
        )
        self.db.add(event)

        profile = await self._get_or_create_profile(user_id)
        self._apply_decay(profile)
        self._boost_weights(profile.entity_weights, [payload.video_id.strip()], 2.5)
        self._boost_weights(
            profile.category_weights,
            self._to_str_list(context.get("categories")),
            2.4,
        )
        self._boost_weights(
            profile.tag_weights,
            self._to_str_list(context.get("tags")),
            1.8,
        )
        self._boost_weights(
            profile.entity_weights,
            self._to_str_list(context.get("entities")),
            2.0,
        )

    async def get_recommendations(
        self,
        *,
        user_id: int,
        limit: int,
        refresh: bool = False,
    ) -> RecommendationResponseSchema:
        safe_limit = max(1, min(limit, settings.RECOMMENDATION_MAX_LIMIT))
        profile = await self._get_or_create_profile(user_id)
        if refresh:
            self._apply_decay(profile)
        await self._merge_playlist_signals(user_id=user_id, profile=profile)

        profile_seed = self._build_seed(profile)
        recent_seed = await self._build_seed_from_recent_search_events(user_id=user_id)
        seed = self._merge_seed(profile_seed=profile_seed, recent_seed=recent_seed)
        resolved_entities = await self._resolve_entity_ids(seed["entities"])
        seed_payload = RecommendationSeedSchema(
            categories=seed["categories"],
            tags=seed["tags"],
            entities=seed["entities"],
            query_terms=seed["query_terms"],
            resolved_entities=resolved_entities,
        )
        personalized_items = await self._fetch_personalized_candidates(seed=seed, limit=safe_limit)
        trending_items = await self._fetch_trending_candidates(limit=safe_limit)
        recent_seen_ids = await self._get_recent_seen_video_ids(user_id=user_id, limit=200)
        blended = self._blend_candidates(
            user_id=user_id,
            personalized_items=personalized_items,
            trending_items=trending_items,
            seen_video_ids=recent_seen_ids,
            limit=safe_limit,
        )

        return RecommendationResponseSchema(
            items=blended,
            total=len(blended),
            generated_at=datetime.now(timezone.utc),
            seed=seed_payload,
        )

    async def _get_or_create_profile(self, user_id: int) -> UserInterestProfileModel:
        result = await self.db.execute(
            select(UserInterestProfileModel).where(UserInterestProfileModel.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is not None:
            return profile

        profile = UserInterestProfileModel(
            user_id=user_id,
            category_weights={},
            tag_weights={},
            entity_weights={},
        )
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def _merge_playlist_signals(
        self,
        *,
        user_id: int,
        profile: UserInterestProfileModel,
    ) -> None:
        result = await self.db.execute(
            select(PlaylistVideoModel.video_id)
            .join(PlaylistModel, PlaylistModel.id == PlaylistVideoModel.playlist_id)
            .where(PlaylistModel.user_id == user_id)
        )
        video_ids = [video_id for (video_id,) in result.all() if isinstance(video_id, str)]
        if not video_ids:
            return
        counts = Counter(video_ids)
        for video_id, count in counts.items():
            profile.entity_weights[video_id] = float(profile.entity_weights.get(video_id, 0.0)) + (1.2 * float(count))

    async def _fetch_personalized_candidates(
        self,
        *,
        seed: dict[str, list[str]],
        limit: int,
    ) -> list[dict[str, Any]]:
        if not seed["query_terms"] and not seed["categories"] and not seed["tags"]:
            return []

        query_text = " ".join(seed["query_terms"]).strip()
        if not query_text:
            query_text = " ".join((seed["tags"][:2] + seed["categories"][:2])).strip()

        payload = {
            "query": query_text,
            "filters": {
                "categories": seed["categories"],
                "tags": seed["tags"],
            },
            "sort": {"by": "relevance", "order": "desc"},
            "pagination": {"offset": 0, "limit": max(limit * 3, 20)},
        }
        return await self._call_advanced_search(payload)

    async def _fetch_trending_candidates(self, *, limit: int) -> list[dict[str, Any]]:
        payload = {
            "query": "",
            "filters": {},
            "sort": {"by": "views", "order": "desc"},
            "pagination": {"offset": 0, "limit": max(limit * 2, 20)},
        }
        return await self._call_advanced_search(payload)

    async def _call_advanced_search(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        url = f"{settings.VIDEOS_SEARCH_API_URL.rstrip('/')}/api/videos/advanced-search"
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": settings.VIDEOS_SEARCH_API_KEY,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(settings.RECOMMENDATION_UPSTREAM_TIMEOUT_SECONDS)) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
        except Exception:
            logger.exception("Recommendation upstream request failed")
            return []

        data = body.get("data", body) if isinstance(body, dict) else {}
        if not isinstance(data, dict):
            return []
        items = data.get("items", [])
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]

    def _blend_candidates(
        self,
        *,
        user_id: int,
        personalized_items: list[dict[str, Any]],
        trending_items: list[dict[str, Any]],
        seen_video_ids: set[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}

        def ensure(video_id: str, document: dict[str, Any]) -> dict[str, Any]:
            if video_id not in merged:
                merged[video_id] = {
                    "video_id": video_id,
                    "document": document,
                    "p": 0.0,
                    "t": 0.0,
                    "source": set(),
                }
            return merged[video_id]

        for rank, item in enumerate(personalized_items, start=1):
            video_id = self._video_id_from_item(item)
            if not video_id:
                continue
            document = item.get("document", {}) if isinstance(item.get("document"), dict) else {}
            bucket = ensure(video_id, document)
            score = self._score_from_item(item, rank)
            bucket["p"] = max(float(bucket["p"]), score)
            bucket["source"].add("personalized")

        for rank, item in enumerate(trending_items, start=1):
            video_id = self._video_id_from_item(item)
            if not video_id:
                continue
            document = item.get("document", {}) if isinstance(item.get("document"), dict) else {}
            bucket = ensure(video_id, document)
            score = 1.0 / float(rank + 1)
            bucket["t"] = max(float(bucket["t"]), score)
            bucket["source"].add("trending")

        personalized_weight = settings.RECOMMENDATION_PERSONALIZED_WEIGHT
        trend_weight = 1.0 - personalized_weight

        ranked = []
        for value in merged.values():
            base_score = (personalized_weight * float(value["p"])) + (trend_weight * float(value["t"]))
            freshness_bonus = self._freshness_bonus(value["document"])
            diversity_penalty = 0.0
            if value["video_id"] in seen_video_ids:
                diversity_penalty = 0.25
            final_score = max(0.0, base_score + freshness_bonus - diversity_penalty)
            ranked.append(
                {
                    "video_id": value["video_id"],
                    "document": value["document"],
                    "recommendation_score": final_score,
                    "source": sorted(value["source"]),
                }
            )

        ranked.sort(
            key=lambda item: (float(item["recommendation_score"]), str(item["video_id"])),
            reverse=True,
        )

        filtered = [item for item in ranked if item["video_id"] not in seen_video_ids]
        primary_pool = filtered if len(filtered) >= limit else ranked

        diversify_pool = self._diversify_by_category(primary_pool, cap=max(limit * 3, 18))
        rotated_pool = self._rotate_pool(user_id=user_id, items=diversify_pool)
        return self._mix_exploration(rotated_pool, limit=limit)

    async def _get_recent_seen_video_ids(self, *, user_id: int, limit: int) -> set[str]:
        seen: set[str] = set()

        events_result = await self.db.execute(
            select(UserVideoEventModel.video_id)
            .where(UserVideoEventModel.user_id == user_id)
            .order_by(UserVideoEventModel.created_at.desc())
            .limit(limit)
        )
        for (video_id,) in events_result.all():
            if isinstance(video_id, str) and video_id.strip():
                seen.add(video_id.strip())

        playlist_result = await self.db.execute(
            select(PlaylistVideoModel.video_id)
            .join(PlaylistModel, PlaylistModel.id == PlaylistVideoModel.playlist_id)
            .where(PlaylistModel.user_id == user_id)
            .limit(limit)
        )
        for (video_id,) in playlist_result.all():
            if isinstance(video_id, str) and video_id.strip():
                seen.add(video_id.strip())

        return seen

    def _freshness_bonus(self, document: dict[str, Any]) -> float:
        created_ts = self._extract_created_timestamp(document)
        if created_ts is None:
            return 0.0
        now_ts = datetime.now(timezone.utc).timestamp()
        age_days = max(0.0, (now_ts - created_ts) / 86400.0)
        # Smooth recency decay, max ~0.12 for very fresh content.
        return 0.12 * math.exp(-age_days / 45.0)

    def _extract_created_timestamp(self, document: dict[str, Any]) -> float | None:
        candidates: list[Any] = [
            document.get("created_at"),
            document.get("created_ts"),
            document.get("raw", {}).get("created") if isinstance(document.get("raw"), dict) else None,
        ]
        for service_key in ("cts", "rms"):
            service_obj = document.get(service_key, {})
            if not isinstance(service_obj, dict):
                continue
            service_data = service_obj.get("data", {})
            if not isinstance(service_data, dict):
                continue
            candidates.append(service_data.get("created"))

        for raw in candidates:
            parsed = self._parse_timestamp(raw)
            if parsed is not None:
                return parsed
        return None

    @staticmethod
    def _parse_timestamp(value: Any) -> float | None:
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None
            if cleaned.isdigit():
                value = int(cleaned)
            else:
                try:
                    dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.timestamp()
                except Exception:
                    return None

        if not isinstance(value, (int, float)):
            return None

        number = float(value)
        if number <= 0:
            return None

        if number > 1e14:
            # yyyymmddHHMMSSmmm
            digits = str(int(number))
            if len(digits) >= 8:
                try:
                    year = int(digits[0:4])
                    month = int(digits[4:6])
                    day = int(digits[6:8])
                    hour = int(digits[8:10]) if len(digits) >= 10 else 0
                    minute = int(digits[10:12]) if len(digits) >= 12 else 0
                    second = int(digits[12:14]) if len(digits) >= 14 else 0
                    dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
                    return dt.timestamp()
                except Exception:
                    return None
            return None

        if number > 1e12:
            return number / 1000.0
        if number > 1e10:
            return number / 1000.0
        return number

    def _diversify_by_category(self, items: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
        if not items:
            return []
        category_counts: Counter[str] = Counter()
        diversified: list[dict[str, Any]] = []
        for item in items:
            if len(diversified) >= cap:
                break
            categories = self._extract_categories(item.get("document", {}))
            primary = categories[0] if categories else "__none__"
            if category_counts[primary] >= 3:
                continue
            category_counts[primary] += 1
            diversified.append(item)

        if len(diversified) < cap:
            existing_ids = {item.get("video_id") for item in diversified}
            for item in items:
                if len(diversified) >= cap:
                    break
                if item.get("video_id") in existing_ids:
                    continue
                diversified.append(item)
        return diversified

    def _rotate_pool(self, *, user_id: int, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(items) <= 1:
            return items
        day_key = datetime.now(timezone.utc).strftime("%Y%m%d")
        offset = abs(hash(f"{user_id}:{day_key}")) % len(items)
        return items[offset:] + items[:offset]

    @staticmethod
    def _mix_exploration(items: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
        if not items:
            return []
        if len(items) <= limit:
            return items

        exploit_count = max(1, int(round(limit * 0.8)))
        explore_count = max(0, limit - exploit_count)

        exploit = items[:exploit_count]
        tail = items[exploit_count:]
        if not tail or explore_count <= 0:
            return items[:limit]

        step = max(1, len(tail) // explore_count)
        explore: list[dict[str, Any]] = []
        idx = 0
        while len(explore) < explore_count and idx < len(tail):
            explore.append(tail[idx])
            idx += step

        merged: list[dict[str, Any]] = []
        merged_ids: set[str] = set()
        for item in exploit + explore:
            vid = item.get("video_id")
            if not isinstance(vid, str) or vid in merged_ids:
                continue
            merged_ids.add(vid)
            merged.append(item)
            if len(merged) >= limit:
                return merged

        for item in items:
            vid = item.get("video_id")
            if not isinstance(vid, str) or vid in merged_ids:
                continue
            merged_ids.add(vid)
            merged.append(item)
            if len(merged) >= limit:
                break
        return merged

    @staticmethod
    def _video_id_from_item(item: dict[str, Any]) -> str:
        video_id = item.get("video_id")
        if isinstance(video_id, str) and video_id.strip():
            return video_id.strip()
        document = item.get("document", {})
        if isinstance(document, dict):
            doc_video_id = document.get("video_id")
            if isinstance(doc_video_id, str) and doc_video_id.strip():
                return doc_video_id.strip()
        return ""

    @staticmethod
    def _score_from_item(item: dict[str, Any], rank: int) -> float:
        scores = item.get("scores", {})
        if isinstance(scores, dict):
            for key in ("final", "rrf", "lex", "vec"):
                value = scores.get(key)
                if isinstance(value, (int, float)):
                    return float(value)
        return 1.0 / float(rank + 1)

    @staticmethod
    def _to_str_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        output: list[str] = []
        for item in value:
            if isinstance(item, str):
                cleaned = item.strip()
                if cleaned:
                    output.append(cleaned)
        return output

    @staticmethod
    def _extract_terms(query: str) -> list[str]:
        tokens = [
            token
            for token in re.findall(r"[\w']+", query.lower())
            if len(token) > 2 and token not in _STOP_WORDS
        ]
        return tokens[:8]

    @staticmethod
    def _boost_weights(weights: dict[str, Any], keys: list[str], delta: float) -> None:
        for key in keys:
            current = weights.get(key, 0.0)
            try:
                base = float(current)
            except (TypeError, ValueError):
                base = 0.0
            weights[key] = max(0.0, base + float(delta))

    @staticmethod
    def _decay(weights: dict[str, Any], factor: float) -> dict[str, float]:
        decayed: dict[str, float] = {}
        for key, value in weights.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            updated = numeric * factor
            if updated > 0.05:
                decayed[key] = updated
        return decayed

    def _apply_decay(self, profile: UserInterestProfileModel) -> None:
        factor = settings.RECOMMENDATION_DECAY_FACTOR
        profile.category_weights = self._decay(profile.category_weights or {}, factor)
        profile.tag_weights = self._decay(profile.tag_weights or {}, factor)
        profile.entity_weights = self._decay(profile.entity_weights or {}, factor)

    def _build_seed(self, profile: UserInterestProfileModel) -> dict[str, list[str]]:
        categories = self._top_keys(profile.category_weights or {}, 3)
        tags = self._top_keys(profile.tag_weights or {}, 5)
        entities = self._top_keys(profile.entity_weights or {}, 5)
        textual_entities = [entity for entity in entities if not self._is_video_id_like(entity)]
        query_terms = []
        query_terms.extend(textual_entities[:3])
        query_terms.extend(tags[:2])
        query_terms.extend(categories[:2])
        return {
            "categories": categories,
            "tags": tags,
            "entities": entities,
            "query_terms": query_terms,
        }

    async def _build_seed_from_recent_search_events(self, *, user_id: int) -> dict[str, list[str]]:
        result = await self.db.execute(
            select(UserSearchEventModel)
            .where(UserSearchEventModel.user_id == user_id)
            .order_by(UserSearchEventModel.created_at.desc())
            .limit(30)
        )
        events = result.scalars().all()
        if not events:
            return {"categories": [], "tags": [], "entities": [], "query_terms": []}

        category_counter: Counter[str] = Counter()
        tag_counter: Counter[str] = Counter()
        entity_counter: Counter[str] = Counter()
        query_term_counter: Counter[str] = Counter()

        for event in events:
            if not isinstance(event.parsed_intent, dict):
                parsed_intent: dict[str, Any] = {}
            else:
                parsed_intent = event.parsed_intent

            for value in self._to_str_list(parsed_intent.get("categories")):
                category_counter[value] += 1
            for value in self._to_str_list(parsed_intent.get("tags")):
                tag_counter[value] += 1
            for value in self._to_str_list(parsed_intent.get("entities")):
                entity_counter[value] += 1
            for value in self._extract_terms(event.query):
                query_term_counter[value] += 1

        categories = [key for key, _ in category_counter.most_common(3)]
        tags = [key for key, _ in tag_counter.most_common(5)]
        entities = [key for key, _ in entity_counter.most_common(5)]
        query_terms = [key for key, _ in query_term_counter.most_common(6)]

        if not query_terms:
            query_terms = (tags[:2] + categories[:2])[:4]

        return {
            "categories": categories,
            "tags": tags,
            "entities": entities,
            "query_terms": query_terms,
        }

    @staticmethod
    def _merge_seed(
        *,
        profile_seed: dict[str, list[str]],
        recent_seed: dict[str, list[str]],
    ) -> dict[str, list[str]]:
        def merge_values(primary: list[str], secondary: list[str], limit: int) -> list[str]:
            merged: list[str] = []
            for value in primary + secondary:
                if not isinstance(value, str):
                    continue
                cleaned = value.strip()
                if not cleaned or cleaned in merged:
                    continue
                merged.append(cleaned)
                if len(merged) >= limit:
                    break
            return merged

        categories = merge_values(recent_seed.get("categories", []), profile_seed.get("categories", []), 3)
        tags = merge_values(recent_seed.get("tags", []), profile_seed.get("tags", []), 5)
        entities = merge_values(recent_seed.get("entities", []), profile_seed.get("entities", []), 5)
        query_terms = merge_values(recent_seed.get("query_terms", []), profile_seed.get("query_terms", []), 6)

        if not query_terms:
            query_terms = (tags[:2] + categories[:2])[:4]

        return {
            "categories": categories,
            "tags": tags,
            "entities": entities,
            "query_terms": query_terms,
        }

    async def _resolve_entity_ids(
        self,
        entity_values: list[str],
    ) -> list[RecommendationResolvedEntitySchema]:
        resolved: list[RecommendationResolvedEntitySchema] = []
        for entity in entity_values:
            if not self._is_video_id_like(entity):
                continue
            item = await self._fetch_item_by_video_id(entity)
            if item is None:
                continue
            resolved.append(item)
        return resolved

    async def _fetch_item_by_video_id(
        self,
        video_id: str,
    ) -> RecommendationResolvedEntitySchema | None:
        payload = {
            "query": video_id,
            "filters": {},
            "sort": {"by": "relevance", "order": "desc"},
            "pagination": {"offset": 0, "limit": 3},
        }
        items = await self._call_advanced_search(payload)
        if not items:
            return None
        best_item = None
        for item in items:
            item_video_id = self._video_id_from_item(item)
            if item_video_id == video_id:
                best_item = item
                break
        if best_item is None:
            best_item = items[0]
        document = best_item.get("document", {}) if isinstance(best_item.get("document"), dict) else {}
        title = self._extract_title(document)
        categories = self._extract_categories(document)
        tags = self._extract_tags(document)
        return RecommendationResolvedEntitySchema(
            video_id=video_id,
            title=title,
            categories=categories,
            tags=tags,
        )

    @staticmethod
    def _top_keys(weights: dict[str, Any], limit: int) -> list[str]:
        sortable: list[tuple[str, float]] = []
        for key, value in weights.items():
            if not isinstance(key, str) or not key.strip():
                continue
            try:
                score = float(value)
            except (TypeError, ValueError):
                continue
            sortable.append((key, score))
        sortable.sort(key=lambda item: item[1], reverse=True)
        return [key for key, _ in sortable[:limit]]

    @staticmethod
    def _is_video_id_like(value: str) -> bool:
        normalized = value.strip().lower()
        if not normalized:
            return False
        if " " in normalized:
            return False
        if len(normalized) < 12:
            return False
        return bool(re.fullmatch(r"[a-z0-9_-]+", normalized))

    @staticmethod
    def _extract_title(document: dict[str, Any]) -> str:
        top_title = document.get("title")
        if isinstance(top_title, str) and top_title.strip():
            return top_title.strip()

        data = document.get("data", {}) if isinstance(document.get("data"), dict) else {}
        default = data.get("default", {}) if isinstance(data.get("default"), dict) else {}
        title = data.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
        default_name = default.get("Name")
        if isinstance(default_name, str) and default_name.strip():
            return default_name.strip()

        for service_key in ("cts", "rms"):
            service_obj = document.get(service_key, {})
            if not isinstance(service_obj, dict):
                continue
            service_data = service_obj.get("data", {})
            if not isinstance(service_data, dict):
                continue
            service_name = service_data.get("name")
            if isinstance(service_name, str) and service_name.strip():
                return service_name.strip()
            service_default = service_data.get("default", {})
            if isinstance(service_default, dict):
                name = service_default.get("Name")
                if isinstance(name, str) and name.strip():
                    return name.strip()
        return "Untitled Video"

    @staticmethod
    def _extract_categories(document: dict[str, Any]) -> list[str]:
        top_categories = document.get("categories")
        if isinstance(top_categories, list):
            cleaned = [item.strip() for item in top_categories if isinstance(item, str) and item.strip()]
            if cleaned:
                return cleaned[:5]
        if isinstance(top_categories, str) and top_categories.strip():
            return [top_categories.strip()]

        data = document.get("data", {}) if isinstance(document.get("data"), dict) else {}
        keywords = data.get("keyword", [])
        if isinstance(keywords, list):
            cleaned = [item.strip() for item in keywords if isinstance(item, str) and item.strip()]
            if cleaned:
                return cleaned[:5]
        if isinstance(keywords, str) and keywords.strip():
            return [keywords.strip()]

        for service_key in ("cts", "rms"):
            service_obj = document.get(service_key, {})
            if not isinstance(service_obj, dict):
                continue
            service_data = service_obj.get("data", {})
            if not isinstance(service_data, dict):
                continue
            keyword = service_data.get("keyword")
            if isinstance(keyword, list):
                cleaned = [item.strip() for item in keyword if isinstance(item, str) and item.strip()]
                if cleaned:
                    return cleaned[:5]
            if isinstance(keyword, str) and keyword.strip():
                return [keyword.strip()]
        return []

    @staticmethod
    def _extract_tags(document: dict[str, Any]) -> list[str]:
        top_tags = document.get("tags")
        if isinstance(top_tags, list):
            cleaned = [tag.strip() for tag in top_tags if isinstance(tag, str) and tag.strip()]
            if cleaned:
                return cleaned[:8]
        if isinstance(top_tags, str) and top_tags.strip():
            return [top_tags.strip()]

        data = document.get("data", {}) if isinstance(document.get("data"), dict) else {}
        additional = data.get("additional", {}) if isinstance(data.get("additional"), dict) else {}
        ai_tags = additional.get("AI_Tags")
        if isinstance(ai_tags, str):
            cleaned = [tag.strip() for tag in ai_tags.split(",") if tag.strip()]
            if cleaned:
                return cleaned[:8]
        if isinstance(ai_tags, list):
            cleaned = [tag.strip() for tag in ai_tags if isinstance(tag, str) and tag.strip()]
            if cleaned:
                return cleaned[:8]

        for service_key in ("cts", "rms"):
            service_obj = document.get(service_key, {})
            if not isinstance(service_obj, dict):
                continue
            service_data = service_obj.get("data", {})
            if not isinstance(service_data, dict):
                continue
            tag_list = service_data.get("tag")
            if isinstance(tag_list, list):
                cleaned = [tag.strip() for tag in tag_list if isinstance(tag, str) and tag.strip()]
                if cleaned:
                    return cleaned[:8]
            if isinstance(tag_list, str) and tag_list.strip():
                return [tag_list.strip()]
        return []
