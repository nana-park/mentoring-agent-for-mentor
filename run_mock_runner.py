import os
from dotenv import load_dotenv
import runpy

# Ensure UTF-8 mode for output
os.environ['PYTHONUTF8'] = '1'

# Load local .env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Execute the mock_test module as __main__ so relative imports work
runpy.run_module('tools.mentoring.mock_test', run_name='__main__')
