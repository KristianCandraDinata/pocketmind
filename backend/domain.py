from backend.config import DOMAIN

from backend.ai.prompts.mpasi import SYSTEM_PROMPT as MPASI_PROMPT
from backend.ai.prompts.student_support import SYSTEM_PROMPT as STUDENT_SUPPORT_PROMPT


DOMAIN_SETTINGS = {
    "mpasi": {
        "system_prompt": MPASI_PROMPT,
        "knowledge_file": "backend/knowledge/mpasi.txt",
    },
    "student_support": {
        "system_prompt": STUDENT_SUPPORT_PROMPT,
        "knowledge_file": "backend/knowledge/student_support.txt",
    },
}

ACTIVE_DOMAIN = DOMAIN_SETTINGS[DOMAIN]
