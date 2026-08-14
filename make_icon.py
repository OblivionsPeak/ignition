"""Generates icon.ico — the red engine-start button every race car has, with a
bolt through it.

Two masters rather than one. At 16-20px the button, its rim and its gradients
collapse into a red blob with a smudge on it, so the small master throws the
button away and keeps only what carries the identity: a red tile and a white
bolt, drawn fat enough to survive. Everything is drawn at 8x and downsampled,
which is what keeps the diagonals clean.

    python make_icon.py
"""
from PIL import Image, ImageDraw

SS = 8  # supersample factor

BG_TOP = (29, 32, 39)
BG_BOT = (17, 19, 23)
RED_TOP = (232, 74, 58)
RED_BOT = (162, 18, 14)
RED_FLAT = (206, 44, 34)
RIM = (255, 122, 108)
BOLT = (255, 255, 255)

# Normalised lightning bolt, y down.
BOLT_PTS = [(0.585, 0.055), (0.235, 0.560), (0.445, 0.560),
            (0.395, 0.955), (0.762, 0.430), (0.545, 0.430)]

# Same silhouette with the strokes widened — thin diagonals are the first thing
# to disappear when an icon is downsampled to 16px.
BOLT_FAT = [(0.620, 0.040), (0.175, 0.585), (0.430, 0.585),
            (0.380, 0.960), (0.825, 0.400), (0.565, 0.400)]


def _vgrad(size, top, bot):
    """Vertical gradient as an image, one row at a time."""
    g = Image.new('RGB', (1, size))
    px = g.load()
    for y in range(size):
        t = y / max(1, size - 1)
        px[0, y] = tuple(round(a + (b - a) * t) for a, b in zip(top, bot))
    return g.resize((size, size), Image.NEAREST)


def _disc_mask(size, r):
    m = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(m)
    c = size / 2
    d.ellipse([c - r, c - r, c + r, c + r], fill=255)
    return m


def draw(px, simple):
    """One icon layer at `px` pixels square."""
    s = px * SS
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # rounded-square body
    radius = s * 0.22
    body = Image.new('L', (s, s), 0)
    ImageDraw.Draw(body).rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=255)
    bg = _vgrad(s, RED_TOP, RED_BOT) if simple else _vgrad(s, BG_TOP, BG_BOT)
    img.paste(bg, (0, 0), body)

    c = s / 2
    r = s * 0.355

    if simple:
        # no button, no rim — just the bolt, as large as the tile allows
        pts = [(c + (x - 0.5) * s * 0.86, c + (y - 0.5) * s * 0.86) for x, y in BOLT_FAT]
        d.polygon(pts, fill=BOLT)
        return img.resize((px, px), Image.LANCZOS)

    # machined rim: a slightly larger ring behind the button face
    d.ellipse([c - r * 1.13, c - r * 1.13, c + r * 1.13, c + r * 1.13],
              fill=(48, 53, 63, 255))
    d.ellipse([c - r * 1.06, c - r * 1.06, c + r * 1.06, c + r * 1.06],
              fill=RIM + (90,))

    img.paste(_vgrad(s, RED_TOP, RED_BOT), (0, 0), _disc_mask(s, r))

    # top-edge sheen, so the button reads as convex
    gloss = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).ellipse(
        [c - r * 0.78, c - r * 0.86, c + r * 0.78, c - r * 0.10],
        fill=(255, 255, 255, 38))
    img.alpha_composite(gloss)

    # bolt, scaled about the disc centre
    scale = r * 1.46
    pts = [(c + (x - 0.5) * scale, c + (y - 0.5) * scale) for x, y in BOLT_PTS]
    # a soft dark edge keeps the bolt legible against the lighter top half
    d.polygon([(x, y + s * 0.012) for x, y in pts], fill=(90, 8, 6, 120))
    d.polygon(pts, fill=BOLT)

    return img.resize((px, px), Image.LANCZOS)


def main():
    sizes = [16, 20, 24, 32, 48, 64, 128, 256]
    layers = [draw(px, simple=px <= 24) for px in sizes]
    layers[-1].save('icon.ico', format='ICO',
                    sizes=[(px, px) for px in sizes], append_images=layers[:-1])
    draw(512, simple=False).save('icon.png')
    print('wrote icon.ico ({} layers) and icon.png'.format(len(sizes)))


if __name__ == '__main__':
    main()
