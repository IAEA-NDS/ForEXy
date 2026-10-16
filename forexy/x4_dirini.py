#!/usr/bin/python3
ver="2026.10.16"
############################################################
# DIRINI Ver.2026.10.16
# (Utility to initialize EXFOR entry local storage)
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


def dirini():
  args=get_args(ver)
  main(*get_input(args))


def main(file_lib,dir_storage,file_log,force0,cut660):
  time_start=time.time()

  global cut66
  force=force0
  cut66=cut660

  clean(dir_storage)
  (ok,tid_new,tdate_new)=split(file_lib,dir_storage)
 
  if ok==0:
    msg="Program terminated abnormally. Proper END record is absent"
    print_error_fatal(msg,"")
  else:
    update_log(file_log,tid_new,tdate_new,file_lib)

    time_end=time.time()
    time_elapsed=format(time_end-time_start, ".2f")
    print("DIRINI: Processing terminated normally. "+time_elapsed+" sec.\n")


# delete directory having single character name
def clean(dir_storage):
  files=os.listdir(dir_storage)
  for file in files:
    if os.path.isdir(dir_storage+"/"+file):
      if re.compile("^[a-zA-Z0-9]$").search(file):
        print("Directory "+dir_storage+"/"+file+" deleted")
        shutil.rmtree(dir_storage+"/"+file, onerror=remove_readonly)


# extraction of each entry and its output to *.txt
def split(file_lib,dir_storage):
  ok=0
  sec=""
  g=open(file_lib,'r',encoding='iso-8859-1')

  for i,line in enumerate(g):

    if cut66:
      if len(line)>79:
        line=line[0:66].rstrip()
        line=line.rstrip()
        line=line+"\n"
      
      if re.compile("^END(BIB|COMMON|DATA|SUBENT|ENTRY|DICT)").search(line):
        line=line[0:22]+"\n" # Delete N2=0

    key=line[0:10]
    if i==0: # first record must be REQUEST or LIB
      if key!="REQUEST   " and key!="LIB       " and\
         key!="MASTER    " and key!="BACKUP    ":
        msg="The first record must be REQUEST or LIB."
        print_error_fatal(msg,line)

    if key=="REQUEST   " and sec!="DIC":
      tid_new=line[18:22]
      tdate_new=line[25:33]

    elif key=="ENDREQUEST" and sec!="DIC":
      ok=1
      return ok, tid_new, tdate_new

    elif key=="LIB       " and sec!="DIC":
      tid_new=line[18:22]
      tdate_new=line[25:33]

    elif key=="ENDLIB    " and sec!="DIC":
      ok=1
      return ok, tid_new, tdate_new

    elif key=="MASTER    " and sec!="DIC":
      tid_new=line[18:22]
      tdate_new=line[25:33]

    elif key=="ENDMASTER " and sec!="DIC":
      ok=1
      return ok, tid_new, tdate_new

    elif key=="BACKUP    " and sec!="DIC":
      tid_new=line[18:22]
      tdate_new=line[25:33]

    elif key=="ENDBACKUP " and sec!="DIC":
      ok=1
      return ok, tid_new, tdate_new

    elif key=="ENTRY     " and sec!="DIC":
      sec="ENT"
      area=line[17:18].lower()
      dir_out=dir_storage+"/"+area 
      if not (os.path.isdir(dir_out)):
        os.mkdir(dir_out)

      an=line[17:22].lower()
      exfor_out=dir_out+"/"+an+".txt"
      f=open(exfor_out,'w')
      print("creating ... "+exfor_out)

      line=line[0:33]+"                      "+line[55:]
      f.write(line)

    elif key=="ENDENTRY  " and sec!="DIC":
      sec="   "
      f.write(line)
      f.close()

    elif key=="DICTION   ":
      sec="DIC"
      dir_out=dir_storage+"/9"
      if not (os.path.isdir(dir_out)):
        os.mkdir(dir_out)

      an=line[17:22].lower()
      exfor_out=dir_out+"/90001.txt"

      if line[32:33]=="1":
        f=open(exfor_out,'w')
        print("creating ... "+exfor_out)
      else:
        f=open(exfor_out,'a')

      line=line[0:33]+"                      "+line[55:]
      f.write(line)

    elif key=="ENDDICTION":
      sec="   "
      f.write(line)
      f.close()

    elif key=="SUBENT    " and sec!="DIC":
      line=line[0:33]+"                      "+line[55:]
      f.write(line)

    elif key=="NOSUBENT  " and sec!="DIC":
      line=line[0:33]+"                      "+line[55:]
      f.write(line)

    elif sec=="ENT" or sec=="DIC":
      f.write(line)

    else:
      msg="Unexpected line found."
      print_error_fatal(msg,line)

  msg="Unexpected last line found."
  print_error_fatal(msg,line)


def get_args(ver):
  parser=argparse.ArgumentParser(\
          usage="Initialize an EXFOR entry local storage",\
          epilog="example: x4_dirini.py -l library.txt -d entry")
  parser.add_argument("-v", "--version",\
         action="version", version=ver)
  parser.add_argument("-l", "--file_lib",\
   help="input library file")
  parser.add_argument("-d", "--dir_storage",\
   help="directory of output entry storage")
  parser.add_argument("-g", "--file_log",\
   help="output log file (optional, default: x4_dirupd.log)", default="x4_dirupd.log")
  parser.add_argument("-f", "--force",\
   help="never prompt", action="store_true")
  parser.add_argument("-c", "--cut66",\
   help="delete cols.67-80 and trailing blanks before col.67", action="store_true")

  args=parser.parse_args()
  return args


def get_input(args):
  time=datetime.datetime.now()
  date=time.strftime("%Y-%m-%d")
  print("DIRINI (Ver."+ver+") run on "+date)
  print("-----------------------------------------")

  force0=args.force
  cut660=args.cut66

  file_lib=args.file_lib
  if file_lib is None:
    file_lib=input("input library tape [library.txt] ----------> ")
    if file_lib=="":
      file_lib="library.txt"
  if not os.path.exists(file_lib):
    print(" ** File '"+file_lib+"' does not exist.")
  while not os.path.exists(file_lib):
    file_lib=input("input library tape [library.txt] ----------> ")
    if file_lib=="":
      file_lib="library.txt"
    if not os.path.exists(file_lib):
      print(" ** File '"+file_lib+"' does not exist.")

  dir_storage=args.dir_storage
  if dir_storage is None:
    dir_storage=input("directory of output entry storage [entry] -> ")
    if dir_storage=="":
      dir_storage="entry"

  if os.path.isdir(dir_storage):
    msg="Directory '"+dir_storage+"' exists and must be initialised."
    print_error(msg,"",force0)
  else:
    msg="Directory '"+dir_storage+"' does not exist and must be created."
    print_error(msg,"",force0)
    os.mkdir(dir_storage)

  file_log=args.file_log
  print("output log file ---------------------------> "+file_log)
  print("\n")
  if os.path.isfile(file_log):
    msg="File '"+file_log+"' exists and will be updated."
    print_error(msg,"",force0)

  return file_lib,dir_storage,file_log,force0,cut660


def update_log(file_log,tid_new,tdate_new,file_lib):
  if os.path.isfile(file_log):
    seq=-1
    with open(file_log) as f:
      for line in f:
        seq+=1
    seq_out='{:>4}'.format(seq)
    time=datetime.datetime.now()
    stamp=time.strftime("%Y-%m-%d %H:%M:%S.%f")
    line=seq_out+" "+stamp+" ----      --------          (Initialized)\n"  
    f=open(file_log,'a')
    f.write(line)
    seq+=1
  else:
    seq=0
    line="Seq. Update date/time           Trans(N1) Trans(N2)  Centre Tape\n"
    f=open(file_log,'w')
    f.write(line)
  time=datetime.datetime.now()
  stamp=time.strftime("%Y-%m-%d %H:%M:%S.%f")
  seq_out='{:>4}'.format(seq)
  line=seq_out+" "+stamp+" "+tid_new+"      "+tdate_new+"          "+file_lib+"\n"  
  f.write(line)
  f.close()


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


if __name__ == "__main__":
  dirini()
  exit()
