"""
chipmod.py
Copyright 2015 Adam Greig

Create two-terminal chip packages.
"""

# Package Configuration =======================================================
# Top keys are package names.
# Format is SIZE[-SPECIAL]. Examples: 0402, 0603-LED
# Valid inner keys are:
#   * pad_shape: (width, height) of the pads
#   * pitch: spacing between pad centres
#   * chip_shape: (width, height) of the chip
#   * terminal: width of terminal metallisation
#   * silk: "internal", "external", "triangle", "pin1", None.
#           What sort of silk to draw. Default is "internal".
#
# Except where otherwise noted, all packages are in IPC nominal environment.
# Chip drawings are nominal sizes rather than maximum sizes.
# All lengths are in millimetres.

config = {
    # 0201 from IPC-7351B: CAPC0603X33N
    "0201": {
        "pad_shape": (0.46, 0.42),
        "pitch": 0.66,
        "chip_shape": (0.6, 0.3),
        "terminal": 0.15,
        "silk": None,
    },

    # 0402 from IPC-7351B: CAPC1005X55N
    "0402": {
        "pad_shape": (0.62, 0.62),
        "pitch": 0.90,
        "chip_shape": (1.00, 0.50),
        "terminal": 0.30,
        "silk": None,
    },

    # 0603 from IPC-7351B: CAPC1608X90N
    "0603": {
        "pad_shape": (0.95, 1.00),
        "pitch": 1.60,
        "chip_shape": (1.60, 0.80),
        "terminal": 0.35,
    },

    # 0603-LED from IPC-7351B: CAPC1608X90N
    # Modified silkscreen to indicate LED polarity.
    "0603-LED": {
        "pad_shape": (0.95, 1.00),
        "pitch": 1.60,
        "chip_shape": (1.60, 0.80),
        "terminal": 0.25,
        "silk": "triangle",
    },

    # 0805 from IPC-7351B: CAPC2013X100N
    "0805": {
        "pad_shape": (1.15, 1.45),
        "pitch": 1.80,
        "chip_shape": (2.00, 1.25),
        "terminal": 0.50,
    },

    # 1206 from IPC-7351B: CAPC3216X130N
    "1206": {
        "pad_shape": (1.15, 1.80),
        "pitch": 3.00,
        "chip_shape": (3.20, 1.60),
        "terminal": 0.60,
    },

    # 0402-L from IPC-7351B: CAPC1005X55L
    # This is a LEAST environment
    "0402-L": {
        "pad_shape": (0.52, 0.52),
        "pitch": 0.80,
        "chip_shape": (1.00, 0.50),
        "terminal": 0.30,
        "silk": None,
    },

    # 0603-L from IPC-7351B: CAPC1608X90L
    # This is a LEAST environment
    "0603-L": {
        "pad_shape": (0.75, 0.90),
        "pitch": 1.40,
        "chip_shape": (1.60, 0.80),
        "terminal": 0.35,
    },
}

# Other constants =============================================================

# Courtyard clearance
# Use 0.25 for IPC nominal and 0.10 for IPC least.
ctyd_gap = 0.25

# Courtyard grid
ctyd_grid = 0.05

# Courtyard line width
ctyd_width = 0.01

# Internal silk clearance from pads
silk_pad_igap = 0.2

# External silk clearance from pads
silk_pad_egap = 0.2

# Silk line width
silk_width = 0.15

# Fab layer line width
fab_width = 0.01

# Ref/Val font size (width x height)
font_size = (1.0, 1.0)

# Ref/Val font thickness
font_thickness = 0.15

# Ref/Val font spacing from centre to top/bottom edge
font_halfheight = 0.7

# End constants ===============================================================

import os
import sys
import time
import math

from sexp import sexp_parse, sexp_generate
from kicad_mod import fp_line, fp_arc, fp_text, pad, draw_square


def refs(conf):
    """Generate val and ref labels."""
    out = []
    x = conf['pitch']/2 + conf['pad_shape'][0]/2 + ctyd_gap + font_halfheight
    out.append(fp_text("reference", "REF**", (-x, 0, 90), "F.Fab",
                       font_size, font_thickness))
    out.append(fp_text("value", conf['name'], (x, 0, 90), "F.Fab",
                       font_size, font_thickness))
    return out


def fab(conf):
    """Generate a drawing of the chip on the Fab layer."""
    out = []
    w, h = conf['chip_shape']
    t = conf['terminal']

    nw, ne, se, sw, sq = draw_square(w, h, (0, 0), "F.Fab", fab_width)
    out += sq
    out.append(fp_line((nw[0]+t, -h/2), (nw[0]+t, h/2), "F.Fab", fab_width))
    out.append(fp_line((ne[0]-t, -h/2), (ne[0]-t, h/2), "F.Fab", fab_width))
    return out


def internal_silk(conf):
    """Draw internal silkscreen."""
    w = conf['pitch'] - conf['pad_shape'][0] - 2*silk_pad_igap
    h = conf['chip_shape'][1] - silk_width
    _, _, _, _, sq = draw_square(w, h, (0, 0), "F.SilkS", silk_width)
    return sq


def external_silk(conf):
    """Draw external silkscreen."""
    out = []
    return out


def triangle_silk(conf):
    """Draw a triangle silkscreen pointing to pin 1."""
    out = []
    w = conf['pitch'] - conf['pad_shape'][0] - 2*silk_pad_igap
    h = conf['chip_shape'][1] - silk_width
    out.append(fp_line((-w/2, 0), (w/2, -h/2), "F.SilkS", silk_width))
    out.append(fp_line((-w/2, 0), (w/2, +h/2), "F.SilkS", silk_width))
    out.append(fp_line((w/2, -h/2), (w/2, +h/2), "F.SilkS", silk_width))
    return out


def pin1_silk(conf):
    """Draw a small pin1 indicator on the silkscreen."""
    out = []
    return out


def silk(conf):
    s = conf.get('silk', 'internal')
    if s == "internal":
        return internal_silk(conf)
    elif s == "external":
        return external_silk(conf)
    elif s == "triangle":
        return triangle_silk(conf)
    elif s == "pin1":
        return pin1_silk(conf)
    else:
        return []


def ctyd(conf):
    """Draw a courtyard around the part."""
    # Compute width and height of courtyard
    width = conf['pad_shape'][0] + conf['pitch'] + 2*ctyd_gap
    height = conf['pad_shape'][1] + 2*ctyd_gap

    # Ensure courtyard lies on a specified grid
    # (double the grid since we halve the width/height)
    grid = 2*ctyd_grid
    width = grid * int(math.ceil(width / (2*ctyd_grid)))
    height = grid * int(math.ceil(height / (2*ctyd_grid)))

    # Render courtyard
    _, _, _, _, sq = draw_square(width, height, (0, 0), "F.CrtYd", ctyd_width)
    return sq


def pads(conf):
    """Place the part pads."""
    out = []
    x = conf['pitch'] / 2.0
    layers = ["F.Cu", "F.Mask", "F.Paste"]
    out.append(pad(1, "smd", "rect", (-x, 0), conf['pad_shape'], layers))
    out.append(pad(2, "smd", "rect", (+x, 0), conf['pad_shape'], layers))
    return out


def footprint(conf):
    tedit = format(int(time.time()), 'X')
    sexp = ["module", conf['name'], ("layer", "F.Cu"), ("tedit", tedit)]
    sexp += refs(conf)
    sexp += fab(conf)
    sexp += silk(conf)
    sexp += ctyd(conf)
    sexp += pads(conf)
    return sexp_generate(sexp)


def main(prettypath):
    for name, conf in config.items():
        # Generate footprint
        conf['name'] = name
        fp = footprint(conf)
        path = os.path.join(prettypath, name+".kicad_mod")

        # Check if an identical part already exists
        if os.path.isfile(path):
            with open(path) as f:
                old = f.read()
            old = [n for n in sexp_parse(old) if n[0] != "tedit"]
            new = [n for n in sexp_parse(fp) if n[0] != "tedit"]
            if new == old:
                continue

        # Write new file
        with open(path, "w") as f:
            f.write(fp)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        prettypath = sys.argv[1]
        main(prettypath)
    else:
        print("Usage: {} <.pretty path>".format(sys.argv[0]))
        sys.exit(1)
