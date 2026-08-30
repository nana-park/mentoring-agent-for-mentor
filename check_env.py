from dotenv import load_dotenv
import os

load_dotenv(r'C:/Users/user/Documents/antigravity/notion-mentoring/notion-data-tool/tools/mentoring/.env')
nt = os.getenv('NOTION_TOKEN')
gk = os.getenv('GEMINI_API_KEY')
print('NOTION_TOKEN present:', bool(nt))
print('GEMINI_API_KEY present:', bool(gk))
if nt:
    print('NOTION_TOKEN mask:', nt[:6] + '...' + nt[-4:])
if gk:
    print('GEMINI_API_KEY mask:', gk[:6] + '...' + gk[-4:])
