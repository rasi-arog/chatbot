from PIL import Image
import os

def compress_image(input_path: str) -> str:
    if os.path.getsize(input_path) < 200 * 1024:
        return input_path
    output_path = input_path.replace(".jpg", "_compressed.jpg")
    img = Image.open(input_path).convert("RGB")
    img.thumbnail((800, 800))
    img.save(output_path, "JPEG", quality=65, optimize=True)
    return output_path
