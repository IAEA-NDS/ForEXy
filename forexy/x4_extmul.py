#!/usr/bin/python3
ver="2026.10.02"
############################################################
# EXTMUL Ver.2026.10.02
# (Utility to extract a dataset from multiple reaction formalism)
#
# Naohiko Otuka (IAEA Nuclear Data Section)
############################################################
import argparse
import datetime
import glob
import os
import re
import time

if os.path.isfile("x4_x4toj4.py"):
  import x4_x4toj4
else:
  from forexy import x4_x4toj4

if os.path.isfile("x4_poipoi.py"):
  import x4_poipoi
else:
  from forexy import x4_poipoi

if os.path.isfile("x4_j4tox4.py"):
  import x4_j4tox4
else:
  from forexy import x4_j4tox4

def extmul():
  args=get_args(ver)
  main(*get_input(args))


def main(file_inp,file_dict,data_id,file_out,force0):
  time_start=time.time()

  force=force0
  chkrid   = False  # record identificaiton not checked in X4TOJ4
  key_keep =["all"] # keep all keywords in X4TOJ4 and POIPOI
  add19    = True   # add '19' to two-digit year
  keepflg  = False  # ignore flags at col.80 in X4TOJ4
  outstr   = True   # print real numbers as strings in X4TOJ4
  delpoin  = True   # delete pointer in the output in POIPOI
  keep001  = True   # keep common subentry in POIPOI
  keepres  = False  # keep resonance parameter table in POIPOI


# Conversion to J4 format by X4TOJ4
  if data_id=="all":
    entry="all"
  else:
    entry=data_id[0:5]
  file_js0 = "exfor0.json"
  email    = None
  x4_x4toj4.main(file_inp,file_dict,"all",file_js0,key_keep,email,force,chkrid,add19,keepflg,outstr)

# Conversion to J4 format without pointer structure by POIPOI
  if data_id=="all":
    time_now=datetime.datetime.now()
    dir_js1 = time_now.strftime('%Y%m%d%H%M%S%f')
    os.mkdir(dir_js1)
    x4_poipoi.main(file_js0,file_dict,data_id,dir_js1,key_keep,force,delpoin,keep001,keepres)
  else:
    file_js1 = "exfor1.json"
    x4_poipoi.main(file_js0,file_dict,data_id,file_js1,key_keep,force,delpoin,keep001,keepres)

# Conversion to X4 format by J4TOX4
  if data_id=="all":
    file_js1s=glob.glob("./"+dir_js1+"/*.json")
    for file_js1 in file_js1s:
      file_exf=re.sub('json$', 'txt',file_js1)
      x4_j4tox4.main(file_js1,file_dict,file_exf,force)
  else:
    x4_j4tox4.main(file_js1,file_dict,file_out,force)

# Merging of J4TOX4 output
  if data_id=="all":
    f=open(file_out,"w")
    file_x4s=glob.glob("./"+dir_js1+"/*.txt")
    nsub=len(file_x4s)
    for isub, file_x4 in enumerate(file_x4s):
      lines=get_file_lines(file_x4)
      san=0
      for line in lines:
        if line[0:8]=="ENDENTRY":
          if isub==nsub-1:
            f.write(line)
        else:
          if line[0:6]=="SUBENT":
            san+=1
          if isub==0 or san==2:
            f.write(line)
    f.close()

  os.remove("exfor0.json")
  if data_id=="all":
    files=glob.glob("./"+dir_js1+"/*")
    for file in files:
      os.remove(file)
    os.rmdir(dir_js1)
  else:
    os.remove(file_js1)

  time_end=time.time()
  time_elapsed=format(time_end-time_start, ".2f")
  print("EXTMUL: Processing terminated normally. "+time_elapsed+" sec.\n")


def get_file_lines(file):
  if os.path.exists(file):
    f=open(file, "r")
    lines=f.readlines()
    f.close()
  else:
    msg="File "+file+" does not exist."
    print_error_fatal(msg)
  return lines


def get_args(ver):

  parser=argparse.ArgumentParser(\
   usage="Extract a dataset from multiple reaction formalism",\
   epilog="example: x4_extmul.py -i exfor.txt -e 23756.002.3 -o exfor_out.txt")
  parser.add_argument("-v", "--version",\
   action="version", version=ver)
  parser.add_argument("-i", "--file_inp",\
   help="input EXFOR file")
  parser.add_argument("-d", "--file_dict",\
   help="input JSON dictionary (optional, default: dict.json)", default="dict.json")
  parser.add_argument("-e", "--data_id",\
   help="EXFOR dataset ID for extraction ('all' to process all datasets)")
  parser.add_argument("-o", "--file_out",\
   help="output EXFOR file")
  parser.add_argument("-f", "--force",\
   help="never prompt", action="store_true")

  args=parser.parse_args()
  return args


def get_input(args):
  time=datetime.datetime.now()
  date=time.strftime("%Y-%m-%d")
  print("EXTMUL (Ver."+ver+") run on "+date)
  print("-----------------------------------------")

  force0=args.force

  file_inp=args.file_inp
  if file_inp is None:
    file_inp=input("input EXFOR file [exfor.txt] ------------------> ")
    if file_inp=="":
      file_inp="exfor.txt"
  if not os.path.exists(file_inp):
    print(" ** File "+file_inp+" does not exist.")
  while not os.path.exists(file_inp):
    file_inp=input("input EXFOR file [exfor.txt] ------------------> ")
    if file_inp=="":
      file_inp="exfor.txt"
    if not os.path.exists(file_inp):
      print(" ** File "+file_inp+" does not exist.")

  file_dict=args.file_dict
  print("JSON Dictionary -------------------------------> "+file_dict)
  if not os.path.exists(file_dict):
    print(" ** File "+file_dict+" does not exist.")
  while not os.path.exists(file_dict):
    file_dict=input("JSON DIctionary [dict.json] -------------------> ")
    if file_dict=="":
      file_dict="dict.json"
    if not os.path.exists(file_dict):
      print(" ** File "+file_dict+" does not exist.")

  data_id=args.data_id
  if data_id is None:
    data_id=input("EXFOR dataset ID for extraction [23756.002.3] -> ")
    if data_id=="":
      data_id="23756.002.3"
  if data_id!="all":
    data_id=data_id.upper()
  if not re.compile(r"^[1-9A-Z]\d{4}\.\d{3}(\.[1-9A-Z])?$").search(data_id) and data_id!="all":
    print(" ** EXFOR dataset ID "+data_id+" is illegal.")
  while not re.compile(r"^[1-9A-Z]\d{4}\.\d{3}(\.[1-9A-Z])?$").search(data_id) and data_id!="all":
    data_id=input("EXFOR dataset ID for extraction [23756.002.3] -> ")
    if data_id!="all":
      data_id=data_id.upper()
    if data_id=="":
      data_id="23756.002.3"
    if not re.compile(r"^[1-9A-Z]\d{4}\.\d{3}(\.[1-9A-Z])?$").search(data_id) and data_id!="all":
      print(" ** EXFOR dataset ID "+data_id+" is illegal.")

  file_out=args.file_out
  if file_out is None:
    file_out=input("output EXFOR file [exfor_out.txt] -------------> ")
  if file_out=="":
    file_out="exfor_out.txt"
  if os.path.isfile(file_out):
    msg="File '"+file_out+"' exists and must be overwritten."
    print_error(msg,"",force0)

  return file_inp,file_dict,data_id,file_out,force0


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


if __name__ == "__main__":
  extmul()
  exit()
