import base64
import csv
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
import re
import urllib.request

# GitHub API URL for the file (not the raw.githubusercontent URL)
api_url = "https://api.github.com/repos/CSU-CS-314-Fall-2026/students/contents/test/brews/wwbrews.json?ref=main"

input_csv_path = "countries_un_geoscheme_COMMON_NAMES.csv"
output_txt_path = "ww_brew_report.txt"


def load_and_lint_private_reference_data():
    """Fetches wwbrews.json, validates syntax, and falls back to recovery if broken."""
    token = os.environ.get("GH_PAT")

    req = urllib.request.Request(api_url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")

    try:
        with urllib.request.urlopen(req) as response:
            api_data = json.loads(response.read().decode())
            file_content = base64.b64decode(api_data["content"]).decode("utf-8")

        # 1. Try strict JSON load
        try:
            parsed_json = json.loads(file_content)
            lint_status = "JSON Syntax Check (JSONLint): PASSED (Valid JSON)"
            return parsed_json.get("places", []), lint_status
        except json.JSONDecodeError as jde:
            # 2. Try automatic recovery (fixing trailing commas)
            cleaned_content = re.sub(r',\s*([\]}])', r'\1', file_content)
            try:
                parsed_json = json.loads(cleaned_content)
                lint_status = f"JSON Syntax Check (JSONLint): FAILED (Recovered via trailing comma fix) -> {jde}"
                return parsed_json.get("places", []), lint_status
            except json.JSONDecodeError:
                # 3. Fallback: Extract via regex so report generation doesn't block
                lint_status = f"JSON Syntax Check (JSONLint): FAILED -> {jde} (Using fallback parser)"
                places = []
                matches = re.findall(r"\{([^}]+)\}", file_content, re.DOTALL)
                for block in matches:
                    id_match = re.search(r'"id"\s*:\s*"([^"]+)"', block)
                    team_match = re.search(r'"team"\s*:\s*"([^"]+)"', block)
                    country_match = re.search(r'"country"\s*:\s*"([^"]+)"', block)
                    if id_match and country_match:
                        places.append(
                            {
                                "id": id_match.group(1),
                                "team": team_match.group(1) if team_match else "unknown",
                                "country": country_match.group(1),
                            }
                        )
                return places, lint_status

    except Exception as e:
        return [], f"JSON Fetch Error: {e}"


def process_countries(csv_path, places, lint_status):
    """Reads the CSV and parsed places, matches them, flags duplicates, and writes the report."""
    # 1. Check if countries in JSON places are in alphabetical order
    alphabetical_check_msg = (
        "JSON Order Check: All countries are in alphabetical order."
    )
    for i in range(len(places) - 1):
        curr_country = places[i].get("country", "").strip()
        next_country = places[i + 1].get("country", "").strip()

        if curr_country.lower() > next_country.lower():
            offending_place = places[i + 1]
            brewery_name = (
                offending_place.get("name")
                or offending_place.get("brewery")
                or offending_place.get("id")
                or "Unknown Brewery"
            )
            alphabetical_check_msg = (
                f"JSON Order Check: Order breaks down at '{brewery_name}' "
                f"(Country: '{next_country}' follows '{curr_country}')"
            )
            break

    # 2. Load CSV countries into a set and tracking dictionary
    csv_countries = set()
    csv_original_names = {}
    try:
        with open(csv_path, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if not row:
                    continue
                name = row[0].strip()
                clean_name = name.lower()
                csv_countries.add(clean_name)
                csv_original_names[clean_name] = name
    except FileNotFoundError:
        print(f"Error: Could not find the CSV file at '{csv_path}'.")
        return None

    # 3. Group JSON places by country (saving id, team, and original name)
    json_claims = {}
    for place in places:
        c_name = place.get("country")
        p_id = place.get("id")
        p_team = place.get("team", "unknown")
        if c_name and p_id:
            clean_c = c_name.strip().lower()
            if clean_c not in json_claims:
                json_claims[clean_c] = []
            json_claims[clean_c].append(
                {"id": p_id, "team": p_team, "original_name": c_name.strip()}
            )

    # 4. Categorize data
    matched_countries = []
    unclaimed_rows = []
    duplicate_groups = []
    unmatched_json_rows = []

    for clean_c, orig_name in csv_original_names.items():
        if clean_c in json_claims:
            matched_countries.append(orig_name)
        else:
            unclaimed_rows.append(orig_name)

    for clean_c, claims in json_claims.items():
        if len(claims) > 1:
            duplicate_groups.append(claims)

    for clean_c, claims in json_claims.items():
        if clean_c not in csv_countries:
            unmatched_json_rows.append(claims[0]["original_name"])

    # Generate current timestamp in Mountain Time
    run_timestamp = datetime.now(ZoneInfo("America/Denver")).strftime(
        "%Y-%m-%d %H:%M"
    )

    # 5. Write the structured report
    with open(output_txt_path, mode="w", encoding="utf-8") as outfile:
        # Header with Timestamp, JSONLint status, and Alphabetical Check
        outfile.write(f"Most Recent Run : {run_timestamp} MT\n")
        outfile.write(f"{lint_status}\n")
        outfile.write(f"{alphabetical_check_msg}\n")
        outfile.write("=" * 60 + "\n\n")

        # Section 1: Duplicate Claims (Top) - Detailed with team & id
        outfile.write("1. DUPLICATES (duplicated rows OR Multiple people per country)\n")
        outfile.write("-" * 30 + "\n")
        if duplicate_groups:
            for idx, group in enumerate(duplicate_groups, start=1):
                country_name = group[0]["original_name"]
                outfile.write(f"{idx}. {country_name}:\n")
                for entry in group:
                    outfile.write(f"   - Team: {entry['team']}, ID: {entry['id']}\n")
                outfile.write("\n")
        else:
            outfile.write("None found.\n")

        # Section 2: Unmatched JSON
        outfile.write(
            "\n2. UNMATCHED JSON COUNTRIES (In wwbrews.json, but not in countries_un_geoscheme_COMMON_NAMES.csv)\nList includes common name variants to match list entries through 8am Sept 3rd\n"
        )
        outfile.write("-" * 30 + "\n")
        if unmatched_json_rows:
            for idx, country in enumerate(unmatched_json_rows, start=1):
                outfile.write(f"{idx}. {country}\n")
        else:
            outfile.write("None found.\n")

        # Section 3: Taken Countries (Found)
        outfile.write("\n\n3. TAKEN COUNTRIES\n")
        outfile.write("-" * 30 + "\n")
        for idx, country in enumerate(matched_countries, start=1):
            outfile.write(f"{idx}. {country}\n")

        # Section 4: Available Countries (Unclaimed - Bottom)
        outfile.write("\n\n4. AVAILABLE COUNTRIES\n")
        outfile.write("-" * 30 + "\n")
        for idx, country in enumerate(unclaimed_rows, start=1):
            outfile.write(f"{idx}. {country}\n")

    print(f"\nProcessing complete! Saved report to '{output_txt_path}'.")


if __name__ == "__main__":
    print(
        "Loading and linting remote reference data via API with resilient parsing..."
    )
    places, lint_status = load_and_lint_private_reference_data()

    process_countries(input_csv_path, places, lint_status)