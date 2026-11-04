"""Tools for the Land Truth Agent.

Independent, data-based checks a villager can run on a land plot before
believing a broker's claims about water and price.

- Rainfall: live from Open-Meteo (ERA5 reanalysis, free, no API key).
- Groundwater and guideline values: local JSON files in ./data that YOU must
  fill with verified numbers (see data/README.md). Entries marked
  "verified": false are placeholders and are reported as such.
"""

import json
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from statistics import mean

from strands import tool

DATA_DIR = Path(__file__).parent / "data"
SQFT_PER_CENT = 435.6

UNVERIFIED_WARNING = (
    "WARNING: this figure is a PLACEHOLDER and has not been verified against an "
    "official source. Do not present it as fact."
)


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _find(table: dict, place: str):
    key = place.strip().lower()
    for name, row in table.items():
        if name.lower() == key:
            return name, row
    return None, None


def _geocode(place: str):
    url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        + urllib.parse.urlencode({"name": place, "count": 5, "country_code": "IN"})
    )
    results = _get_json(url).get("results") or []
    # Prefer Tamil Nadu matches: many village names repeat across states.
    for r in results:
        if r.get("admin1") == "Tamil Nadu":
            return r
    return results[0] if results else None


@tool
def get_rainfall_history(place: str, years: int = 5) -> str:
    """Get real yearly and monsoon rainfall history for a village or town in India.

    Use this to check a broker's claim that an area has 'good rain'.

    Args:
        place: Village or town name (e.g. 'Annur', 'Sulur')
        years: How many full past years to analyse (1 to 10)
    """
    years = max(1, min(int(years), 10))
    loc = _geocode(place)
    if not loc:
        return f"Could not find a location named '{place}' in India."

    end_year = date.today().year - 1
    start_year = end_year - years + 1
    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        + urllib.parse.urlencode(
            {
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "start_date": f"{start_year}-01-01",
                "end_date": f"{end_year}-12-31",
                "daily": "precipitation_sum",
                "timezone": "Asia/Kolkata",
            }
        )
    )
    daily = _get_json(url)["daily"]

    totals, sw, ne, dry_days = {}, {}, {}, {}
    for day, mm in zip(daily["time"], daily["precipitation_sum"]):
        if mm is None:
            continue
        y, m = int(day[:4]), int(day[5:7])
        totals[y] = totals.get(y, 0) + mm
        if 6 <= m <= 9:
            sw[y] = sw.get(y, 0) + mm
        if 10 <= m <= 12:
            ne[y] = ne.get(y, 0) + mm
        if mm < 1:
            dry_days[y] = dry_days.get(y, 0) + 1

    avg = mean(totals.values())
    lines = [
        f"Location matched: {loc['name']}, {loc.get('admin2', '')}, {loc.get('admin1', '')} "
        f"({loc['latitude']:.3f}, {loc['longitude']:.3f})",
        f"Years analysed: {start_year}-{end_year}",
    ]
    for y in sorted(totals):
        lines.append(
            f"  {y}: total {totals[y]:.0f} mm | SW monsoon (Jun-Sep) {sw.get(y, 0):.0f} mm | "
            f"NE monsoon (Oct-Dec) {ne.get(y, 0):.0f} mm | days under 1 mm: {dry_days.get(y, 0)}"
        )
    low_years = [y for y, t in totals.items() if t < 0.75 * avg]
    lines.append(f"Average annual rainfall: {avg:.0f} mm")
    lines.append(
        f"Years more than 25% below average: {sorted(low_years) if low_years else 'none'}"
    )
    lines.append(
        "Caveat: values come from a gridded model (ERA5), not a rain gauge at the plot. "
        "Treat them as an indicator and confirm with local rain-gauge records."
    )
    return "\n".join(lines)


@tool
def get_groundwater_status(place: str) -> str:
    """Get groundwater level and category for a village, taluk or block.

    Use this to check a broker's claim that 'water is available' at a plot.

    Args:
        place: Village, taluk or block name (e.g. 'Annur')
    """
    name, row = _find(_load("groundwater.json"), place)
    if not row:
        return (
            f"No groundwater record for '{place}' in the local dataset. "
            "Tell the user to check the CGWB / India-WRIS groundwater report "
            "or ask the local PWD / TWAD office."
        )
    out = (
        f"{name}: category = {row['category']}, typical water table depth = "
        f"{row['water_table_depth_m']} m, trend = {row['trend']}. Source: {row['source']}"
    )
    if not row.get("verified"):
        out += "\n" + UNVERIFIED_WARNING
    return out


@tool
def get_guideline_value(place: str) -> str:
    """Get the government guideline value (registration value) of land for a village.

    Args:
        place: Village or town name
    """
    name, row = _find(_load("guideline_values.json"), place)
    if not row:
        return (
            f"No guideline value for '{place}' in the local dataset. "
            "Tell the user to check the Tamil Nadu registration department "
            "guideline value site or the sub-registrar office."
        )
    out = (
        f"{name}: guideline value = Rs {row['rupees_per_cent']:,} per cent "
        f"(1 cent = {SQFT_PER_CENT} sq ft). Source: {row['source']}"
    )
    if not row.get("verified"):
        out += "\n" + UNVERIFIED_WARNING
    return out


@tool
def check_quoted_price(place: str, quoted_rupees_per_cent: float) -> str:
    """Compare a broker's quoted price per cent against the government guideline value.

    Args:
        place: Village or town name
        quoted_rupees_per_cent: Price per cent in rupees quoted by the broker
    """
    name, row = _find(_load("guideline_values.json"), place)
    if not row:
        return f"No guideline value for '{place}', so the quoted price cannot be compared."
    guide = row["rupees_per_cent"]
    ratio = quoted_rupees_per_cent / guide
    # Heuristic only: market prices are normally above guideline values.
    if ratio < 1:
        flag = "BELOW guideline value: unusual, check for a title or dispute problem."
    elif ratio <= 3:
        flag = "Within a commonly seen range above guideline value."
    elif ratio <= 6:
        flag = "HIGH versus guideline value: ask for recent registered sale deeds nearby."
    else:
        flag = "VERY HIGH versus guideline value: strong sign of an inflated price."
    out = (
        f"Quoted Rs {quoted_rupees_per_cent:,.0f}/cent vs guideline Rs {guide:,}/cent "
        f"= {ratio:.1f}x. {flag}\n"
        "Note: the 1x-3x-6x bands are a rough heuristic, not a legal valuation."
    )
    if not row.get("verified"):
        out += "\n" + UNVERIFIED_WARNING
    return out
