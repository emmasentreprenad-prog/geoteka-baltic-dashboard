import os
from PIL import Image


def create_clean_logo(input_logo="GeoTeka_logo.png", output_logo="GeoTeka_logo_clean.png"):
    if not os.path.exists(input_logo):
        return None

    img = Image.open(input_logo).convert("RGBA")
    bbox = img.getbbox()

    if bbox:
        img = img.crop(bbox)

    new_pixels = []
    for r, g, b, a in img.getdata():
        if r > 175 and g > 175 and b > 175:
            new_pixels.append((255, 255, 255, 0))
        else:
            new_pixels.append((r, g, b, a))

    img.putdata(new_pixels)
    img.save(output_logo)
    return output_logo
