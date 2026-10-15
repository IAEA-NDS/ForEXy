#!/usr/bin/python3
ver="2026.10.01"
############################################################
# POIPOI Ver.2026.10.01
# (Utility to remove pointer from EXFOR in JSON)
#
# Naohiko Otuka (IAEA Nuclear Data Section)
############################################################
import argparse
import copy
import datetime
import json
import os
import re
import time
from datetime import timezone

def poipoi():
  args=get_args(ver)
  main(*get_input(args))


def main(file_inp,file_dict,data_id,file_out,key_keep,force0,delpoin0,keep0010,keepres0):
  time_start=time.time()

  global keep001
  global keepres
  global x4_json
  global delpoin
  global dict_json

  force=force0
  delpoin=delpoin0
  keep001=keep0010
  keepres=keepres0

  x4_json_full=read_x4json(file_inp)
  dict_json=read_dict(file_dict)

  found=True
  if data_id=="all" or len(data_id)==5:
    dir_out=file_out
  else:
    found=False
    if len(data_id)==11:
      pointer=data_id[10:11]
    elif len(data_id)==9:
      pointer=""

  for nentry, entry in enumerate(x4_json_full["entries"]):
    x4_json=dict()
    x4_json=x4_json_full["entries"][nentry]
    title=x4_json_full["title"]
    for nsubent, subentry in enumerate(x4_json["subentries"]):
      if nsubent==0:
        continue

      if "SUBENT" in subentry:
  
        reaction_pointers=[]

        if "REACTION" in x4_json["subentries"][nsubent]:
          reaction0=x4_json["subentries"][nsubent]["REACTION"][0]
          quantity_236=reaction0["coded_information"]["code_unit"][0]["field"]["quantity_236"]

          if quantity_236 is None: # quantity code undefined in Dict.236
            quantity=reaction0["coded_information"]["code_unit"][0]["field"]["quantity"]
            msg="Quantity code absent in Dict.236 and cannot judge if it is a resonance parameter: "+quantity
            print_error_1(msg,"")
            respar=False
          else:
            l=[x["resonance_flag"] for x in dict_json["236"] if x["code"]==quantity_236]
            if len(l)==0: # Use an older JSON dict. without this quantity code?
              respar=False
            elif l[0]==".":
              respar=True
            else:
              respar=False

          for reaction in x4_json["subentries"][nsubent]["REACTION"]:
            reaction_pointers.append(reaction["pointer"])

        else: # SUPPL-INF
          reaction_pointers.append("")

        ansan=subentry["SUBENT"]["N1"]

        for reaction_pointer in reaction_pointers:
          if data_id=="all" or (len(data_id)==5 and ansan[0:5]==data_id[0:5]):
            if len(data_id)==5 and ansan[0:5]==data_id[0:5]:
              found=True
            if reaction_pointer=="":
              file_out=dir_out+"/"+ansan[0:5].lower()+"."+ansan[5:8]+".json"
              print("** POIPOI: Processing "+ansan[0:5]+"."+ansan[5:8])
            elif respar and keepres:
              file_out=dir_out+"/"+ansan[0:5].lower()+"."+ansan[5:8]+".json"
              print("** POIPOI: Processing "+ansan[0:5]+"."+ansan[5:8])
            else:
              file_out=dir_out+"/"+ansan[0:5].lower()+"."+ansan[5:8]+"."+reaction_pointer+".json"
              print("** POIPOI: Processing "+ansan[0:5]+"."+ansan[5:8]+"."+reaction_pointer)
            pointer_removal(title,nsubent,reaction_pointer,file_out,key_keep,respar)

          elif ansan[0:5]==data_id[0:5] and ansan[5:8]==data_id[6:9] and reaction_pointer==pointer:
            found=True
            print("** POIPOI: Processing "+data_id)
            pointer_removal(title,nsubent,pointer,file_out,key_keep,respar)

      else:
        respar=False
        ansan=subentry["NOSUBENT"]["N1"]
        if not keep001:
          if data_id=="all" or (len(data_id)==5 and ansan[0:5]==data_id[0:5]):
            if len(data_id)==5 and ansan[0:5]==data_id[0:5]:
              found=True
            file_out=dir_out+"/"+ansan[0:5].lower()+"."+ansan[5:8]+".json"
            print("** POIPOI: Processing "+ansan[0:5]+"."+ansan[5:8])
            pointer_removal(title,nsubent,"",file_out,key_keep,respar)
          elif ansan[0:5]==data_id[0:5] and ansan[5:8]==data_id[6:9]:
            found=True
            print("** POIPOI: Processing "+data_id)
            pointer_removal(title,nsubent,"",file_out,key_keep,respar)
        else:
          if data_id=="all" or (len(data_id)==5 and ansan[0:5]==data_id[0:5]):
            if len(data_id)==5 and ansan[0:5]==data_id[0:5]:
              found=True
            file_out=dir_out+"/"+ansan[0:5].lower()+"."+ansan[5:8]+".json"
            print("** POIPOI: Processing "+ansan[0:5]+"."+ansan[5:8])
            pointer_removal(title,nsubent,"",file_out,key_keep,respar)
          elif ansan[0:5]==data_id[0:5] and ansan[5:8]==data_id[6:9]:
            found=True
            print("** POIPOI: Processing "+data_id)
            pointer_removal(title,nsubent,"",file_out,key_keep,respar)

  if not found:
    msg="The dataset "+data_id+" does not exist in "+file_inp+"."
    print_error_fatal(msg,"")

  time_end=time.time()
  time_elapsed=format(time_end-time_start, ".2f")
  print("POIPOI: Processing terminated normally. "+time_elapsed+" sec.\n")


def pointer_removal(title,nsubent,pointer,file_out,key_keep,respar):

  if respar and keepres:
    if keep001:
      title+=" (resonance parameter)"
    else:
      title+=" without common subentry (resonance parameter)"
  else:
    if keep001:
      title+=" without pointer with common subentry"
    else:
      title+=" without pointer without common subentry"

  time=datetime.datetime.now(timezone.utc)
  time_out=time.strftime("%Y-%m-%dT%H:%M:%S%z")

  x4_json_poi=[]

# BIB section (001) of condensed JSON file when preservation of 001 choosen
  if keep001:
    nsubents=[0]

    x4_json_poi.append(None)
    x4_json_poi[0]=dict()
    x4_json_poi[0]["SUBENT"]={
      "N1": x4_json["subentries"][0]["SUBENT"]["N1"],
      "N2": x4_json["subentries"][0]["SUBENT"]["N2"],
      "alteration_flag": x4_json["subentries"][0]["SUBENT"]["alteration_flag"],
      "transmission_identification": x4_json["subentries"][0]["SUBENT"]["transmission_identification"]
    }
    bib_condensed=dict() 
    bib_condensed=condense_bib(nsubents,pointer,key_keep,keep001,respar,1)
    if len(bib_condensed)==0:
      x4_json_poi[0]["NOBIB"]={
        "N1": 0,
        "N2": 0
      }
    else:
      x4_json_poi[0]["BIB"]={
        "N1": len(bib_condensed),
        "N2": 0
      }
     
      x4_json_poi[0].update(bib_condensed)
     
      x4_json_poi[0]["ENDBIB"]={
        "N1": 0,
        "N2": 0
      }

# COMMON section (001) of condensed JSON file when preservation of 001 choosen
    common_condensed=dict()
    common_condensed=condense_common(nsubents,pointer,keep001,respar,1)
    if len(common_condensed["pointer"])==0:
      x4_json_poi[0]["NOCOMMON"]={
        "N1": 0,
        "N2": 0
      }
    else:
      x4_json_poi[0]["COMMON"]={
        "N1": len(common_condensed["pointer"]),
        "N2": 0
      }

      x4_json_poi[0]["COMMON"].update(common_condensed)

      x4_json_poi[0]["ENDCOMMON"]={
        "N1": 0,
        "N2": 0
      }
    x4_json_poi[0]["ENDSUBENT"]={
      "N1": 0,
      "N2": 0
    }

# END of output for 001 (common subentry)

  if keep001:
    nsubents=[nsubent,0]
    ind=1
  else:
    nsubents=[0,nsubent]
    ind=0

  x4_json_poi.append(None)

  x4_json_poi[ind]=dict()

  if "SUBENT" not in x4_json["subentries"][nsubent]: # NOSUBENT
    x4_json_poi[ind]["NOSUBENT"]={
      "N1": x4_json["subentries"][nsubent]["NOSUBENT"]["N1"],
      "N2": x4_json["subentries"][nsubent]["NOSUBENT"]["N2"],
      "transmission_identification": x4_json["subentries"][nsubent]["NOSUBENT"]["transmission_identification"]
    }

    x4_json_poi_out=dict()
    x4_json_poi_out={
     "title"              : title,
     "time_stamp"         : time_out,
     "entries":[
       {
         "ENTRY":{
           "N1": x4_json["ENTRY"]["N1"],
           "N2": x4_json["ENTRY"]["N2"],
           "alteration_flag": x4_json["ENTRY"]["alteration_flag"],
           "transmission_identification": x4_json["ENTRY"]["transmission_identification"]
         },
         "subentries":[
         ]
       }
     ]
    }
    x4_json_poi_out["entries"][0]["subentries"]=x4_json_poi

    x4_json_poi_out["entries"][0]["ENDENTRY"]={
      "N1": 2,
      "N2": 0
    }
    json_out=json.dumps(x4_json_poi_out,indent=2)
    f=open(file_out,"w")
    f.write(json_out)
    f.close()

    return

  else:
    if not delpoin:
      x4_json_poi[ind]["SUBENT"]={
        "N1": x4_json["subentries"][nsubent]["SUBENT"]["N1"],
        "N2": x4_json["subentries"][nsubent]["SUBENT"]["N2"],
        "alteration_flag": x4_json["subentries"][nsubent]["SUBENT"]["alteration_flag"],
        "transmission_identification": x4_json["subentries"][nsubent]["SUBENT"]["transmission_identification"]
      }
    else:
      ansan_out=x4_json["subentries"][0]["SUBENT"]["N1"][0:5]+"???"
      x4_json_poi[ind]["SUBENT"]={
        "N1": ansan_out,
        "N2": x4_json["subentries"][0]["SUBENT"]["N2"],
        "alteration_flag": x4_json["subentries"][0]["SUBENT"]["alteration_flag"],
        "transmission_identification": x4_json["subentries"][0]["SUBENT"]["transmission_identification"]
      }

# BIB section of condensed JSON file
  bib_condensed=dict()
  bib_condensed=condense_bib(nsubents,pointer,key_keep,keep001,respar,2)
  x4_json_poi[ind]=print_sysid_bib(x4_json_poi[ind],bib_condensed)

# COMMON section of condensed JSON file
  common_condensed=dict()
  common_condensed=condense_common(nsubents,pointer,keep001,respar,2)
  x4_json_poi[ind]=print_sysid_common(x4_json_poi[ind],common_condensed)

# DATA section of condensed JSON file
  data_condensed=dict()
  data_condensed=condense_data(nsubent,pointer,respar)
  x4_json_poi[ind]=print_sysid_data(x4_json_poi[ind],data_condensed) 

  x4_json_poi_out=dict()
  x4_json_poi_out={
   "title"              : title,
   "time_stamp"         : time_out,
   "entries":[
     {
       "ENTRY":{
         "N1": x4_json["ENTRY"]["N1"],
         "N2": x4_json["ENTRY"]["N2"],
         "alteration_flag": x4_json["ENTRY"]["alteration_flag"],
         "transmission_identification": x4_json["ENTRY"]["transmission_identification"]
       },
       "subentries":[
       ]
     }
   ]
  }
  x4_json_poi_out["entries"][0]["subentries"]=x4_json_poi

  if keep001:
    x4_json_poi_out["entries"][0]["ENDENTRY"]={
      "N1": 2,
      "N2": 0
    }
  else:
    x4_json_poi_out["entries"][0]["ENDENTRY"]={
      "N1": 1,
      "N2": 0
    }

  json_out=json.dumps(x4_json_poi_out,indent=2)
  f=open(file_out,"w")
  f.write(json_out)
  f.close()

  return


def condense_bib(nsubents,pointer,key_keep,keep001,respar,imod):

# pointers=["",pointer]
# pointers=list(dict.fromkeys(pointers)) # ["",""] -> [""]

  new=dict()
  identifiers=[] # list of all identifiers
  for nsubent in nsubents:
    identifiers.extend(list(x4_json["subentries"][nsubent].keys()))
  identifiers=list(dict.fromkeys(identifiers))

  keywords=[] # list of all keywords (i.e., w/o system identifier)
  for keyword in identifiers:
    if keyword in [x["keyword"] for x in dict_json["002"]]:
      keywords.append(keyword) 

  for keyword in keywords:
    if key_keep!=["all"]:
      if keyword not in key_keep and keyword!="REACTION":
        continue
    new[keyword]=[]
    for nsubent in nsubents:
      if keyword in x4_json["subentries"][nsubent]:

        x4_copy=copy.deepcopy(x4_json["subentries"][nsubent][keyword])

        if imod==1: # output common subent records without pointer to 001
          records=[x for x in x4_copy if x["pointer"]==""]

        else:       # output common subent records with/without pointer and data subent records
          if keep001 and nsubent==0:
            if pointer!="":
              if respar and keepres:
                records=[x for x in x4_copy if x["pointer"]!=""]
              else:
                records=[x for x in x4_copy if x["pointer"]==pointer]
            else:
              records=[]
          else:
            if respar and keepres:
              records=x4_copy
            else:
              records=[x for x in x4_copy if x["pointer"]=="" or x["pointer"]==pointer]

        for record in records:
          if not delpoin:
            pass
          elif respar and keepres:
            pass
          else:
            record["pointer"]=""

        new[keyword]+=records

  for keyword in list(new):
    if len(new[keyword])==0:
      new.pop(keyword) # remove keyword with empty array

  return new


def print_sysid_bib(x4_json_poi_ind,bib_condensed):

  if len(bib_condensed)==0:
    x4_json_poi_ind["NOBIB"]={
      "N1": 0,
      "N2": 0
    }
  else:
    x4_json_poi_ind["BIB"]={
      "N1": len(bib_condensed),
      "N2": 0
    }
   
    x4_json_poi_ind.update(bib_condensed)
   
    x4_json_poi_ind["ENDBIB"]={
      "N1": 0,
      "N2": 0
    }
  return x4_json_poi_ind


def condense_common(nsubents,pointer,keep001,respar,imod):

  new=dict()
  new["pointer"]=[]
  new["heading"]=[]
  new["unit"]=[]
  new["value"]=[]

  for nsubent in nsubents:
    if "COMMON" in x4_json["subentries"][nsubent]:
      pointers=x4_json["subentries"][nsubent]["COMMON"]["pointer"]

      for i, poi in enumerate(pointers):
        iout=0

        if imod==1: # output common subent records without pointer to 001
          if poi=="": 
            iout=1
        else:       # output common subent records with/without pointer and data subent records
          if keep001 and nsubent==0: # output common subent records with pointer
            if respar and keepres:
              if poi!="":
                iout=1
            else:
              if poi==pointer and poi!="":
                iout=1
          else:                            # output data subent records
            if respar and keepres:
              iout=1
            else:
              if poi=="" or poi==pointer:
                iout=1

        if iout==1:
          if not delpoin:
            new["pointer"].append(poi)
          elif respar and keepres:
            new["pointer"].append(poi)
          else:
            new["pointer"].append("")
          new["heading"].append(x4_json["subentries"][nsubent]["COMMON"]["heading"][i])
          new["unit"].append(x4_json["subentries"][nsubent]["COMMON"]["unit"][i])
          new["value"].append(x4_json["subentries"][nsubent]["COMMON"]["value"][i])

  return new


def print_sysid_common(x4_json_poi_ind,common_condensed):

  if len(common_condensed["pointer"])==0:
    x4_json_poi_ind["NOCOMMON"]={
      "N1": 0,
      "N2": 0
    }
  else:
    x4_json_poi_ind["COMMON"]={
      "N1": len(common_condensed["pointer"]),
      "N2": 0
    }

    x4_json_poi_ind["COMMON"].update(common_condensed)

    x4_json_poi_ind["ENDCOMMON"]={
      "N1": 0,
      "N2": 0
    }

  return x4_json_poi_ind


def condense_data(nsubent,pointer,respar):
  new=dict()

  new["pointer"]=[]
  new["heading"]=[]
  new["unit"]=[]
  new["value"]=[]

  if "DATA" in x4_json["subentries"][nsubent]:

    if "flag" in x4_json["subentries"][nsubent]["DATA"]:
      new["flag"]=[]

    pointers=x4_json["subentries"][nsubent]["DATA"]["pointer"]
    cols=[]

    for i, poi in enumerate(pointers):
      iout=0

      if respar and keepres:
        iout=1
      elif poi=="" or poi==pointer:
        iout=1

      if iout==1:
        if not delpoin:
          new["pointer"].append(poi)
        elif respar and keepres:
          new["pointer"].append(poi)
        else:
          new["pointer"].append("")
        new["heading"].append(x4_json["subentries"][nsubent]["DATA"]["heading"][i])
        new["unit"].append(x4_json["subentries"][nsubent]["DATA"]["unit"][i])
        cols.append(i)

    if "flag" in x4_json["subentries"][nsubent]["DATA"]:
      for i, (vals,flgs) in enumerate((zip(x4_json["subentries"][nsubent]["DATA"]["value"],\
                                           x4_json["subentries"][nsubent]["DATA"]["flag"]))):
        new["value"].append([])
        for j in cols:
          new["value"][i].append(vals[j])
        new["flag"].append(flgs)

    else:
      for i, vals in enumerate(x4_json["subentries"][nsubent]["DATA"]["value"]):
        new["value"].append([])
        for j in cols:
          new["value"][i].append(vals[j])

  return new


def print_sysid_data(x4_json_poi_ind,data_condensed):

  if len(data_condensed["pointer"])==0:
    x4_json_poi_ind["NODATA"]={
      "N1": 0,
      "N2": 0
    }
  else:
    x4_json_poi_ind["DATA"]={
      "N1": len(data_condensed["pointer"]),
      "N2": len(data_condensed["value"])
    }

    x4_json_poi_ind["DATA"].update(data_condensed)

    x4_json_poi_ind["ENDDATA"]={
      "N1": 0,
      "N2": 0
    }

  x4_json_poi_ind["ENDSUBENT"]={
    "N1": 0,
    "N2": 0
  }

  return x4_json_poi_ind


def get_args(ver):

  parser=argparse.ArgumentParser(\
   usage="Remove pointer structure in J4",\
   epilog="example: x4_poipoi.py -i exfor.json -d dict.json -e 22742.004.1 -o exfor_poi.json -k all")
  parser.add_argument("-v", "--version",\
         action="version", version=ver)
  parser.add_argument("-i", "--file_inp",\
   help="input J4 file")
  parser.add_argument("-d", "--file_dict",\
   help="input JSON dictionary (optional, default: dict.json)", default="dict.json")
  parser.add_argument("-e", "--data_id",\
   help="EXFOR Dataset ID ('all' to process all datasets)")
  parser.add_argument("-o", "--file_out",\
   help="output J4 file")
  parser.add_argument("-k", "--key_keep",\
   help="keywords to be kept (optional, default: 'all' which process all keywords)", default=["all"], nargs="+")
  parser.add_argument("-f", "--force",\
   help="never prompt", action="store_true")
  parser.add_argument("-p", "--delpoin",\
   help="delete pointer", action="store_true")
  parser.add_argument("-c", "--keep001",\
   help="keep common subentry 001", action="store_true")
  parser.add_argument("-r", "--keepres",\
   help="keep resonance parameter table", action="store_true")

  args=parser.parse_args()
  return args


def get_input(args):
  time=datetime.datetime.now()
  date=time.strftime("%Y-%m-%d")
  print("POIPOI (Ver."+ver+") run on "+date)
  print("----------------------------------------")

  force0=args.force
  delpoin0=args.delpoin
  keep0010=args.keep001
  keepres0=args.keepres

  file_inp=args.file_inp
  if file_inp is None:
    file_inp=input("input J4 file [exfor.json] ----------> ")
    if file_inp=="":
      file_inp="exfor.json"
  if not os.path.exists(file_inp):
    print(" ** File "+file_inp+" does not exist.")
  while not os.path.exists(file_inp):
    file_inp=input("Input J4 file [exfor.json] ----------> ")
    if file_inp=="":
      file_inp="exfor.json"
    if not os.path.exists(file_inp):
      print(" ** File "+file_inp+" does not exist.")

  file_dict=args.file_dict
  print("JSON Dictionary ---------------------> "+file_dict)
  if not os.path.exists(file_dict):
    print(" ** File "+file_dict+" does not exist.")
  while not os.path.exists(file_dict):
    file_dict=input("JSON DIctionary [dict.json] ---------> ")
    if file_dict=="":
      file_dict="dict.json"
    if not os.path.exists(file_dict):
      print(" ** File "+file_dict+" does not exist.")

  data_id=args.data_id
  if data_id is None:
    data_id=input("EXFOR Dataset ID [all] --------------> ")
    if data_id=="":
      data_id="all"
  if data_id!="all":
    data_id=data_id.upper()
  if not re.compile(r"^[1-9A-Z]\d{4}(\.\d{3}(\.[1-9A-Z])?)?$").search(data_id) and data_id!="all":
    print(" ** EXFOR Dataset ID "+data_id+" is illegal.")
  while not re.compile(r"^[1-9A-Z]\d{4}(\.\d{3}(\.[1-9A-Z])?)?$").search(data_id) and data_id!="all":
    data_id=input("EXFOR Dataset ID [all] --------------> ")
    if data_id=="":
      data_id="22742.004.1"
    elif data_id!="all":
      data_id=data_id.upper()
    if not re.compile(r"^[1-9A-Z]\d{4}(\.\d{3}(\.[1-9A-Z])?)?$").search(data_id) and data_id!="all":
      print(" ** EXFOR Dataset ID "+data_id+" is illegal.")

  file_out=args.file_out
  if data_id=="all" or len(data_id)==5:
    if file_out is None:
      file_out=input("Directory of output J4 files [j4] ---> ")
    if file_out=="":
      file_out="j4"
   
    if os.path.isdir(file_out):
      msg="Directory '"+file_out+"' exists and must be overwritten."
      print_error(msg,"",force0)
    else:
      msg="Directionry '"+file_out+"' does not exist and must be created."
      print_error(msg,"",force0)
      os.mkdir(file_out)

  else:
    if file_out is None:
      file_out=input("Output J4 file [exfor_poi.json] -----> ")
    if file_out=="":
      file_out="exfor_poi.json"
    if os.path.isfile(file_out):
      msg="File '"+file_out+"' exists and must be overwritten."
      print_error(msg,"",force0)

  key_keep=args.key_keep
  print("input keywords to keep --------------> ", end="")
  for char in key_keep:
    print(char+" ", end="")
  print("\n")

  return file_inp,file_dict,data_id,file_out,key_keep,force0,delpoin0,keep0010,keepres0
  

def read_x4json(file_inp):
  f=open(file_inp)
  try:
    x4_json=json.load(f)
  except json.JSONDecodeError:
    msg=file_inp+" is not in JSON format."
    print_error_fatal(msg,"")

  if x4_json["title"]!="J4 - EXFOR in JSON" and\
     x4_json["title"]!="J4 - EXFOR in JSON, number as string" :
    msg=file_inp+" is not an EXFOR in JSON."
    print_error_fatal(msg,"")

  f.close()
  return x4_json


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


def print_error_1(msg,line):
  print("**  "+msg)
  print(line)

  return


def print_error_fatal(msg,line):
  print("**  "+msg)
  print(line)
  exit()


if __name__ == "__main__":
  poipoi()
  exit()
