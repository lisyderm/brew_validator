import csv
import json

# 1. File paths for your local files
json_file_path = "wwbrews.json"
input_csv_path = "countries.csv"
output_txt_path = "countries_report_num_cats.txt"


def load_local_reference_data(file_path):
    """Loads and parses the JSON reference data from a local file."""
    try:
        with open(file_path, mode="r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find the reference JSON file at '{file_path}'.")
        return None
    except json.JSONDecodeError:
        print(f"Error: '{file_path}' is not a valid JSON file.")
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

    # Check CSV countries against JSON claims
    for clean_c, orig_name in csv_original_names.items():
        if clean_c in json_claims:
            claims = json_claims[clean_c]
            # Use the first ID for the standard found list
            matched_rows.append({"country": orig_name, "id": claims[0]["id"]})
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

    # 4. Write the structured report to a text file
    with open(output_txt_path, mode="w", encoding="utf-8") as outfile:
        # Section 1: Found
        outfile.write("1. FOUND COUNTRIES\n")
        outfile.write("-" * 30 + "\n")
        for idx, item in enumerate(matched_rows, start=1):
            outfile.write(f"{idx}. {item['country']} --> {item['id']}\n")

        # Section 2: Unclaimed
        outfile.write("\n\n2. UNCLAIMED COUNTRIES\n")
        outfile.write("-" * 30 + "\n")
        for idx, country in enumerate(unclaimed_rows, start=1):
            outfile.write(f"{idx}. {country}\n")

        # Section 3: Duplicates
        outfile.write("\n\n3. DUPLICATE CLAIMS (Multiple people per country)\n")
        outfile.write("-" * 30 + "\n")
        if duplicate_rows:
            for idx, item in enumerate(duplicate_rows, start=1):
                outfile.write(f"{idx}. {item['country']} --> IDs: {item['ids']}\n")
        else:
            outfile.write("None found.\n")

        # Section 4: Unmatched JSON
        outfile.write("\n\n4. UNMATCHED JSON COUNTRIES (In wwbrews.json, but not in countries.csv)\n")
        outfile.write("-" * 30 + "\n")
        if unmatched_json_rows:
            for idx, country in enumerate(unmatched_json_rows, start=1):
                outfile.write(f"{idx}. {country}\n")
        else:
            outfile.write("None found.\n")

    print(f"\nProcessing complete! Saved detailed report to '{output_txt_path}'.")


if __name__ == "__main__":
    print("Loading local reference data...")
    ref_data = load_local_reference_data(json_file_path)

    if ref_data:
        process_countries(input_csv_path, ref_data)