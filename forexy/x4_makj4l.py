#!/usr/bin/python3
ver="2026.10.15"
############################################################
# MAKJ4L Ver.2026.10.15
# (Utility for production and update of J4 file storage)
#
# Naohiko Otuka (IAEA Nuclear Data Section)
############################################################
import argparse
import datetime
import os
import re
import shutil
import stat
import time

if os.path.isfile("x4_x4toj4.py"):
  import x4_x4toj4
else:
  from forexy import x4_x4toj4

def makj4l():
  args=get_args(ver)
  main(*get_input(args))


def main(dir_storage,file_dict,dir_j4lib,file_trans,file_log,email0,force0):
  time_start=time.time()
  global email

  email=email0
  force=force0

  if file_trans is None:
    tid=None
    tdate=None
    clean(dir_j4lib)
    dirs=os.listdir(dir_storage)
    for dir in dirs:
      if re.compile("^[a-z0-8]$").search(dir):
        files=os.listdir(dir_storage+"/"+dir)
        files=sorted(files)
        for file in files:
          if re.compile(dir+r"\d{4}\.txt").search(file):
            file_x4=dir_storage+"/"+dir+"/"+file
            make_j4(file_x4,dir_storage,file_dict,dir_j4lib,force)
  else:
    (tid,tdate,entries)=get_entry_number(file_trans,dir_storage)
    for entry in entries:
      entry=entry.lower()
      area=entry[0:1].lower()
      file_x4=dir_storage+"/"+ area+"/"+entry+".txt"
      make_j4(file_x4,dir_storage,file_dict,dir_j4lib,force)

  update_log(file_log,file_trans,tid,tdate,dir_j4lib)

  time_end=time.time()
  time_elapsed=format(time_end-time_start, ".2f")
  print("MAKJ4L: Processing terminated normally. "+time_elapsed+" sec.\n")


def update_log(file_log,file_trans,tid,tdate,dir_j4lib):
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
    line=seq_out+" "+stamp+"                             "+dir_j4lib+"\n"
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
        shutil.rmtree(dir_storage+"/"+file, onexc=remove_readonly)


def get_entry_number(file_trans,dir_storage):
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
      file=dir_storage+"/"+area+"/"+entry+".txt"
      if altflag==" ":           # new entries
        entries.append(entry)
      elif os.path.exists(file): # retransmitted entries
        entries.append(entry)
      else:
        msg="Revised entry "+entry+" is in "+file_trans+" but "+file+" is not in the entry storage."
        print_error_fatal(msg,"")
        
  return tid,tdate,entries


def make_j4(file_x4,dir_storage,file_dict,dir_j4lib,force):
  m=re.compile(r"([a-z0-8]\d{4,4})\.txt$").search(file_x4)
  entry=m.group(1)
  area=entry[0:1]
  dir_out=dir_j4lib+"/"+ area
  if not (os.path.isdir(dir_out)): 
    os.mkdir(dir_out)
  file_j4=dir_out+"/"+entry+".json"
  if os.path.isfile(file_j4):
    print("updating ..."+file_j4)
  else:
    print("creating ..."+file_j4)

  data_id  ="all"
  key_keep =["all"]
  chkrid   = False
  add19    = True
  keepflg  = False
  outstr   = False

  x4_x4toj4.main(file_x4,file_dict,data_id,file_j4,key_keep,email,force,chkrid,add19,keepflg,outstr)

  return


def get_args(ver):
  parser=argparse.ArgumentParser(\
   usage="Production and update of J4 file storage",\
   epilog="example: x4_makj4l.py -i entry -d dict.json -j j4")
  parser.add_argument("-v", "--version",\
   action="version", version=ver)
  parser.add_argument("-i", "--dir_storage",\
   help="input entry storage directory")
  parser.add_argument("-d", "--file_dict",\
   help="input JSON Dictionary (optional, default: dict.json)", default="dict.json")
  parser.add_argument("-j", "--dir_j4lib",\
   help="output J4 library storage")
  parser.add_argument("-t", "--file_trans",\
   help="input trans tape (optional, default: None)", default=None)
  parser.add_argument("-g", "--file_log",\
   help="output log file (optional, default: x4_makj4l.log)", default="x4_makj4l.log")
  parser.add_argument("-m", "--email",\
   help="your email address (optional, default: None)", default=None)
  parser.add_argument("-f", "--force",\
   help="never prompt", action="store_true")

  args=parser.parse_args()
  return args


def get_input(args):
  time=datetime.datetime.now()
  date=time.strftime("%Y-%m-%d")
  print("MAKJ4L (Ver."+ver+") run on "+date)
  print("-----------------------------------------")

  force0=args.force

  dir_storage=args.dir_storage
  if dir_storage is None:
    dir_storage=input("directory of input entry storage [entry] -> ")
    if dir_storage=="":
      dir_storage="entry"

  if not os.path.isdir(dir_storage):
    print(" ** Directory '"+dir_storage+"' does not exist.")
  while not os.path.isdir(dir_storage):
    dir_storage=input("directory of input entry storage [entry] -------> ")
    if dir_storage=="":
      dir_storage="entry"
    if not os.path.isdir(dir_storage):
      print(" ** Directory '"+dir_storage+"' does not exist.")

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

  file_trans=args.file_trans
  dir_j4lib=args.dir_j4lib
  if dir_j4lib is None:
    dir_j4lib=input("directory of output J4 file storage [j4] -> ")
    if dir_j4lib=="":
      dir_j4lib="j4"
  if os.path.isdir(dir_j4lib):
    if file_trans is None:
      msg="Directory '"+dir_j4lib+"' exists and must be initialised."
      print_error(msg,"",force0)
  else:
    msg="Directory '"+dir_j4lib+"' does not exist and must be created."
    print_error(msg,"",force0)
    os.mkdir(dir_j4lib)

  if file_trans is None:
    print("input trans tape -------------------------> (unspecified)")
  else:
    if not os.path.exists(file_trans):
      print(" ** File '"+file_trans+"' does not exist.")
      while not os.path.exists(file_trans):
        file_trans=input("input trans tape [trans.txt] --------------> ")
        if file_trans=="":
          file_trans="trans.txt"
        if not os.path.exists(file_trans):
          print(" ** File '"+file_trans+"' does not exist.")
    print("input trans tape -------------------------> "+file_trans)

  file_log=args.file_log
  print("output log file --------------------------> "+file_log)
  if not os.path.isfile(file_log):
    msg="File '"+file_log+"' is absent and will be created."
    print_error(msg,"",force0)

  email=args.email
  if email is None:
    print("your email adress ------------------------> (unspecified)")
  if email is not None:
    print("your email address --------------------> "+email)
    if not re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$").search(email):
      print(" ** Input a correct email address.")
    while not re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$").search(email):
      email=input("your email address --------------------> ")
      if not re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$").search(email):
        print(" ** Input a correct email address.")

  print("\n")

  return dir_storage,file_dict,dir_j4lib,file_trans,file_log,email,force0


def remove_readonly(func, path, _):
    "Clear the readonly bit and reattempt the removal"
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
  makj4l()
  exit()
