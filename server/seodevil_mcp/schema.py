"""Structured data: extract JSON-LD / microdata / RDFa and check Google's rich-result properties."""
from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from .report import Report

# type -> (required, recommended). Based on Google Search Central structured-data docs.
RULES: Dict[str, Tuple[List[str], List[str]]] = {
    "Article": (["headline"], ["image", "datePublished", "dateModified", "author", "publisher"]),
    "Product": (["name"], ["image", "description", "offers", "aggregateRating", "review", "brand", "sku"]),
    "Offer": (["price|priceSpecification", "priceCurrency|priceSpecification"], ["availability", "url", "priceValidUntil"]),
    "AggregateRating": (["ratingValue", "ratingCount|reviewCount"], ["bestRating"]),
    "Review": (["author", "reviewRating", "itemReviewed|@nested"], ["datePublished"]),
    "Organization": ([], ["name", "url", "logo", "sameAs", "contactPoint", "address"]),
    "LocalBusiness": (["name", "address"], ["telephone", "url", "openingHoursSpecification|openingHours", "geo", "priceRange", "image", "aggregateRating"]),
    "WebSite": (["name|url"], ["url", "name", "potentialAction"]),
    "BreadcrumbList": (["itemListElement"], []),
    "FAQPage": (["mainEntity"], []),
    "QAPage": (["mainEntity"], []),
    "Recipe": (["name", "image"], ["author", "datePublished", "description", "prepTime", "cookTime", "totalTime", "recipeYield", "recipeIngredient", "recipeInstructions", "nutrition", "aggregateRating", "video"]),
    "Event": (["name", "startDate", "location"], ["endDate", "eventStatus", "eventAttendanceMode", "image", "description", "offers", "organizer", "performer"]),
    "JobPosting": (["title", "description", "datePosted", "hiringOrganization", "jobLocation|applicantLocationRequirements"], ["validThrough", "employmentType", "baseSalary", "identifier", "directApply"]),
    "VideoObject": (["name", "thumbnailUrl", "uploadDate"], ["description", "duration", "contentUrl|embedUrl"]),
    "SoftwareApplication": (["name", "offers", "aggregateRating|review"], ["applicationCategory", "operatingSystem"]),
    "Course": (["name", "description"], ["provider", "offers", "hasCourseInstance"]),
    "Person": (["name"], ["url", "sameAs", "jobTitle", "image"]),
    "ImageObject": (["contentUrl|url"], ["creator", "license", "creditText", "copyrightNotice"]),
    "Dataset": (["name", "description"], ["license", "creator", "url"]),
    "ProfilePage": (["mainEntity"], ["dateCreated", "dateModified"]),
    "DiscussionForumPosting": (["author", "datePublished", "text|image|video"], ["headline", "url", "interactionStatistic"]),
    "Book": (["name", "author"], ["url", "workExample"]),
    "Movie": (["name", "image"], ["director", "dateCreated", "aggregateRating"]),
    "ProductGroup": (["name", "hasVariant"], ["productGroupID", "variesBy"]),
}
ALIASES = {
    "NewsArticle": "Article", "BlogPosting": "Article", "TechArticle": "Article", "Report": "Article",
    "ScholarlyArticle": "Article", "OpinionNewsArticle": "Article", "LiveBlogPosting": "Article",
    "Corporation": "Organization", "NGO": "Organization", "EducationalOrganization": "Organization",
    "OnlineStore": "Organization", "OnlineBusiness": "Organization", "NewsMediaOrganization": "Organization",
    "MobileApplication": "SoftwareApplication", "WebApplication": "SoftwareApplication", "VideoGame": "SoftwareApplication",
    "AggregateOffer": "Offer",
}
LOCAL_BUSINESS = set("""
LocalBusiness Restaurant CafeOrCoffeeShop Bakery BarOrPub FastFoodRestaurant Dentist Physician MedicalClinic Hospital
Pharmacy Store ClothingStore ElectronicsStore GroceryStore HardwareStore AutoRepair AutoDealer HairSalon BeautySalon
DaySpa NailSalon HealthClub ExerciseGym Hotel LodgingBusiness Motel BedAndBreakfast Hostel ProfessionalService
LegalService Attorney Notary AccountingService FinancialService RealEstateAgent InsuranceAgency Plumber Electrician
HVACBusiness RoofingContractor GeneralContractor HousePainter Locksmith MovingCompany HomeAndConstructionBusiness
ChildCare School Preschool TravelAgency VeterinaryCare AnimalShelter Florist FurnitureStore JewelryStore PetStore
ShoeStore SportingGoodsStore TouristInformationCenter EntertainmentBusiness MedicalBusiness Optician
EmploymentAgency RealEstateAgent SelfStorage FoodEstablishment IceCreamShop Winery Brewery
""".split())
DEPRECATED = {
    "HowTo": "HowTo rich results were removed by Google in 2023; the markup is harmless but shows nothing.",
    "SpecialAnnouncement": "SpecialAnnouncement is no longer used by Google.",
    "ClaimReview": "Fact-check rich results were phased out by Google in 2025.",
}
DATE_PROPS = {"datePublished", "dateModified", "uploadDate", "startDate", "endDate", "datePosted", "validThrough", "priceValidUntil"}
URL_PROPS = {"url", "logo", "image", "thumbnailUrl", "contentUrl", "embedUrl", "sameAs"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$")


def _types(entity: dict) -> List[str]:
    t = entity.get("@type", [])
    t = t if isinstance(t, list) else [t]
    return [str(x).split("/")[-1].split(":")[-1] for x in t if x]


def canonical_type(t: str) -> Optional[str]:
    if t in RULES:
        return t
    if t in ALIASES:
        return ALIASES[t]
    if t in LOCAL_BUSINESS:
        return "LocalBusiness"
    return None


def _empty(v: Any) -> bool:
    return v is None or v == "" or v == [] or v == {}


def _has(entity: dict, spec: str) -> bool:
    return any(not _empty(entity.get(k)) for k in spec.split("|") if k != "@nested")


def flatten(data: Any) -> List[dict]:
    """Top-level entities from a JSON-LD block (handles arrays and @graph)."""
    out: List[dict] = []
    if isinstance(data, list):
        for d in data:
            out += flatten(d)
    elif isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            out += flatten(data["@graph"])
        elif data.get("@type"):
            out.append(data)
    return out


def _walk_nested(entity: Any, path: str = "") -> List[Tuple[str, dict]]:
    """Nested typed entities worth validating (offers, ratings, reviews...)."""
    found: List[Tuple[str, dict]] = []
    if isinstance(entity, dict):
        for k, v in entity.items():
            if k.startswith("@"):
                continue
            for item in (v if isinstance(v, list) else [v]):
                if isinstance(item, dict):
                    if item.get("@type"):
                        found.append((f"{path}.{k}" if path else k, item))
                    found += _walk_nested(item, f"{path}.{k}" if path else k)
    return found


def validate_entity(entity: dict, nested: bool = False) -> Dict:
    types = _types(entity)
    result: Dict[str, Any] = {"type": types[0] if len(types) == 1 else types, "errors": [], "warnings": []}
    for t in types:
        if t in DEPRECATED:
            result["warnings"].append(DEPRECATED[t])
        ct = canonical_type(t)
        if not ct:
            continue
        req, rec = RULES[ct]
        for spec in req:
            if spec.endswith("|@nested") and nested:
                if not _has(entity, spec):
                    continue
            if not _has(entity, spec):
                result["errors"].append(f"{t}: missing required '{spec.replace('|@nested', '').replace('|', ' or ')}'")
        if not nested:
            missing_rec = [s.replace("|", " or ") for s in rec if not _has(entity, s)]
            if missing_rec:
                result["warnings"].append(f"{t}: missing recommended {', '.join(missing_rec)}")
        if ct == "Product" and not any(_has(entity, k) for k in ("offers", "review", "aggregateRating")):
            result["errors"].append("Product: needs at least one of offers, review or aggregateRating for a rich result")
        if ct == "FAQPage":
            qs = entity.get("mainEntity") or []
            qs = qs if isinstance(qs, list) else [qs]
            bad = [q for q in qs if not (isinstance(q, dict) and q.get("name") and isinstance(q.get("acceptedAnswer"), dict) and q["acceptedAnswer"].get("text"))]
            if bad:
                result["errors"].append(f"FAQPage: {len(bad)} question(s) without name or acceptedAnswer.text")
            result["warnings"].append("FAQ rich results only show for well-known government and health sites since 2023; the markup still helps AI and other engines.")
        if ct == "BreadcrumbList":
            items = entity.get("itemListElement") or []
            items = items if isinstance(items, list) else [items]
            for i, it in enumerate(items):
                if not isinstance(it, dict) or not it.get("position") or not (it.get("name") or (isinstance(it.get("item"), dict) and it["item"].get("name"))):
                    result["errors"].append(f"BreadcrumbList: item {i + 1} needs position and name")
                    break
        if ct == "Offer":
            price = entity.get("price")
            if isinstance(price, str) and re.search(r"[^\d.]", price.strip()):
                result["errors"].append(f"Offer: price must be a number without currency symbols (got {price!r})")
            avail = str(entity.get("availability", ""))
            if avail and "schema.org/" not in avail:
                result["warnings"].append("Offer: availability should be a schema.org URL, e.g. https://schema.org/InStock")
        if ct == "AggregateRating":
            try:
                if float(entity.get("ratingValue", 0)) > float(entity.get("bestRating", 5)):
                    result["errors"].append("AggregateRating: ratingValue is higher than bestRating")
            except (TypeError, ValueError):
                result["errors"].append("AggregateRating: ratingValue must be a number")
    for k in DATE_PROPS:
        v = entity.get(k)
        if isinstance(v, str) and v and not ISO_DATE.match(v.strip()):
            result["errors"].append(f"{k} is not ISO 8601 ({v!r}); use e.g. 2026-01-31 or 2026-01-31T09:00:00+00:00")
    for k in URL_PROPS:
        v = entity.get(k)
        vals = v if isinstance(v, list) else [v]
        for x in vals:
            if isinstance(x, str) and x and not x.startswith(("http://", "https://")):
                result["warnings"].append(f"{k} should be an absolute URL (got {x[:80]!r})")
                break
    if not nested:
        for path, child in _walk_nested(entity):
            sub = validate_entity(child, nested=True)
            result["errors"] += [f"{path} → {e}" for e in sub.get("errors", [])]
            result["warnings"] += [f"{path} → {w}" for w in sub.get("warnings", []) if "missing recommended" not in w]
    if not result["errors"]:
        del result["errors"]
    if not result["warnings"]:
        del result["warnings"]
    return result


def _loose_json(raw: str) -> Any:
    raw = raw.strip()
    raw = re.sub(r"^\s*<!--|-->\s*$", "", raw)
    raw = re.sub(r"^\s*//\s*<!\[CDATA\[|//\s*\]\]>\s*$", "", raw).strip()
    return json.loads(raw)


def extract(doc) -> Dict[str, Any]:
    blocks, errors = [], []
    for s in doc.find_all("script"):
        if s.get("type").lower().strip() != "application/ld+json":
            continue
        raw = "".join(c for c in s.children if isinstance(c, str))
        try:
            blocks.append(_loose_json(raw))
        except (ValueError, json.JSONDecodeError) as e:
            errors.append(f"line {s.line}: {e.msg if hasattr(e, 'msg') else e} — {raw.strip()[:100]!r}")
    micro = sorted({n.get("itemtype").split("/")[-1] for n in doc.find_all(itemtype=True) if n.get("itemtype")})
    rdfa = sorted({n.get("typeof") for n in doc.find_all(typeof=True) if n.get("typeof")})
    return {"jsonld": blocks, "parse_errors": errors, "microdata_types": micro, "rdfa_types": rdfa}


def validate_blocks(blocks: List[Any]) -> List[Dict]:
    out = []
    for b in blocks:
        for e in flatten(b):
            out.append(validate_entity(e))
    return out


def analyze_schema(p, r: Report) -> None:
    ex = extract(p.doc)
    entities = validate_blocks(ex["jsonld"])
    types = sorted({t for e in entities for t in (e["type"] if isinstance(e["type"], list) else [e["type"]])})
    r.data["schema"] = {
        "jsonld_types": types,
        "microdata_types": ex["microdata_types"],
        "rdfa_types": ex["rdfa_types"],
        "entities": entities[:20],
    }
    for err in ex["parse_errors"]:
        r.add("schema_invalid_json", "high", "schema", "JSON-LD block has invalid JSON", detail=err,
              fix="Fix the syntax (trailing commas, unescaped quotes, comments are common). Google ignores the whole block.")
    errs = [x for e in entities for x in e.get("errors", [])]
    if errs:
        r.add("schema_errors", "medium", "schema", f"{len(errs)} structured data error(s)", affected=errs,
              fix="Add the missing required properties; otherwise the item isn't eligible for rich results.")
    warns = [x for e in entities for x in e.get("warnings", [])]
    if warns:
        r.add("schema_warnings", "low", "schema", f"{len(warns)} structured data warning(s)", affected=warns)
    if not types and not ex["microdata_types"] and not ex["rdfa_types"]:
        path = urllib.parse.urlsplit(p.url).path.strip("/")
        hint = "Organization + WebSite" if not path else "a type that fits the page (Article, Product, LocalBusiness, BreadcrumbList...)"
        r.add("schema_missing", "medium", "schema", "No structured data",
              detail="Structured data makes pages eligible for rich results and helps AI search understand entities.",
              fix=f"Add JSON-LD for {hint}.")
    elif ex["microdata_types"] and not types:
        r.add("schema_microdata_only", "info", "schema", "Uses microdata only", detail="Valid, but JSON-LD is Google's recommended format and easier to maintain.")


def validate_any(text: str) -> Dict:
    """Validate a raw JSON-LD string (or a whole HTML document)."""
    text = (text or "").strip()
    if text.startswith("<"):
        from .dom import Document

        ex = extract(Document(text))
        return {"parse_errors": ex["parse_errors"], "entities": validate_blocks(ex["jsonld"]),
                "microdata_types": ex["microdata_types"], "rdfa_types": ex["rdfa_types"]}
    try:
        data = _loose_json(text)
    except (ValueError, json.JSONDecodeError) as e:
        return {"parse_errors": [str(e)], "entities": []}
    ents = flatten(data)
    if not ents:
        return {"parse_errors": ["No entity with @type found"], "entities": []}
    ctx = data.get("@context") if isinstance(data, dict) else None
    out = {"parse_errors": [], "entities": [validate_entity(e) for e in ents]}
    if isinstance(data, dict) and not ctx:
        out["parse_errors"].append("Missing @context (use \"https://schema.org\")")
    return out
