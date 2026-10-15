#!/usr/bin/python3
ver="2026.10.15"
############################################################
# PLOTCX Ver.2026.10.15
# (Utility to plot a CX4 file by gnuplot)
#
# Naohiko Otuka (IAEA Nuclear Data Section)
############################################################
import argparse
import datetime
import os
import re
import shutil
import time
import glob
import subprocess

def plotcx():
  args=get_args(ver)
  main(*get_input(args))


def main(file_cx4,file_pdf,force):
  time_start=time.time()

  gnuplot=get_gnuplot_command()
  gnuplot=gnuplot.rstrip() 
  if shutil.which(gnuplot) is None:
    msg="Check if the gnuplot command "+gnuplot+ " defined in gnuplot_command.txt is correct"
    print_error_fatal(msg,"")

  print("plotting ... "+file_cx4)

  m=re.compile(r"(.+?\/)*(\w+?)\-(.+?)\-(.+?)\-(.+?)\-(.+?)\-(.+?)\-(.+?)\.cx4$").search(file_cx4)
  if not m:
    msg=file_cx4+": Plotting skipped. Unexpected file name structure."
    print_error(msg,"",force)
    return
  proj=m.group(2)
  targ=m.group(3)
  reac=m.group(4)
  quan=m.group(5)
  dist=m.group(6)
  spec=m.group(7)
  const=m.group(8)
  m=re.compile(r"^([A-Z][a-z]*)(\d+)").search(proj)
  if m:
    aproj=int(m.group(2))
    if aproj<13:
      aproj=None
  else:
    aproj=None

  const_texts=const.split("_")
  ansan=const_texts[-1]
  ansan=ansan.capitalize()
  year=const_texts[-2]
  author=const_texts[-3]
  author=re.sub(r"\+","-",author)
  author=re.sub(r"%"," ",author)

  (const_value,const_unit)=edit_constant(const_texts,aproj)
  reaction=make_reaction(targ,proj,reac,quan,const_value)
  constant=make_constant(quan,const_value,const_unit,aproj)
  title=reaction+constant

  (npts,xmin,xmax,ymin,ymax)=get_nptsminmax(file_cx4)
  (xlabel,xfac)=make_xlabel(quan,dist,xmin,xmax,aproj)
  (ylabel,yfac)=make_ylabel(quan,dist,ymin,ymax)

  if dist=="nucdis":
    xtics_products=make_product_xtics(file_cx4)

  (logx,logy)=set_scale(dist,xmin,xmax,xfac,ymin,ymax,yfac)

  file_pdf=re.sub(r"cx4$","pdf",file_cx4)
  cmds=[
       'set terminal pdfcairo colour enh size 29.7cm, 21.0cm font "Arial,20"',
       'set output "'+file_pdf+'"',
       'set title "'+title+'"',
       'set xlabel "'+xlabel+'"',
       'set ylabel "'+ylabel+'"'
  ]

  if logx:
    cmds.append('set log x')
    cmds.append('set format x "10^{%L}"')
  if logy:
    cmds.append('set log y')
    cmds.append('set format y "10^{%L}"')

  xfac=str(xfac)
  yfac=str(yfac)

  if dist=="nucdis":
    cmds.append('set xrange [0:'+str(npts+1)+']')
    cmds.append('set xtics '+xtics_products+' right rotate by 90')
    cmds.append('plot "'+file_cx4+'" u ($0+1):($2*'+yfac+'):($3*'+yfac+') w e lt 8 pt 7 t "'+author+','+year+' (EXFOR# '+ansan+')"')
  elif dist=="sponnu":
    cmds.append('set xrange [0:'+str(npts+1)+']')
    cmds.append('plot "'+file_cx4+'" u ($0+1):($1*'+yfac+'):($2*'+yfac+') w e lt 8 pt 7 t "'+author+','+year+' (EXFOR# '+ansan+')"')
  else:
    cmds.append('plot "'+file_cx4+'" u ($1*'+xfac+'):($3*'+yfac+'):($2*'+xfac+'):($4*'+yfac+') w xye lt 8 pt 7 t "'+author+','+year+' (EXFOR# '+ansan+')"')
  cmds.append("exit")
# for cmd in cmds:
#   print(cmd)
  cmd=';'.join(cmds)
  cmd=gnuplot+' -e \'{}\''.format(cmd)
  if os.name=="nt": # Swap ' and " on Windows
    cmd=cmd.translate(str.maketrans({'\'': '"', '"': '\''}))
# print(cmd)
  subprocess.run(cmd,shell=True)

  time_end=time.time()
  time_elapsed=format(time_end-time_start, ".2f")
  print("PLOTCX: Processing terminated normally. "+time_elapsed+" sec.\n")


def get_gnuplot_command():
  lines=get_file_lines("gnuplot_command.txt")
  for line in lines:
    if line[0:1]=="#":
      continue
    else:
      gnuplot=line
  return gnuplot


def edit_constant(const_texts,aproj):
  const_value=dict()
  const_unit=dict()
  for const_text in const_texts:
    if re.compile(r"^angc(.+)$").search(const_text):
      m=re.match(r"^angc(.+)$",const_text)
      const_value["angc"]=m.group(1)
    elif re.compile(r"^angl(.+)$").search(const_text):
      m=re.match(r"^angl(.+)$",const_text)
      const_value["angl"]=m.group(1)
    elif re.compile(r"^einc(.+)$").search(const_text):
      m=re.match(r"^einc(.+)$",const_text)
      const_value["einc"]=m.group(1)
    elif re.compile(r"^elvl(.+)$").search(const_text):
      m=re.match(r"^elvl(.+)$",const_text)
      const_value["elvl"]=m.group(1)
    elif re.compile(r"^eoutc(.+)$").search(const_text):
      m=re.match(r"^eoutc(.+)$",const_text)
      const_value["eoutc"]=m.group(1)
    elif re.compile(r"^eoutl(.+)$").search(const_text):
      m=re.match(r"^eoutl(.+)$",const_text)
      const_value["eoutl"]=m.group(1)
    elif re.compile(r"^prod(.+)$").search(const_text):
      m=re.match(r"^prod(.+)$",const_text)
      const_value["prod"]=m.group(1)

  for key in const_value:
    m=re.compile(r"(\d\.\d\d\d)E((\+|-)\d\d)").search(const_value[key])
    if m:
      value=float(const_value[key])
      if key=="einc" and aproj is not None:
        value=value/aproj
      if key=="einc" or key=="elvl" or key=="eoutc" or key=="eoutl":
        if value<1E+03:
          const_unit[key]="eV"
        elif value<1E+06:
          value=value*1E-03
          const_unit[key]="keV"
        elif value<1E+09:
          value=value*1E-06
          const_unit[key]="MeV"
        else:
          value=value*1E-09
          const_unit[key]="GeV"
      if value==0:
        value="%1.0f" % value
        const_value[key]=value
      elif value>=0.01 and value<10000:
        if value<10:
          value="%5.3f" % value
          value=re.sub(r"(\.)*0+$","",value)
        elif value<100:
          value="%5.2f" % value
          value=re.sub(r"(\.)*0+$","",value)
        elif value<1000:
          value="%5.1f" % value
          value=re.sub(r"\.0$","",value)
        else:
          value="%4.0f" % value
        const_value[key]=value
      else:
        value="%9.3E" % value
        m=re.compile(r"(\d\.\d\d\d)E((\+|-)\d\d)").search(value)
        a=m.group(1)
        b=m.group(2)
        b=re.sub(r"\+0","",b)
        b=re.sub(r"-0","-",b)
        if b!="":
          if b=="0":
            value=a
          else:
            value=a+"{/Symbol \\264}10^{"+b+"}"
          const_value[key]=value

  return const_value,const_unit


def make_reaction(targ,proj,reac,quan,const_value):
  m=re.compile(r"([A-Za-z]+)(\d+)*(m|m1|m2)*").search(targ)
  targ_s=m.group(1)
  if m.group(2) is not None:
    targ_a=m.group(2)
  else:
    targ_a=""
  if m.group(3) is not None:
    targ_i=m.group(3)
    targ="^{"+targ_a+targ_i+"}"+targ_s
  else:
    targ="^{"+targ_a+"}"+targ_s

  if proj=="0":
    proj=""
  elif re.compile(r"^(g|n|p|d|t|h|a)$").search(proj):
    if proj=="g":
      proj="{/Symbol g}"
    elif proj=="a":
      proj="{/Symbol a}"
  else:
    m=re.compile(r"([A-Za-z]+)(\d+)*").search(proj)
    proj_s=m.group(1)
    if m.group(2) is not None:
      proj_a=m.group(2)
    else:
      proj_a=""

    if re.compile(r"^\d+(g|m|n|p|q|r)$").search(proj):
      m=re.compile(r"^\d+(g|m|n|p|q|r)$").search(proj)
      i=m.group(1)
      if i=="p":
        proj="^{"+proj_a+"g+m}"+proj_s
      elif i=="q":
        proj="^{"+proj_a+"g+n}"+proj_s
      elif i=="r":
        proj="^{"+proj_a+"m+n}"+proj_s
      else:
        proj="^{"+proj_a+i+"}"+proj_s
    else:
      proj="^{"+proj_a+"}"+proj_s

  if reac=="xg":
    reac="{/Symbol g}+x"
  elif reac=="xn":
    reac="n+x"
  elif reac=="xp":
    reac="p+x"
  elif reac=="xd":
    reac="d+x"
  elif reac=="xt":
    reac="t+x"
  elif reac=="xh":
    reac="^3He+x"
  elif reac=="xa":
    reac="{/Symbol a}+x"
  elif reac=="abs":
    pass
  else:
    reac=re.sub(r"a","{/Symbol a}",reac)
    reac=re.sub(r"g","{/Symbol g}",reac)
    reac=re.sub(r"h","^3He",reac)

  if proj=="":
    reaction=targ+"(sf)"
  elif quan=="sigg" or "adxg" in quan or "edxg" in quan:
    reaction=targ+"("+proj+","+reac+"+{/Symbol g})"
  else:
    reaction=targ+"("+proj+","+reac+")"

  if "prod" in const_value:
    prod=const_value["prod"]
    m=re.compile(r"([A-Za-z]+)(\d+)*").search(prod)
    prod_s=m.group(1)
    if m.group(2) is not None:
      prod_a=m.group(2)
    else:
      prod_a=""
    if re.compile(r"\d+(g|m|n|p|q|r)$").search(prod):
      m=re.compile(r"\d+(g|m|n|p|q|r)$").search(prod)
      i=m.group(1)
      if i=="p":
        prod="^{"+prod_a+"g+m}"+prod_s
      elif i=="q":
        prod="^{"+prod_a+"g+n}"+prod_s
      elif i=="r":
        prod="^{"+prod_a+"m+n}"+prod_s
      else:
        prod="^{"+prod_a+i+"}"+prod_s
    else:
      prod="^{"+prod_a+"}"+prod_s
    reaction+=prod

  return reaction


def make_constant(quan,const_value,const_unit,aproj):
  constant=""
  if "einc" in const_value:
    if aproj is not None:
      constant+=", E_{inc}="+const_value["einc"]+" "+const_unit["einc"]+"/A"
    else:
      constant+=", E_{inc}="+const_value["einc"]+" "+const_unit["einc"]
  if "elvl" in const_value:
    constant+=", E_{lvl}="+const_value["elvl"]+" "+const_unit["elvl"]

  if quan=="sigg" or "adxg" in quan or "edxg" in quan:
    if "angc" in const_value:
      constant+=", {/Symbol q}_{{/Symbol g},cm}="+const_value["angc"]+" deg"
    if "angl" in const_value:
      constant+=", {/Symbol q}_{{/Symbol g},lab}="+const_value["angl"]+" deg"
    if "eoutc" in const_value:
      constant+=", E_{{/Symbol g},cm}="+const_value["eoutc"]+" "+const_unit["eoutc"]
    if "eoutl" in const_value:
      constant+=", E_{{/Symbol g},lab}="+const_value["eoutl"]+" "+const_unit["eoutl"]
  else:
    if "angc" in const_value:
      constant+=", {/Symbol q}_{cm}="+const_value["angc"]+" deg"
    if "angl" in const_value:
      constant+=", {/Symbol q}_{lab}="+const_value["angl"]+" deg"
    if "eoutc" in const_value:
      constant+=", E_{out,cm}="+const_value["eoutc"]+" "+const_unit["eoutc"]
    if "eoutl" in const_value:
      constant+=", E_{out,lab}="+const_value["eoutl"]+" "+const_unit["eoutl"]

  return constant


def make_xlabel(quan,dist,xmin,xmax,aproj):
  if quan=="sigg" or "adxg" in quan or "edxg" in quan:
    gamma="{/Symbol g},"
  else:
    gamma=""

  if dist=="angdisc" or dist=="enedisc":
    frame="cm"
  elif dist=="angdisl" or dist=="enedisl":
    frame="lab"
  else:
    frame=""

  if dist=="angdisc" or dist=="angdisl":
    xlabel="{/Symbol q}_{"+gamma+frame+"} (deg)"
    xfac=1

  elif dist=="enedisc" or dist=="enedisl" or dist=="excfun" or dist=="lvldis":

    if dist=="enedisc" or dist=="enedisl":
      if gamma=="":
        enesuf=gamma+"out,"+frame
      else:
        enesuf=gamma+frame
    elif dist=="excfun":
      enesuf="inc"
    elif dist=="lvldis":
      enesuf="lvl"

    if dist=="excfun" and aproj is not None:
      unisuf="/A"
      xmin=xmin/aproj
      xmax=xmax/aproj
    else:
      unisuf=""

    if xmax<1E+03:
      xlabel="E_{"+enesuf+"} (eV"+unisuf+")"
      xfac=1E+00
    elif xmax<1E+06:
      xlabel="E_{"+enesuf+"} (keV"+unisuf+")"
      xfac=1E-03
    elif xmax<1E+09:
      xlabel="E_{"+enesuf+"} (MeV"+unisuf+")"
      xfac=1E-06
    else:
      xlabel="E_{"+enesuf+"} (GeV"+unisuf+")"
      xfac=1E-09

    if dist=="excfun" and aproj is not None:
      xfac=xfac/aproj

  elif dist=="nucdis":
    xlabel="Product"
    xfac=None
  elif dist=="sponnu":
    xlabel="Data No."
    xfac=None
  else:
    xlabel="????"
    xfac=1

  return xlabel,xfac


def make_ylabel(quan,dist,ymin,ymax):
  if quan=="sigg" or "adxg" in quan or "edxg" in quan:
    gamma1="{/Symbol g}"
    gamma2="{/Symbol g},"
  else:
    gamma1=""
    gamma2=""

  if dist=="enedisc" or dist=="enedisl":
    out="out,"
  else:
    out=""

  if quan=="adxc" or quan=="edxc" or quan=="ddxc" or quan=="adxgc" or quan=="edxgc":
    frame="cm"
  elif quan=="adxl" or quan=="edxl" or quan=="ddxl" or quan=="adxgl" or quan=="edxgl":
    frame="lab"
  else:
    frame=""

  if quan=="sig"  or quan=="sigc" or quan=="sigg" or\
     quan=="adxc" or quan=="adxl" or quan=="adxgc" or quan=="adxgl":
    if ymax<1E-06:
      yfac=1E+09
      sigpre="n"
    elif ymax<1E-03:
      yfac=1E+06
      sigpre="{/Symbol m}"
    elif ymax<1:
      yfac=1E+03
      sigpre="m"
    else:
      yfac=1
      sigpre=""

  elif quan=="edxc" or quan=="edxl" or quan=="edxgc" or quan=="edxgl" or\
       quan=="ddxc" or quan=="ddxl":
    if ymax<1E-12:
      yfac=1E+15
      sigpre="n"
    elif ymax<1E-09:
      yfac=1E+12
      sigpre="{/Symbol m}"
    elif ymax<1E-06:
      yfac=1E+09
      sigpre="m"
    else:
      yfac=1E+06
      sigpre=""

  else:
    yfac=1

  if quan=="nut":
    ylabel="{/Symbol n}_{tot} (neutrons/fission)"
  elif quan=="nud":
    ylabel="{/Symbol n}_{d} (neutrons/fission)"
  elif quan=="nup":
    ylabel="{/Symbol n}_{p} (neutrons/fission)"
  elif quan=="sig":
    ylabel="{/Symbol s} ("+sigpre+"b)"
  elif quan=="sigc":
    ylabel="{/Symbol s}_{cum} ("+sigpre+"b)"
  elif quan=="sigg":
    ylabel="{/Symbol s}_{/Symbol g} ("+sigpre+"b)"
  elif quan=="adxc" or quan=="adxl" or quan=="adxgc" or quan=="adxgl":
    ylabel="d{/Symbol s}_{"+gamma1+"}/d{/Symbol W}_{"+frame+"} ("+sigpre+"b/sr)"
  elif quan=="edxc" or quan=="edxl" or quan=="edxgc" or quan=="edxgl":
    ylabel="d{/Symbol s}_{"+gamma1+"}/dE_{"+gamma2+out+frame+"} ("+sigpre+"b/MeV)"
  elif quan=="ddxc" or quan=="ddxl":
    ylabel="d{/Symbol s}/d{/Symbol W}_{"+frame+"}dE_{out,"+frame+"} ("+sigpre+"b/sr/MeV)"
  elif quan=="fyi":
    ylabel="Y_{ind} (/fission)"
  elif quan=="fyc":
    ylabel="Y_{cum} (/fission)"
  else:
    ylabel="????"

  return ylabel,yfac


def make_product_xtics(file):
  f=open(file,"r")
  lines=f.readlines()
  i=1
  xtics_product=[]
  for line in lines:
    if re.compile(r"^\#").search(line):
      continue 
    else:
      prod_num=int(float(line[0:12])*10)
      prod_z=int(float(prod_num)/10000.)
      prod_a=int((float(prod_num)-prod_z*10000.)/10.)
      prod_i=int((float(prod_num)-prod_z*10000.)-prod_a*10)
      prod_z=str(prod_z)
      prod_a=str(prod_a)
      prod_s=convert_z_to_s(prod_z)
      if prod_i==9:
        prod_s="^{"+prod_a+"}"+prod_s
      elif prod_i==0:
        prod_s="^{"+prod_a+"g}"+prod_s
      elif prod_i==1:
        prod_s="^{"+prod_a+"m}"+prod_s
      elif prod_i==2:
        prod_s="^{"+prod_a+"n}"+prod_s
      elif prod_i==3:
        prod_s="^{"+prod_a+"g+m}"+prod_s
      elif prod_i==4:
        prod_s="^{"+prod_a+"g+n}"+prod_s
      elif prod_i==5:
        prod_s="^{"+prod_a+"m+n}"+prod_s
      elif prod_i==6:
        prod_s="^{"+prod_a+"?}"+prod_s
      prod_s="\""+prod_s+"\""+str(i)
      i+=1
      xtics_product.append(prod_s)

  xtics_products=",".join(xtics_product)
  xtics_products="("+xtics_products+")"

  return xtics_products


def get_nptsminmax(file):
  f=open(file,"r")
  lines=f.readlines()
  for line in lines:
    value=line.split(':')
    if "npts" in line:
      npts=float(value[1])
    elif "xmin" in line:
      xmin=float(value[1])
    elif "xmax" in line:
      xmax=float(value[1])
    elif "ymin" in line:
      ymin=float(value[1])
    elif "ymax" in line:
      ymax=float(value[1])
      break

  return npts,xmin,xmax,ymin,ymax


def set_scale(dist,xmin,xmax,xfac,ymin,ymax,yfac):
  if dist!="nucdis" and dist!="sponnu":
    xmin=xmin*xfac
    xmax=xmax*xfac
  ymin=float(ymin)*yfac
  ymax=float(ymax)*yfac

  if dist=="nucdis" or dist=="sponnu":
    logx=False
    if ymin>0 and ymax/ymin>100:
      logy=True
    else:
      logy=False

  else:
    if xmin>0 and xmax/xmin>100:
      logx=True
    else:
      logx=False
    if ymin>0 and ymax/ymin>100:
      logy=True
    else:
      logy=False

  return logx,logy


def convert_z_to_s(z):
  z_to_s={\
    "0": "Nn",
    "1": "H",     "2": "He",    "3": "Li",    "4": "Be",    "5": "B",
    "6": "C",     "7": "N",     "8": "O",     "9": "F",    "10": "Ne",
   "11": "Na",   "12": "Mg",   "13": "Al",   "14": "Si",   "15": "P",
   "16": "S",    "17": "Cl",   "18": "Ar",   "19": "K",    "20": "Ca",
   "21": "Sc",   "22": "Ti",   "23": "V",    "24": "Cr",   "25": "Mn",
   "26": "Fe",   "27": "Co",   "28": "Ni",   "29": "Cu",   "30": "Zn",
   "31": "Ga",   "32": "Ge",   "33": "As",   "34": "Se",   "35": "Br",
   "36": "Kr",   "37": "Rb",   "38": "Sr",   "39": "Y",    "40": "Zr",
   "41": "Nb",   "42": "Mo",   "43": "Tc",   "44": "Ru",   "45": "Rh",
   "46": "Pd",   "47": "Ag",   "48": "Cd",   "49": "In",   "50": "Sn",
   "51": "Sb",   "52": "Te",   "53": "I",    "54": "Xe",   "55": "Cs",
   "56": "Ba",   "57": "La",   "58": "Ce",   "59": "Pr",   "60": "Nd",
   "61": "Pm",   "62": "Sm",   "63": "Eu",   "64": "Gd",   "65": "Tb",
   "66": "Dy",   "67": "Ho",   "68": "Er",   "69": "Tm",   "70": "Yb",
   "71": "Lu",   "72": "Hf",   "73": "Ta",   "74": "W",    "75": "Re",
   "76": "Os",   "77": "Ir",   "78": "Pt",   "79": "Au",   "80": "Hg",
   "81": "Tl",   "82": "Pb",   "83": "Bi",   "84": "Po",   "85": "At",
   "86": "Rn",   "87": "Fr",   "88": "Ra",   "89": "Ac",   "90": "Th",
   "91": "Pa",   "92": "U",    "93": "Np",   "94": "Pu",   "95": "Am",
   "96": "Cm",   "97": "Bk",   "98": "Cf",   "99": "Es",  "100": "Fm",
  "101": "Md",  "102": "No",  "103": "Lr",  "104": "Rf",  "105": "Db",
  "106": "Sg",  "107": "Bh",  "108": "Hs",  "109": "Mt",  "110": "Ds",
  "111": "Rg",  "112": "Cn",  "113": "Nh",  "114": "Fl",  "115": "Mc",
  "116": "Lv",  "117": "Ts",  "118": "Og",  "119": "Uue", "120": "Ubn",
  "121": "Ubu", "122": "Ubb", "123": "Ubt", "124": "Ubq", "125": "Ubp",
  "126": "Ubh", "127": "Ubs", "128": "Ubo", "129": "Ube", "130": "Utn"}

  s=z_to_s[z]
  return s


def get_args(ver):
  parser=argparse.ArgumentParser(\
   usage="Plot CX4 file by gnuplot",\
   epilog="example: x4_plotcx -i n-Ti-tot-sig-excfun-mon-Schwartz_1974_10003.002.cx4")
  parser.add_argument("-v", "--version",\
   action="version", version=ver)
  parser.add_argument("-i", "--file_cx4",\
   help="input CX4 file")
  parser.add_argument("-o", "--file_pdf",\
   help="output pdf file")
  parser.add_argument("-f", "--force",\
   help="never prompt", action="store_true")

  args=parser.parse_args()
  return args


def get_input(args):
  time=datetime.datetime.now()
  date=time.strftime("%Y-%m-%d")
  print("PLOTCX (Ver."+ver+") run on "+date)
  print("-----------------------------------------")

  force=args.force

  file_cx4=args.file_cx4
  if file_cx4 is None:
    file_cx4=input("input CX4 file ---------------> ")
  if not os.path.exists(file_cx4):
    print(" ** File "+file_cx4+" does not exist.")
  while not os.path.exists(file_cx4):
    file_cx4=input("input CX4 file ---------------> ")
    if not os.path.exists(file_cx4):
      print(" ** File "+file_cx4+" does not exist.")

  file_pdf=args.file_pdf
  if file_pdf is None:
    char=re.sub(r"\.cx4$",".pdf",file_cx4)
    file_pdf=input("output pdf file ["+char+"] --> ")
  if file_pdf=="":
    file_pdf=char
  if os.path.isfile(file_pdf):
    msg="File '"+file_pdf+"' exists and must be overwritten."
    print_error(msg,"",force)

  print("\n")

  return file_cx4,file_pdf,force


def get_file_lines(file):
  if os.path.exists(file):
    f=open(file, "r")
    lines=f.readlines()
    f.close()
  else:
    msg="File "+file+" does not exist."
    print_error_fatal(msg,"")
  return lines


def print_error(msg,line,force):
  print("** "+msg)
  print(line)

  if force:
    answer="Y"
  else:
    answer=""

  while answer!="Y" and answer!="N":
    answer=input("Continue? [Y] --> ")
    if answer=="":
      answer="Y"
    if answer!="Y" and answer!="N":
      print(" ** Answer must be Y (Yes) or N (No).")
  if answer=="N":
    print("program terminated")
    exit()


def print_error_fatal(msg,line):
  print("**  "+msg)
  print(line)
  exit()


if __name__ == "__main__":
  plotcx()
  exit()
