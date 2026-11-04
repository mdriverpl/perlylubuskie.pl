import os
# External research is tested explicitly with fixtures, never started by API tests.
os.environ.setdefault('REGION_RESEARCH_WORKER','0')
os.environ.setdefault('CONTACT_RESEARCH_WORKER','0')
os.environ.setdefault('PHOTO_RESEARCH_WORKER','0')
os.environ.setdefault('PROMPT_TASK_WORKER','0')
os.environ.setdefault('LAKE_CATALOG_IMPORT','0')
os.environ.setdefault('LAKE_MAP_PREVIEWS_IMPORT','0')
