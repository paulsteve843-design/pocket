"""
Input validation and quality checks
"""
import json
from pathlib import Path
from typing import List, Dict, Tuple

class CharacterValidator:
    REQUIRED_FIELDS = ["appearance", "clothing"]
    OPTIONAL_FIELDS = ["role", "age", "gender", "ethnicity", "expression", "voice", "emotion", "distinguishing"]
    VALID_ROLES = ["protagonist", "antagonist", "supporting", "narrator", "voiceover"]

    def validate(self, data: Dict) -> Tuple[bool, List[str]]:
        errors = []
        warnings = []

        for name, char in data.items():
            # Check required fields
            for field in self.REQUIRED_FIELDS:
                if field not in char:
                    errors.append(f"Character '{name}': missing required field '{field}'")

            # Check role validity
            role = char.get("role", "").lower()
            if role and role not in self.VALID_ROLES:
                warnings.append(f"Character '{name}': unknown role '{role}', using 'supporting'")

            # Check description quality
            appearance = char.get("appearance", "")
            if len(appearance) < 20:
                warnings.append(f"Character '{name}': appearance description is very short ({len(appearance)} chars)")

            # Check for visual vs narrator
            if role in ["narrator", "voiceover"]:
                if "appearance" in char and char["appearance"] != "N/A":
                    warnings.append(f"Character '{name}': narrator should have minimal/no visual description")

        return len(errors) == 0, errors + warnings

class LocationValidator:
    REQUIRED_FIELDS = ["description"]
    OPTIONAL_FIELDS = ["type", "lighting", "time_of_day", "atmosphere", "acoustic_quality", "key_features"]

    def validate(self, data: Dict) -> Tuple[bool, List[str]]:
        errors = []
        warnings = []

        for name, loc in data.items():
            for field in self.REQUIRED_FIELDS:
                if field not in loc:
                    errors.append(f"Location '{name}': missing required field '{field}'")

            desc = loc.get("description", "")
            if len(desc) < 30:
                warnings.append(f"Location '{name}': description is very short ({len(desc)} chars)")

        return len(errors) == 0, errors + warnings

def validate_all(characters_path: Path, locations_path: Path) -> Dict:
    """Validate all input files and return report"""
    report = {"valid": True, "errors": [], "warnings": []}

    if characters_path.exists():
        with open(characters_path) as f:
            chars = json.load(f)
        ok, msgs = CharacterValidator().validate(chars)
        report["valid"] = report["valid"] and ok
        for m in msgs:
            if "missing" in m.lower() or "error" in m.lower():
                report["errors"].append(m)
            else:
                report["warnings"].append(m)
    else:
        report["valid"] = False
        report["errors"].append(f"Characters file not found: {characters_path}")

    if locations_path.exists():
        with open(locations_path) as f:
            locs = json.load(f)
        ok, msgs = LocationValidator().validate(locs)
        report["valid"] = report["valid"] and ok
        for m in msgs:
            if "missing" in m.lower() or "error" in m.lower():
                report["errors"].append(m)
            else:
                report["warnings"].append(m)
    else:
        report["valid"] = False
        report["errors"].append(f"Locations file not found: {locations_path}")

    return report
