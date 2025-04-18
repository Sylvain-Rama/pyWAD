import base64

def image_to_base64(img_path):
    with open(img_path, "rb") as f:
        content = f.read()
        
        raw_base64 = base64.b64encode(content).decode()
        return f"data:image/png;base64,{raw_base64}"


banner_html = """
<div class="banner">
    <img src=""" + image_to_base64("media\header.png") + """ alt="WadViewer Banner">
</div>
<style>
    .banner {
        width: 100%;
        height: 100%;
        overflow: hidden;
    }
    .banner img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
</style>
"""
