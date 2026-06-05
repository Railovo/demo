import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'outputs')
IMG_ORDER = [
    ('IC significance', 'stat_ic_pvalues.png'),
    ('Robustness heatmap', 'robustness_heatmap_cost_600bps.png'),
    ('Portfolio NAV', 'highres_multi_factor_cum.png'),
    ('Quintile cumulative returns', 'highres_filtered_quintile_cum_returns.png')
]
PDF_PATH = os.path.join(OUT, 'multi_factor_presentation.pdf')

pages = []
for title, fname in IMG_ORDER:
    img_path = os.path.join(OUT, fname)
    if os.path.exists(img_path):
        img = Image.open(img_path).convert('RGB')
        # add a small title bar at top
        w, h = img.size
        new_h = h + 80
        page = Image.new('RGB', (w, new_h), 'white')
        draw = ImageDraw.Draw(page)
        try:
            font = ImageFont.truetype('arial.ttf', 24)
        except Exception:
            font = ImageFont.load_default()
        draw.text((20, 20), title, fill='black', font=font)
        page.paste(img, (0, 80))
        pages.append(page)
    else:
        # create placeholder page
        page = Image.new('RGB', (1200, 800), 'white')
        draw = ImageDraw.Draw(page)
        try:
            font = ImageFont.truetype('arial.ttf', 24)
        except Exception:
            font = ImageFont.load_default()
        draw.text((20, 20), f'{title} - image missing: {fname}', fill='black', font=font)
        pages.append(page)

# add a final one-pager text slide if present
onepager = os.path.join(OUT, 'project_one_pager_final.md')
if os.path.exists(onepager):
    with open(onepager, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
    page = Image.new('RGB', (1200, 800), 'white')
    draw = ImageDraw.Draw(page)
    try:
        font_title = ImageFont.truetype('arial.ttf', 28)
        font_body = ImageFont.truetype('arial.ttf', 14)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
    draw.text((20, 20), 'Project One-pager', fill='black', font=font_title)
    y = 70
    for line in lines:
        if y > 760:
            break
        draw.text((20, y), line, fill='black', font=font_body)
        y += 20
    pages.append(page)

# try to assemble PDF using img2pdf for reliability
try:
    import img2pdf
    tmp_dir = os.path.join(OUT, 'tmp_pdf_pages')
    os.makedirs(tmp_dir, exist_ok=True)
    png_paths = []
    for i, page in enumerate(pages):
        pth = os.path.join(tmp_dir, f'page_{i:02d}.png')
        page.save(pth, format='PNG')
        png_paths.append(pth)
    with open(PDF_PATH, 'wb') as f:
        f.write(img2pdf.convert(png_paths))
    print('Wrote', PDF_PATH)
except Exception:
    # fallback to PIL save
    if pages:
        pages[0].save(PDF_PATH, save_all=True, append_images=pages[1:])
        print('Wrote', PDF_PATH)
    else:
        print('No pages to write')
