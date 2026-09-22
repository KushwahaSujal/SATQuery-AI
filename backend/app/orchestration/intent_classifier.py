"""
SatQuery AI — Structured Intent Classifier & Entity Extractor
Extracts structured query attributes (object, color, size, position, relation, ordering, temporal intent)
and computes explicit routing_confidence with ambiguity detection.
"""
import re
from typing import Any, Dict, List, Optional, Tuple
from backend.app.orchestration.schemas import (
    ExtractedQueryEntities,
    IntentClassificationResult,
)
from backend.app.logging import logger


class IntentClassifier:
    """
    Parses user natural language queries into structured geospatial entities
    and determines primary intent with explicit routing confidence.
    """

    # Lexical patterns for entity extraction
    OBJECT_PATTERNS = [
        r"\b(vehicle|car|truck|bus|van|automobile)\b",
        r"\b(ship|vessel|boat|cargo ship|tanker|barge|ferry|frigate)\b",
        r"\b(plane|airplane|aircraft|jet|helicopter)\b",
        r"\b(building|structure|house|facility|warehouse|terminal|hangar|shed|roof)\b",
        r"\b(harbor|harbour|dock|pier|wharf|port|marina)\b",
        r"\b(road|highway|street|runway|bridge|railway|track)\b",
        r"\b(storage tank|oil tank|water tank|silo|fuel depot|storage depot|depot)\b",
        r"\b(platform|oil platform|offshore platform)\b",
        r"\b(container|shipping container|cargo container)\b",
        r"\b(field|farm|plantation|forest|tree canopy|canopy|vegetation|tree)\b",
        r"\b(water body|lake|river|pond|reservoir|coastline)\b"
    ]
    # Plural forms ("trees", "buildings", "buses") must match too; group(1) stays the singular (Q-015).
    # Only a singular noun still implies grounding without a verb: "how many buildings are in this image?" stays VQA.
    SINGULAR_OBJECT_PATTERNS = OBJECT_PATTERNS
    OBJECT_PATTERNS = [p[:-2] + r"(?:e?s)?\b" for p in OBJECT_PATTERNS]

    COLOR_PATTERNS = [
        r"\b(red|dark-colored|dark|white|blue|green|yellow|silver|gray|grey|black|bright|orange|brown)\b"
    ]

    SIZE_PATTERNS = [
        r"\b(small|little|tiny|compact|medium|large|huge|massive|giant|elongated)\b"
    ]

    POSITION_PATTERNS = [
        r"\b(top-left|top-right|bottom-left|bottom-right|top|bottom|left|right|center|middle|upper|lower|north|south|east|west)\b"
    ]

    RELATION_PATTERNS = [
        r"\b(near|next to|adjacent to|beside|close to|around|inside|within|outside|between|along|crossing|surrounded by)\b"
    ]

    ORDERING_PATTERNS = [
        r"\b(first|second|third|fourth|fifth|last|furthest|closest|topmost|bottommost)\b"
    ]

    TEMPORAL_PATTERNS = [
        r"\b(before|after|earlier|later|new|previous|recent|historical|temporal|epoch)\b"
    ]

    CHANGE_PATTERNS = [
        r"\b(change|changed|difference|differences|expansion|growth|deforestation|loss|damage|destroyed|constructed|built|demolished)\b"
    ]

    SPECTRAL_PATTERNS = [
        r"\b(ndvi|ndwi|ndbi|vegetation index|water index|false color|false-color|nir|infrared|near infrared|red edge)\b"
    ]

    SAR_PATTERNS = [
        r"\b(sar|radar|polarization|polarimetry|vv|vh|backscatter|decibel|db)\b"
    ]

    GROUNDING_VERB_PATTERNS = [
        r"\b(locate|find|highlight|point\s+out|where\s+is|where\s+are|identify\s+the|show\s+me|detect|segment|outline|isolate|box|search\s+for|mask|masks|masking|mark|delineate)\b"
    ]

    # Scene-level land-cover classification, routed to the trained EuroSAT EfficientNet-B0
    # (`eurosat_classifier`, project/qna.md Q-041). Deliberately narrow: the phrase must name land
    # cover / land use / terrain, or aim a classification verb at the *scene* rather than at an
    # object. "classify the vehicles in this image" and "how many airplanes are there" must stay on
    # the VQA fallback, because EuroSAT has no vehicle or airplane class and the classifier answers
    # with one label for the whole tile.
    # Checked strictly after grounding, spectral, SAR, change and captioning (see classify_intent),
    # so the only queries this can capture are the ones that today reach the generic VQA fallback.
    SCENE_CLASSIFICATION_PATTERNS = [
        # The model's own vocabulary, in any spelling: "land cover", "land-cover", "landuse".
        r"\b(land\s*-?\s*cover|land\s*-?\s*use|landcover|landuse)\b",
        # A classification verb or noun aimed at the whole scene. The scene noun must follow
        # immediately (after an optional determiner) so an object noun cannot slip in between.
        r"\b(classify|classification|categorise|categorize)\s+(?:the\s+|this\s+|these\s+|a\s+|an\s+)?"
        r"(scene|image|tile|photo|picture|terrain|area)\b",
        r"\b(scene|image|tile|terrain)\s+(class|classification|category|type)\b",
        r"\bwhat\s+(type|kind|class|category)\s+of\s+(terrain|surface|scene|ground\s*cover)\b",
        r"\b(terrain|surface)\s+type\b",
        # Bare "classify this" / "categorise it" — only at the end of the query, so
        # "classify this warehouse" is not swallowed.
        r"\b(classify|categorise|categorize)\s+(?:this|it)\s*[?.!]*$",
    ]

    @classmethod
    def extract_entities(cls, query: str) -> ExtractedQueryEntities:
        """
        Extracts entities and spatial grounding facets from query text.
        """
        q = query.lower().strip()
        entities = ExtractedQueryEntities(raw_query=query)

        # 1. Object class from dictionary. The target is the object before a relation phrase: in "trees near
        # houses" it is trees, not whichever of the two comes first in OBJECT_PATTERNS.
        rel_m = next((m for m in (re.search(rp, q) for rp in cls.RELATION_PATTERNS) if m), None)
        target_text = q[:rel_m.start()] if rel_m and rel_m.start() > 0 else q
        for p in cls.OBJECT_PATTERNS:
            m = re.search(p, target_text)
            if m:
                entities.object_class = m.group(1)
                break

        # Fallback noun phrase extractor if grounding verb is present but dictionary missed
        if not entities.object_class:
            m_verb = re.search(r"(?:locate|find|highlight|point\s+out|where\s+is|where\s+are|identify\s+the|show\s+me|detect|segment|outline|isolate|box|search\s+for|mask|masks|masking|mark|delineate)\s+(?:the\s+|a\s+|an\s+)?([a-zA-Z0-9_\s-]+?)(?:\s+(?:near|next\s+to|adjacent|beside|in|on|at|around|within|outside|between)|[?.!,]|$)", q)
            if m_verb:
                candidate = m_verb.group(1).strip()
                for word in ["red", "dark", "white", "blue", "green", "yellow", "black", "small", "large", "huge", "damaged", "offshore"]:
                    if candidate.startswith(word + " "):
                        candidate = candidate[len(word)+1:].strip()
                if candidate and len(candidate) > 2:
                    entities.object_class = candidate

        # 2. Color
        for p in cls.COLOR_PATTERNS:
            m = re.search(p, q)
            if m:
                entities.color = m.group(1)
                break

        # 3. Size
        for p in cls.SIZE_PATTERNS:
            m = re.search(p, q)
            if m:
                entities.size = m.group(1)
                break

        # 4. Position
        for p in cls.POSITION_PATTERNS:
            m = re.search(p, q)
            if m:
                entities.position = m.group(1)
                break

        # 5. Relation & Reference Object
        for p in cls.RELATION_PATTERNS:
            m = re.search(p, q)
            if m:
                entities.relation = m.group(1)
                rel_idx = m.end()
                remainder = q[rel_idx:].strip()
                # Find reference object in remainder
                for obj_p in cls.OBJECT_PATTERNS:
                    ref_m = re.search(obj_p, remainder)
                    if ref_m:
                        entities.reference_object = ref_m.group(1)
                        break
                break

        # 6. Ordering
        for p in cls.ORDERING_PATTERNS:
            m = re.search(p, q)
            if m:
                entities.ordering = m.group(1)
                break

        # 7. Temporal & Change
        for p in cls.TEMPORAL_PATTERNS:
            m = re.search(p, q)
            if m:
                entities.temporal_intent = m.group(1)
                break

        for p in cls.CHANGE_PATTERNS:
            m = re.search(p, q)
            if m:
                entities.change_intent = m.group(1)
                break

        # Ambiguity check
        # e.g., "Find it" or "Locate" without any object or reference
        has_grounding_verb = any(bool(re.search(p, q)) for p in cls.GROUNDING_VERB_PATTERNS)
        if has_grounding_verb and not entities.object_class and not entities.color and not entities.position:
            entities.is_ambiguous = True
            entities.ambiguity_reason = "Grounding directive provided without specific object category or spatial anchor."

        return entities

    @classmethod
    def classify_intent(
        cls,
        query: str,
        num_inputs: int = 1,
        input_types: Optional[List[str]] = None,
        modalities: Optional[List[str]] = None
    ) -> IntentClassificationResult:
        """
        Classifies intent and computes routing_confidence.
        """
        q = query.lower().strip()
        entities = cls.extract_entities(query)
        input_types = input_types or ["image"]
        modalities = modalities or ["optical"]

        is_video = "video" in input_types or any("video" in m.lower() for m in modalities)
        has_sar = any("sar" in m.lower() for m in modalities) or any(bool(re.search(p, q)) for p in cls.SAR_PATTERNS)
        has_spectral = any(bool(re.search(p, q)) for p in cls.SPECTRAL_PATTERNS)
        has_change = bool(entities.change_intent) or any(bool(re.search(p, q)) for p in cls.CHANGE_PATTERNS)
        has_singular_object = any(bool(re.search(p, q)) for p in cls.SINGULAR_OBJECT_PATTERNS)
        has_grounding = any(bool(re.search(p, q)) for p in cls.GROUNDING_VERB_PATTERNS) or bool(
            entities.object_class and has_singular_object and not has_change)

        # 1. Video intent
        if is_video:
            if entities.ordering or entities.relation or "track" in q:
                task = "video_grounding_tracking"
                conf = 0.95
            else:
                task = "video_grounding"
                conf = 0.90
            return IntentClassificationResult(
                task=task,
                routing_confidence=conf,
                input_requirements=["video"],
                entities=[entities.object_class] if entities.object_class else [],
                attributes=entities.model_dump(exclude_none=True),
                extracted_entities=entities
            )

        # 2. Multi-image temporal change intent
        if num_inputs >= 2:
            is_cross_modal = len(modalities) >= 2 and (
                ("optical" in modalities[0] and "sar" in modalities[1]) or
                ("sar" in modalities[0] and "optical" in modalities[1])
            )
            if is_cross_modal or (has_sar and any("optical" in m for m in modalities)):
                return IntentClassificationResult(
                    task="optical_sar_analysis",
                    routing_confidence=0.95,
                    input_requirements=["optical_image", "sar_image"],
                    entities=[entities.object_class] if entities.object_class else [],
                    attributes=entities.model_dump(exclude_none=True),
                    extracted_entities=entities
                )

            # Check question vs detection
            is_question = any(q.startswith(w) for w in ["what", "has", "where", "did", "is", "how", "why"]) or "?" in q
            if is_question or entities.change_intent in ["difference", "differences"]:
                task = "temporal_change_vqa"
                conf = 0.92
            else:
                task = "temporal_change_detection"
                conf = 0.94

            return IntentClassificationResult(
                task=task,
                routing_confidence=conf,
                input_requirements=["temporal_image_1", "temporal_image_2"],
                entities=[entities.object_class] if entities.object_class else [],
                attributes=entities.model_dump(exclude_none=True),
                extracted_entities=entities
            )

        # 3. Single Image Intent
        # Rule: Explicit Grounding intent takes strict priority over generic VQA
        if has_spectral and not has_grounding:
            return IntentClassificationResult(
                task="multispectral_analysis",
                routing_confidence=0.88,
                input_requirements=["multispectral_raster"],
                entities=[],
                attributes=entities.model_dump(exclude_none=True),
                extracted_entities=entities
            )

        if has_sar and not has_grounding:
            return IntentClassificationResult(
                task="sar_analysis",
                routing_confidence=0.88,
                input_requirements=["sar_raster"],
                entities=[],
                attributes=entities.model_dump(exclude_none=True),
                extracted_entities=entities
            )

        if has_grounding:
            # High confidence if object + spatial facets are clear
            score = 0.80
            if entities.object_class:
                score += 0.10
            if entities.color or entities.size or entities.position or entities.relation:
                score += 0.08
            score = min(score, 0.98)

            ambiguous = entities.is_ambiguous
            clarification = None
            if ambiguous:
                score = 0.50
                clarification = "The query asks to locate an object, but no specific object type or descriptive anchor was recognized. Please specify what to find (e.g., 'Find the red car' or 'Locate the cargo ship')."

            return IntentClassificationResult(
                task="single_image_grounding",
                routing_confidence=round(score, 2),
                input_requirements=["single_image"],
                entities=[entities.object_class] if entities.object_class else [],
                attributes=entities.model_dump(exclude_none=True),
                extracted_entities=entities,
                is_ambiguous=ambiguous,
                suggested_clarification=clarification
            )

        # Captioning request
        if any(k in q for k in ["caption", "summarize", "summarise", "overview of scene", "brief description"]) or re.search(
            r"\b(describe|description of)\b.*\b(image|scene|picture|photo|area|this)\b"
            r"|\bwhat (is|does) (this|the) (image|scene|picture) (show|contain|depict)|\bwhat do you see\b", q
        ):
            return IntentClassificationResult(
                task="single_image_caption",
                routing_confidence=0.89,
                input_requirements=["single_image"],
                entities=[],
                attributes=entities.model_dump(exclude_none=True),
                extracted_entities=entities
            )

        # Scene-level land-cover classification request (Q-041). Placed here on purpose: last check
        # before the generic VQA fallback, so it cannot take a query away from grounding
        # ("mask all roads"), spectral analysis ("compute NDVI"), SAR, change detection or
        # captioning ("describe this image") — every one of those returns above. The only traffic it
        # can win is traffic that currently lands on `single_image_vqa`, whose model (Qwen3-VL/BLIP)
        # is frequently NOT_CONFIGURED and which has no measured land-cover score at all.
        # A whole-tile label cannot answer a query scoped to a sub-region ("what land cover is in the
        # north"), to an ordinal, or to a change between epochs ("what land cover changed here" on a
        # single image). Those keep whatever route they have today rather than receiving a
        # confidently-wrong scene label — the same reason trained_segmenter.py refuses relational and
        # colour-qualified requests.
        scene_scoped = not (entities.position or entities.relation or entities.ordering or has_change)
        if scene_scoped and any(bool(re.search(p, q)) for p in cls.SCENE_CLASSIFICATION_PATTERNS):
            return IntentClassificationResult(
                task="single_image_classification",
                # Router confidence, not ML accuracy (see IntentClassificationResult). Below
                # captioning's 0.89 and grounding's 0.90, matching this check's position in the
                # chain: the lexical trigger is explicit, but anything more specific already won.
                routing_confidence=0.87,
                input_requirements=["single_image"],
                entities=[],
                attributes=entities.model_dump(exclude_none=True),
                extracted_entities=entities
            )

        # Fallback to general VQA
        return IntentClassificationResult(
            task="single_image_vqa",
            routing_confidence=0.82,
            input_requirements=["single_image"],
            entities=[entities.object_class] if entities.object_class else [],
            attributes=entities.model_dump(exclude_none=True),
            extracted_entities=entities
        )
