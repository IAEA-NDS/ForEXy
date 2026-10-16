#!/usr/bin/python3
ver="2026.10.16"
############################################################
# MAKC6L Ver.2026.10.16
# (Utility for production and update of C6 file storage)
#
# Naohiko Otuka (IAEA Nuclear Data Section)
############################################################
import argparse
import datetime
import glob
import os
import re
import shutil
import stat
import time

if os.path.isfile("x4_poipoi.py"):
  import x4_poipoi
else:
  from forexy import x4_poipoi

if os.path.isfile("x4_j4toc6.py"):
  import x4_j4toc6
else:
  from forexy import x4_j4toc6

def makc6l():
  args=get_args(ver)
  main(*get_input(args))


def main(dir_j4lib,file_dict,dir_c6lib,seplvl,file_trans,file_log,file_idx,sysout,enewid,force,exclhi,incder,c4out):
  time_start=time.time()


  if file_trans is None:
    tid=None
    tdate=None
    clean(dir_c6lib)
    dirs=os.listdir(dir_j4lib)
    dirs=sorted(dirs)
    for dir in dirs:
      if re.compile("^[a-z0-8]$").search(dir):
        files=os.listdir(dir_j4lib+"/"+dir)
        files=sorted(files)
        for file in files:
          if re.compile(dir+r"\d{4}\.json").search(file):
            file_j4=dir_j4lib+"/"+dir+"/"+file
            make_c6(file_j4,file_dict,dir_c6lib,seplvl,file_idx,sysout,enewid,force,exclhi,incder,c4out)
  else:
    (tid,tdate,entries)=get_entry_number(file_trans,dir_j4lib)
    delete_idx(file_idx,entries)
    for entry in entries:
      area=entry[0:1]
      pattern=dir_c6lib+"/"+area+"/"+entry+".*"
      oldfiles=glob.glob(pattern)
      for oldfile in oldfiles:
        os.remove(oldfile)
        print("File "+oldfile+" deleted")

      file_j4=dir_j4lib+"/"+ area+"/"+entry+".json"
      make_c6(file_j4,file_dict,dir_c6lib,seplvl,file_idx,sysout,enewid,force,exclhi,incder,c4out)

  if tid!=None:
    sort_idx(file_idx,entries)
  update_log(file_log,file_trans,tid,tdate,dir_j4lib)

  time_end=time.time()
  time_elapsed=format(time_end-time_start, ".2f")
  print("MAKC6L: Processing terminated normally. "+time_elapsed+" sec.\n")


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


def update_log(file_log,file_trans,tid,tdate,dir_c4lib):
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
    line=seq_out+" "+stamp+"                             "+dir_c4lib+"\n"
  else:
    line=seq_out+" "+stamp+" "+tid+"      "+tdate+"   "+centre_out+" "+file_trans+"\n"

  f.write(line)
  f.close()


def clean(dir_storage):
  files=os.listdir(dir_storage)
  for file in files:
    if os.path.isdir(dir_storage+"/"+file):
      if re.compile("^[a-z0-8]$").search(file):
        print("Directory "+dir_storage+"/"+file+" deleted")
        shutil.rmtree(dir_storage+"/"+file, onerror=remove_readonly)


def get_entry_number(file_trans,dir_j4lib):
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
      file=dir_j4lib+"/"+area+"/"+entry+".json"
      if os.path.exists(file):
        entries.append(entry)
      else:
        msg="Entry "+entry+" is in "+file_trans+" but "+file+" is not in the J4 storage."
        print_error_fatal(msg,"")
        
  return tid,tdate,entries


def make_c6(file_j4,file_dict,dir_c6lib,seplvl,file_idx,sysout,enewid,force,exclhi,incder,c4out):
  m=re.compile(r"([a-z0-8]\d{4,4})\.json$").search(file_j4)
  entry=m.group(1)
  area=entry[0:1]
  dir_out=dir_c6lib+"/"+ area
  if not (os.path.isdir(dir_out)): 
    os.mkdir(dir_out)
  if seplvl==1:
    if c4out:
      file_out=dir_out+"/"+entry+".c4"
    else:
      file_out=dir_out+"/"+entry+".c6"
  else:
    file_out=dir_out

  key_keep =["all"] # keep all keywords in X4TOJ4 and POIPOI
  delpoin  = False  # delete pointer in the output in POIPOI
  keep001  = False  # keep common subentry in POIPOI
  keepres  = False  # keep resonance parameter table in POIPOI

  time_now=datetime.datetime.now()
  dir_wrk = time_now.strftime('%Y%m%d%H%M%S%f')
  os.mkdir(dir_wrk)

  x4_poipoi.main(file_j4,file_dict,"all",dir_wrk,key_keep,force,delpoin,keep001,keepres)

  pattern=dir_wrk+"/"+entry+".[0-9][0-9][0-9]*.json"
  all_files=glob.glob(pattern)
  files=[file for file in all_files if re.search(r"\d\d\d(\.[A-Z1-9])?\.json", file)]
  if len(files)!=0:
    x4_j4toc6.main(dir_wrk,file_dict,entry,file_out,seplvl,file_idx,sysout,enewid,force,exclhi,incder,c4out)

  files=glob.glob("./"+dir_wrk+"/*")
  for file in files:
    os.remove(file)
  os.rmdir(dir_wrk)

  return


def get_args(ver):
  parser=argparse.ArgumentParser(\
   usage="Production and update of C6 file storage",\
   epilog="example: x4_makc6l.py -i j4 -o c6")
  parser.add_argument("-v", "--version",\
   action="version", version=ver)
  parser.add_argument("-i", "--dir_j4lib",\
   help="input j4 storage directory")
  parser.add_argument("-d", "--file_dict",\
   help="input JSON Dictionary (optional, default: dict.json)", default="dict.json")
  parser.add_argument("-o", "--dir_c6lib",\
   help="output C6 library storage")
  parser.add_argument("-l", "--seplvl",\
   help="output separation level 1, 2 or 3 (optional, default: 3)", default="3")
  parser.add_argument("-t", "--file_trans",\
   help="input trans tape (optional, default: None)", default=None)
  parser.add_argument("-g", "--file_log",\
   help="output log file (optional, default: x4_makc6l.log)", default="x4_makc6l.log")
  parser.add_argument("-n", "--file_idx",\
   help="output index file (optional, default: x4_makc6l.txt)", default="x4_makc6l.txt")
  parser.add_argument("-s", "--sysout",\
   help="output reference system identifier (optional, default: OOO)", default="OOO")
  parser.add_argument("-w", "--enewid",\
   help="energy width allowance (percent) for SACS (optional, default: 10)", default="10")
  parser.add_argument("-f", "--force",\
   help="never prompt", action="store_true")
  parser.add_argument("-x", "--exclhi",\
   help="particle-induced reaction only", action="store_true")
  parser.add_argument("-y", "--incder",\
   help="include DERIVed data", action="store_true")
  parser.add_argument("-c4", "--c4out",\
   help="output in C4 format", action="store_true")

  args=parser.parse_args()
  return args


def get_input(args):
  time=datetime.datetime.now()
  date=time.strftime("%Y-%m-%d")
  print("MAKC6L (Ver."+ver+") run on "+date)
  print("-----------------------------------------")

  file_trans=args.file_trans
  force=args.force
  exclhi=args.exclhi
  incder=args.incder
  c4out=args.c4out

  dir_j4lib=args.dir_j4lib
  if dir_j4lib is None:
    dir_j4lib=input("directory of input J4 storage [j4] -------> ")
    if dir_j4lib=="":
      dir_j4lib="j4"

  if not os.path.isdir(dir_j4lib):
    print(" ** Directory '"+dir_j4lib+"' does not exist.")
  while not os.path.isdir(dir_j4lib):
    dir_j4lib=input("directory of input J4 storage [j4] -------> ")
    if dir_j4lib=="":
      dir_j4lib="j4"
    if not os.path.isdir(dir_j4lib):
      print(" ** Directory '"+dir_j4lib+"' does not exist.")

  file_dict=args.file_dict
  print("JSON Dictionary --------------------------> "+file_dict)
  if not os.path.exists(file_dict):
    print(" ** File "+file_dict+" does not exist.")
  while not os.path.exists(file_dict):
    file_dict=input("JSON DIctionary [dict.json] --------------> ")
    if file_dict=="":
      file_dict="dict.json"
    if not os.path.exists(file_dict):
      print(" ** File "+file_dict+" does not exist.")

  seplvl=args.seplvl
  print("output separation level ------------------> "+seplvl)
  if seplvl!="1" and seplvl!="2" and seplvl!="3":
    print(" ** Separation level must be 1, 2 or 3.")
  while seplvl!="1" and seplvl!="2" and seplvl!="3":
    seplvl=input("output separation level [3] ----------------> ")
    if seplvl=="":
      seplvl="3"
    if seplvl!="1" and seplvl!="2" and seplvl!="3":
      print(" ** Separation level must be 1, 2 or 3.")
  seplvl=int(seplvl)

  dir_c6lib=args.dir_c6lib
  if dir_c6lib is None:
    dir_c6lib=input("directory of output C6 file storage [c6] -> ")
    if dir_c6lib=="":
      dir_c6lib="c6"

  if os.path.isdir(dir_c6lib):
    if file_trans is None:
      msg="Directory '"+dir_c6lib+"' exists and must be initialised."
      print_error(msg,"",force)
  else:
    msg="Directory '"+dir_c6lib+"' does not exist and must be created."
    print_error(msg,"",force)
    os.mkdir(dir_c6lib)

  if file_trans is None:
    file_trans=args.file_trans
    print("input trans tape -------------------------> (unspecified)")
  else:
    file_trans=args.file_trans
    if not os.path.exists(file_trans):
      print(" ** File '"+file_trans+"' does not exist.")
    while not os.path.exists(file_trans):
      file_trans=input("input trans tape [trans.txt] --------------> ")
      if file_trans=="":
        file_trans="trans.txt"
      if not os.path.exists(file_trans):
        print(" ** File '"+file_trans+"' does not exist.")
    print("input trans tape ---------------------------> "+file_trans)



  print("\n")
  file_log=args.file_log
  print("output log file --------------------------> "+file_log)
  if file_log is None:
    file_log=input("output log file [x4_makc6l.log] ----------> ")
  if file_log=="":
    file_log="x4_makc6l.log"
  if os.path.isfile(file_log):
    msg="File '"+file_log+"' exists and must be appended."
    print_error(msg,"",force)

  print("\n")
  file_idx=args.file_idx
  print("output index file ------------------------> "+file_idx)
  if file_idx is None:
    file_idx=input("output index file [x4_makc6l.txt] --------> ")
  if file_idx=="":
    file_idx="x4_makc6l.txt"
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
      file_idx=input("output index file [x4_makc6l.txt] --------> ")
      if file_idx=="":
        file_idx="x4_makc6l.txt"
      if not os.path.exists(file_idx):
        print(" ** File '"+file_idx+"' should exist but does not exist.")

  sysout=args.sysout
  sysout=sysout.upper()
  print("output reference system id ---------------> "+sysout)
  if len(sysout)==2:
    sysout+="O"
  if seplvl!=1 and sysout!="OOO":
    msg="The reference system identifier is set to OOO (no transformation) since separation level is not 1"
    print_error(msg,"",False)
    sysout="OOO"
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

  enewid=args.enewid
  print("energy width allowance (%) for SACS ------> "+enewid)
  if not is_float(enewid):
    print(" ** "+enewid+" is not a number. Must be a real number or integer.")
    while not is_float(enewid):
      enewid=input("energy width allowance (%) for SACS [10] -> ")
      if enewid=="":
        enewid=10
      if not is_float(enewid):
        print(" ** "+enewid+" is not a number. Must be a real number or integer.")
  enewid=float(enewid)

  print("\n")

  return dir_j4lib,file_dict,dir_c6lib,seplvl,file_trans,file_log,file_idx,sysout,enewid,force,exclhi,incder,c4out


def is_float(s):
  try:
    float(s)
    return True
  except ValueError:
    return False


def remove_readonly(func, path, exc_info):
  os.chmod(path, stat.S_IWRITE)
  func(path)


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
  makc6l()
  exit()
