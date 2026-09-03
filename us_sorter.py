import base64
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
import urllib.request

# GitHub API URL for usbrews.json
api_url = "https://api.github.com/repos/CSU-CS-314-Fall-2026/students/contents/test/brews/usbrews.json?ref=main"

output_txt_path = "us_brew_report.txt"


def load_and_lint_private_reference_data():
    """Fetches usbrews.json from GitHub and validates its JSON syntax."""
    token = os.environ.get("GH_PAT")

    req = urllib.request.Request(api_url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")

    try:
        with urllib.request.urlopen(req) as response:
            api_data = json.loads(response.read().decode())
            file_content = base64.b64decode(api_data["content"]).decode("utf-8")

        # Perform JSON Syntax Check
        try:
            parsed_json = json.loads(file_content)
            lint_status = "JSON Syntax Check (JSONLint): PASSED (Valid JSON)"
            return parsed_json, lint_status
        except json.JSONDecodeError as jde:
            lint_status = f"JSON Syntax Check (JSONLint): FAILED -> {jde}"
            return None, lint_status

    except Exception as e:
        lint_status = f"JSON Fetch Error: {e}"
        return None, lint_status


def process_usbrews(reference_data, lint_status):
    """Analyzes usbrews data for alphabetization breaks and duplicate municipalities."""
    places = reference_data.get("places", [])

    # 1. Check alphabetical order (sorting primarily by Region/State, then Municipality)
    alphabetical_check_msg = (
        "JSON Order Check: All regions and municipalities are in alphabetical order."
    )
    for i in range(len(places) - 1):
        curr_p = places[i]
        next_p = places[i + 1]

        curr_region = curr_p.get("region", "").strip().lower()
        next_region = next_p.get("region", "").strip().lower()
        curr_muni = curr_p.get("municipality", "").strip().lower()
        next_muni = next_p.get("municipality", "").strip().lower()

        # Compare regions first, then municipalities if regions are equal
        is_out_of_order = False
        if curr_region > next_region:
            is_out_of_order = True
        elif curr_region == next_region and curr_muni > next_muni:
            is_out_of_order = True

        if is_out_of_order:
            brewery_name = (
                next_p.get("name") or next_p.get("id") or "Unknown Brewery"
            )
            alphabetical_check_msg = (
                f"JSON Order Check: Order breaks down at '{brewery_name}' "
                f"(Location: {next_p.get('municipality')}, {next_p.get('region')} "
                f"follows {curr_p.get('municipality')}, {curr_p.get('region')})"
            )
            break

    # 2. Check for duplicate municipalities (where state/region also matches)
    location_claims = {}
    for place in places:
        muni = place.get("municipality", "").strip()
        region = place.get("region", "").strip()
        p_id = place.get("id", "")
        name = place.get("name", "")

        if muni and region:
            # Create a unique key combining municipality and state
            key = (muni.lower(), region.lower())
            if key not in location_claims:
                location_claims[key] = {
                    "municipality": muni,
                    "region": region,
                    "entries": [],
                }
            location_claims[key]["entries"].append(
                {"id": p_id, "name": name}
            )

    # Filter out only those with more than 1 entry
    duplicate_municipalities = [
        data for data in location_claims.values() if len(data["entries"]) > 1
    ]

    # Generate current timestamp in Mountain Time
    run_timestamp = datetime.now(ZoneInfo("America/Denver")).strftime(
        "%Y-%m-%d %H:%M"
    )

    # 3. Write the structured report
    with open(output_txt_path, mode="w", encoding="utf-8") as outfile:
        # Header Section
        outfile.write(f"Most Recent Run : {run_timestamp} MT\n")
        outfile.write(f"{lint_status}\n")
        outfile.write(f"{alphabetical_check_msg}\n")
        outfile.write("=" * 60 + "\n\n")

        # Duplicate Municipalities Section
        outfile.write(
            "1. DUPLICATE MUNICIPALITIES (Multiple breweries in the same City & State)\n"
        )
        outfile.write("-" * 50 + "\n")
        if duplicate_municipalities:
            for idx, dup in enumerate(duplicate_municipalities, start=1):
                outfile.write(
                    f"{idx}. {dup['municipality']}, {dup['region']}:\n"
                )
                for entry in dup["entries"]:
                    outfile.write(f"   - {entry['name']} (ID: {entry['id']})\n")
                outfile.write("\n")
        else:
            outfile.write("None found.\n")

    print(
        f"\nProcessing complete! Saved US Brews report to '{output_txt_path}'."
    )


if __name__ == "__main__":
    print("Loading and linting usbrews reference data via API...")
    ref_data, lint_status = load_and_lint_private_reference_data()

    if ref_data:
        process_usbrews(ref_data, lint_status)
    else:
        print(f"Aborting process due to error: {lint_status}")