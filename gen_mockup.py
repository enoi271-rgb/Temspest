#!/usr/bin/env python3
"""Mockup estatico da FROTA TEMSPEST (fiel ao canvas do index.html): 4 naves + nave-mae + minions."""
from PIL import Image, ImageDraw, ImageFont
import os, math

OUT=os.path.join(os.path.dirname(__file__),"assets","mockup_station.png")
W,H=1140,420
img=Image.new("RGB",(W,H),(5,6,10))
d=ImageDraw.Draw(img)

def font(sz,bold=False):
    cands=["/Library/Fonts/Teko-Bold.ttf" if bold else "/Library/Fonts/Teko-Regular.ttf",
           "/System/Library/Fonts/Supplemental/Teko-Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Teko-Regular.ttf",
           "/System/Library/Fonts/Supplemental/Arial.ttf"]
    for c in cands:
        if os.path.exists(c): return ImageFont.truetype(c,sz)
    return ImageFont.load_default()

# estrelas
import random
random.seed(7)
for _ in range(140):
    x,y=random.randint(0,W),random.randint(0,H)
    r=random.choice([1,1,1,2])
    d.ellipse([x-r,y-r,x+r,y+r],fill=(180+random.randint(0,60),200+random.randint(0,30),255))

HUB=(W//2,H//2)
SALAS=[
 {"pos":(40+150,40+100),"size":(300,200),"color":(143,179,90),"num":"R1","name":"SALA DE CRIACAO"},
 {"pos":(W-400+180,40+80),"size":(360,160),"color":(217,154,62),"num":"R2","name":"NEGOCIOS ANGOLA"},
 {"pos":(W-400+180,H-180+75),"size":(360,150),"color":(120,180,230),"num":"R3","name":"SALA DE EDICAO"},
 {"pos":(40+150,H-200+85),"size":(300,170),"color":(230,120,160),"num":"R4","name":"GESTORES FINANCEIROS"},
]

def nave(cx,cy,w,h,col):
    # casco
    d.ellipse([cx-w//2,cy-h//2,cx+w//2,cy+h//2],fill=(30,34,28),outline=col,width=3)
    # anel
    d.ellipse([cx-w//2+4,cy-h//2+4,cx+w//2-4,cy+h//2-4],outline=(col[0],col[1],col[2],90),width=1)
    # cockpit
    d.ellipse([cx-w//3,cy-h//2+18,cx+w//3,cy-h//2+50],fill=(col[0],col[1],col[2],60))
    for i in(-1,0,1):
        d.ellipse([cx+i*22-3,cy-h//2+30, cx+i*22+3,cy-h//2+36],fill=(col[0],col[1],col[2]))
    # propulsores
    for i in(-1,1):
        px=cx+i*(w//3)
        d.line([(px,cy+h//2-12),(px,cy+h//2-2)],fill=(190,150,90),width=3)
        d.ellipse([px-4,cy+h//2-2,px+4,cy+h//2+8],fill=(230,140,40,140))

def minion(x,y,col):
    d.ellipse([x-9,y-11,x+9,y+11],fill=(230,210,80),outline=(120,100,20),width=1)
    d.ellipse([x-3,y-4,x-1,y-2],fill=(10,12,8))
    d.ellipse([x+1,y-4,x+3,y-2],fill=(10,12,8))
    d.line([(x-3,y-4),(x-7,y-8)],fill=(120,100,20),width=1)
    d.line([(x+3,y-4),(x+7,y-8)],fill=(120,100,20),width=1)
    d.arc([x-3,y+1,x+3,y+6],10,170,fill=(10,12,8),width=1)
    d.line([(x-11,y+14),(x+11,y+14)],fill=(143,179,90),width=2)
    d.line([(x-11,y+14),(x-11+22,y+14)],fill=(143,179,90),width=2)

# feixes E->salas
for s in SALAS:
    sx,sy=s["pos"]; col=s["color"]
    d.line([HUB,(sx,sy)],fill=(col[0],col[1],col[2],70),width=8)

# salas (naves)
for s in SALAS:
    cx,cy=s["pos"]; w,h=s["size"]; col=s["color"]
    nave(cx,cy,w,h,col)
    # minions em circulo
    n=2
    for k in range(n):
        ang=math.pi*2*k/n
        mx=cx+math.cos(ang)*(w/2-55); my=cy+math.sin(ang)*(h/2-40)
        minion(int(mx),int(my),col)
    # rotulo
    ft=font(20,bold=True)
    d.text((s["pos"][0]-w//2+14, s["pos"][1]-h//2+6), s["num"]+" · "+s["name"], fill=col, font=ft)

# HUB E = nave-mae
d.ellipse([HUB[0]-52,HUB[1]-56,HUB[0]+52,HUB[1]+56],fill=(30,34,28),outline=(143,179,90),width=3)
d.ellipse([HUB[0]-60,HUB[1]-64,HUB[0]+60,HUB[1]+64],outline=(143,179,90,110),width=2)
d.ellipse([HUB[0]-46,HUB[1]-46,HUB[0]+46,HUB[1]+46],fill=(77,95,55))
fe=font(54,bold=True)
d.text((HUB[0],HUB[1]),"E",fill=(143,179,90),font=fe,anchor="mm")
d.text((HUB[0],HUB[1]+70),"NAVE-MAE // CORE",fill=(143,179,90),font=font(14,bold=True),anchor="mm")
# hermes minion
hy=HUB[1]+86
d.ellipse([HUB[0]-7,hy-7,HUB[0]+7,hy+7],fill=(217,154,62),outline=(10,12,8),width=1)
d.text((HUB[0],hy+20),"HERMES // SUP",fill=(217,154,62),font=font(12,bold=True),anchor="mm")

# titulo
d.text((14,10),"TEMSPEST FLEET // AGENTES-MINIONS",fill=(200,220,255),font=font(20,bold=True))

img.save(OUT)
print("mockup:",OUT,img.size)
