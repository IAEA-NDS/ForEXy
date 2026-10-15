#!/usr/bin/python3
ver="2026.10.02"
############################################################
# X4VIEW Ver.2026.10.02
# (Utility to convert EXFOR to HTML)
#
# Naohiko Otuka (IAEA Nuclear Data Section)
############################################################
import argparse
import datetime
import glob
import os
import re
import time

if os.path.isfile("x4_seqadd.py"):
  import x4_seqadd
else:
  from forexy import x4_seqadd

if os.path.isfile("x4_x4toj4.py"):
  import x4_x4toj4
else:
  from forexy import x4_x4toj4

if os.path.isfile("x4_poipoi.py"):
  import x4_poipoi
else:
  from forexy import x4_poipoi

if os.path.isfile("x4_j4view.py"):
  import x4_j4view
else:
  from forexy import x4_j4view

def x4view():
  args=get_args(ver)
  main(*get_input(args))


def main(file_x4,file_dict,file_css,entry,file_html,email,force0,gothi0,unfor0,limit0):
  time_start=time.time()

  force=force0
  gothi=gothi0
  unfor=unfor0
  limit=limit0


  master   = False  # do not add 19 to two-digit year and do not alter N2 of END records
  deltid   = False  # delete the transmission ID in N6
  chkrid   = False  # record identificaiton not checked in X4TOJ4
  add19    = True   # add '19' to two-digit year
  keepflg  = False  # ignore flags at col.80 in X4TOJ4
  outstr   = True   # print real numbers as strings in X4TOJ4
  key_keep =["all"] # keep all keywords in X4TOJ4 and POIPOI
  delpoin  = False  # delete pointer in the output in POIPOI
  keep001  = True   # keep common subentry in POIPOI
  keepres  = True   # keep resonance parameter table in POIPOI

  time_now=datetime.datetime.now()
  dir_wrk = time_now.strftime('%Y%m%d%H%M%S%f')
  os.mkdir(dir_wrk)

# Process the EXFOR input file by SEQADD
  file_out =dir_wrk+"/exfor_ord.txt"
  x4_seqadd.main(file_x4,file_out,force,master,deltid)

# Conversion to J4 format by X4TOJ4
  file_js = "exfor.json"
  x4_x4toj4.main(file_out,file_dict,entry,file_js,key_keep,email,force,chkrid,add19,keepflg,outstr)

# Conversion to J4 format without pointer structure by POIPOI
  x4_poipoi.main(file_js,file_dict,"all",dir_wrk,key_keep,force,delpoin,keep001,keepres)

# Check presence of J4 files
  entry_lower=entry.lower()
  pattern=dir_wrk+"/"+entry_lower+".[0-9][0-9][0-9]*.json"
  all_files=glob.glob(pattern)
  files = [file for file in all_files if re.search(r"\d\d\d(\.[A-Z1-9])?", file)]
  if len(files)==0:
    os.remove(file_js)
    files=glob.glob("./"+dir_wrk+"/*")
    for file in files:
      os.remove(file)
    os.rmdir(dir_wrk)
    print_error_fatal("The input EXFOR file does not include EXFOR# "+entry+".", "")

  entry=entry.lower()

# Conversion to HTML format by J4VIEW
  x4_j4view.main(dir_wrk,file_dict,file_css,entry,file_html,force,gothi,unfor,limit)

  os.remove(file_js)
  files=glob.glob("./"+dir_wrk+"/*")
  for file in files:
    os.remove(file)
  os.rmdir(dir_wrk)

  time_end=time.time()
  time_elapsed=format(time_end-time_start, ".2f")
  print("X4VIEW: Processing terminated normally. "+time_elapsed+" sec.\n")


def get_args(ver):
  parser=argparse.ArgumentParser(\
   usage="Convert EXFOR file to HTML file",\
   epilog="example: x4_x4view.py -i exfor.txt -e 22742 -o exfor.html")
  parser.add_argument("-v", "--version",\
   action="version", version=ver)
  parser.add_argument("-i", "--file_x4",\
   help="input EXFOR file")
  parser.add_argument("-d", "--file_dict",\
   help="input JSON dictionary (optional, default: dict.json)", default="dict.json")
  parser.add_argument("-c", "--file_css",\
   help="input CSS file (optional, defailt: exfor.css)", default="exfor.css")
  parser.add_argument("-e", "--entry",\
   help="EXFOR Entry number")
  parser.add_argument("-o", "--file_html",\
   help="output HTML file")
  parser.add_argument("-l", "--limit",\
   help="number of data lines to print (optional, print all lines if negative)", default="-1")
  parser.add_argument("-m", "--email",\
   help="your email address for addition of DOI (optional)", default=None)
  parser.add_argument("-f", "--force",\
   help="never prompt", action="store_true")
  parser.add_argument("-g", "--gothi",\
   help="use sans-serif (gothic) font", action="store_true")
  parser.add_argument("-s", "--unfor",\
   help="output with unformatted free text", action="store_true")

  args=parser.parse_args()
  return args


def get_input(args):
  time=datetime.datetime.now()
  date=time.strftime("%Y-%m-%d")
  print("X4VIEW (Ver."+ver+") run on "+date)
  print("-----------------------------------------")

  force0=args.force
  gothi0=args.gothi
  unfor0=args.unfor
  limit0=args.limit

  try:
    int(limit0)
  except ValueError:
    limit0=-1
  else:
    limit0=int(limit0)
  if limit0<-1:
    limit0=-1

  file_x4=args.file_x4
  if file_x4 is None:
    file_x4=input("input EXFOR file [exfor.txt] ------> ")
    if file_x4=="":
      file_x4="exfor.txt"
  if not os.path.exists(file_x4):
    print(" ** File "+file_x4+" does not exist.")
  while not os.path.exists(file_x4):
    file_x4=input("input EXFOR file [exfor.txt] ------> ")
    if file_x4=="":
      file_x4="exfor.txt"
    if not os.path.exists(file_x4):
      print(" ** File "+file_x4+" does not exist.")

  file_dict=args.file_dict
  print("JSON Dictionary -------------------> "+file_dict)
  if not os.path.exists(file_dict):
    print(" ** File "+file_dict+" does not exist.")
  while not os.path.exists(file_dict):
    file_dict=input("JSON DIctionary [dict.json] -------> ")
    if file_dict=="":
      file_dict="dict.json"
    if not os.path.exists(file_dict):
      print(" ** File "+file_dict+" does not exist.")

  file_css=args.file_css
  print("input CSS file --------------------> "+file_css)
  if not os.path.exists(file_css):
    print(" ** File "+file_css+" does not exist.")
  while not os.path.exists(file_css):
    file_css=input("input CSS file [exfor.css] --------> ")
    if file_css=="":
      file_css="exfor.css"
    if not os.path.exists(file_css):
      print(" ** File "+file_css+" does not exist.")

  entry=args.entry
  if entry is None:
    entry=input("EXFOR Entry # [22742] -------------> ")
    if entry=="":
      entry="22742"
  if not re.compile(r"^[1-9A-Za-z]\d{4}$").search(entry):
    print(" ** EXFOR Entry # "+entry+" is illegal.")
  while not re.compile(r"^[1-9A-Za-z]\d{4}$").search(entry):
    entry=input("EXFOR Entry # [22742] -------------> ")
    if entry=="":
      entry="22742"
    if not re.compile(r"^[1-9A-Za-z]\d{4}$").search(entry):
      print(" ** EXFOR Entry # "+entry+" is illegal.")

  file_html=args.file_html
  if file_html is None:
    file_html=input("output HTML file [exfor.html] -----> ")
  if file_html=="":
    file_html="exfor.html"
  if os.path.isfile(file_html):
    msg="File '"+file_html+"' exists and must be overwritten."
    print_error(msg,"",force0)

  email=args.email
  if email is not None:
    print("your email address --------------------> "+email)
    if not re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$").search(email):
      print(" ** Input a correct email address.")
    while not re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$").search(email):
      email=input("your email address --------------------> ")
      if not re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$").search(email):
        print(" ** Input a correct email address.")

  return file_x4,file_dict,file_css,entry,file_html,email,force0,gothi0,unfor0,limit0


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
  x4view()
  exit()
