from PIL import Image, ImageDraw, ImageFont
import io
import os
from pathlib import Path
from typing import List, Dict

try:
    from hoshino import logger
except ImportError:
    import logging
    logger = logging.getLogger("todo_render")

# Helper to find a font
def get_font_path():
    # Try some common fonts on Windows or Linux
    candidates = [
        "msyh.ttc", "simhei.ttf", # Windows
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", # Linux common
        "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc"
    ]
    
    # Also check local module path
    local_font = Path(__file__).parent / "msyh.ttc"
    if local_font.exists():
        return str(local_font)
        
    for font in candidates:
        if os.path.exists(font):
            return font
        # Check system font dir on Windows
        if os.name == 'nt':
            win_font = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', font)
            if os.path.exists(win_font):
                return win_font
                
    return None # Fallback to default

def render_todo_list_pil(todos: List[Dict]) -> bytes:
    """
    Render todo list as a sticky note image using PIL.
    """
    # Canvas settings
    width = 400
    # Dynamic height based on items, min 400
    line_height = 40
    header_height = 80
    footer_height = 60
    content_height = len(todos) * line_height
    height = max(400, header_height + content_height + footer_height)
    
    # Colors
    bg_color = (254, 243, 189) # #fef3bd Light Yellow
    text_color = (85, 85, 85) # #555
    line_color = (224, 216, 160) # #e0d8a0
    done_color = (153, 153, 153) # #999
    id_color = (211, 84, 0) # #d35400
    
    # Create image
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Load Font
    font_path = get_font_path()
    try:
        title_font = ImageFont.truetype(font_path, 32) if font_path else ImageFont.load_default()
        item_font = ImageFont.truetype(font_path, 20) if font_path else ImageFont.load_default()
        meta_font = ImageFont.truetype(font_path, 14) if font_path else ImageFont.load_default()
    except Exception:
        title_font = ImageFont.load_default()
        item_font = ImageFont.load_default()
        meta_font = ImageFont.load_default()
        
    # Draw Tape (Simple visual trick)
    # Translucent white rect at top center
    tape_w, tape_h = 120, 35
    tape_x = (width - tape_w) // 2
    tape_y = 5
    draw.rectangle([tape_x, tape_y, tape_x + tape_w, tape_y + tape_h], fill=(255, 255, 255))
    
    # Draw Title
    title = "Todo List"
    # Get text bbox to center
    try:
        _, _, w, h = draw.textbbox((0, 0), title, font=title_font)
    except AttributeError:
         w, h = draw.textsize(title, font=title_font)
         
    draw.text(((width - w) / 2, 50), title, font=title_font, fill=text_color)
    
    # Draw dashed line under title
    dash_y = 90
    for x in range(20, width - 20, 10):
        draw.line([(x, dash_y), (x + 5, dash_y)], fill=(170, 170, 170), width=2)
        
    # Draw Items
    start_y = 110
    
    if not todos:
        empty_text = "喵~ 暂时没有待办事项哦！\n输入 '记 [事情]' 来添加吧！"
        try:
            _, _, w, h = draw.textbbox((0, 0), empty_text, font=item_font)
        except AttributeError:
             w, h = draw.textsize(empty_text, font=item_font)
        draw.text(((width - w) / 2, 200), empty_text, font=item_font, fill=(136, 136, 136), align="center")
    
    current_y = start_y
    for item in todos:
        # ID Badge
        id_text = f"#{item['id']}"
        draw.text((20, current_y), id_text, font=item_font, fill=id_color)
        
        # Content
        content_text = item['content']
        # Simple truncation if too long
        if len(content_text) > 18:
            content_text = content_text[:17] + "..."
            
        # Check if done
        is_done = item.get('is_done', False)
        fill_color = done_color if is_done else text_color
        
        draw.text((90, current_y), content_text, font=item_font, fill=fill_color)
        
        # Strikethrough if done
        if is_done:
            draw.line([(90, current_y + 10), (350, current_y + 10)], fill=done_color, width=2)
            
        # Due Date
        if item.get('due_date') and not is_done:
            due_text = f"⏰ {item['due_date']}"
            draw.text((90, current_y + 24), due_text, font=meta_font, fill=id_color)
            item_h = line_height + 15 # extra space for date
        else:
            item_h = line_height
            
        # Separator line
        draw.line([(20, current_y + item_h - 5), (width - 20, current_y + item_h - 5)], fill=line_color, width=1)
        
        current_y += item_h

    # Output to bytes
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

# Compatibility wrapper
async def render_todo_list(todos: list) -> bytes:
    # Run sync PIL code
    return render_todo_list_pil(todos)
