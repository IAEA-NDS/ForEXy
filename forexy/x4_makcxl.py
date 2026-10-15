#!/usr/bin/python3
ver="2026.10.14"
############################################################
# MAKCXL Ver.2026.10.14
# (Utility for production and update of CX4 file storage)
#
# Naohiko Otuka (IAEA Nuclear Data Section)
############################################################
import argparse
import datetime
import glob
import os
import re
import shutil
import time
import heapq

if os.path.isfile("x4_c6tocx.py"):
  import x4_c6tocx
else:
  from forexy import x4_c6tocx

if os.path.isfile("x4_plotcx.py"):
  import x4_plotcx
else:
  from forexy import x4_plotcx

def makcxl():
  args=get_args(ver)
  main(*get_input(args))


def main(dir_c6lib,file_dict,dir_cx4lib,file_trans,file_log,file_idx,sysout,force,plot,exclhi):
  time_start=time.time()

  light_particle=["0","g","n","p","d","t","h","a"]

  if file_trans is None:
    tid=None
    tdate=None
    clean(dir_cx4lib)
    dirs=os.listdir(dir_c6lib)
    dirs=sorted(dirs)
    for dir in dirs:
      if re.compile("^[0-8a-z]$").search(dir):
        files=os.listdir(dir_c6lib+"/"+dir)
        files=sorted(files)
        if len(files)!=0:
          dir_c6=dir_c6lib+"/"+dir
          x4_c6tocx.main(dir_c6,file_dict,"all",dir_cx4lib,file_idx,sysout,force,exclhi)

  else:
    (tid,tdate,entries)=get_entry_number(file_trans,dir_c6lib,force)
    delete_idx(file_idx,entries)
    for entry in entries:
      entry=entry.upper()
      pattern=dir_cx4lib+"/*/*/*/*/*-*-*-*-*-*-*_"+entry+".*.cx4"
      oldfiles=glob.glob(pattern)
      for oldfile in oldfiles:
        os.remove(oldfile)
        oldplot=re.sub('cx4$', 'pdf', oldfile)
        if os.path.isfile(oldplot):
          os.remove(oldplot)
        print("File "+oldfile+" deleted")

      entry=entry.lower()
      area=entry[0:1]
      pattern=dir_c6lib+"/"+area+"/"+entry+"*-*-*-*-*-*-*-*.c6"
      files=glob.glob(pattern)
      files=sorted(files)
      if len(files)==0:
        entry_out=entry.upper()
        msg="Entry "+entry_out+" is in "+file_trans+" but a C6 file of this entry is not in the C6 storage. Quantity not supported by J4TOC6?"
        print_error(msg,"",force)
      else:
        dir_c6=dir_c6lib+"/"+area
        x4_c6tocx.main(dir_c6,file_dict,entry,dir_cx4lib,file_idx,sysout,force,exclhi)

  files=os.listdir(dir_cx4lib)
  files=sorted(files)
  for file_tmp in files:
    m=re.search(r"^(.+?)-(.+?)-(.+?)-(.+?)-.+?\.cx4$",file_tmp)
    if m:
      proj=m.group(1)
      targ=m.group(2)
      reac=m.group(3)
      quan=m.group(4)
      file_cx4=dir_cx4lib+"/"+proj+"/"+targ+"/"+reac+"/"+quan+"/"+file_tmp
      file_old=dir_cx4lib+"/"+file_tmp
      if not os.path.isdir(dir_cx4lib+"/"+proj):
        os.mkdir(dir_cx4lib+"/"+proj)
      if not os.path.isdir(dir_cx4lib+"/"+proj+"/"+targ):
        os.mkdir(dir_cx4lib+"/"+proj+"/"+targ)
      if not os.path.isdir(dir_cx4lib+"/"+proj+"/"+targ+"/"+reac):
        os.mkdir(dir_cx4lib+"/"+proj+"/"+targ+"/"+reac)
      if not os.path.isdir(dir_cx4lib+"/"+proj+"/"+targ+"/"+reac+"/"+quan):
        os.mkdir(dir_cx4lib+"/"+proj+"/"+targ+"/"+reac+"/"+quan)
      os.rename(file_old,file_cx4)
      if plot:
        file_pdf=re.sub(r"cx4$","pdf",file_cx4)
        x4_plotcx.main(file_cx4,file_pdf,force)


  if tid!=None:
    sort_idx(file_idx,entries)
  update_log(file_log,file_trans,tid,tdate,dir_c6lib)

  time_end=time.time()
  time_elapsed=format(time_end-time_start, ".2f")
  print("MAKCXL: Processing terminated normally. "+time_elapsed+" sec.\n")


def get_cx4_name(file_c6,dir_cx4lib,sysout):
  m=re.search(r"([0-8a-z]\d{4}\.\d{3}(\.[0-9a-z])?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?)-(.+?\d\d\d\d)\.c6$",file_c6)
  ansan=m.group(1)
  proj=m.group(3)
  targ=m.group(4)
  reac=m.group(5)
  quan=m.group(6)
  dist=m.group(7)
  spec=m.group(8)
  const=m.group(9)

  if sysout!="OOO":
    frame_out_qua=sysout[0:1]
    frame_out_ang=sysout[1:2]
    frame_out_ene=sysout[2:3]
    if "adx" in quan and reac[0:1]!="x":
      if dist=="angdisc" or dist=="angdisl":
        if quan=="adxc" and frame_out_qua=="L":
          quan="adxl"
        elif quan=="adxl" and frame_out_qua=="C":
          quan="adxc"
        if dist=="angdisc" and frame_out_ang=="L":
          dist="angdisl"
        elif dist=="angdisl" and frame_out_ang=="C":
          dist="angdisc"
    elif "ddx" in quan and reac[0:1]=="x":
      if dist=="angdisc" or dist=="angdisl":
        if quan=="ddxc" and frame_out_qua=="L":
          quan="ddxl"
        elif quan=="ddxl" and frame_out_qua=="C":
          quan="ddxc"
        if dist=="angdisc" and frame_out_ang=="L":
          dist="angdisl"
        elif dist=="angdisl" and frame_out_ang=="C":
          dist="angdisc"
      elif dist=="enedisc" or dist=="enedisl":
        if quan=="ddxc" and frame_out_qua=="L":
          quan="ddxl"
        elif quan=="ddxl" and frame_out_qua=="C":
          quan="ddxc"
        if dist=="enedisc" and frame_out_ene=="L":
          dist="enedisl"
        elif dist=="enedisl" and frame_out_ene=="C":
          dist="enedisc"

  if not os.path.isdir(dir_cx4lib+"/"+proj):
    os.mkdir(dir_cx4lib+"/"+proj)
  if not os.path.isdir(dir_cx4lib+"/"+proj+"/"+targ):
    os.mkdir(dir_cx4lib+"/"+proj+"/"+targ)
  if not os.path.isdir(dir_cx4lib+"/"+proj+"/"+targ+"/"+reac):
    os.mkdir(dir_cx4lib+"/"+proj+"/"+targ+"/"+reac)
  if not os.path.isdir(dir_cx4lib+"/"+proj+"/"+targ+"/"+reac+"/"+quan):
    os.mkdir(dir_cx4lib+"/"+proj+"/"+targ+"/"+reac+"/"+quan)

  ansan=ansan.upper()
  dir_cx4=dir_cx4lib+"/"+proj+"/"+targ+"/"+reac+"/"+quan
  base_cx4=proj+"-"+targ+"-"+reac+"-"+quan+"-"+dist+"-"+spec+"-"+const+"_"+ansan+".cx4"
  file_cx4=dir_cx4+"/"+base_cx4

  return file_cx4


def delete_idx(file_idx,entries):
  f=open(file_idx,'r')
  lines=f.readlines() 
  f.close()
  line_hed=[]
  line_dat=[]
  for line in lines:
    if line[0:1]=="#":
      line_hed.append(line)
    else:
      if line[0:5] not in entries:
        line_dat.append(line)

  f=open(file_idx,'w')
  for line in line_hed:
    f.write(line)
  for line in line_dat:
    f.write(line)
  f.close()


def sort_idx(file_idx,entries):
  f=open(file_idx,'r')
  lines=f.readlines() 
  f.close()
  line_hed=[]
  line_dat=[]
  for line in lines:
    if line[0:1]=="#":
      line_hed.append(line)
    else:
      line_dat.append(line)

  line_dat=sorted(line_dat)

  f=open(file_idx,'w')
  for line in line_hed:
    f.write(line)
  for line in line_dat:
    f.write(line)
  f.close()


def update_log(file_log,file_trans,tid,tdate,dir_c6lib):
  centre={'1': 'NNDC  ',  '2': 'NEADB ', '3': 'NDS   ',  '4': 'CJD   ',
          '9': 'NDS   ',
          'A': 'CNPD  ',  'B': 'NDS   ', 'C': 'NNDC  ',  'D': 'NDS   ',
          'E': 'JCPRG ',  'F': 'CNPD  ', 'G': 'NDS   ',  'J': 'JCPRG ',
          'K': 'JCPRG ',  'L': 'NNDC  ', 'M': 'CDFE  ',  'O': 'NEADB ',
          'R': 'JCPRG ',  'S': 'CNDC  ', 'V': 'NDS   ',  'X': 'adhoc '}

  if tid is None:
    centre_out='      '
  else:
    area=tid[0:1]
    if area in centre:
      centre_out=centre[area]
    else:
      msg="Unexpected area character in TRANS ID: "+area
      print_error_fatal(msg,"")

  if not os.path.isfile(file_log):
    seq=0
    line="Seq. Update date/time           Trans(N1) Trans(N2)  Centre Tape\n"
    f=open(file_log,'w')
    f.write(line)
  else:
    seq=-1
    with open(file_log) as f:
      for line in f:
        seq+=1
    f=open(file_log,'a')
  seq_out='{:>4}'.format(seq)

  time=datetime.datetime.now()
  stamp=time.strftime("%Y-%m-%d %H:%M:%S.%f")
  if tid is None:
    line=seq_out+" "+stamp+" ----      --------          (Initialized)\n"
    f.write(line)
    seq+=1
    seq_out='{:>4}'.format(seq)
    line=seq_out+" "+stamp+"                             "+dir_c6lib+"\n"
  else:
    line=seq_out+" "+stamp+" "+tid+"      "+tdate+"   "+centre_out+" "+file_trans+"\n"

  f.write(line)
  f.close()


def clean(dir_storage):
  files=os.listdir(dir_storage)
  for file in files:
    if os.path.isdir(dir_storage+"/"+file):
      print("Directory "+dir_storage+"/"+file+" deleted")
      shutil.rmtree(dir_storage+"/"+file)


def get_entry_number(file_trans,dir_c6lib,force):
  lines=get_file_lines(file_trans)
  entries=[]
  for line in lines:
    if re.compile("^TRANS").search(line):
      tid=line[18:22]
      tdate=line[25:33]
    elif re.compile("^ENTRY").search(line):
      area=line[17:18].lower()
      entry=line[17:22].lower()
      altflag=line[10:11]
      pattern=dir_c6lib+"/"+area+"/"+entry+"*-*-*-*-*-*-*-*.c6"
      files=glob.glob(pattern)
      entries.append(entry)
        
  return tid,tdate,entries


def get_args(ver):
  parser=argparse.ArgumentParser(\
   usage="Production and update of CX4 file storage",\
   epilog="example: x4_makcxl.py -i c6 j-o cx4")
  parser.add_argument("-v", "--version",\
   action="version", version=ver)
  parser.add_argument("-i", "--dir_c6lib",\
   help="input C6 storage directory")
  parser.add_argument("-d", "--file_dict",\
   help="input JSON Dictionary (optional, default: dict.json)", default="dict.json")
  parser.add_argument("-o", "--dir_cx4lib",\
   help="output CX4 library storage")
  parser.add_argument("-t", "--file_trans",\
   help="input trans tape (optional, default: None)", default=None)
  parser.add_argument("-g", "--file_log",\
   help="output log file (optional, default: x4_makcxl.log)", default="x4_makcxl.log")
  parser.add_argument("-n", "--file_idx",\
   help="output index file (optional, default: x4_makcxl.txt)", default="x4_makcxl.txt")
  parser.add_argument("-s", "--sysout",\
   help="output reference system identifier (optional, default: OOO)", default="OOO")
  parser.add_argument("-f", "--force",\
   help="never prompt", action="store_true")
  parser.add_argument("-p", "--plot",\
   help="plot the CX4 file by gnuplot", action="store_true")
  parser.add_argument("-x", "--exclhi",\
   help="do not convert heavy-ion induced reaction data", action="store_true")

  args=parser.parse_args()
  return args


def get_input(args):
  time=datetime.datetime.now()
  date=time.strftime("%Y-%m-%d")
  print("MAKCXL (Ver."+ver+") run on "+date)
  print("-----------------------------------------")

  file_trans=args.file_trans
  force=args.force
  plot=args.plot
  exclhi=args.exclhi

  dir_c6lib=args.dir_c6lib
  if dir_c6lib is None:
    dir_c6lib=input("directory of input C6 storage [c6] ----------> ")
    if dir_c6lib=="":
      dir_c6lib="c6"

  if not os.path.isdir(dir_c6lib):
    print(" ** Directory '"+dir_c6lib+"' does not exist.")
  while not os.path.isdir(dir_c6lib):
    dir_c6lib=input("directory of input C6 storage [c6] ----------> ")
    if dir_c6lib=="":
      dir_c6lib="c6"
    if not os.path.isdir(dir_c6lib):
      print(" ** Directory '"+dir_c6lib+"' does not exist.")

  file_dict=args.file_dict
  print("JSON Dictionary -----------------------------> "+file_dict)
  if not os.path.exists(file_dict):
    print(" ** File "+file_dict+" does not exist.")
  while not os.path.exists(file_dict):
    file_dict=input("JSON DIctionary [dict.json] -----------------> ")
    if file_dict=="":
      file_dict="dict.json"
    if not os.path.exists(file_dict):
      print(" ** File "+file_dict+" does not exist.")

  dir_cx4lib=args.dir_cx4lib
  if dir_cx4lib is None:
    dir_cx4lib=input("directory of output CX4 file storage [cx4] --> ")
    if dir_cx4lib=="":
      dir_cx4lib="cx4"

  if os.path.isdir(dir_cx4lib):
    if file_trans is None:
      msg="Directory '"+dir_cx4lib+"' exists and must be initialised."
      print_error(msg,"",force)
  else:
    msg="Directory '"+dir_cx4lib+"' does not exist and must be created."
    print_error(msg,"",force)
    os.mkdir(dir_cx4lib)

  if file_trans is None:
    file_trans=args.file_trans
    print("input trans tape ----------------------------> (unspecified)")
  else:
    file_trans=args.file_trans
    if not os.path.exists(file_trans):
      print(" ** File '"+file_trans+"' does not exist.")
    while not os.path.exists(file_trans):
      file_trans=input("input trans tape [trans.txt] ---------------> ")
      if file_trans=="":
        file_trans="trans.txt"
      if not os.path.exists(file_trans):
        print(" ** File '"+file_trans+"' does not exist.")
    print("input trans tape ----------------------------> "+file_trans)

  print("\n")
  file_log=args.file_log
  print("output log file -----------------------------> "+file_log)
  if file_log is None:
    file_log=input("output log file [x4_makcxl.log] -------------> ")
  if file_log=="":
    file_log="x4_makcxl.log"
  if os.path.isfile(file_log):
    msg="File '"+file_log+"' exists and must be appended."
    print_error(msg,"",force)

  print("\n")
  file_idx=args.file_idx
  print("output index file ---------------------------> "+file_idx)
  if file_idx is None:
    file_idx=input("output index file [x4_makcxl.txt] -----------> ")
  if file_idx=="":
    file_idx="x4_makcxl.idx"
  if os.path.isfile(file_idx):
    if file_trans is None:
      msg="File '"+file_idx+"' exists and must be overwritten."
      print_error(msg,"",force)
      os.remove(file_idx)
    else:
      msg="File '"+file_idx+"' exists and must be appended."
      print_error(msg,"",force)
  elif file_trans is not None:
    print(" ** File '"+file_idx+"' should exist but does not exist.")
    while not os.path.exists(file_idx):
      file_idx=input("output index file [x4_makcxl.txt] ---------> ")
      if file_idx=="":
        file_idx="x4_makcxl.txt"
      if not os.path.exists(file_idx):
        print(" ** File '"+file_idx+"' should exist but does not exist.")


  sysout=args.sysout
  sysout=sysout.upper()
  print("output reference system id ------------------> "+sysout)
  if len(sysout)==2:
    sysout+="O"
  if not re.compile(r"^(O|L|C)(O|L|C)(O|L|C)$").search(sysout):
    print(" ** "+sysout+" is an invalid reference system identifier. Must be a combination of O, L and C.")
  while not re.compile(r"^(O|L|C)(O|L|C)(O|L|C)$").search(sysout):
    sysout=input("output reference system identifier [OOO] -> ")
    if sysout=="":
      sysout="OOO"
    sysout=sysout.upper()
    if len(sysout)==2:
      sysout+="O"
    if not re.compile(r"^(O|L|C)(O|L|C)(O|L|C)$").search(sysout):
      print(" ** "+sysout+" is an invalid reference system identifier. Must be a combination of O, L and C.")

  plot=args.plot
  if shutil.which('gnuplot') is None:
    msg="The plot option disabled. gnuplot is not available on this computer."
    print_error(msg,"",force)
    plot=False

  print("\n")

  return dir_c6lib,file_dict,dir_cx4lib,file_trans,file_log,file_idx,sysout,force,plot,exclhi


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
  makcxl()
  exit()
