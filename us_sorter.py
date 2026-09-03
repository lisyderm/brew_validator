import json

# File paths
input_json_path = "usbrews.json"
output_json_path = "usbrews_sorted.json"


def sort_and_format_json(file_path):
    """Loads JSON, sorts 'places' by region then municipality,

    and writes out the file with each place on a single line.
    """
    try:
        with open(file_path, mode="r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find '{file_path}'.")
        return
    except json.JSONDecodeError:
        print(f"Error: '{file_path}' is not a valid JSON file.")
        return

    # Extract top-level metadata and places
    earth_radius = data.get("earthRadius", 3959.0)
    units = data.get("units", "km")
    places = data.get("places", [])

    # Sort places primarily by 'region', secondarily by 'municipality'
    sorted_places = sorted(
        places,
        key=lambda x: (
            x.get("region", "").strip().lower(),
            x.get("municipality", "").strip().lower(),
        ),
    )

    # Build the custom one-liner text structure
    lines = []
    lines.append("{")
    lines.append(f'  "earthRadius"   : {earth_radius},')
    lines.append(f'  "units"         : "{units}",')
    lines.append('  "places"        : [')

    for i, place in enumerate(sorted_places):
        # Convert the dictionary into a single-line JSON string
        place_str = json.dumps(place)
        if i == 0:
            lines.append(f"    {place_str}")
        else:
            lines.append(f"    ,{place_str}")

    lines.append("  ]")
    lines.append("}")

    # Write out to the new JSON file
    with open(output_json_path, mode="w", encoding="utf-8") as outfile:
        outfile.write("\n".join(lines))

    print(f"Success! Sorted one-liner JSON saved to '{output_json_path}'.")


if __name__ == "__main__":
    sort_and_format_json(input_json_path)