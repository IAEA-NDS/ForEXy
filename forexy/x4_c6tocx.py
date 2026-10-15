#!/usr/bin/python3
ver="2026.10.15"
############################################################
# C6TOCX Ver.2026.10.15
# (Utility for production and update of CX4 file storage)
#
# Naohiko Otuka (IAEA Nuclear Data Section)
############################################################
import argparse
import datetime
import glob
import os
import re
import time

if os.path.isfile("x4_lotran.py"):
  import x4_lotran
else:
  from forexy import x4_lotran

def c6tocx():
  args=get_args(ver)
  main(*get_input(args))


def main(dir_c6,file_dict,entry,dir_cx4,file_idx,sysout0,force0,exclhi):
  time_start=time.time()

  global sysout
  global force
  sysout=sysout0
  force=force0

  if entry=="all":
    pattern=dir_c6+"/[a-z0-9][0-9][0-9][0-9][0-9].[0-9][0-9][0-9]*_[0-9][0-9][0-9][0-9].c6"
  else:
    pattern=dir_c6+"/"+entry+".[0-9][0-9][0-9]*_[0-9][0-9][0-9][0-9].c6"
  all_files=glob.glob(pattern)
  files=[file for file in all_files if re.search(r"\d\d\d(\.[A-Z1-9])?", file)]
  files=sorted(files)
  if entry!="all" and len(files)==0:
    msg="C6 file for EXFOR Entry "+entry+" does not exist."
    print_error_fatal(msg,"")
  

  for nfile, file_c6 in enumerate(files):
    print("processing ... "+file_c6)
    
    m=re.search(r"([0-8a-z]\d{4}\.\d{3}(\.[0-9a-z])?)-(.+?)\.c6",file_c6)
    if m:
      file1=m.group(1)
      file1=file1.upper()
      file2=m.group(3)
      n=re.search(r"^(.+?)\-",file2)
      proj=n.group(1)
      if not re.compile(r"^(g|n|p|d|t|h|a)$").search(proj) and exclhi==True:
        msg=file1+" Projectile "+proj+" is a heavy-ion. Not converted."
        print_error(msg,"",True)
        continue
      file_cx4=dir_cx4+"/"+file2+"_"+file1+".cx4"
    else:
      msg="Input C6 file does not follow the standard naming convention."
      print_error_fatal(msg,file_c6)

    if os.path.isfile(file_cx4):
      msg="File '"+file_cx4+"' exists and must be overwritten."
      print_error(msg,"",force0)

    cx4able=check_c6_dist_quan(file_c6)

    if cx4able==True:
      (tid,quan,dist,line_preamble,line_const,line_head,line_unit,line_data,x,y)=read_c6(file_c6,file_dict)
    
    if len(x)>0:
      (npts,xmin,xmax,ymin,ymax)=print_cx4(file_cx4,dist,line_preamble,line_const,line_head,line_unit,line_data,x,y)
      print_idx(file_c6,file_idx,tid,quan,dist,npts,xmin,xmax,ymin,ymax)

  time_end=time.time()
  time_elapsed=format(time_end-time_start, ".2f")
  print("C6TOCX: Processing terminated normally. "+time_elapsed+" sec.\n")


def check_c6_dist_quan(file_c6):
  m=re.compile(r"([0-8a-z]\d{4}\.\d{3}(\.[0-9a-z])?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?\d\d\d\d)\.c6$").search(file_c6)
  if not m:
    msg=file_c6+": Conversion skipped. Unexpected file name structure."
    print_error(msg,"",force)
    return
  quan=m.group(6)
  dist=m.group(7)

  if dist=="othdis":
    msg=file_c6+": Conversion skipped. Distribution type othdis is not supported in CX4."
    print_error(msg,"",force)
    cx4able=False
    return cx4able

  elif dist=="lvldis":
    if quan=="edxl" or quan=="edxc" or quan=="ddxl" or quan=="ddxc":
      msg=file_c6+": Conversion skipped. Distribution type lvldis is not supported for EDX and DDX in CX4."
      print_error(msg,"",force)
      cx4able=False
      return cx4able

  else:
    cx4able=True
    return cx4able


def read_c6(file_c6,file_dict):
  lines=get_file_lines(file_c6)
  line_preamble=[]
  line_data=[]
  x=[]
  y=[]

  m=re.compile(r"([0-8a-z]\d{4}\.\d{3}(\.[0-9a-z])?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?\d\d\d\d)\.c6$").search(file_c6)
  ansan=m.group(1)
  proj=m.group(3)
  targ=m.group(4)
  reac=m.group(5)
  quan=m.group(6)
  dist=m.group(7)
  spec=m.group(8)
  const=m.group(9)

  if dist=="excfun":
    col_ini=22
  elif dist=="angdisc" or dist=="angdisl" or dist=="nucdis":
    col_ini=58
  elif dist=="enedisc" or dist=="enedisl" or dist=="lvldis":
    col_ini=76
  elif dist=="sponnu":
    col_ini=0

  for line in lines:
    if not re.compile(r"\w").search(line):
      continue
    elif re.compile(r"^\#").search(line):
      if re.compile(r"^\# TRANS").search(line):
        m=re.compile(r": ([0-9A-Z]\d{3}|\?\?\?\?)").search(line)
        tid=m.group(1)
        line=re.sub(":","      :",line,1)
        line_preamble.append(line)
      elif re.compile(r"^\# REACTION").search(line):
        m=re.compile(r": (.+?)\((.+?),(.+?)\)(.*?),").search(line)
        sf1=m.group(1)
        sf2=m.group(2)
        sf3=m.group(3)
        sf4=m.group(4)
        line=re.sub(":","      :",line,1)
        line_preamble.append(line)
        continue
      elif re.compile(r"^\# MF/MT   ").search(line):
        continue
      elif re.compile(r"^\#Proj").search(line):
        continue
      elif re.compile(r"^\#F").search(line):
        continue
      elif re.compile(r"^\#C").search(line):
        (line_const,const_inp,frame_inp)=make_line_const(line,const)
        (quan,dist,lorentz,frame_inp,frame_out)=get_frame(reac,quan,dist,frame_inp)
        (line_head,line_unit)=make_line_head_unit(dist,quan)
        base_cx4=proj+"-"+targ+"-"+reac+"-"+quan+"-"+dist+"-"+spec+"-"+const+"_"+ansan
        line_preamble.append("# File ID         : "+base_cx4+"\n")
        if lorentz:
          line_preamble.append("# Remark          : Lorentz transformation is applied to the original dataset in EXFOR.\n")
      elif re.compile(r"^\#--->").search(line):
        continue
      elif re.compile(r"^\#          ").search(line):
        continue
      else:
        line=re.sub(":","      :",line,1)
        line_preamble.append(line)

    else:
      j=len(x)
      (skip,char,x0,y0)=make_line_data(file_dict,j,ansan,line,quan,dist,col_ini,lorentz,sf1,sf2,sf3,sf4,const_inp,frame_inp,frame_out)
      if x0 is not None:
        line_data.append(char)
        x.append(x0)
        y.append(y0)

  return tid,quan,dist,line_preamble,line_const,line_head,line_unit,line_data,x,y


def print_idx(file_c6,file_idx,tid,quan,dist,npts,xmin,xmax,ymin,ymax):
  if os.path.isfile(file_idx):
    f=open(file_idx,"a")
  else:
    f=open(file_idx,"w")
    f.write("#EXFOR #     TRANS Proj   Targ   Reac   Prod    Quant   Spa Dist    Min       Max       Pts    Einc      Elvl      Ang   Eout        Year Author  \n")
    f.write("#----------- ----- ------ ------ ------ ------  ------- --- ------- --------- --------- ------ --------- --------- ----- ----------- ---- --------\n")
  m=re.compile(r"([0-8a-z]\d{4}\.\d{3}(\.[0-9a-z])?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?\d\d\d\d)\.c6$").search(file_c6)
  ansan=m.group(1)
  proj=m.group(3)
  targ=m.group(4)
  reac=m.group(5)
  spec=m.group(8)
  const=m.group(9)

  consts=const.split("_")
  author=consts[-2]
  author=author.replace("%"," ")
  author=author.replace("+","-")
  year=consts[-1]

  value=dict()
  einc="        -"
  ang_fra="-"
  ang_val="  -"
  lvl_val="        -"
  eout_fra="-"
  eout_val="        -"
  prod="-     "

  for const in consts:
    if "einc" in const:
      einc=const[4:]
    elif "angc" in const:
      ang_val=const[4:]
      ang_fra="C"
    elif "angl" in const:
      ang_val=const[4:]
      ang_fra="L"
    elif "elvl" in const:
      lvl_val=const[4:]
    elif "eoutc" in const:
      eout_val=const[5:]
      eout_fra="C"
    elif "eoutl" in const:
      eout_val=const[5:]
      eout_fra="L"
    elif "prod" in const:
      prod=const[4:]

  f.write(" ")
  ansan=ansan.upper()
  ansan="%-12s" % ansan 
  f.write(ansan)

  f.write(tid)
  f.write("  ")

  proj="%-7s" % proj
  f.write(proj)

  targ="%-7s" % targ
  f.write(targ)

  reac="%-7s" % reac
  f.write(reac)

  prod="%-7s" % prod
  f.write(prod)

  f.write(" ")
  quan="%-8s" % quan
  f.write(quan)

  spec="%-4s" % spec
  f.write(spec)

  dist="%-8s" % dist
  f.write(dist)


  if dist=="nucdis  ":
    xmin="%9.1F" % float(xmin)
  elif "E" in xmin:
    xmin="%9.2E" % float(xmin)
  elif "." in xmin:
    xmin="%9.4F" % float(xmin)
  f.write(" ")
  f.write(xmin)

  if dist=="nucdis  ":
    xmax="%9.1F" % float(xmax)
  elif "E" in xmax:
    xmax="%9.2E" % float(xmax)
  elif "." in xmax:
    xmax="%9.4F" % float(xmax)
  f.write(" ")
  f.write(xmax)

  npts="%6s" % int(npts)
  f.write(npts)

  f.write(" ")
  f.write(einc)
  f.write(" ")
  f.write(lvl_val)
  f.write(" ")
  f.write(ang_fra)
  f.write(" ")
  ang_val="%3s" % ang_val
  f.write(ang_val)
  f.write(" ")
  f.write(eout_fra)
  f.write(" ")
  f.write(eout_val)
  f.write(" ")
  f.write(year)
  f.write(" ")
  f.write(author)

  f.write("\n")
  f.close()

  return


def print_cx4(file_cx4,dist,line_preamble,line_const,line_head,line_unit,line_data,x,y):
  f=open(file_cx4,"w")

  for line in line_preamble:
    f.write(line)
  if len(line_const)!=0:
    f.write("#\n")
  for line in line_const:
    f.write(line+"\n")

  f.write("#\n")

  npts="%-12s" % len(y)
  f.write("# npts            : "+npts+"\n")

  if dist=="sponnu":
    xmin="%-12s" % 0.
    xmax="%-12s" % 0.

  if dist=="nucdis":
    xmin="%-12s" % min(x)
    xmax="%-12s" % max(x)
  elif dist=="angdisc" or dist=="angdisl":
    xmin="%12.7F" % min(x)
    xmax="%12.7F" % max(x)
  else:
    xmin="%12.4E" % min(x)
    xmax="%12.4E" % max(x)
  f.write("# xmin            : "+xmin+"\n")
  f.write("# xmax            : "+xmax+"\n")

  ymin="%12.4E" % min(y)
  ymax="%12.4E" % max(y)
  f.write("# ymin            : "+ymin+"\n")
  f.write("# ymax            : "+ymax+"\n")

  f.write("#\n")
  f.write("#---------------------------------------------------\n")
  f.write(line_head+"\n")
  f.write(line_unit+"\n")
  f.write("#---------------------------------------------------\n")
  for line in line_data:
    f.write(line+"\n")
  f.write("#---------------------------------------------------\n")
  f.close()

  return npts,xmin,xmax,ymin,ymax


def get_frame(reac,quan,dist,frame_inp):
  frame_out=dict()
  lorentz=False

  if quan=="adxc" or quan=="ddxc":
    frame_inp["*"]="C"
  elif quan=="adxl" or quan=="ddxl":
    frame_inp["*"]="L"
  else:
    return quan,dist,lorentz,frame_inp,frame_out

  if dist=="angdisc":
    frame_inp["G"]="C"
  elif dist=="angdisl":
    frame_inp["G"]="L"
  elif dist=="enedisc":
    frame_inp["E"]="C"
  elif dist=="enedisl":
    frame_inp["E"]="L"
  else:
    return quan,dist,lorentz,frame_inp,frame_out

  frame_out["*"]=sysout[0:1]
  if "*" in frame_inp and frame_out["*"]=="O":
    frame_out["*"]=frame_inp["*"]

  frame_out["G"]=sysout[1:2]
  if "G" in frame_inp:
    if frame_out["G"]=="O":
      frame_out["G"]=frame_inp["G"]

  frame_out["E"]=sysout[2:3]
  if "E" in frame_inp:
    if frame_out["E"]=="O":
      frame_out["E"]=frame_inp["E"]

  if quan=="adxc" or quan=="adxl":
    if reac[0:1]=="x":
      return quan,dist,lorentz,frame_inp,frame_out
    if frame_inp["G"]!=frame_out["G"] or frame_inp["*"]!=frame_out["*"]:
      lorentz=True
      if frame_out["*"]=="C":
        quan="adxc"
      else:
        quan="adxl"
      if frame_out["G"]=="C":
        dist="angdisc"
      else:
        dist="angdisl"

  elif quan=="ddxc" or quan=="ddxl":
    if reac[0:1]!="x":
      return quan,dist,lorentz,frame_inp,frame_out
    if frame_inp["G"]!=frame_out["G"] or frame_inp["E"]!=frame_out["E"] or frame_inp["*"]!=frame_out["*"]:
      if dist=="angdisc" or dist=="angdisl":
        if frame_inp["E"]==frame_out["E"]:
          lorentz=True
          if frame_out["G"]=="C":
            dist="angdisc"
          else:
            dist="angdisl"
        else:
          return quan,dist,lorentz,frame_inp,frame_out
      elif dist=="enedisc" or dist=="enedisl":
        if frame_inp["G"]==frame_out["G"]:
          lorentz=True
          if frame_out["E"]=="C":
            dist="enedisc"
          else:
            dist="enedisl"
        else:
          return quan,dist,lorentz,frame_inp,frame_out
      if frame_out["*"]=="C":
        quan="ddxc"
      else:
        quan="ddxl"

  return quan,dist,lorentz,frame_inp,frame_out


def make_line_const(line,const):
  line_const=[]
  const_inp=dict()
  frame_inp=dict()
  consts=const.split("_")

  for const in consts:
    if const.startswith("einc"):
      value=print_float(line[22:31])
      value="%12.4E" % float(value)
      line_const.append("# Einc (eV)       : "+value)
      const_inp["A"]=float(value)
      if line[31:40]!="         ":
        value=print_float(line[31:40])
        value="%12.4E" % float(value)
        line_const.append("# dEinc (eV)      : "+value)
        const_inp["B"]=float(value)

    elif const.startswith("angc"):
      frame_inp["G"]="C"
      value=print_float(line[58:67])
      value="%12.7F" % float(value)
      line_const.append("# theta,cm (deg)  : "+value)
      const_inp["G"]=float(value)
      if line[67:76]!="         ":
        value=print_float(line[67:76])
        value="%12.7F" % float(value)
        line_const.append("# dtheta,cm (deg) : "+value)
        const_inp["H"]=float(value)

    elif const.startswith("angl"):
      frame_inp["G"]="L"
      value=print_float(line[58:67])
      value="%12.7F" % float(value)
      line_const.append("# theta,lab (deg) : "+value)
      const_inp["G"]=float(value)
      if line[67:76]!="         ":
        value=print_float(line[67:76])
        value="%12.7F" % float(value)
        line_const.append("# dtheta,lab (deg): "+value)
        const_inp["H"]=float(value)

    elif const.startswith("eoutc"):
      frame_inp["E"]="C"
      value=print_float(line[76:85])
      value="%12.4E" % float(value)
      line_const.append("# Eout,cm (eV)    : "+value)
      const_inp["E"]=float(value)
      if line[85:94]!="         ":
        value=print_float(line[85:94])
        value="%12.4E" % float(value)
        line_const.append("# dEout,cm (eV)   : "+value)
        const_inp["F"]=float(value)

    elif const.startswith("eoutl"):
      frame_inp["E"]="L"
      value=print_float(line[76:85])
      value="%12.4E" % float(value)
      line_const.append("# Eout,lab (eV)   : "+value)
      const_inp["E"]=float(value)
      if line[85:94]!="         ":
        value=print_float(line[85:94])
        value="%12.4E" % float(value)
        line_const.append("# dEout,lab (eV)  : "+value)
        const_inp["F"]=float(value)

    elif const.startswith("elvl"):
      frame_inp["E"]="?"
      value=print_float(line[76:85])
      value="%12.4E" % float(value)
      line_const.append("# Elvl (eV)       : "+value)
      const_inp["E"]=float(value)
      if line[85:94]!="         ":
        value=print_float(line[85:94])
        value="%12.4E" % float(value)
        line_const.append("# dElvl (eV)      : "+value)
        const_inp["F"]=float(value)
       
  return line_const,const_inp,frame_inp


def make_line_head_unit(dist,quan):
  if dist=="angdisc":
    line_head="# theta,cm    dtheta,cm   "
    line_unit="#  deg         deg        "
  elif dist=="angdisl":
    line_head="# theta,lab   dtheta,lab  "
    line_unit="#  deg         deg        "
  elif dist=="enedisc":
    line_head="# Eout,cm     dEout,cm    "
    line_unit="#  eV          eV         "
  elif dist=="enedisl":
    line_head="# Eout,lab    dEout,lab   "
    line_unit="#  eV          eV         "
  elif dist=="excfun":
    line_head="# Einc        dEinc       "
    line_unit="#  eV          eV         "
  elif dist=="lvldis":
    line_head="# Elvl        dElvl       "
    line_unit="#  eV          eV         "
  elif dist=="nucdis":
    line_head="# Product     "
    line_unit="#             "
  elif dist=="sponnu":
    line_head="# "
    line_unit="# "
  
  if quan=="nud":
    line_head+="nu-d        dnu-d       "
    line_unit+="/fis         /fis       "
  elif quan=="nup":
    line_head+="nu-p        dnu-p       "
    line_unit+="/fis         /fis       "
  elif quan=="nut":
    line_head+="nu-t        dnu-t       "
    line_unit+="/fis         /fis       "
  elif quan=="sig" or quan=="sigg":
    line_head+="sig         dsig        "
    line_unit+=" b           b          "
  elif quan=="sigc":
    line_head+="sig,cum     dsig,cum    "
    line_unit+=" b           b          "
  elif quan=="adxc":
    line_head+="adx,cm      dadx,cm     "
    line_unit+=" b/sr        b/sr       "
  elif quan=="adxl" or quan=="adxgl":
    line_head+="adx,lab     dadx,lab    "
    line_unit+=" b/sr        b/sr       "
  elif quan=="edxc" or quan=="edxgc":
    line_head+="edx,cm      dedx,cm     "
    line_unit+=" b/eV        b/eV       "
  elif quan=="edxl":
    line_head+="edx,lab     dedx,lab    "
    line_unit+=" b/eV        b/eV       "
  elif quan=="ddxc":
    line_head+="ddx,cm      dddx,cm     "
    line_unit+=" b/sr/eV     b/sr/eV    "
  elif quan=="ddxl":
    line_head+="ddx,lab     dddx,lab    "
    line_unit+=" b/sr/eV     b/sr/eV    "
  elif quan=="fyc":
    line_head+="FY,cum      dFY,cum     "
    line_unit+=" /fis         /fis      "
  elif quan=="fyi":
    line_head+="FY,ind      dFY,ind     "
    line_unit+=" /fis         /fis      "

  return line_head, line_unit


def make_line_data(file_dict,j,ansan,line,quan,dist,col_ini,lorentz,sf1,sf2,sf3,sf4,const_inp,frame_inp,frame_out):
  value_inp=dict()
  values=[]
  skip=False

  if dist!="sponnu":
    x=line[col_ini:col_ini+9]
    values.append(x)

  if dist!="nucdis" and dist!="sponnu":
    dx=line[col_ini+9:col_ini+18]
    values.append(dx)

  y=line[40:49]
  values.append(y)

  dy=line[49:58]
  values.append(dy)

  for i,value in enumerate(values):
    value=print_float(value)
    if not re.compile(r"\d").search(value):
      value=0.0
    values[i]=float(value)

  if lorentz:

    value_inp["A"]=const_inp["A"]
    if "B" in const_inp:
      value_inp["B"]=const_inp["B"]
    if dist=="angdisc" or dist=="angdisl":
      value_inp["G"]=values[0]
      value_inp["H"]=values[1]
      if quan=="ddxc" or quan=="ddxl":
        value_inp["E"]=const_inp["E"]
        if "F" in const_inp:
          value_inp["F"]=const_inp["F"]
    elif dist=="enedisc" or dist=="enedisl":
      value_inp["E"]=values[0]
      value_inp["F"]=values[1]
      if quan=="ddxc" or quan=="ddxl":
        value_inp["G"]=const_inp["G"]
        if "H" in const_inp:
          value_inp["H"]=const_inp["H"]
    value_inp["*"]=values[2]
    value_inp[" "]=values[3]

    if quan=="adxc" or quan=="adxl":
      (skip,value_out)=x4_lotran.main(file_dict,"",j,ansan,"ADX",sf1,sf2,sf3,sf4,value_inp,frame_inp,frame_out,force)
      if skip:
         char=""
         x_float=None
         y_float=None
         return skip, char, x_float, y_float
      else:
        values[0]=value_out["G"]
        values[1]=value_out["H"]
        values[2]=value_out["*"]
        values[3]=value_out[" "]
    elif quan=="ddxc" or quan=="ddxl":
      (skip,value_out)=x4_lotran.main(file_dict,"",j,ansan,"DDX",sf1,sf2,sf3,sf4,value_inp,frame_inp,frame_out,force)
      if skip:
         char=""
         x_float=None
         y_float=None
         return skip, char, x_float, y_float
      else:
        if dist=="angdisc" or dist=="angdisl":
          values[0]=value_inp["G"]
          values[1]=value_inp["H"]
        elif dist=="enedisc" or dist=="enedisl":
          values[0]=value_inp["E"]
          values[1]=value_inp["F"]
        values[2]=value_out["*"]
        values[3]=value_out[" "]

  char=""
  for i,value in enumerate(values):
    if i==0:
      if dist=="angdisc" or dist=="angdisl":
        value="%12.7F" % value
      elif dist=="nucdis":
        value="%12.1F" % value
      else:
        value="%12.4E" % value
      if dist=="sponnu":
        x_float=0.
        y_float=float(value)
      else:
        x_float=float(value)

    elif i==1:
      if dist=="angdisc" or dist=="angdisl":
        value="%12.7F" % value
      else:
        value="%12.4E" % value
      if dist=="nucdis":
        y_float=float(value)

    elif i==2:
      value="%12.4E" % value
      if dist!="nucdis" and dist!="sponnu":
        y_float=float(value)

    else:
      value="%12.4E" % value

    char+=value

  return skip, char, x_float, y_float


def print_float(value):
  value=re.sub(r"(\d)-(\d)",r"\1E-\2",value)
  value=re.sub(r"(\d)\+(\d)",r"\1E+\2",value)

  return value


def get_args(ver):
  parser=argparse.ArgumentParser(\
   usage="Convert C6 file to CX4 file",\
   epilog="example: x4_c6tocx.py -i c6 -e 22742")
  parser.add_argument("-v", "--version",\
   action="version", version=ver)
  parser.add_argument("-i", "--dir_c6",\
   help="directory of input C6 files")
  parser.add_argument("-d", "--file_dict",\
   help="input JSON Dictionary (optional, default: dict.json)", default="dict.json")
  parser.add_argument("-e", "--entry",\
   help="EXFOR Entry number ('all' to process all files in the input directory)")
  parser.add_argument("-o", "--dir_cx4",\
   help="output CX4 directory")
  parser.add_argument("-n", "--file_idx",\
   help="output index file (optional, default: x4_c6tocx.txt)", default="x4_c6tocx.txt")
  parser.add_argument("-s", "--sysout",\
   help="output reference system identifier (optional, default: OOO)", default="OOO")
  parser.add_argument("-f", "--force",\
   help="never prompt", action="store_true")
  parser.add_argument("-x", "--exclhi",\
   help="do not convert heavy-ion induced reaction data", action="store_true")

  args=parser.parse_args()
  return args


def get_input(args):
  time=datetime.datetime.now()
  date=time.strftime("%Y-%m-%d")
  print("C6TOCX (Ver."+ver+") run on "+date)
  print("-----------------------------------------")

  force0=args.force
  exclhi=args.exclhi

  dir_c6=args.dir_c6
  if dir_c6 is None:
    dir_c6=input("Directory of input C6 files [c6] --------> ")
    if dir_c6=="":
      dir_c6="c6"
  if not os.path.exists(dir_c6):
    print(" ** Directory "+dir_c6+" does not exist.")
  while not os.path.exists(dir_c6):
    dir_c6=input("Directory of input C6 files [c6] --------> ")
    if dir_c6=="":
      dir_c6="c6"
    if not os.path.exists(dir_c6):
      print(" ** Directory "+dir_c6+" does not exist.")

  file_dict=args.file_dict
  print("JSON Dictionary -------------------------> "+file_dict)
  if not os.path.exists(file_dict):
    print(" ** File "+file_dict+" does not exist.")
  while not os.path.exists(file_dict):
    file_dict=input("JSON Dictionary [dict.json] ------> ")
    if file_dict=="":
      file_dict="dict.json"
    if not os.path.exists(file_dict):
      print(" ** File "+file_dict+" does not exist.")

  entry=args.entry
  if entry is None:
    entry=input("EXFOR Entry # [all] ---------------------> ")
    if entry=="":
      entry="all"
  entry_lower=entry.lower()
  if entry=="all":
    pattern=dir_c6+"/[a-z0-9][0-9][0-9][0-9][0-9].[0-9][0-9][0-9]*_[0-9][0-9][0-9][0-9].c6"
  else:
    pattern=dir_c6+"/"+entry_lower+".[0-9][0-9][0-9]*_[0-9][0-9][0-9][0-9].c6"
  all_files=glob.glob(pattern)
  files = [file for file in all_files if re.search(r"\d\d\d(\.[A-Z1-9])?", file)]
  if len(files)==0:
    if entry=="all":
      print(" ** C6 file does not exist.")
    else:
      print(" ** C6 file for EXFOR Entry "+entry+" does not exist.")
  while len(files)==0:
    entry=input("EXFOR Entry # [all] ---------------------> ")
    if entry=="":
      entry="all"
    entry_lower=entry.lower()
    if entry=="all":
      pattern=dir_c6+"/[a-z0-9][0-9][0-9][0-9][0-9].[0-9][0-9][0-9]*_[0-9][0-9][0-9][0-9].c6"
    else:
      pattern=dir_c6+"/"+entry_lower+".[0-9][0-9][0-9]*_[0-9][0-9][0-9][0-9].c6"
    all_files=glob.glob(pattern)
    files = [file for file in all_files if re.search(r"\d\d\d(\.[A-Z1-9])?", file)]
    if len(files)==0:
      if entry=="all":
        print(" ** C6 file does not exist.")
      else:
        print(" ** C6 file for EXFOR Entry "+entry+" does not exist.")
  entry=entry.lower()

  dir_cx4=args.dir_cx4
  if dir_cx4 is None:
    dir_cx4=input("Directory of output CX4 files [cx4] -----> ")
  if dir_cx4=="":
    dir_cx4="cx4"
  if os.path.isdir(dir_cx4):
    msg="Directory '"+dir_cx4+"' exists and must be overwritten."
    print_error(msg,"",force0)
  else:
    msg="Directionry '"+dir_cx4+"' does not exist and must be created."
    print_error(msg,"",force0)
    os.mkdir(dir_cx4)

  file_idx=args.file_idx
  print("output index file ----------------> "+file_idx)
  print("\n")
  if os.path.isfile(file_idx):
    msg="File '"+file_idx+"' exists and must be appended."
    print_error(msg,"",force0)

  sysout=args.sysout
  sysout=sysout.upper()
  print("output reference system id -------> "+sysout)
  if len(sysout)==2:
    sysout+="O"
  if not re.compile(r"^(O|L|C)(O|L|C)(O|L|C)$").search(sysout):
    print(" ** "+sysout+" is an invalid reference system identifier. Must be a combination of O, L and C.")
  while not re.compile(r"^(O|L|C)(O|L|C)(O|L|C)$").search(sysout):
    sysout=input("output reference system id [OOO] -> ")
    if sysout=="":
      sysout="OOO"
    sysout=sysout.upper()
    if len(sysout)==2:
      sysout+="O"
    if not re.compile(r"^(O|L|C)(O|L|C)(O|L|C)$").search(sysout):
      print(" ** "+sysout+" is an invalid reference system identifier. Must be a combination of O, L and C.")

  print("\n")

  return dir_c6,file_dict,entry,dir_cx4,file_idx,sysout,force0,exclhi


def print_error_fatal(msg,line):
  print("** "+msg)
  print(line)
  exit()


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


def get_file_lines(file):
  if os.path.exists(file):
    f=open(file, "r")
    lines=f.readlines()
    f.close()
  else:
    msg="File "+file+" does not exist."
    print_error_fatal(msg,"")

  return lines


if __name__ == "__main__":
  c6tocx()
  exit()
