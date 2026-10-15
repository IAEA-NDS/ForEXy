#!/usr/bin/python3
ver="2026.10.14"
############################################################
# X4TOJ4 Ver.2026.10.14
# (Utility to convert EXFOR to JSON)
#
# Naohiko Otuka (IAEA Nuclear Data Section)
############################################################
import argparse
import datetime
import json
import os
import re
import time
from datetime import timezone

if os.path.isfile("x4_refbib.py"):
  import x4_refbib
else:
  from forexy import x4_refbib

def x4toj4():
  args=get_args(ver)
  main(*get_input(args))


def main(file_x4,file_dict,data_id,file_j4,key_keep,email0,force0,chkrid0,add190,keepflg0,outstr0):
  time_start=time.time()
  global x4_json
  global email
  global force
  global chkrid
  global add19
  global keepflg
  global outstr
  global dict_json

  email=email0
  force=force0
  chkrid=chkrid0
  add19=add190
  keepflg=keepflg0
  outstr=outstr0

  dict_json=read_dict(file_dict)

  time_now=datetime.datetime.now(timezone.utc)
  time_out=time_now.strftime("%Y-%m-%dT%H:%M:%S%z")

  x4_json=dict()
  if outstr:
    x4_json={
     "title"          : "J4 - EXFOR in JSON, number as string",
     "time_stamp"     : time_out
    }
  else:
    x4_json={
     "title"          : "J4 - EXFOR in JSON",
     "time_stamp"     : time_out
    }

  lines=get_file_lines(file_x4)

# Check if the first and last lines are legal (e.g., TRANS/ENDTRANS)
  check_first_last(lines)

# Analyze lines and convert to Python dictionary
  read_system_identifier(lines,key_keep,file_dict,data_id)

# Production of JSON output
  json_out=json.dumps(x4_json,indent=2)
  f=open(file_j4,"w")
  f.write(json_out)
  f.close()

  time_end=time.time()
  time_elapsed=format(time_end-time_start, ".2f")
  print("X4TOJ4: Processing terminated normally. "+time_elapsed+" sec.\n")


def read_dict(file_dict):
  f=open(file_dict)
  try:
    dict_json=json.load(f)
  except json.JSONDecodeError:
    msg=file_dict+" is not in JSON format."
    print_error_fatal(msg,"")

  if dict_json["title"]!="EXFOR/CINDA Dictionary in JSON":
    msg=file_dict+" is not an EXFOR/CINDA Dictionary in JSON."
    print_error_fatal(msg,"")

  return dict_json


def get_index(dict_id,code):
  if code=="":
    return -10

  primary_key=get_primary_key(dict_id)

  indexes=[dict_json[dict_id].index(x) for x in dict_json[dict_id]\
          if x[primary_key]==code]

  if len(indexes)==0:
    return -10
  else:
    return indexes[0]


def get_primary_key(dict_id):
  if dict_id=="001" or dict_id=="002" or\
     dict_id=="024" or dict_id=="025":
    primary_key="keyword"
  elif dict_id=="008":
    primary_key="atomic_number_of_element"
  elif dict_id=="950":
    primary_key="dictionary_identification_number"
  else:
    primary_key="code"

  return primary_key


def get_args(ver):

  parser=argparse.ArgumentParser(\
   usage="Convert EXFOR to JSON",\
   epilog="example: x4_x4toj4.py -i exfor.txt -o exfor.json -k all")
  parser.add_argument("-v", "--version",\
   action="version", version=ver)
  parser.add_argument("-i", "--file_x4",\
   help="input EXFOR file")
  parser.add_argument("-d", "--file_dict",\
   help="input JSON Dictionary (optional, default: dict.json)", default="dict.json")
  parser.add_argument("-e", "--data_id",\
   help="EXFOR Entry number ('all' to process all datasets in the EXFOR file)")
  parser.add_argument("-o", "--file_j4",\
   help="output J4 file")
  parser.add_argument("-k", "--key_keep",\
   help="keywords to be kept (optional, 'all' to process all keywords)", default=["all"], nargs="+")
  parser.add_argument("-m", "--email",\
   help="your email address (optional)", default=None)
  parser.add_argument("-f", "--force",\
   help="never prompt", action="store_true")
  parser.add_argument("-c", "--chkrid",\
   help="check record identification", action="store_true")
  parser.add_argument("-a", "--add19",\
   help="addition of '19' to two-digit year ", action="store_true")
  parser.add_argument("-g", "--keepflg",\
   help="keep flag at column 80 of each record of the DATA section", action="store_true")
  parser.add_argument("-s", "--outstr",\
   help="real number keep as string", action="store_true")

  args=parser.parse_args()
  return args


def get_input(args):
  time=datetime.datetime.now()
  date=time.strftime("%Y-%m-%d")
  print("X4TOJ4 (Ver."+ver+") run on "+date)
  print("-----------------------------------------")

  force0=args.force
  chkrid0=args.chkrid
  add190=args.add19
  keepflg0=args.keepflg
  outstr0=args.outstr

  file_x4=args.file_x4
  if file_x4 is None:
    file_x4=input("input EXFOR file [exfor.txt] -> ")
    if file_x4=="":
      file_x4="exfor.txt"
  if not os.path.exists(file_x4):
    print(" ** File "+file_x4+" does not exist.")
  while not os.path.exists(file_x4):
    file_x4=input("input EXFOR file [exfor.txt] -> ")
    if file_x4=="":
      file_x4="exfor.txt"
    if not os.path.exists(file_x4):
      print(" ** File "+file_x4+" does not exist.")

  file_dict=args.file_dict
  print("JSON Dictionary --------------> "+file_dict)
  if not os.path.exists(file_dict):
    print(" ** File "+file_dict+" does not exist.")
  while not os.path.exists(file_dict):
    file_dict=input("JSON Dictionary [dict.json] --> ")
    if file_dict=="":
      file_dict="dict.json"
    if not os.path.exists(file_dict):
      print(" ** File "+file_dict+" does not exist.")

  data_id=args.data_id
  if data_id is None:
    data_id=input("EXFOR Entry # [all] ---------> ")
    if data_id=="":
      data_id="all"
  if data_id!="all":
    data_id=data_id.upper()
  if not re.compile(r"^[1-9A-Z]\d{4}$").search(data_id) and data_id!="all":
    print(" ** EXFOR Entry # "+entry+" is illegal.")
  while not re.compile(r"^[1-9A-Z]\d{4}$").search(data_id) and data_id!="all":
    data_id=input("EXFOR Entry # [all] ---------> ")
    if data_id=="":
      data_id="all"
    elif data_id!="all":
      data_id=data_id.upper()
    if not re.compile(r"^[1-9A-Z]\d{4}$").search(data_id) and data_id!="all":
      print(" ** EXFOR Entry # "+data_id+" is illegal.")

  file_j4=args.file_j4
  if file_j4 is None:
    file_j4=input("output J4 file [exfor.json] --> ")
  if file_j4=="":
    file_j4="exfor.json"
  if os.path.isfile(file_j4):
    msg="File '"+file_j4+"' exists and must be overwritten."
    print_error(msg,"",force0)

  key_keep=args.key_keep
  print("input keywords to keep -------> ", end="")
  for char in key_keep:
    print(char+" ", end="")
  print("\n")

  email=args.email
  if email is not None:
    print("your email address -----------------------> "+email)
    if not re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$").search(email):
      print(" ** Input a correct email address.")
    while not re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$").search(email):
      email=input("your email address -----------------------> ")
      if not re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$").search(email):
        print(" ** Input a correct email address.")

  return file_x4,file_dict,data_id,file_j4,key_keep,email,force0,chkrid0,add190,keepflg0,outstr0


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

  return


def print_error_1(msg,line):
  print("**  "+msg)
  print(line)

  return


def print_error_2(ansan,keyword,msg,line):
  print("**  {:9s} {:<11s}{:<50s}".format(ansan,keyword,msg))
  print(line)

  return


def print_error_3(ansan,keyword,msg,line,col1,col2,offset):
  print("** "+ansan+": "+keyword+": "+msg)
  for i in range(offset):
    line=" "+line
  print(line.rstrip())
  col1=col1+offset
  col2=col2+offset
  print_underline(col1,col2)

  return


def print_error_fatal(msg,line):
  print("**  "+msg)
  print(line)
  exit()


def print_underline(col1,col2):
  char=" "*(col1-1)+"^"*(col2-col1+1)
  print(char)

  return


def get_file_lines(file):
  if os.path.exists(file):
    f=open(file, "r")
    lines=f.readlines()
    f.close()
  else:
    msg="File "+file+" does not exist."
    print_error_fatal(msg,"")
  return lines


def str2int(char,line):
  if re.compile(r"^\s*$").search(char):
    char=None
  else:
    try:
      int(char)
    except ValueError:
      msg="An integer is expected but illegal characters are found: "\
         +char
      print_error_1(msg,line)
      char="?"
    else:
      char=int(char)
  return char


def str2float(char,line):
  if not outstr:
    if re.compile(r"^\s*$").search(char):
      char=None
    else:
      char=re.sub(r"\s+","",char)
      char=re.sub(r"(\d|\.)(-|\+)","\\1E\\2",char)
      try:
        float(char)
      except ValueError:
        msg="A real number is expected but illegal characters are found: "\
           +char
        print_error_1(msg,line)
        char="?"
      else:
        char=float(char)
  return char


def str2nul(char,line):
  if char=="":
    char=None
  return char


def check_character(ansan,keyword,line):
  permitted_character_list=[
  "+", "-", ".", ")", "(", "*", "/", "=", "'", ",", "%", "<", ">", ":",
  ";", "!", "?", "&", "#", "[", "]", '"', "~", "@", "{", "}", "|", " "]

  chars=list(line.rstrip())
  for char in chars:
    if not re.compile("[a-zA-Z0-9]").search(char):
      if char not in permitted_character_list:
        msg="Illegal character: "+char
        col1=line.find(char)+1
        print_error_3(ansan,keyword,msg,line,col1,col1,0)

  return


def check_record_id(keyword,line,entry):
  length=len(line)
  if length>73:
    an=line[66:71].replace("0{1,4}$,","")
    san=line[71:74].replace("^0{1,2}","")
    ansan=an+"."+san
    san=int(san)
  else:
    ansan="     .   "
  if length<80:
    msg="Line length less than 80. Record identification check skipped"
    print_error_3(ansan,keyword,msg,line,length+1,80,0)
    return

  seq=int(line[74:79].replace("^0{1,4}",""))

  if an!=entry:
    if keyword=="TRANS" or keyword=="MASTER":
      if entry!="":
        if line[66:67]!=entry[0]:
          msg="Col.67 does not agree with the 1st character of Trans ID."
          print_error_3(ansan,keyword,msg,line,67,67,0)
        if line[67:79]!="000000000000":
          msg="Col.67-79 must be 000000000000 for the TRANS record."
          print_error_3(ansan,keyword,msg,line,68,79,0)

    elif keyword=="ENDTRANS" or keyword=="ENDMASTER" or\
         keyword=="ENDREQUEST":
      if an[1:5]!="9999":
        msg="Col.68-71 must be 9999 for "+keyword+" record."
        print_error_3(ansan,keyword,msg,line,68,71,0)
      elif san!=999:
        msg="Col.72-74 must be 999 for "+keyword+" record."
        print_error_3(ansan,keyword,msg,line,72,74,0)
      elif seq!=99999:
        msg="Col.75-79 must be 99999 for "+keyword+" record."
        print_error_3(ansan,keyword,msg,line,75,79,0)

    else:
      msg="Col.67-71 must be the entry #."
      print_error_3(ansan,keyword,msg,line,67,71,0)

  elif keyword=="ENTRY":
    if san!=0:
      msg="Col.72-74 must be 0 for ENTRY record."
      print_error_3(ansan,keyword,msg,line,72,74,0)
    elif seq!=1:
      msg="Col.75-79 must be 1 for ENTRY record."
      print_error_3(ansan,keyword,msg,line,75,79,0)

  elif keyword=="ENDENTRY":
    if san!=999:
      msg="Col.72-74 must be 999 for ENDENTRY record."
      print_error_3(ansan,keyword,msg,line,72,74,0)
    elif seq!=99999:
      msg="Col.75-79 must be 99999 for ENDENTRY record."
      print_error_3(ansan,keyword,msg,line,75,79,0)

  elif keyword=="ENDSUBENT":
    if seq!=99999:
      msg="Col.75-79 must be 99999 for ENDSUBENT record."
      print_error_3(ansan,keyword,msg,line,75,79,0)

  elif keyword=="NOSUBENT":
    if seq!=1:
      msg="Col.75-79 must be 1 for NOSUBENT record."
      print_error_3(ansan,keyword,msg,line,75,79,0)

  return


# Check the first and last line of the file
def check_first_last(lines):
  if re.compile("^ENTRY").search(lines[0]):
    if not re.compile("^ENDENTRY").search(lines[-1]):
      msg="Last line of the file must be ENDENTRY record."
      print_error_fatal(msg,lines[-1])
      time=datetime.datetime.now(timezone.utc)
      date_out=time.strftime("%Y%m%d")
      x4_json["TRANS"]={
        "N1": "0000",
        "N2": date_out
      }

  elif re.compile("^TRANS").search(lines[0]):
    if not re.compile("^ENDTRANS").search(lines[-1]):
      msg="Last line of the file must be ENDTRANS record."
      print_error_fatal(msg,lines[-1])
    else:
      date=str2int(lines[0][22:33].lstrip(),lines[0])
      date=check_date("00000.000","TRANS",date,lines[0])
      x4_json["TRANS"]={
        "N1": lines[0][11:22].lstrip(),
        "N2": date
      }

  elif re.compile("^MASTER").search(lines[0]):
    if not re.compile("^ENDMASTER").search(lines[-1]):
      msg="Last line of the file must be ENDMASTER record."
      print_error_fatal(msg,lines[-1])
    else:
      date=str2int(lines[0][22:33].lstrip(),lines[0])
      date=check_date("00000.000","MASTER",date,lines[0])
      x4_json["MASTER"]={
        "N1": lines[0][11:22].lstrip(),
        "N2": date
      }

  elif re.compile("^REQUEST").search(lines[0]):
    if not re.compile("^ENDREQUEST").search(lines[-1]):
      msg="Last line of the file must be ENDREQUEST record."
      print_error_fatal(msg,lines[-1])
    else:
      date=str2int(lines[0][22:33].lstrip(),lines[0])
      date=check_date("00000.000","REQUEST",date,lines[0])
      x4_json["REQUEST"]={
        "N1": lines[0][11:22].lstrip(),
        "N2": date
      }

  elif re.compile("^DICTION").search(lines[0]):
    msg="This tool does not support the EXFOR/CINDA dictionary."
    print_error_fatal(msg,lines[0])

  else:
    msg="First line of the file must be ENTRY, TRANS, MASTER, or REQUEST record."
    print_error_fatal(msg,lines[0])

  x4_json["entries"]=[]

  return


# Checking and extraction of system identifier lines
def read_system_identifier(lines,key_keep,file_dict,data_id):
  sys_id="ENDENTRY"
  entry="00000"
  ansan="00000.000"
  nentry=-1
  msg_last=""
  n_msg=0
  for line in lines:
    if re.compile(r"\S").search(line[0:10]): # first line of the keyword
      keyword=line[0:10].rstrip()

    if keyword=="DICTION":
      print(line[0:66])
      if sys_id!="ENDENTRY":
        msg="DICTION record is not expected but detected."
        print_error_fatal(msg,line)
      sys_id="DICTION"
      msg="This tool does not support the EXFOR/CINDA dictionary and skip its records."
      print_error_1(msg,line)


    elif keyword=="ENDDICTION":
      if sys_id!="DICTION":
        msg="ENDDICTION record is not expected but detected."
        print_error_fatal(msg,line)
      sys_id="ENDDICTION"


    elif sys_id=="DICTION": # processing of dictionaries skipped
      continue


    elif keyword=="TRANS" or keyword=="MASTER" or\
      keyword=="REQUEST":
      print(line[0:66])

      if keyword=="TRANS" or keyword=="MASTER":
        if not re.compile(r"^\s{7}[0-9A-Z]\d{3}").search(line[11:22]):
          msg="Illegal file identification #: "+line[11:22]
          print_error_3(ansan,keyword,msg,line,19,22,0)
 
      if chkrid:
        check_record_id(keyword,line,x4_json[keyword]["N1"])

    elif keyword=="ENDTRANS" or keyword=="ENDMASTER" or\
      keyword=="ENDREQUEST":

      if chkrid:
        check_record_id(keyword,line,"")

      x4_json[keyword]={
        "N1": str2int(line[11:22].lstrip(),line),
        "N2": 0
      }

    elif keyword=="ENTRY":
      if sys_id!="ENDENTRY" and sys_id!="ENDDICTION":
        msg="ENTRY record is not expected but detected."
        print_error_fatal(msg,line)
      if not re.compile(r"^\s{6}[0-9A-Z]\d{4}$").search(line[11:22]):
        msg="Illegal entry #: "+line[11:22]
        print_error_3(ansan,keyword,msg,line,11,22,0)
      elif line[17:22]<=entry:
        msg="Entry# not in ascending order: "+line[17:22]
        print_error_3(ansan,keyword,msg,line,17,22,0)

      entry=line[17:22]
      if data_id=="all" or data_id==entry:
        print_entry=True
      else:
        print_entry=False
        continue

      print(line[0:66])
      sys_id="ENTRY"
      nentry+=1
      subent="000"
      nsubent=-1

      ansan=entry+".000"
      x4_json["entries"].append(None)
      x4_json["entries"][nentry]=dict()

      date=str2int(line[22:33].lstrip(),line)
      date=check_date(ansan,keyword,date,line)

      alteration_flag=line[10:11]

      if re.compile(r"[0-9A-Z]\d{3}").search(line[62:66]):
        transmission_identification=line[62:66]
      else:
        transmission_identification=None

      x4_json["entries"][nentry]["ENTRY"]={
        "N1": entry,
        "N2": date,
        "alteration_flag": alteration_flag,
        "transmission_identification": transmission_identification
      }

      if chkrid:
        check_record_id(keyword,line,entry)
      x4_json["entries"][nentry]["subentries"]=[]

    elif keyword=="ENDENTRY":
      if print_entry==False:
        continue
      if sys_id!="ENDSUBENT" and sys_id!="NOSUBENT":
        msg="ENDENTRY record is not expected but detected."
        print_error_fatal(msg,line)

      sys_id="ENDENTRY"
      ansan=entry+".999"
      x4_json["entries"][nentry]["ENDENTRY"]={
        "N1": str2int(line[11:22].lstrip(),line),
        "N2": 0
      }
      if chkrid:
        check_record_id(keyword,line,entry)

    elif keyword=="SUBENT":
      if print_entry==False:
        continue
      if sys_id!="ENTRY" and sys_id!="ENDSUBENT" and sys_id!="NOSUBENT":
        msg="SUBENT record is not expected but detected."
        print_error_fatal(msg,line)

      sys_id="SUBENT"
      nsubent+=1
      if not re.compile(r"^\s{3}[0-9A-Z]\d{7}$").search(line[11:22]):
        msg="Illegal subentry#: "+line[11:22]
      elif line[14:19]!=entry:
        msg="Subentry# inconsistent with entry#: "+line[14:19]
        print_error_3(ansan,keyword,msg,line,14,19,0)
      elif line[14:22]<=subent:
        msg="Subentry# not in ascending order: "+line[14:22]
        print_error_3(ansan,keyword,msg,line,14,22,0)

      subent=line[14:22]
      ansan=line[14:19]+"."+line[19:22]
      x4_json["entries"][nentry]["subentries"].append(None)

      x4_json["entries"][nentry]["subentries"][nsubent]=dict()

      date=str2int(line[22:33].lstrip(),line)
      date=check_date(ansan,keyword,date,line)

      alteration_flag=line[10:11]

      if re.compile(r"[0-9A-Z]\d{3}").search(line[62:66]):
        transmission_identification=line[62:66]
      else:
        transmission_identification=None

      x4_json["entries"][nentry]["subentries"][nsubent]["SUBENT"]={
        "N1": subent,
        "N2": date,
        "alteration_flag": alteration_flag,
        "transmission_identification": transmission_identification
      }
      if chkrid:
        check_record_id(keyword,line,entry)

    elif keyword=="ENDSUBENT":
      if print_entry==False:
        continue
      if subent[5:8]=="001":
        if sys_id!="ENDCOMMON" and sys_id!="NOCOMMON":
          msg="ENDSUBENT record is not expected but detected."
          print_error_fatal(msg,line)
      else:
        if sys_id!="ENDDATA" and sys_id!="NODATA":
          msg="ENDSUBENT record is not expected but detected."
          print_error_fatal(msg,line)

      sys_id="ENDSUBENT"
      x4_json["entries"][nentry]["subentries"][nsubent]["ENDSUBENT"]={
        "N1": 0,
        "N2": 0
      }
      if chkrid:
        check_record_id(keyword,line,entry)

    elif keyword=="NOSUBENT":
      if print_entry==False:
        continue
      if sys_id!="ENDSUBENT" and sys_id!="NOSUBENT":
          msg="NOSUBENT record is not expected but detected."
          print_error_fatal(msg,line)

      sys_id="NOSUBENT"
      nsubent+=1
      if not re.compile(r"^\s{3}[0-9A-Z]\d{7}$").search(line[11:22]):
        msg="Illegal subentry#: "+line[11:22]
      subent=line[14:22]
      x4_json["entries"][nentry]["subentries"].append(None)

      x4_json["entries"][nentry]["subentries"][nsubent]=dict()

      if len(line)>32 and re.compile(r"\d{6,8}").search(line[22:33]):
        date=str2int(line[22:33].lstrip(),line)
        date=check_date(ansan,keyword,date,line)
      else:
        msg="The date field (N2) is empty."
        print_error_1(msg,line)
        date=None
        
      if re.compile(r"[0-9A-Z]\d{3}").search(line[62:66]):
        transmission_identification=line[62:66]
      else:
        transmission_identification=None

      x4_json["entries"][nentry]["subentries"][nsubent]["NOSUBENT"]={
        "N1": subent,
        "N2": date,
        "transmission_identification": transmission_identification
      }

      if chkrid:
        check_record_id(keyword,line,entry)

    elif keyword=="BIB":
      if print_entry==False:
        continue
      if sys_id!="SUBENT":
        msg="BIB record is not expected but detected."
        print_error_fatal(msg,line)

      sys_id="BIB"
      pointer=" "
      bib_text=dict()

      x4_json["entries"][nentry]["subentries"][nsubent]["BIB"]={
        "N1": str2int(line[11:22].lstrip(),line),
        "N2": 0
       }

    elif keyword=="ENDBIB":
      if print_entry==False:
        continue
      if sys_id!="BIB":
        msg="ENDBIB record is not expected but detected."
        print_error_fatal(msg,line)

      sys_id="ENDBIB"
      for keyword in bib_text:
        if key_keep!=["all"]:
          if keyword not in key_keep and keyword!="REACTION":
            continue
        x4_json["entries"][nentry]["subentries"][nsubent][keyword]=[]
        for pointer, record in bib_text[keyword].items():
          anal_bib_out=anal_bib(ansan,keyword,pointer,file_dict,record)
          for item in anal_bib_out:
            x4_json["entries"][nentry]["subentries"][nsubent][keyword].append(item)

      x4_json["entries"][nentry]["subentries"][nsubent]["ENDBIB"]={
        "N1": 0,
        "N2": 0
       }

    elif keyword=="NOBIB":
      if print_entry==False:
        continue
      if sys_id!="SUBENT":
        msg="NOBIB record is not expected but detected."
        print_error_fatal(msg,line)

      sys_id="NOBIB"

      x4_json["entries"][nentry]["subentries"][nsubent]["NOBIB"]={
        "N1": str2int(line[11:22].lstrip(),line),
        "N2": str2int(line[22:33].lstrip(),line)
       }

    elif keyword=="COMMON":
      if print_entry==False:
        continue
      if sys_id!="ENDBIB" and sys_id!="NOBIB":
        msg="COMMON record is not expected but detected."
        print_error_fatal(msg,line)

      sys_id="COMMON"

      x4_json["entries"][nentry]["subentries"][nsubent]["COMMON"]={
        "N1": str2int(line[11:22].lstrip(),line),
        "N2": 0
       }

    elif keyword=="ENDCOMMON":
      if print_entry==False:
        continue
      if sys_id!="COMMON":
        msg="ENDCOMMON record is not expected but detected."
        print_error_fatal(msg,line)

      sys_id="ENDCOMMON"

      x4_json["entries"][nentry]["subentries"][nsubent]["ENDCOMMON"]={
        "N1": 0,
        "N2": 0
       }

      del t_field, n_field

    elif keyword=="NOCOMMON":
      if print_entry==False:
        continue
      if sys_id!="ENDBIB":
        msg="NOCOMMON record is not expected but detected."
        print_error_fatal(msg,line)

      sys_id="NOCOMMON"

      x4_json["entries"][nentry]["subentries"][nsubent]["NOCOMMON"]={
        "N1": str2int(line[11:22].lstrip(),line),
        "N2": str2int(line[22:33].lstrip(),line)
       }

    elif keyword=="DATA" and sys_id!="DATA":
      if print_entry==False:
        continue
      if sys_id!="ENDCOMMON" and sys_id!="NOCOMMON":
        print(sys_id)
        msg="DATA record is not expected but detected."
        print_error_fatal(msg,line)

      sys_id="DATA"

      x4_json["entries"][nentry]["subentries"][nsubent]["DATA"]={
        "N1": str2int(line[11:22].lstrip(),line),
        "N2": str2int(line[22:33].lstrip(),line)
       }

    elif keyword=="ENDDATA":
      if print_entry==False:
        continue
      if sys_id!="DATA":
        msg="ENDDATA record is not expected but detected."
        print_error_fatal(msg,line)

      sys_id="ENDDATA"

      x4_json["entries"][nentry]["subentries"][nsubent]["ENDDATA"]={
        "N1": 0,
        "N2": 0
       }

      del t_field, n_field


    elif keyword=="NODATA":
      if print_entry==False:
        continue
      if sys_id!="ENDCOMMON" and sys_id!="NOCOMMON":
        msg="NODATA record is not expected but detected."
        print_error_fatal(msg,line)

      sys_id="NODATA"

      x4_json["entries"][nentry]["subentries"][nsubent]["NODATA"]={
        "N1": str2int(line[11:22].lstrip(),line),
        "N2": str2int(line[22:33].lstrip(),line)
       }

    elif sys_id=="BIB": # processing of BIB contents
      if print_entry==False:
        continue
      (pointer,keyword,bib_text)=read_bib(ansan,keyword,pointer,bib_text,line)

    elif sys_id=="COMMON" or sys_id=="DATA": # processing of COMMON/DATA contents
      if print_entry==False:
        continue
      if "n_field" not in locals():
        t_field="heading"
        n_field=0
        data_line=[]
        flag_line=[]

      (t_field,n_field,data_line,flag_line,msg_last,n_msg)=\
      read_table(ansan,keyword,line,nentry,nsubent,sys_id,t_field,n_field,data_line,flag_line,msg_last,n_msg)

    else:
      if print_entry==False:
        continue
      msg="Unexpected line."
      print_error_fatal(msg,line)

    check_character(ansan,keyword,line)

  return


# Extraction of bib section line (code+free text) for pointer/keyword
def read_bib(ansan,keyword,pointer,bib_text,line):
  if re.compile(r"\S").search(line[0:10]): # first line of the keyword
    bib_text[keyword]=dict()
    check_code_dict(ansan,keyword,"002",keyword,line[0:66])
    pointer=""
    if re.compile(r"\s").search(line[10:11]):
      bib_text[keyword][pointer]=[]

  if re.compile(r"\S").search(line[10:11]):
    pointer=line[10:11]
    if not pointer in bib_text[keyword]:
      bib_text[keyword][pointer]=dict()
    bib_text[keyword][pointer]=[]
    if not re.compile("[1-9A-Z]").search(pointer):
      msg="Character not permitted for pointer "+pointer
      print_error_3(ansan,keyword,msg,line,11,11,0)

  bib_text[keyword][pointer].append(line[11:66].rstrip())

  return pointer,keyword,bib_text


# Extraction of heading, unit and number of COMMON/DATA section
def read_table(ansan,keyword,line,nentry,nsubent,sys_id,t_field,n_field,data_line,flag_line,msg_last,n_msg):
  line=line.rstrip(os.linesep) 
  if len(line)>66:
    line_out=line[0:66]
  else:
    line_out=line
  if t_field=="value":
    flag_line.append(line[79:80])
  for i in range (6):
    col1=i*11
    col2=(i+1)*11
    if t_field=="heading":
      if n_field==0:
        x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["pointer"]=[]
        x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["heading"]=[]
        x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["unit"]=[]
        if sys_id=="DATA":
          x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["value"]=[]
          if keepflg:
            x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["flag"]=[]
      if re.compile(r"\S").search(line[col2-1:col2]):
        pointer=line[col2-1:col2]
      else:
        pointer=""
      
      x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["pointer"].append(pointer)
      content=line[col1:col2-1]
      content=content.rstrip()
      x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["heading"].append(content)
      check_code_dict(ansan,keyword,"024",content,line_out)
    elif t_field=="unit":
      content=line[col1:col2]
      content=content.rstrip()
      x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["unit"].append(content)
      check_code_dict(ansan,keyword,"025",content,line_out)
    elif t_field=="value":
      content=line[col1:col2]
      content=str2float(content,line)
      data_line.append(content)
    else:
      msg="Unexpected line."
      print_error_fatal(msg,line)

    n_field+=1
    if n_field==x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["N1"]: # end of one table line
      if t_field=="heading":
        t_field="unit"
      elif t_field=="unit":
        t_field="value"
      elif t_field=="value":
        if sys_id=="DATA":
          x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["value"].append(data_line)
          n_line=len(x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["value"])
          if n_line > x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["N2"]:
            msg="DATA N2 expects "+str(n_line)+" data lines but extra lines are found."
            if msg==msg_last:
              n_msg+=1
            if n_msg<11:
              print_error_3(ansan,keyword,msg,line,col2+1,66,0)
              if n_msg==10:
                msg="The same message has been repeated 10 times. Not printed anymore."
              else:
                msg_last=msg
              print_error_3(ansan,keyword,msg,line,col2+1,66,0)
          if keepflg:
            x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["flag"].append(flag_line)
        else:
          x4_json["entries"][nentry]["subentries"][nsubent][sys_id]["value"]=data_line

        data_line=[]
        flag_line=[]
          
      if re.compile(r"\S").search(line[col2:66]):
        msg="DATA N1 expects "+str(n_field)+" data fields but extra characters are found."
        if msg==msg_last:
          n_msg+=1
        if n_msg<5:
          if n_msg==4:
            msg+="\n (The same message has been repeated 5 times. Not printed again.)"
          else:
            msg_last=msg
          print_error_3(ansan,keyword,msg,line,col2+1,66,0)

      n_field=0

      break

  return t_field,n_field,data_line,flag_line,msg_last,n_msg


# Processing of bib section for each pointer/keyword
def anal_bib(ansan,keyword,pointer,file_dict,record):
  anal_bib_out=[]
  pointer_code_text=dict()
  nparen=0
  lines=[] # array keepng all lines containing the whole code string
  free_text=""
  for i, line in enumerate(record): # process for each line in EXFOR format
    if nparen==0 and line[0:1]=="(": # first line of code string
      lines.append(line)
      if pointer_code_text!={}:
        pointer_code_text["free_text"]=free_text
        anal_bib_out.append(pointer_code_text)
        pointer_code_text={}
      code_str=""
      nparen=0
      (code_str,text,nparen)=code_extraction(line,code_str,nparen)
      if nparen==0: # code string ends in one line
        pointer_code_text=anal_code(ansan,keyword,file_dict,line,lines,pointer,code_str)
        lines=[]
        free_text=[text]

    elif nparen>0:  # continuing code string lines
      lines.append(line)
      (code_str,text,nparen)=code_extraction(line,code_str,nparen)
      if nparen==0: # line with the end of code string
        pointer_code_text=anal_code(ansan,keyword,file_dict,line,lines,pointer,code_str)
        lines=[]
        free_text=[text]

    elif i==0: # free text without code (1st line of the keyword)
      pointer_code_text={}
      pointer_code_text["pointer"]=pointer
      pointer_code_text["coded_information"]=None
      free_text=[line]

    else:      # free text without code
      if len(free_text)==0: # first line of the free text
        pointer_code_text["coded_information"]=None
        free_text=[line]
      else:                       # continuation of an existing free text
        free_text.append(line)

  if nparen!=0:
    msg="End of code string not found"
    print_error_1(msg,line)

  if pointer_code_text!={}: # last set of code+free text
    pointer_code_text["free_text"]=free_text
    anal_bib_out.append(pointer_code_text)
    pointer_code_text={}

  return anal_bib_out


# Contruction of code arrays depending on the keyword
def anal_code(ansan,keyword,file_dict,line,lines,pointer,code_str):
  code_str=re.sub(r"\s+$","",code_str)
  codes=re.split(r"\s*,",code_str)
  code=dict()
  code["pointer"]=pointer


  if keyword=="ANG-SEC" or \
     keyword=="EN-SEC" or  \
     keyword=="MOM-SEC":
    heading=None
    particle=None

    if len(codes)!=2:
      msg="Too few or many comma separators: "+code_str
      col1=line.find(code_str)+1
      col2=col1+len(code_str)-1
      print_error_3(ansan,keyword,msg,line,col1,col2,11)

    else:
      heading=codes[0]
      check_code_dict(ansan,keyword,"024",heading,line)

      particle=codes[1]
      items=re.split(r"/|\+",particle)

      for item in items:
        (ind,dict_id)=check_code_dict(ansan,keyword,"033",item,line)
        if ind>=0:
          if dict_id=="033":
            if dict_json["033"][ind]["allowed_subfield_flag_1"]!="D":
              msg="Particle code not allowed under this keyword: "+item
              col1=line.find(item)+1
              col2=col1+len(item)-1
              print_error_3(ansan,keyword,msg,line,col1,col2,11)
          elif dict_id=="227":
            if dict_json["227"][ind]["use_flag"]=="Z":
              msg="Nuclide code not allowed under this keyword: "+item
              col1=line.find(item)+1
              col2=col1+len(item)-1
              print_error_3(ansan,keyword,msg,line,col1,col2,11)


    code["coded_information"]={
      "heading": heading,
      "particle": particle
    }


  elif keyword=="ASSUMED":
    heading=None
    reaction=None

    heading=codes[0]
    reaction=codes[1]

    check_code_dict(ansan,keyword,"024",heading,line)

    for index, item in enumerate(codes):
      if index>1:
        reaction=reaction+","+item
    
    code["coded_information"]={
      "heading": heading,
      "reaction": reaction
    }
    code=deepupdate(code,anal_reaction(ansan,keyword,code["coded_information"]["reaction"],line,lines))


  elif keyword=="DECAY-DATA":
    code.update(anal_decaydata(ansan,keyword,line,lines,codes))


  elif keyword=="DECAY-MON":
    code.update(anal_decaydata(ansan,keyword,line,lines,codes)) # addition of decay data part


  elif keyword=="ERR-ANALYS":
    heading=None
    minimum_value=None
    maximum_value=None
    correlation_property=None

    if len(codes)<1 or len(codes)>4:
      msg="Too few or many comma separators: "+code_str
      col1=line.find(code_str)+1
      col2=col1+len(code_str)-1
      print_error_3(ansan,keyword,msg,line,col1,col2,11)

    else:
      heading=codes[0]
      check_code_dict(ansan,keyword,"024",heading,line)

      if len(codes)>1:
        minimum_value=str2float(codes[1],"")
      if len(codes)>2:
        maximum_value=str2float(codes[2],"")
      if len(codes)>3:
        correlation_property=codes[3]

    code["coded_information"]={
      "heading": heading,
      "minimum_value": minimum_value,
      "maximum_value": maximum_value,
      "correlation_property": correlation_property
    }


  elif keyword=="FACILITY":
    facilities=[]
    facilities.append(codes[0])
    institute=None
    if len(codes)>1:
      ind=get_index("003",codes[1])
      if ind>=0:
        institute=codes[1]
      else:
        if len(codes)>1:
          for index, item in enumerate(codes):
            if index>0:
              facilities.append(item)

    for facility in facilities:
      check_code_dict(ansan,keyword,"018",facility,line)

    code["coded_information"]={
     "facility": facilities,
     "institute": institute
    }


  elif keyword=="HALF-LIFE":
    heading=None
    nuclide=None

    if len(codes)<2 or len(codes)>3:
      msg="Too few or many comma separators: "+code_str
      col1=line.find(code_str)+1
      col2=col1+len(code_str)-1
      print_error_3(ansan,keyword,msg,line,col1,col2,11)

    else:
      heading=codes[0]
      nuclide=codes[1]

      check_code_dict(ansan,keyword,"024",heading,line)

      (ind,dict_id)=check_code_dict(ansan,keyword,"227",nuclide,line)
      if ind>=0:
        if dict_json["227"][ind]["use_flag"]=="Z":
          msg="Nuclide code not allowed under this keyword: "+particle
          col1=line.find(particle)+1
          col2=col1+len(particle)-1
          print_error_3(ansan,keyword,msg,line,col1,col2,11)

    code["coded_information"]={
      "heading": heading,
      "nuclide": nuclide
    }


  elif keyword=="HISTORY":
    date=None
    history=None

    if len(codes)>1:
      msg="Too many comma separators: "+code_str
      col1=line.find(code_str)+1
      col2=col1+len(code_str)-1
      print_error_3(ansan,keyword,msg,line,col1,col2,11)

    else:
      date=re.sub("[A-Z]$","",codes[0])
      date=check_date(ansan,keyword,date,line)
      if re.compile("[A-Z]$").search(codes[0]):
        history=codes[0][-1]
        check_code_dict(ansan,keyword,"015",history,line)

    code["coded_information"]={
      "date": date,
      "history": history
    }



  elif keyword=="INC-SOURCE":
    incident_source=[]
    reaction=None
    target=None
    projectile=None
    process=None
    product=None

    if re.compile(r"^MPH=\(\d+\-[A-Z]+\-\d+\(.+?,.+?\)(\d+\-[A-Z]+\-\d+)?\)").search(code_str):
      m=re.compile(r"^MPH=\((\d+\-[A-Z]+\-\d+\(.+?,.+?\)(\d+\-[A-Z]+\-\d+)?)\)").search(code_str)
      reaction=m.group(1)
      codes=re.split(r",|\(|\)",reaction)
   
      incident_source=["MPH"]
      target=codes[0]
      projectile=codes[1]
      process=codes[2]
      product=codes[3]

      check_code_dict(ansan,keyword,"227",target,line)
      check_code_dict(ansan,keyword,"033",projectile,line)

      particles=re.split(r"\+",process)
      for particle in particles:
        particle=re.sub(r"^\d+", "", particle)
        check_code_dict(ansan,keyword,"030",particle,line)

      if product!="":
        check_code_dict(ansan,keyword,"227",product,line)

    else:
      for index, item in enumerate(codes):
        item=re.sub(r"^\s+", "", item)
        check_code_dict(ansan,keyword,"019",item,line)
        incident_source.append(item)

    if reaction is None:
      code["coded_information"]={
        "incident_source": incident_source,
        "reaction": None
      }
    else:
      code["coded_information"]={
        "incident_source": incident_source,
        "reaction": {
          "code": reaction,
          "field": {
            "target": target,
            "projectile": projectile,
            "process": process,
            "product": product
          }
        }
      }

  elif keyword=="LEVEL-PROP":
    code.update(anal_levelprop(ansan,keyword,line,codes,code_str))


  elif keyword=="MONITOR":
    heading=None
    reaction=None

    if re.compile(r"^\(MONIT.+?\)").search(code_str):
      char=re.search(r"^\(.+?\)",code_str).group()
      heading=char
      heading=re.sub(r"\(|\s*\)","",heading)
      check_code_dict(ansan,keyword,"024",heading,line)
      reaction=code_str.replace(char,"")
    else:
      reaction=code_str

    code["coded_information"]={
      "heading": heading,
      "reaction": reaction
    }
    code=deepupdate(code,anal_reaction(ansan,keyword,code["coded_information"]["reaction"],line,lines))


  elif keyword=="MONIT-REF":
    heading=None
    subentry_number=None
    author=None
    reference=None

    if len(codes)<5 or len(codes)>8:
      msg="Too few or many comma separators: "+code_str
      col1=line.find(code_str)+1
      col2=col1+len(code_str)-1
      print_error_3(ansan,keyword,msg,line,col1,col2,11)

    else:
      if re.compile(r"\S").search(codes[0]):
        if re.compile(r"^\(.+?\)").search(codes[0]):
          char=re.search(r"^\(.+?\)",codes[0]).group()
          heading=char
          heading=re.sub(r"\(|\)","",heading)
          subentry_number=codes[0].replace(char,"")
        else:
          subentry_number=codes[0]

      if re.compile(r"\S").search(codes[1]):
        author=codes[1]
      else:
        author=None
      for index, item in enumerate(codes):
        if index==2:
          reference=item
        elif index>2:
          reference=reference+","+item

    code["coded_information"]={
      "heading": heading,
      "subentry_number": subentry_number,
      "author": author
    }
    code=deepupdate(code,anal_reference(ansan,keyword,line,reference,file_dict))


  elif keyword=="RAD-DET":
    flag=None
    nuclide=None
    radiation_type=[]

    if re.compile(r"^\(.+?\)").search(codes[0]):
      char=re.search(r"^\(.+?\)",codes[0]).group()
      char=re.sub(r"\(|\)","",char)
      flag=str2float(char,"")
      nuclide=codes[0].replace("("+char+")","")
    else:
      nuclide=codes[0]

    for i, particle in enumerate(codes):
      if i!=0:    
        radiation_type.append(particle)
        (ind,dict_id)=check_code_dict(ansan,keyword,"033",particle,line)
        if ind>=0:
          if dict_json["033"][ind]["allowed_subfield_flag_1"]!="D":
            msg="Particle code not allowed under this keyword: "+particle
            col1=line.find(particle)+1
            col2=col1+len(particle)-1
            print_error_3(ansan,keyword,msg,line,col1,col2,11)


    code["coded_information"]={
      "flag": flag,
      "nuclide": nuclide,
      "radiation_type": radiation_type
    }


  elif keyword=="REFERENCE":
    code["coded_information"]=code_str
    code.update(anal_reference(ansan,keyword,line,code["coded_information"],file_dict))


  elif keyword=="REACTION":
    code["coded_information"]=code_str
    code.update(anal_reaction(ansan,keyword,code["coded_information"],line,lines))


  elif keyword=="REL-REF":
    related_reference_type=codes[0]
    if re.compile(r"\S").search(codes[1]):
      subentry_number=codes[1]
    else:
      subentry_number=None

    if re.compile(r"\S").search(codes[2]):
      author=codes[2]
    else:
      author=None

    for index, item in enumerate(codes):
      if index==3:
        reference=item
      elif index>3:
        reference=reference+","+item

    code["coded_information"]={
      "code": related_reference_type,
      "subentry_number": subentry_number,
      "author": author
    }
    code=deepupdate(code,anal_reference(ansan,keyword,line,reference,file_dict))


  elif keyword=="SAMPLE":
    nuclide=None
    abundance_identifier=None
    abundance_value=None
    
    if len(codes)!=2:
      msg="Too few or many comma separators: "+code_str
      col1=line.find(code_str)+1
      col2=col1+len(code_str)-1
      print_error_3(ansan,keyword,msg,line,col1,col2,11)

    else:
      nuclide=codes[0]
      arr=codes[1].split("=")
      if len(arr)!=2:
        msg="Too few or many equal separators: "+code_str
        col1=line.find(codes[1])+1
        col2=col1+len(codes[1])-1
        print_error_3(ansan,keyword,msg,line,col1,col2,11)

      else:
        if arr[0]!="NAT" and arr[0]!="ENR":
          col1=line.find(abundance_identifier)+1
          col2=col1+len(abundance_identifier)-1
          msg="Unknown abundance identifier: "+abundance_identifier
          print_error_3(ansan,keyword,msg,line,col1,col2,11)
       
        abundance_identifier=arr[0]
        abundance_value=str2float(arr[1],"")

    code["coded_information"]={
      "nuclide": nuclide,
      "field_identifier": abundance_identifier,
      "value": abundance_value
    }


  elif keyword=="STATUS":
    status=[]
    status.append(codes[0])
    subentry_number=None
    author=None
    reference=None
    if len(codes)>1:
      ind=get_index("016",codes[1])
      if ind>=0: # status code in 2nd field
        for index, item in enumerate(codes):
          if index>0:
            status.append(item)
      else:
        if re.compile(r"\S").search(codes[1]): # SAN in 2nd field
          subentry_number=codes[1]
        else:
          if len(codes)>2: # author in 3rd field, reference in 4+ fields
            for index, item in enumerate(codes):
              if index==2:
                author=item
              elif index==3:
                reference=item
              elif index>3:
                reference=reference+","+item

    code["coded_information"]={
     "status": status,
     "subentry_number": subentry_number,
     "author": author
    }
    if reference==None:
      code["coded_information"]["reference"]=None
    else:
      code=deepupdate(code,anal_reference(ansan,keyword,line,reference,file_dict))


  else:
    code["coded_information"]=[]
    for index, item in enumerate(codes):
      item=re.sub(r"^\s+", "", item)

      if keyword=="ADD-RES":
        check_code_dict(ansan,keyword,"020",item,line)
      elif keyword=="ANALYSIS":
        check_code_dict(ansan,keyword,"023",item,line)
      elif keyword=="DETECTOR":
        check_code_dict(ansan,keyword,"022",item,line)
      elif keyword=="EXP-YEAR":
        if not re.compile(r"^(\d\d|\d\d\d\d)$").search(item):
          msg="Suspicious year under  EXP-YEAR: "+item
          col1=line.find(item)+1
          col2=col1+len(item)-1
          print_error_3(ansan,keyword,msg,line,col1,col2,11)
        item=str2int(item,"")
      elif keyword=="FLAG":
#       if not re.compile(r"^\d+\.0*$").search(item):
        if not re.compile(r"^\d+\.$").search(item):
          msg="Non-integer coded under FLAG: "+item
          col1=line.find(item)+1
          col2=col1+len(item)-1
          print_error_3(ansan,keyword,msg,line,col1,col2,11)
        item=str2float(item,"")
      elif keyword=="INC-SPECT":
        check_code_dict(ansan,keyword,"024",item,line)
      elif keyword=="INSTITUTE":
        check_code_dict(ansan,keyword,"003",item,line)
      elif keyword=="METHOD":
        check_code_dict(ansan,keyword,"021",item,line)
      elif keyword=="MISC-COL":
        check_code_dict(ansan,keyword,"024",item,line)
      elif keyword=="PART-DET":
        particles=item.split("+")
        for particle in particles:
          check_code_dict(ansan,keyword,"033",particle,line)
      elif keyword=="RESULT":
        check_code_dict(ansan,keyword,"037",item,line)
      elif keyword=="SUPPL-INF":
        check_code_dict(ansan,keyword,"038",item,line)

      code["coded_information"].append(item)

  return code


# Processing of DECAY-DATA code string
def anal_decaydata(ansan,keyword,line,lines,codes):

  code=dict()
  radiations=[]
  radiation=dict()

  if re.compile(r"^\(.+?\)").search(codes[0]):
    char=re.search(r"^\(.+?\)",codes[0]).group()
    char=re.sub(r"\(|\)","",char)
    if keyword=="DECAY-DATA":
#     if not re.compile(r"^\d+\.0*$").search(char):
      if not re.compile(r"^\d+\.$").search(char):
        msg="Non-integer flag coded under DECAY-DATA: "+char
        col1=line.find(char)+1
        col2=col1+len(char)-1
        print_error_3(ansan,keyword,msg,line,col1,col2,11)
      flag=str2float(char,"")
    elif keyword=="DECAY-MON":
      heading=char
      check_code_dict(ansan,keyword,"024",heading,line)
    nuclide=codes[0].replace("("+char+")","")
  else:
    if keyword=="DECAY-DATA":
      flag=None
    elif keyword=="DECAY-MON":
      heading=None

    nuclide=codes[0]

  check_code_dict(ansan,keyword,"227",nuclide,line)

  halflife_value=None
  halflife_unit=None
  radiation=None   

  regex = r"[-+]?[0-9]*\.?[0-9]*([eE]?[-+]?[0-9]+)?"
  if len(codes)>1: # half-life field exist
    if re.compile(r"\S").search(codes[1]):
      char=re.search(regex,codes[1]).group()
      halflife_value=str2float(char,"")
      halflife_unit=codes[1].replace(char,"")

  if len(codes)>2: # radiation fields exist
    for i in range(len(codes)//3):
      j=2+3*i # radiation type
      k=j+1   # energy
      l=j+2   # intensity
      radiation={}
      codes[j]=codes[j].lstrip()

      items=codes[j].split("/")
      radiation["radiation_type"]=items
      for item in items:
        for char in lines:
          if re.compile(item).search(char):
            break

        (ind,dict_id)=check_code_dict(ansan,keyword,"033",item,char)

        if ind>=0:
          if dict_json["033"][ind]["allowed_subfield_flag_1"]!="D":
            msg="Particle code not allowed under this keyword: "+item
            col1=char.find(item)+1
            col2=col1+len(item)-1
            print_error_3(ansan,keyword,msg,char,col1,col2,11)

      if len(codes)==j+1: # energy field absent
        radiation["energy"]=None
      else:
        if re.compile(r"\S").search(codes[k]):
          energies=codes[k].split("/")
          radiation["energy"]=[]
          for energy in energies:
            radiation["energy"].append(str2float(energy,line))
        else:          # energy field empty
          radiation["energy"]=None
      if len(codes)<l+1: # intensity field absent
        radiation["intensity"]=None
      else:
        if re.compile(r"\S").search(codes[l]):
          radiation["intensity"]=str2float(codes[l],line)
        else: # intensity field empty
          radiation["intensity"]=None
      radiations.append(radiation)

  if halflife_value is None:
    if keyword=="DECAY-DATA":
      code["coded_information"]={
        "flag": flag,
        "nuclide": nuclide,
        "half-life": None,
        "radiation": radiations
      }
    elif keyword=="DECAY-MON":
      code["coded_information"]={
        "heading": heading,
        "nuclide": nuclide,
        "half-life": None,
        "radiation": radiations
      }
  else:
    if keyword=="DECAY-DATA":
      code["coded_information"]={
        "flag": flag,
        "nuclide": nuclide,
        "half-life":{
          "value": halflife_value,
          "unit": halflife_unit
        },
        "radiation": radiations
      }
    elif keyword=="DECAY-MON":
      code["coded_information"]={
        "heading": heading,
        "nuclide": nuclide,
        "half-life":{
          "value": halflife_value,
          "unit": halflife_unit
        },
        "radiation": radiations
      }

  return code


# Processing of LEVEL-PROP code string
def anal_levelprop(ansan,keyword,line,codes,code_str):

  flag=None
  nuclide=None
  level_identification_field_identifier=None
  level_identification_value=None
  level_properties=[]

  if len(codes)<2 or len(codes)>4:
    msg="Too few or many comma separators: "+code_str
    col1=line.find(code_str)+1
    col2=col1+len(code_str)-1
    print_error_3(ansan,keyword,msg,line,col1,col2,11)

  else:
    code=dict()
    if re.compile(r"^\(.+?\)").search(codes[0]):
      char=re.search(r"^\(.+?\)",codes[0]).group()
      flag=re.sub(r"\(|\)","",char)
#     if not re.compile(r"^\d+\.0*$").search(flag):
      if not re.compile(r"^\d+\.$").search(flag):
        msg="Non-integer flag coded under LEVEL-PROP: "+flag
        col1=line.find(flag)+1
        col2=col1+len(flag)-1
        print_error_3(ansan,keyword,msg,line,col1,col2,11)
      flag=str2float(flag,line)
      nuclide=codes[0].replace(char,"")
    else:
      nuclide=codes[0]

    check_code_dict(ansan,keyword,"227",nuclide,line)
   
    for i, item in enumerate(codes):
      if i>0:
        if re.compile(r"^E-LVL\d?=|^E-EXC\d?=|^LVL-NUMB=|^IAS-NUMB=").search(item):
          arr=item.split("=")
          level_identification_field_identifier=arr[0]
          level_identification_value=str2float(arr[1],line)

        elif re.compile("^SPIN=").search(item):
          level_property={}
          arr=item.split("=")
          level_property["field_identifier"]="SPIN"
          spins=arr[1].split("/")
          level_property["value"]=[]
          for spin in spins:
            level_property["value"].append(str2float(spin,line))
          level_properties.append(level_property)

        elif re.compile("^PARITY=").search(item):
          level_property={}
          arr=item.split("=")
          level_property["field_identifier"]="PARITY"
          parities=arr[1].split("/")
          if len([parities])>1:
            msg="Illegal use of slash separater for parity: "+item
            col1=line.find(item)+1
            col2=col1+len(item)-1
            print_error_3(ansan,keyword,msg,line,col1,col2,11)

          level_property["value"]=[]
          for parity in parities:
            level_property["value"].append(str2float(parity,line))
          level_properties.append(level_property)

        else:
          msg="Unknown level identification/property field format: "+item
          col1=line.find(item)+1
          col2=col1+len(item)-1
          print_error_3(ansan,keyword,msg,line,col1,col2,11)

  if level_identification_field_identifier is None:
    code={
      "coded_information":{
        "flag": flag,
        "nuclide": nuclide,
        "level_identification": None,
        "level_properties": level_properties
      }
    }
  else:
    code={
      "coded_information":{
        "flag": flag,
        "nuclide": nuclide,
        "level_identification":{
          "field_identifier": level_identification_field_identifier,
          "value":            level_identification_value
        },
        "level_properties": level_properties
      }
    }

  return code


# Decomposition of arithmetic combination of code string to units
def decompose_unit_combination(code_str):
  units=[]
  unit_combination=""
  code_str="("+code_str+")"
  arr=list(code_str)
  nparen=0 # counter for all parentheses
  mparen=0 # counter for parenthesis inside of each unit
  for char in arr:
    if char=="(":
      nparen+=1
    elif char==")":
      nparen-=1

    if mparen==0: # outside a unit
      if re.compile(r"\w").search(char): # first character of the unit
        mparen=1
        unit=char
        unit_combination+="%"
      else:
        unit_combination+=char
    elif mparen==1 and char==")":
      mparen=0
      unit_combination+=")"
      units.append(unit)
    else:
      if char=="(":
        mparen+=1
      elif char==")":
        mparen-=1
      unit+=char

  return units,unit_combination


def anal_reaction(ansan,keyword,code_str,line,lines):
  code=dict()
  code_unit=[]
  (units,unit_combination)=decompose_unit_combination(code_str)

  for unit in units:
    codes=unit.split(",")

    genq=None
    data_type=None

    if len(codes)<4 or len(codes)>7:
      msg="Too few or many comma separators: "+code_str
      col1=line.find(code_str)+1
      col2=col1+len(code_str)-1
      print_error_3(ansan,keyword,msg,line,col1,col2,11)

    else:
      for index, item in enumerate(codes):
        if index==0:   # target(projectile
          reaction=item
          arr=item.split("(")

          target=arr[0]
          for char in lines:
            if re.compile(target).search(char):
              break
          check_code_dict(ansan,keyword,"227",target,char)

          projectile=arr[1]
          for char in lines:
            if re.compile(projectile).search(char):
              break
          check_code_dict(ansan,keyword,"033",projectile,char)

        elif index==1: # outgoing)product
          reaction=reaction+","+item
          arr=item.split(")")
          process=arr[0]
          particles=re.split(r"\+",process)
          for particle in particles:
            if re.compile(r"\d+[A-Z]").search(particle):
              particle=re.sub(r"^\d+", "", particle)
            for char in lines:
              if re.compile(particle).search(char):
                break
            check_code_dict(ansan,keyword,"030",particle,char)

          product=arr[1]
          if product!="" and product!="ELEM" and\
             product!="MASS" and product!="ELEM/MASS" and\
             product!="NPART":
            nucls=[]  
            arr=product.split("-")
            if len(arr)==3:
              nucls.append(product)
            elif len(arr)==4:
              base=arr[0]+"-"+arr[1]+"-"+arr[2]
              isoflags=re.split(r"\+|\/",arr[3])
              for isoflag in isoflags:
                if isoflag=="T":
                  nucl=base
                else:
                  nucl=base+"-"+isoflag
                nucls.append(nucl)
            else:
              msg="Unexpected REACTION SF4: "+product
              col1=line.find(product)+1
              col2=col1+len(product)-1
              print_error_3(ansan,keyword,msg,line,col1,col2,11)
         
            if len(nucls)>0:
              if not re.compile("L").search(item): # skip if quasi-isomer is seen
                for nucl in nucls:
                  for char in lines:
                    if re.compile(product).search(char):
                      break
                  check_code_dict_product(ansan,keyword,nucl,product,char)

        elif index==2: # branch
          quantity=item

        elif index<5:  # paramter,particle considered,modifier
          quantity=quantity+","+item

        elif index==5:
          if re.compile(r"\S").search(item):
            arr=item.split("/")
            modifier=None
            for item in arr:
              for char in lines:
                if re.compile(item).search(char):
                  break
              (ind,dict_id)=check_code_dict(ansan,keyword,"034",item,char)
              if ind>=0:
                if dict_json["034"][ind]["general_quantity_modifier_flag"]!="":
                  if genq is None:
                    genq=item
                  else:
                    genq=genq+"/"+item
                else:
                  if modifier is None:
                    modifier=item
                  else:
                    modifier=modifier+"/"+item
            if modifier!=None:
              quantity=quantity+","+modifier
     
        elif index==6:
          data_type=item
          for char in lines:
            if re.compile(data_type).search(char):
              break
          check_code_dict(ansan,keyword,"035",data_type,char)
     
      quantity=quantity.rstrip(",")
      quantity_236=check_code_dict_quantity(ansan,keyword,quantity,line)


    code_unit.append({
      "unit": unit,
      "field":{
        "reaction": reaction,
        "target": target,
        "projectile": projectile,
        "process": process,
        "product": product,
        "quantity": quantity,
        "data_type": data_type,
        "general_quantity_modifier": genq,
        "quantity_236": quantity_236
      }
    })

    if keyword=="ASSUMED" or keyword=="MONITOR":
      code={
        "coded_information":{
          "reaction":{
            "code": code_str,
            "code_unit":code_unit,
            "unit_combination": unit_combination
          }
        }
      }
    elif keyword=="REACTION":
      code={
        "coded_information":{
          "code": code_str,
          "code_unit":code_unit,
          "unit_combination": unit_combination
         }
       }

  return code


def anal_reference(ansan,keyword,line,code_str,file_dict):
  record=dict()
  code_unit=[]
  (units,unit_combination)=decompose_unit_combination(code_str)

  for unit in units:
    if keyword=="REFERENCE":
      if email is None:
        doi=None
      else:
        fauthor=""
        file_tmp="x4_refbib_out.txt"
        form="doi"
        strip=False
        x4_refbib.main(unit,fauthor,file_dict,file_tmp,form,email,force,strip)
        g=open(file_tmp)
        lines=g.readlines()
        g.close()
        if lines[0][0:2]=="**":
          doi=None
        else:
          doi=lines[0]
        print(unit,doi)
        os.remove(file_tmp)
      
    codes=unit.split(",")

    code=None
    number=None
    volume=None
    part=None
    issue=None
    page=None
    version=None
    material_number=None

    reference_type=codes[0]
    check_code_dict(ansan,keyword,"004",reference_type,line)
      
    date=codes[-1]
    date=check_date(ansan,keyword,date,line)

    if reference_type=="A" or reference_type=="B" or \
       reference_type=="C":

      code=codes[1]
      if reference_type=="A" or reference_type=="C": 
        check_code_dict(ansan,keyword,"007",code,line)
      elif reference_type=="B":
        check_code_dict(ansan,keyword,"207",code,line)

      if len(codes)!=5 and len(codes)!=6:
        msg="Too few or many comma separators: "+unit
        col1=line.find(unit)+1
        col2=col1+len(unit)-1
        print_error_3(ansan,keyword,msg,line,col1,col2,11)

      else:
        if len(codes[2])!=0:
          volume=codes[2]
        if len(codes)==5:
          page=codes[3]
        elif len(codes)==6:
          part=codes[3]
          re.sub(r"^\(|\)$", "", part)
          page=codes[4]

    elif reference_type=="J" or reference_type=="K":
      code=codes[1]
      check_code_dict(ansan,keyword,"005",code,line)

      if len(codes)!=5 and len(codes)!=6:
        msg="Too few or many comma separators: "+unit
        col1=line.find(unit)+1
        col2=col1+len(unit)-1
        print_error_3(ansan,keyword,msg,line,col1,col2,11)

      else:
        volume=codes[2]
        if len(codes)==5:
          page=codes[3]
        elif len(codes)==6:
          issue=codes[3]
          if re.search(r"^\(.+?\)$",issue): # issue must be parenthesized
            issue=re.sub(r"^\(|\)$", "", issue)
          else:
            msg="Issue number must be parenthesized: "+issue
            col1=line.find(issue)+1
            col2=col1+len(issue)-1
            print_error_3(ansan,keyword,msg,line,col1,col2,11)

          page=codes[4]

    elif reference_type=="P" or reference_type=="R" or \
         reference_type=="S" or reference_type=="X":
      code=re.search(r"^(.+?-)(\d|\()",codes[1]).group(1)
      check_code_dict(ansan,keyword,"006",code,line)

      if len(codes)!=3 and len(codes)!=4 and len(codes)!=5:
        msg="Too few or many comma separators: "+unit
        col1=line.find(unit)+1
        col2=col1+len(unit)-1
        print_error_3(ansan,keyword,msg,line,col1,col2,11)

      else:
        number=codes[1].replace(code,"")
        if len(codes)==4:
          if re.search(r"^\(.+?\)$",codes[2]): # assume volume rather than page if it is parenthesized
            volume=codes[2]
          else:  
            page=codes[2]
        elif len(codes)==5:
          volume=codes[2]
          page=codes[3]

    elif reference_type=="T" or reference_type=="W":
      if len(codes)!=3 and len(codes)!=4:
        msg="Too few or many comma separators: "+unit
        col1=line.find(unit)+1
        col2=col1+len(unit)-1
        print_error_3(ansan,keyword,msg,line,col1,col2,11)
 
      else:
        code=codes[1]
        if len(codes)==4:
          page=codes[2]

    elif reference_type=="3":
      if len(codes)!=4:
        msg="Too few or many comma separators: "+unit
        col1=line.find(unit)+1
        col2=col1+len(unit)-1
        print_error_3(ansan,keyword,msg,line,col1,col2,11)

      else:
        ind=get_index("144",codes[1])
        if ind>=0: # Library without hyphen
          code=codes[1]
        else:
          code=re.search("^(.+?-)",codes[1]).group(1)
          version=codes[1].replace(code,"")
          if code!="ENDF/B-":
            if not re.compile(r"(\d|\.)+").search(version):
              msg="Library version contains non-Arabic numeral: "+version
              col1=line.find(version)+1
              col2=col1+len(version)-1
              print_error_3(ansan,keyword,msg,line,col1,col2,11)

        check_code_dict(ansan,keyword,"144",code,line)
        if len(codes[2])!=0:
          material_number=codes[2]


    if keyword=="MONIT-REF":
      record={
        "coded_information":{
          "reference":{
            "code": code_str,
            "field":{
              "reference_type": reference_type,
              "reference":{
                "code": code,
                "number": number,
                "volume": volume,
                "part": part,
                "issue": issue,
                "page": page,
                "version": version,
                "material_number": material_number
              },
              "date": date
            },
          }
        }
      }

    elif keyword=="REL-REF" or keyword=="STATUS":
      record={
        "coded_information":{
          "reference":{
            "code": code_str,
            "field":{
              "reference_type": reference_type,
              "reference":{
                "code": code,
                "number": number,
                "volume": volume,
                "part": part,
                "issue": issue,
                "page": page
              },
              "date": date
            },
          }
        }
      }

    else:
      code_unit.append({
        "unit": unit,
        "doi":  doi,
        "field":{
          "reference_type": reference_type,
          "reference":{
            "code": code,
            "number": number,
            "volume": volume,
            "part": part,
            "issue": issue,
            "page": page,
          },
          "date": date
        }
      })

      record={
        "coded_information":{
          "code": code_str,
          "code_unit":code_unit,
          "unit_combination": unit_combination
         }
      }

  return record

def check_date(ansan,keyword,date,line):
  time=datetime.datetime.now(timezone.utc)
  year_now=time.year
  month_now=time.month
  day_now=time.day

  char=str(date)
  msg=""

  if len(char)==0:
    msg="Empty date field"
    print_error_1(msg,line)
    return

  if not re.compile("^(19|20)").search(char):
    year2d=True
    char_chk="19"+char
    if add19 and keyword!="HISTORY":
      char="19"+char
  else:
    year2d=False
    char_chk=char

  if keyword=="TRANS"   or keyword=="MASTER" or\
     keyword=="REQUEST" or keyword=="ENTRY" or\
     keyword=="SUBENT"  or keyword=="NOSUBENT":

   if len(char_chk)!=8:
     if year2d:
       msg="6 digits date are expected: "+str(date)
     else:
       msg="8 digits date are expected: "+str(date)

  else:
    if len(char_chk)!=4 and len(char_chk)!=6 and len(char_chk)!=8:
      if year2d:
        msg="2, 4 or 6 digits date are expected: "+str(date)
      else:
        msg="4, 6 or 8 digits date are expected: "+str(date)

  if msg=="":
    year=int(char_chk[0:4])
    if year<1932 and year>year_now:
      msg="Unexpected year in the date field: "+str(date)

    if len(char_chk)==6 or len(char_chk)==8:
      month=int(char_chk[4:6])
      if year==year_now and month>month_now:
        msg="Unexpected month in the date field: "+str(date)
      elif month>12:
        msg="Unexpected month in the date field: "+str(date)

    if len(char_chk)==8:
      date=int(char_chk[6:8])
      if year==year_now and month==month_now and date>day_now:
        msg="Unexpected day in the date field: "+str(date)
      elif date>31:
        msg="Unexpected day in the date field: "+str(date)

    if msg!="":
      col1=line.find(str(date))+1
      col2=col1+len(str(date))-1
      print_error_3(ansan,keyword,msg,line,col1,col2,0)

  char=int(char)
  return char


def check_code_dict(ansan,keyword,dict_id,code,line):

  status_expansion={
   "CIN": "CINDA",
   "EXT": "Extinct",
   "INT": "Internal",
   "OBS": "Obsolete",
   "PRE": "Preliminary",
   "PRO": "Proposed",
   "TRA": "Transmitted"
  }

  code_org=code

  if dict_id=="227":
    code=re.sub(r"-L\d?$","",code)

  ind=get_index(dict_id,code)

  if ind==-10:
    if dict_id=="030": # check if it is particle rather than process
      if keyword=="ASSUMED" or keyword=="INC-SOURCE" or\
         keyword=="MONITOR" or keyword=="REACTION":
        dict_id="033";
        ind=get_index(dict_id,code)

  if ind==-10:
    if dict_id=="033": # check if it is nuclide rather than particle
      if keyword=="ASSUMED" or keyword=="ANG-SEC" or\
         keyword=="EN-SEC" or keyword=="INC-SOURCE" or\
         keyword=="MOM-SEC" or keyword=="MONITOR" or \
         keyword=="PART-DET" or keyword=="REACTION":
        dict_id="227";
        code=re.sub(r"-L\d?$","",code)
        ind=get_index(dict_id,code)

  if ind==-10:
    if dict_id=="227":
      if re.compile(r"\d$").search(code): # check if it is an metastable state
        if keyword=="ASSUMED" or keyword=="ANG-SEC" or\
           keyword=="DECAY-DATA" or keyword=="DECAY-MON" or\
           keyword=="EN-SEC" or keyword=="INC-SOURCE" or\
           keyword=="LEVEL-PROP" or keyword=="MOM-SEC" or\
           keyword=="MONITOR" or keyword=="PART-DET" or\
           keyword=="REACTION":
          code=code+"-G"
          ind=get_index(dict_id,code)

  if ind==-10:
    if dict_id=="227": # check if it is chemical compound rather than nuclide
      if keyword=="ASSUMED" or keyword=="INC-SOURCE" or\
         keyword=="MONITOR" or keyword=="REACTION":
        dict_id="209"
        ind=get_index(dict_id,code_org)

  if ind==-10:
    if dict_id=="006":
      if re.compile(r"\-$").search(code): # check if it is a report defined without -
        code=re.sub(r"\-$","",code)
        ind=get_index(dict_id,code)

  msg=""

  if ind==-10:
    msg="Unknown code: "+code_org

  else: # check of the code is valid for transmission
    status=dict_json[dict_id][ind]["status_code"]
    if status!="TRA" and status!="EXT":
      msg=status_expansion[status]+" code in Dictionary "+dict_id

  if msg!="":
    col1=line.find(code_org)+1
    col2=col1+len(code_org)-1
    if dict_id=="002":
      print_error_3(ansan,keyword,msg,line,col1,col2,0)
    else:
      print_error_3(ansan,keyword,msg,line,col1,col2,11)

  return ind,dict_id
    

def check_code_dict_product(ansan,keyword,nucl,product,line):

  status_expansion={
   "CIN": "CINDA",
   "EXT": "Extinct",
   "INT": "Internal",
   "OBS": "Obsolete",
   "PRE": "Preliminary",
   "PRO": "Proposed",
   "TRA": "Transmitted"
  }

  dict_id="227"

  nucl_org=nucl
  nucl=re.sub(r"-L\d?$","",nucl)

  ind=get_index(dict_id,nucl)

  if ind==-10:
    if re.compile(r"\d$").search(nucl):
      nucl=nucl+"-G"
      ind=get_index(dict_id,nucl)

  if ind==-10:
    dict_id="209"
    ind=get_index(dict_id,nucl_org)

  if ind==-10:
    msg="Unknown code: "+nucl_org
    col1=line.find(product)+1
    col2=col1+len(product)-1
    print_error_3(ansan,keyword,msg,line,col1,col2,11)

  else: # check of the code is valid for transmission
    status=dict_json[dict_id][ind]["status_code"]
    if status!="TRA":
      msg=status_expansion[status]+" in Dictionary "+dict_id+": "+nucl

  return


def check_code_dict_quantity(ansan,keyword,quantity,line):

  status_expansion={
   "CIN": "CINDA",
   "EXT": "Extinct",
   "INT": "Internal",
   "OBS": "Obsolete",
   "PRE": "Preliminary",
   "PRO": "Proposed",
   "TRA": "Transmitted"
  }

  dict_id="236"

  quantity_org=quantity

  fields=quantity.split(",")

  ind=get_index(dict_id,quantity)

  if ind==-10 and len(fields)>2:
    if fields[2]!="": # particle considered exists

      particle_org=fields[2]

# replace all particle codes with *
      groups=particle_org.split("/")
      groups_new=[]
      for group in groups:
        particles=group.split("+")
        particles_new=[]
        for particle in particles:
          particle=re.sub(particle,"*",particle) 
          particles_new.append(particle)
        groups_new.append("+".join(particles_new))
      fields[2]="/".join(groups_new)
      quantity=",".join(fields)
      ind=get_index(dict_id,quantity)
   
# replace only HF/LF/FF with *F
      if ind==-10:
        groups==particle_org.split("/")
        groups_new=[]
        for group in groups:
          particles=group.split("+")
          particles_new=[]
          for particle in particles:
            if particle=="HF" or particle=="LF" or particle=="FF":
              particle=re.sub(particle,"*F",particle)
            particles_new.append(particle)
          groups_new.append("+".join(particles_new))
        fields[2]="/".join(groups_new)
        quantity=",".join(fields)
        ind=get_index(dict_id,quantity)

# replace particle other than HF/LF/FF with *
      if ind==-10:
        groups==particle_org.split("/")
        groups_new=[]
        for group in groups:
          particles=group.split("+")
          particles_new=[]
          for particle in particles:
            if particle!="HF" and particle!="LF" and particle!="FF":
              particle=re.sub(particle,"*",particle)
            particles_new.append(particle)
          groups_new.append("+".join(particles_new))
        fields[2]="/".join(groups_new)
        quantity=",".join(fields)
        ind=get_index(dict_id,quantity)

# replace particle codes with * or *F
      if ind==-10:
        groups==particle_org.split("/")
        groups_new=[]
        for group in groups:
          particles=group.split("+")
          particles_new=[]
          for particle in particles:
            if particle=="HF" or particle=="LF" or particle=="FF":
              particle=re.sub(particle,"*F",particle)
            else:
              particle=re.sub(particle,"*",particle)
            particles_new.append(particle)
          groups_new.append("+".join(particles_new))
        fields[2]="/".join(groups_new)
        quantity=",".join(fields)
        ind=get_index(dict_id,quantity)
   
  if ind==-10:
    msg="Unknown code: "+quantity_org
    col1=line.find(quantity_org)+1
    col2=col1+len(quantity_org)-1
    print_error_3(ansan,keyword,msg,line,col1,col2,11)
    quantity=None

  else: # check of the code is valid for transmission
    status=dict_json[dict_id][ind]["status_code"]
    if status!="TRA":
      msg=status_expansion[status]+" in Dictionary "+dict_id+": "+quantity
      col1=line.find(quantity_org)+1
      col2=col1+len(quantity_org)-1
      print_error_3(ansan,keyword,msg,line,col1,col2,11)

  return quantity

def code_extraction(content,code,nparen):
  chars=list(content)
  nchar=0
  text=""
  for char in chars:
    if char=="(":
      nparen+=1
    elif char==")":
      nparen-=1
    nchar+=1
    if nparen==0:
      code+=content[0:nchar]
      code=re.sub(r"^\(|\)$","",code,2)
      text+=content[nchar:]
      text=text.rstrip()
      return code, text, nparen

  code+=content.rstrip()
  return code, "", nparen


# an element present in dict_updating but absent in dict_updated is deleted if add_keys=False
def deepupdate(dict_updated, dict_updating, add_keys=True):
  dict_updated = dict_updated.copy()
  if not add_keys:
    dict_updating = {
      k: dict_updating[k]
      for k in set(dict_updated).intersection(set(dict_updating))
    }
  for k in dict_updating.keys():
    if (k in dict_updated and isinstance(dict_updated[k], dict)
          and isinstance(dict_updating[k], dict)):
      dict_updated[k] = deepupdate(dict_updated[k], dict_updating[k], add_keys=add_keys)

    else:
      dict_updated[k] = dict_updating[k]

  return dict_updated


if __name__ == "__main__":
  x4toj4()
  exit()
