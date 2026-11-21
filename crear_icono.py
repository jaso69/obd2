"""Genera icono.ico (reloj de turbo estilo panel). Requiere Pillow (solo en el PC de desarrollo)."""
import math
import os

from PIL import Image, ImageDraw, ImageFont

S = 1024                      # se dibuja grande y se reduce (antialiasing)
BG = (24, 28, 34, 255)
TRACK = (52, 60, 74, 255)
ACCENT = (255, 122, 41, 255)
RED = (239, 83, 80, 255)
FG = (232, 235, 240, 255)


def pt(cx, cy, r, ang):
    a = math.radians(ang)
    return cx + r * math.cos(a), cy - r * math.sin(a)


def dibujar():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((24, 24, S - 24, S - 24), radius=200, fill=BG)

    cx, cy, r, w = S / 2, S * 0.54, S * 0.34, int(S * 0.085)
    box = (cx - r, cy - r, cx + r, cy + r)
    # PIL: angulos en sentido horario desde las 3; arco de 240 grados
    d.arc(box, start=150, end=390, fill=TRACK, width=w)
    d.arc(box, start=150, end=320, fill=ACCENT, width=w)
    d.arc(box, start=360, end=390, fill=RED, width=w)

    for i in range(9):                       # marcas
        ang = 210 - 240 * i / 8
        d.line([pt(cx, cy, r - w * 0.9, ang), pt(cx, cy, r - w * 1.6, ang)], fill=FG, width=int(S * 0.018))

    ang = 210 - 240 * 0.72                   # aguja
    tip = pt(cx, cy, r * 0.82, ang)
    base_l = pt(cx, cy, S * 0.045, ang + 90)
    base_r = pt(cx, cy, S * 0.045, ang - 90)
    d.polygon([tip, base_l, base_r], fill=FG)
    d.ellipse((cx - S * 0.075, cy - S * 0.075, cx + S * 0.075, cy + S * 0.075), fill=ACCENT)
    d.ellipse((cx - S * 0.03, cy - S * 0.03, cx + S * 0.03, cy + S * 0.03), fill=BG)

    try:
        font = ImageFont.truetype("segoeuib.ttf", int(S * 0.15))
        d.text((cx, S * 0.84), "TDI", font=font, fill=FG, anchor="mm")
    except OSError:
        pass
    return img


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icono.ico")
    big = dibujar().resize((256, 256), Image.LANCZOS)
    big.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    big.save(out.replace(".ico", ".png"))
    print("Creado", out)
