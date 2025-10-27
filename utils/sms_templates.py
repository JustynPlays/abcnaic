import json
import os
from typing import Dict

TEMPLATES_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'sms_templates.json')


def _load_raw() -> Dict:
    try:
        with open(TEMPLATES_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def get_templates() -> Dict[str, Dict[str, str]]:
    return _load_raw()


def save_templates(templates: Dict[str, Dict[str, str]]) -> None:
    # Write atomically
    tmp = TEMPLATES_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)
    os.replace(tmp, TEMPLATES_PATH)
