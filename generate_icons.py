# -*- coding: utf-8 -*-
"""
Скрипт для генерации иконок PWA из одного изображения
Требуется: pip install Pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_pwa_icons():
    """Создание иконок PWA разных размеров"""
    
    # Создаем папку для иконок
    icons_dir = 'static/icons'
    os.makedirs(icons_dir, exist_ok=True)
    
    # Размеры иконок для PWA
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    # Создаем базовую иконку с градиентом
    base_size = 512
    img = Image.new('RGB', (base_size, base_size), color='white')
    draw = ImageDraw.Draw(img)
    
    # Рисуем градиентный фон
    for y in range(base_size):
        # Градиент от #667eea до #764ba2
        r = int(102 + (118 - 102) * y / base_size)
        g = int(126 - (126 - 75) * y / base_size)
        b = int(234 - (234 - 162) * y / base_size)
        draw.line([(0, y), (base_size, y)], fill=(r, g, b))
    
    # Добавляем текст/логотип
    try:
        # Пытаемся использовать системный шрифт
        font_size = 200
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Если не получилось, используем дефолтный
        font = ImageFont.load_default()
    
    # Рисуем иконку микрофона (упрощенно)
    center_x, center_y = base_size // 2, base_size // 2
    
    # Микрофон (белый круг и палка)
    draw.ellipse([center_x-80, center_y-120, center_x+80, center_y-20], fill='white')
    draw.rectangle([center_x-20, center_y-20, center_x+20, center_y+60], fill='white')
    draw.ellipse([center_x-50, center_y+60, center_x+50, center_y+100], fill='white', outline='white')
    
    # Добавляем текст "NS"
    draw.text((center_x, center_y+150), "NS", fill='white', font=font, anchor='mm')
    
    # Сохраняем в разных размерах
    for size in sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        filename = os.path.join(icons_dir, f'icon-{size}x{size}.png')
        resized.save(filename, 'PNG')
        print(f'✓ Создана иконка: {filename}')
    
    print(f'\n✅ Создано {len(sizes)} иконок в папке {icons_dir}/')
    print('Вы можете заменить их своими иконками, сохранив те же размеры.')

if __name__ == '__main__':
    try:
        create_pwa_icons()
    except ImportError:
        print('❌ Ошибка: Установите Pillow')
        print('Выполните: pip install Pillow')
    except Exception as e:
        print(f'❌ Ошибка: {e}')
