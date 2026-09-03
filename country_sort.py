import base64
import csv
import json
import os
import urllib.request

# GitHub API URL for the file (not the raw.githubusercontent URL)
api_url = "https://api.github.com/repos/CSU-CS-314-Fall-2026/students/contents/test/brews/wwbrews.json?ref=main"

input_csv_path = "countries_un_geoscheme_COMMON_NAMES.csv"
output_txt_path = "ww_brew_report.txt"


def load_private_reference_data():
    """Fetches the private file from GitHub using an API token."""
    token = os.environ.get("GH_PAT")  # Pulls the secret from environment variables

    req = urllib.request.Request(api_url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")

    try:
        with urllib.request.urlopen(req) as response:
            api_data = json.loads(response.read().decode())
            # The GitHub API returns file content base64 encoded
            file_content = base64.b64decode(api_data["content"]).decode("utf-8")
            return json.loads(file_content)
    except Exception as e:
        print(f"Error fetching private data: {e}")
        return None


def process_countries(csv_path, reference_data):
    """Reads the CSV and JSON, matches them, flags duplicates, and writes a comprehensive text report."""
    places = reference_data.get("places", [])

    # 1. Load CSV countries into a set and tracking dictionary
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

    # 2. Group JSON places by country (to capture multiple claims/duplicates)
    json_claims = {}
    for place in places:
        c_name = place.get("country")
        p_id = place.get("id")
        if c_name and p_id:
            clean_c = c_name.strip().lower()
            if clean_c not in json_claims:
                json_claims[clean_c] = []
            json_claims[clean_c].append({"id": p_id, "original_name": c_name.strip()})

    # 3. Categorize data
    matched_rows = []
    unclaimed_rows = []
    duplicate_rows = []
    unmatched_json_rows = []

    # Check CSV countries against JSON claims (Taken Countries)
    for clean_c, orig_name in csv_original_names.items():
        if clean_c in json_claims:
            claims = json_claims[clean_c]
            # List all IDs taken for this country
            all_ids = ", ".join([c["id"] for c in claims])
            matched_rows.append({"country": orig_name, "ids": all_ids})
        else:
            unclaimed_rows.append(orig_name)

    # Check for duplicates (> 1 claim in JSON)
    for clean_c, claims in json_claims.items():
        if len(claims) > 1:
            ids = ", ".join([c["id"] for c in claims])
            duplicate_rows.append({"country": claims[0]["original_name"], "ids": ids})

    # Check for JSON countries that are NOT in the CSV
    for clean_c, claims in json_claims.items():
        if clean_c not in csv_countries:
            unmatched_json_rows.append(claims[0]["original_name"])

    # 4. Write the structured report to a text file in the requested order
    with open(output_txt_path, mode="w", encoding="utf-8") as outfile:
        # Section 1: Duplicate Claims (Top)
        outfile.write("1. DUPLICATE CLAIMS (Multiple people per country)\n")
        outfile.write("-" * 30 + "\n")
        if duplicate_rows:
            for idx, item in enumerate(duplicate_rows, start=1):
                outfile.write(f"{idx}. {item['country']} --> IDs: {item['ids']}\n")
        else:
            outfile.write("None found.\n")

        # Section 2: Unmatched JSON
        outfile.write("\n\n2. UNMATCHED JSON COUNTRIES (In wwbrews.json, but not in countries_un_geoscheme.csv)\n")
        outfile.write("-" * 30 + "\n")
        if unmatched_json_rows:
            for idx, country in enumerate(unmatched_json_rows, start=1):
                outfile.write(f"{idx}. {country}\n")
        else:
            outfile.write("None found.\n")

        # Section 3: Taken Countries (Found)
        outfile.write("\n\n3. TAKEN COUNTRIES\n")
        outfile.write("-" * 30 + "\n")
        for idx, item in enumerate(matched_rows, start=1):
            outfile.write(f"{idx}. {item['country']} --> {item['ids']}\n")

        # Section 4: Available Countries (Unclaimed - Bottom)
        outfile.write("\n\n4. AVAILABLE COUNTRIES\n")
        outfile.write("-" * 30 + "\n")
        for idx, country in enumerate(unclaimed_rows, start=1):
            outfile.write(f"{idx}. {country}\n")

    print(f"\nProcessing complete! Saved detailed report to '{output_txt_path}'.")


if __name__ == "__main__":
    print("Loading remote reference data via API...")
    ref_data = load_private_reference_data()

    if ref_data:
        process_countries(input_csv_path, ref_data)