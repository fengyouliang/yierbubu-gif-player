from PIL import Image

def convert_png_to_icon_png(input_path, output_path, size=(32, 32)):
    # 打开 PNG 图片并转换为 RGBA 以便处理透明通道
    img = Image.open(input_path).convert('RGBA')

    # 创建白色背景以去除透明
    background = Image.new('RGB', img.size, (255, 255, 255))
    background.paste(img, mask=img.split()[3])  # 使用 alpha 通道作为遮罩

    # 缩放图像到指定尺寸
    resized = background.resize(size, Image.LANCZOS)

    # 保存为 PNG 文件，不含 alpha 通道
    resized.save(output_path, format='PNG')

# 示例调用
convert_png_to_icon_png('./icon/input.png', './icon/output.png', size=(32, 32))
# 或者使用 16x16：convert_png_to_icon_png('input.png', 'output_16.png', size=(16, 16))
