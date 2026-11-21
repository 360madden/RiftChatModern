"""Generate original RCM glass UI textures for the RIFT Lua addon.

Deterministic PNG assets; no runtime Python dependency in RIFT.  The transparent
rounded panels, cyan outlines and dark glass are based on the approved visual
direction.  Do not embed names, chat transcripts, or any text in these textures.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import math

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "addon" / "RiftChatModern" / "textures"


def color_lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(4))


def paint(width, height, *, radius, top, bottom, rim, inner=None,
          glow=False, top_rule=False):
    """Paint a rounded semi-transparent surface without scaling artifacts in
    the source; Lua adjusts the destination rectangle for resized windows."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    mask = Image.new("L", (width, height), 0)
    drawer = ImageDraw.Draw(mask)
    inset = 2
    drawer.rounded_rectangle((inset, inset, width-inset-1, height-inset-1),
                             radius=radius, fill=255)
    gradient = Image.new("RGBA", (width, height))
    px = gradient.load()
    for y in range(height):
        t = y / max(1, height-1)
        shade = color_lerp(top, bottom, t)
        for x in range(width):
            if glow:
                dx = (x-width*.83)/(width*.7)
                dy = (y-height*.06)/(height*.85)
                warmth = max(0.0, 1.0 - math.sqrt(dx*dx+dy*dy))
                px[x,y] = (min(255, shade[0]+int(3*warmth)),
                           min(255, shade[1]+int(21*warmth)),
                           min(255, shade[2]+int(24*warmth)), shade[3])
            else:
                px[x,y] = shade
    img.paste(gradient, (0,0), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 2, width-3, height-3), radius=radius,
                        outline=rim, width=3)
    if inner is not None:
        d.rounded_rectangle((6, 6, width-7, height-7),
                            radius=max(2,radius-4), outline=inner, width=2)
    if top_rule:
        d.line(((max(radius,18), 3), (width-max(radius,18), 3)),
               fill=(94, 234, 212, 220), width=3)
    return img


def generate():
    TARGET.mkdir(parents=True, exist_ok=True)
    recipes = {
        "glass_panel": (1024,768,29,(5,19,28,224),(5,13,23,228),(42,226,221,235),(22,111,128,100),True,True),
        "glass_header": (1024,74,21,(6,24,33,240),(8,23,33,228),(24,143,153,132),(36,183,191,45),True,True),
        "glass_history": (900,480,14,(5,18,24,211),(7,17,26,229),(28,112,123,138),(80,187,188,45),False,False),
        "glass_detail": (900,470,15,(8,29,36,250),(6,17,26,247),(67,195,190,206),(39,130,145,85),True,False),
        "glass_tab_idle": (220,64,17,(5,22,29,246),(6,18,25,239),(47,114,130,169),(20,80,96,100),False,False),
        "glass_tab_active": (220,64,17,(8,46,52,248),(5,29,36,245),(75,237,222,242),(59,175,172,136),True,True),
        "glass_tab_hover": (220,64,17,(12,43,50,249),(8,30,39,246),(78,184,197,224),(64,135,151,94),True,False),
        "glass_button": (280,72,16,(14,38,48,239),(9,25,35,241),(39,111,129,174),(31,96,108,72),False,False),
        "glass_button_hover": (280,72,16,(19,58,68,243),(12,39,51,245),(91,226,221,232),(43,117,129,94),True,False),
        "glass_primary": (280,72,16,(34,206,210,255),(13,151,180,255),(124,253,235,255),(31,116,133,137),True,False),
        "glass_primary_hover": (280,72,16,(71,236,227,255),(24,184,208,255),(200,255,248,255),(64,193,184,123),True,False),
        "glass_input": (900,72,15,(7,22,29,238),(4,16,25,249),(36,137,153,206),(18,95,105,82),False,False),
    }
    for name,recipe in recipes.items():
        width,height,radius,top,bottom,rim,inner,glow,top_rule=recipe
        img = paint(width,height,radius=radius,top=top,bottom=bottom,rim=rim,
                    inner=inner,glow=glow,top_rule=top_rule)
        dest=TARGET/(name+".png")
        img.save(dest,optimize=True)
        print(f"{dest.relative_to(ROOT)} | {width}x{height} | {dest.stat().st_size} bytes")


if __name__ == "__main__":
    generate()
