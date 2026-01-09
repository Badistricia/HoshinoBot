import os
import base64
from pathlib import Path
from typing import List, Dict
from hoshino import logger
import jinja2

# Try to import dailySum's screenshot tool
# This is the cleanest way to reuse existing infrastructure
try:
    from ..dailySum.test_html_report_2 import html_to_screenshot, init_playwright
    HAS_SCREENSHOT_TOOL = True
except ImportError:
    HAS_SCREENSHOT_TOOL = False
    logger.error("Failed to import html_to_screenshot from dailySum. Please ensure dailySum module is present.")

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMP_DIR = Path(__file__).parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# Initialize jinja2 environment
template_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

async def render_todo_list(todos: List[Dict]) -> bytes:
    """
    Render todo list to image using HTML + Playwright (via dailySum).
    """
    if not HAS_SCREENSHOT_TOOL:
        logger.error("Screenshot tool not available.")
        return b""

    # 1. Render HTML
    try:
        template = template_env.get_template("todo_list.html")
        html_content = template.render(todos=todos)
        
        # Save HTML to temp file
        temp_html_path = TEMP_DIR / "todo_list_temp.html"
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
    except Exception as e:
        logger.error(f"Failed to render HTML template: {e}")
        return b""

    # 2. Convert to Image
    temp_img_path = TEMP_DIR / "todo_list_output.png"
    
    # Ensure playwright is ready
    await init_playwright()
    
    success = await html_to_screenshot(str(temp_html_path.absolute()), str(temp_img_path.absolute()))
    
    if success and temp_img_path.exists():
        with open(temp_img_path, "rb") as f:
            img_bytes = f.read()
            
        # Cleanup
        try:
            os.remove(temp_html_path)
            os.remove(temp_img_path)
        except:
            pass
            
        return img_bytes
    else:
        logger.error("Failed to generate screenshot.")
        return b""
