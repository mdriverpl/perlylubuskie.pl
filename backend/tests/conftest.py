import os
# External research is tested explicitly with fixtures, never started by API tests.
os.environ.setdefault('REGION_RESEARCH_WORKER','0')
