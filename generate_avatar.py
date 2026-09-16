"""
Genera la foto de perfil del bot como imagen PNG
Uso: python generate_avatar.py
Requiere: pip install pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_avatar():
    """Crea avatar del bot SPORT EDGE"""
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Fondo circular con gradiente
    for i in range(size):
        for j in range(size):
            # Distancia del centro
            dx = i - size // 2
            dy = j - size // 2
            dist = (dx ** 2 + dy ** 2) ** 0.5
            
            if dist < size // 2 - 4:
                # Gradiente interior
                factor = dist / (size // 2)
                r = int(26 * (1 - factor) + 13 * factor)
                g = int(26 * (1 - factor) + 13 * factor)
                b = int(62 * (1 - factor) + 43 * factor)
                img.putpixel((i, j), (r, g, b, 255))
            elif dist < size // 2:
                # Borde brillante cyan
                img.putpixel((i, j), (0, 217, 255, 255))
    
    # Crear máscara circular
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([4, 4, size-4, size-4], fill=255)
    
    # Aplicar máscara
    output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    output.paste(img, mask=mask)
    
    # Texto "SPORT"
    try:
        font_sport = ImageFont.truetype("arialbd.ttf", 85)
    except:
        try:
            font_sport = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 85)
        except:
            font_sport = ImageFont.load_default()
    
    try:
        font_edge = ImageFont.truetype("arialbd.ttf", 110)
    except:
        try:
            font_edge = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 110)
        except:
            font_edge = ImageFont.load_default()
    
    try:
        font_bot = ImageFont.truetype("arialbd.ttf", 30)
    except:
        try:
            font_bot = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 30)
        except:
            font_bot = ImageFont.load_default()
    
    draw = ImageDraw.Draw(output)
    
    # Sombra del texto
    shadow_color = (0, 0, 0, 128)
    
    # Texto "SPORT" - cyan
    sport_text = "SPORT"
    bbox = draw.textbbox((0, 0), sport_text, font=font_sport)
    text_width = bbox[2] - bbox[0]
    x = (size - text_width) // 2
    y = 120
    
    # Sombra
    draw.text((x+3, y+3), sport_text, fill=shadow_color, font=font_sport)
    # Texto principal
    draw.text((x, y), sport_text, fill=(0, 217, 255, 255), font=font_sport)
    
    # Texto "EDGE" - gradiente verde-cyan
    edge_text = "EDGE"
    bbox = draw.textbbox((0, 0), edge_text, font=font_edge)
    text_width = bbox[2] - bbox[0]
    x = (size - text_width) // 2
    y = 200
    
    # Sombra
    draw.text((x+3, y+3), edge_text, fill=shadow_color, font=font_edge)
    # Texto principal - verde brillante
    draw.text((x, y), edge_text, fill=(0, 255, 136, 255), font=font_edge)
    
    # Badge "BOT"
    bot_text = "BOT"
    bbox = draw.textbbox((0, 0), bot_text, font=font_bot)
    text_width = bbox[2] - bbox[0]
    x = (size - text_width) // 2
    y = 330
    
    # Fondo del badge
    badge_padding = 15
    badge_x1 = x - badge_padding * 2
    badge_y1 = y - badge_padding
    badge_x2 = x + text_width + badge_padding * 2
    badge_y2 = y + 35 + badge_padding
    
    # Dibujar badge redondeado
    draw.rounded_rectangle(
        [badge_x1, badge_y1, badge_x2, badge_y2],
        radius=20,
        fill=(0, 217, 255, 255)
    )
    
    # Texto del badge
    draw.text((x, y), bot_text, fill=(13, 13, 43, 255), font=font_bot)
    
    # Estrellas decorativas
    sparkle_positions = [
        (100, 100), (400, 120), (80, 380), 
        (420, 360), (250, 80), (250, 420)
    ]
    for pos in sparkle_positions:
        draw.ellipse([pos[0]-3, pos[1]-3, pos[0]+3, pos[1]+3], fill=(255, 255, 255, 200))
    
    # Guardar
    output_path = os.path.join(os.path.dirname(__file__), "avatar_bot.png")
    output.save(output_path, "PNG")
    print(f"Avatar guardado en: {output_path}")
    return output_path


if __name__ == "__main__":
    print("Generando avatar del bot SPORT EDGE...")
    path = create_avatar()
    print(f"Listo! Abrir: {path}")
