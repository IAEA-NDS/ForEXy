#!/usr/bin/python3
ver="2026.10.15"
############################################################
# J4TOC6 Ver.2026.10.15
# (Utility to convert J4 to C6)
#
# Naohiko Otuka (IAEA Nuclear Data Section)
############################################################
#
# print_subent
#   -> get_reaction (get operation 3)
#   -> get_mfmt (get mf & mt)
#   -> read_data (get operation 1 & operation 2)
#
#  mf and mt are defined Dict.336.
#  operation1 and operation2 are defined in Dict.324.
#  operation3 is defined in get_reactionsubfield.

import argparse
import datetime
import glob
import json
import os
import re
import time
import math
import shutil
from operator import itemgetter

if os.path.isfile("x4_lotran.py"):
  import x4_lotran
else:
  from forexy import x4_lotran

ueV   = 931.49410242E+06   # 1 atomic mass unit in eV (AME2020)
alpha = 0.0072973525643    # fine-structure constant (PDG2025)
hbarc = 197.3269804E+06    # hbar*c (PDG2025)
pi    = math.pi


def j4toc6():
  args=get_args(ver)
  main(*get_input(args))


def main(dir_j4,file_dict,entry,file_c6,seplvl0,file_idx,sysout0,enewid0,force0,exclhi0,incder0,c4out0):
  time_start=time.time()

  global seplvl
  global sysout
  global enewid
  global force
  global outcos
  global exclhi
  global incder
  global c4out
  global dict_json
  global doi_list

  seplvl=seplvl0
  sysout=sysout0
  enewid=enewid0
  force=force0
  exclhi=exclhi0
  incder=incder0
  c4out=c4out0
  doi_list=dict()

  if c4out:
    outcos=True
  else:
    outcos=False

  l_tot=0 # number of datasets converted

  if entry=="all":
    pattern=dir_j4+"/[a-z0-9][0-9][0-9][0-9][0-9].[0-9][0-9][0-9]*.json"
  else:
    pattern=dir_j4+"/"+entry+".[0-9][0-9][0-9]*.json"
  all_files=glob.glob(pattern)
  files=[file for file in all_files if re.search(r"\d\d\d(\.[A-Z1-9])?\.json", file)]
  files=sorted(files)
  if len(files)==0:
    msg="J4 file for EXFOR Entry "+entry+" does not exist."
    print_error_fatal(msg,"")

  dict_json=read_dict(file_dict)
  read_dict_324() # unofficial archive dictionary 324
  read_dict_336() # unofficial archive dictionary 336

  l=open(file_idx,"a")
  if os.path.getsize(file_idx)==0: # empty index file
    l.write("#EXFOR #    TRANS MF   MT   Isom Total    Coverted Web.Q REACTION                    \n")
    l.write("#---------- ----- ---- ---- ---- -------- -------- ----- ----------------------------\n")

  if seplvl==1:
    f=open(file_c6,"w")
  else:
    dir_out=file_c6

  header_c4_out=True # becomes False when the header is printed

  for nfile, file_j4 in enumerate(files):
    print("processing ... "+file_j4)
    m=re.search(r"([1-9a-z]\d{4,4}\.\d{3,3})(\.[A-Z1-9])?\.json$", file_j4)
    ansan=m.group(1)
    if m.group(2) is None:
      pointer=""
      ansan=ansan+"  "
    else:
      pointer=m.group(2)[1]
      ansan=ansan+"."+pointer

    if seplvl==2 or seplvl==3:
      ansan=ansan.lower()
      file_c6=dir_out+"/"+ansan
      file_c6=re.sub(r"  $","",file_c6)
      f=open(file_c6,"w")
      header_c4_out=True

    ansan_out=ansan.upper()
    x4_json=read_x4json(file_j4)
    tid=x4_json["entries"][0]["ENTRY"]["transmission_identification"]
    if tid is None:
      tid="????"

    if x4_json["title"]!="J4 - EXFOR in JSON without pointer without common subentry":
      msg="Input J4 file should be made by X4TOJ4 without -s and by POIPOI without -c and -r."
      print_error_fatal(msg,x4_json["title"])

    keywords=["TRANS","MASTER","REQUEST"]
    for keyword in keywords:
      if keyword in x4_json:
        msg="Input J4 file should be made from an entry file and should not contain a "+keyword+ "record.\n"
        print_error_fatal(msg,"")
   
    (f,k_tot,l_tot,header_c4_out)=print_subent(f,l,file_dict,file_c6,tid,ansan_out,x4_json["entries"][0]["subentries"][0],nfile,pointer,header_c4_out,l_tot)

    if seplvl==2 or seplvl==3:
      if k_tot==0 and os.path.isfile(file_c6):
        f.close()
        os.remove(file_c6)


  if seplvl==1:
    if l_tot>0:
      if c4out:
        f.write("#/ENTRY     "+str(l_tot)+"\n")
        f.write("#\n")
        f.write("#\n")
    f.close()
    if l_tot==0:
      os.remove(file_c6)

  l.close()


  time_end=time.time()
  time_elapsed=format(time_end-time_start, ".2f")
  print("J4TOC6: Processing terminated normally. "+time_elapsed+" sec.\n")


def print_subent(f,l,file_dict,file_c6,tid,ansan_out,x4_json,nfile,pointer,header_c4_out,l_tot):
  keywords=["SUBENT"
           ,"ENDSUBENT"
           ,"NOSUBENT"
           ,"BIB"
           ,"ENDBIB"
           ,"NOBIB"
           ,"ENDCOMMON"
           ,"NOCOMMON"
           ,"ENDDATA"
           ,"NODATA"]

  year_r=""       # year in the first reference of REFERENCE
  author_a=""     # 1st author in AUTHOR
  header4_last="" # to keep header printed several times for J4TOC6 option -r
  constant_last=""

  j_tot=0 # number of data points in the dataset
  k_tot=0 # number of data points in the dataset and converted

  if "SUBENT" not in x4_json: # NOSUBENT
    return f,k_tot,l_tot,header_c4_out
  else:
    char=x4_json["SUBENT"]["N1"]
    an=char[0:5]
    san=char[5:8]
    if an!=ansan_out[0:5] or san!=ansan_out[6:9]:
      msg=ansan_out+" SUBENT record inconsistent with the input J4 file name"
      print_error_fatal(msg,"")

    subent_n2=str(x4_json["SUBENT"]["N2"])
    trans_id=x4_json["SUBENT"]["transmission_identification"]
    if trans_id is None:
      trans_id="????"

  if "AUTHOR" in x4_json:
    author_a=get_author(x4_json["AUTHOR"],author_a)
  else:
    msg=ansan_out+" AUTHOR is absent"
    print_error(msg,"",True)
    author_a="????"

  if "REFERENCE" in x4_json:
    (year_r,expansion_r,reference_code_r)=get_reference(x4_json["REFERENCE"])
  else:
    msg=ansan_out+" REFERENCE is absent"
    print_error(msg,"",True)
    year_r="????"
    expansion_r="????"
    reference_code_r=""

  if "REACTION" not in x4_json: # SUPPL-INF
    return f,k_tot,l_tot,header_c4_out
  else:
    (skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3)=get_reactionsubfield(ansan_out,x4_json["REACTION"])
    if skip:
      print_idx(l,tid,ansan_out,web_quantity,reaction_code,"-","-","-","-","-")
      return f,k_tot,l_tot,header_c4_out

    (skip,mf,mt,elemmass)=get_mfmt(ansan_out,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec)
    if skip:
      print_idx(l,tid,ansan_out,web_quantity,reaction_code,"-","-","-","-","-")
      return f,k_tot,l_tot,header_c4_out
    elif mf==4 or mf==6:
      if elemmass: # inclusive nuclide production
        msg=ansan_out+" MF4 and MF6 cannot be for inclusive nuclide production."
        print_error(msg,"",True)
        print_idx(l,tid,ansan_out,web_quantity,reaction_code,"-","-","-","-","-")
        return f,k_tot,l_tot,header_c4_out

  if "STATUS" in x4_json:
    (status,author_s,year_s,expansion_s,reference_code_s)=get_status(x4_json["STATUS"])
    if status=="SPSDD" or status=="OUTDT":
      msg=ansan_out+" Data with status not for conversion: "+status
      print_error(msg,"",True)
      print_idx(l,tid,ansan_out,web_quantity,reaction_code,"-","-","-","-","-")
      return f,k_tot,l_tot,header_c4_out
  else:
    status=" "
    author_s=""
    year_s=""
    expansion_s=""
    reference_code_s=""

  if "DATA" not in x4_json:
    return f,k_tot,l_tot,header_c4_out


  (author,reference_code,reference_exp,year,doi)=get_bibliography(author_s,author_a,year_s,year_r,expansion_s,expansion_r,reference_code_s,reference_code_r)

  (line_l,line_r,sf4_iso_char)=get_line_terminator(ansan_out,sf1,sf2,sf4,mf,mt,spec,status,author,year,pointer)

  header_out=True # becomes False when the header is printed

  frame_out_last=dict()

  for j, line in enumerate (x4_json["DATA"]["value"]): # loop for data points
    j_tot+=1

    headings=[]
    units=[]
    values=[]
    value_out=dict()
    frame_out=dict()

    if "COMMON" in x4_json:
      headings+=x4_json["COMMON"]["heading"]
      units+=x4_json["COMMON"]["unit"]
      values+=x4_json["COMMON"]["value"]

    for i, pointer in enumerate (x4_json["DATA"]["pointer"]):
      if x4_json["DATA"]["value"][j][i] is not None: # skip empty data fields
        headings.append(x4_json["DATA"]["heading"][i])
        units.append(x4_json["DATA"]["unit"][i])
        values.append(x4_json["DATA"]["value"][j][i])

# read a data line from J4 file
    (skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running)=read_data(j,ansan_out,sf2,headings,units,values,spec)
    if skip: # skip the data point (e.g., presence of AMIN/ADEG, repetition of two headings)
      if nodata: # blank DATA field (e.g., in multiple reaction formalism)
        j_tot-=1 
      continue

# convert %-uncertainty to absolute uncertainty
    value_out=convert_percent(j,ansan_out,flag_percent,value_out)

# process data for operation2 (e.g., Qval -> Eexc, p -> T)
    (skip,value_out,frame_inp)=operation2_data(j,ansan_out,sf1,sf2,sf3,sf4,value_out,frame_inp,field_E,operation2)
    if skip: # skip this data point if conversion is not successful
      continue

    skip=check_independentvariable(j,ansan_out,sf2,sf4,mf,value_out)
    if skip: # skip this data point if an independent variable is missing
      continue

# process data for operation3 (e.g., removal of RTH, SFC, ...)
    (skip,value_out,frame_inp)=operation3_data(j,ansan_out,sf1,sf2,sf3,sf4,value_out,frame_inp,operation3)
    if skip: # skip the data point (e.g., absence of a required independent variable)
      continue

# Illegal data (negative angle, negative energy, negative cross section)
    if "G" in value_out:
      if value_out["G"]<0:
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": negative angle: "+str(value_out["G"])
        print_error(msg,"",True)
        continue
      elif value_out["G"]>180:
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": angle > 180 deg: "+str(value_out["G"])
        print_error(msg,"",True)
        continue
    if "E" in value_out:
      if field_E=="LVL":
        if value_out["E"]<0:
          msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": negative level energy: "+str(value_out["E"])
          print_error(msg,"",True)
          continue
      else:
        if value_out["E"]<=0:
          msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": non-positive outgoing kinetic energy: "+str(value_out["E"])
          print_error(msg,"",True)
          continue
    if "*" in value_out:
      if value_out["*"]<0:
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": negative quantity measured: "+str(value_out["*"])
        print_error(msg,"",True)
        continue

# Lorentz transformation
    if "G" in frame_inp:
      frame_out["G"]=frame_inp["G"]
    if "E" in frame_inp:
      frame_out["E"]=frame_inp["E"]
    if "*" in frame_inp:
      frame_out["*"]=frame_inp["*"]
    if mf==4:
      if sf3!="X" and ("E" not in value_out or field_E=="LVL"): # two-body cross section without outgoing energy as a variable
        (lorentz,frame_out)=get_outputframe(mf,frame_inp)
        if lorentz:
          (skip,value_out)=x4_lotran.main(file_dict,"",j,ansan_out,"ADX",sf1,sf2,sf3,sf4,value_out,frame_inp,frame_out,force)
          if skip:
            continue  # skip the data point (e.g., two pcm found for a plab during Lorentz transformation)
    
    elif mf==6:
      if sf3=="X" and ("E" in value_out and field_E=="E2"):     # inclusive cross section with outgoing energy as a variable
        (lorentz,frame_out)=get_outputframe(mf,frame_inp)
        if lorentz:
          (skip,value_out)=x4_lotran.main(file_dict,"",j,ansan_out,"DDX",sf1,sf2,sf3,sf4,value_out,frame_inp,frame_out,force)
          if skip:
            continue  # skip the data point (e.g., two pcm found for a plab during Lorentz transformation)

# print
    quantity=expand_reaction(mf,mt,sf1,sf2,sf3,sf4,sf5)
    (f,header_out,header_c4_out,header4_last,constant_last,printed,k_tot)=print_data(j,f,file_c6,ansan_out,subent_n2,trans_id,author,year,reference_code,reference_exp,doi,quantity,line_l,line_r,header_out,header_c4_out,mf,mt,spec,sf1,sf2,sf4,sf5,elemmass,value_out,frame_inp,frame_out,field_E,family_constant,family_running,header4_last,constant_last,x4_json,k_tot)
    if printed:
      k_tot+=1
      family_running_last=family_running
      field_E_last=field_E
      frame_out_last=frame_out

  if c4out and k_tot!=0:
    f.write("#/DATA      "+str(k_tot)+"\n")
    f.write("#/DATASET\n")
  print_idx(l,tid,ansan_out,web_quantity,reaction_code,mf,mt,sf4_iso_char,j_tot,k_tot)

  if k_tot>0:
    l_tot+=1

  if k_tot!=0 and not c4out:
    f.write("\n")
    f.write("\n")

  if seplvl==2 or seplvl==3:
    f.close()
    if k_tot==0: # empty file
      os.remove(file_c6)
    else:
      (file_c6_pre,prod_const)=make_file_c6_pre(sf1,sf2,line_l,family_running_last,field_E_last,frame_out_last,spec)
      file_c6_new=file_c6+file_c6_pre
      constant=get_authoryear(author,year)
      if seplvl==3:
        if prod_const!="":
          constant="prod"+prod_const+"_"+constant
        if constant_last!="":
          constant=constant_last+"_"+constant
      file_c6_new+="-"+constant
      if c4out:
        file_c6_new+=".c4"
      else:
        file_c6_new+=".c6"
      shutil.move(file_c6,file_c6_new)

  return f,k_tot,l_tot,header_c4_out


def get_authoryear(author,year):
  fauthor=re.sub(" et al.","",author)
  fauthor=re.sub(r".+\.","",fauthor)
  fauthor=re.sub(" ","%",fauthor)
  fauthor=re.sub("-","+",fauthor)
  fauthor=re.sub("'","",fauthor)
  author_year=fauthor+"_"+year

  return author_year


def get_author(x4_json_author,author_a):
  for i, item in enumerate(x4_json_author):
    if item["coded_information"] is not None:
      if author_a=="":
        author_a=item["coded_information"][0]
        if len(item["coded_information"])>1:
          author_a=author_a+"+"
          
  return author_a


def get_reference(x4_json_reference):
  for i, item in enumerate(x4_json_reference):
    coded_information=item["coded_information"]
    if i==0: # first reference
      (year_r,expansion_r)=expand_reference(coded_information["code_unit"][0]["field"])
      reference_code=coded_information["code_unit"][0]["unit"] # takes the first code string if an alias exists

    code_units=coded_information["code_unit"]
    for code_unit in code_units:
      if code_unit["doi"] is not None:
        code=code_unit["unit"]
        doi=code_unit["doi"]
        doi_list[code]=doi

  return year_r, expansion_r, reference_code


def get_reactionsubfield(ansan_out,x4_json_reaction):
  skip=True
  operation3=dict()
  sf1=""
  sf2=""
  sf3=""
  sf4=""
  sf5=""
  sf6=""
  sf7=""
  sf8=""
  spec=""

  if len(x4_json_reaction)!=1:
    msg=ansan_out+" Dataset containing two or more REACTION codes?"
    print_error_fatal(msg,"")
  elif "coded_information" not in x4_json_reaction[0]:
    msg=ansan_out+" Dataset without REACTION code?"
    print_error_fatal(msg,"")
    
  coded_information=x4_json_reaction[0]["coded_information"]
  reaction_code=coded_information["code"]
  quantity_236=coded_information["code_unit"][0]["field"]["quantity_236"]

  if quantity_236 is None:
    msg=ansan_out+" Quantity code "+coded_information["code_unit"][0]["field"]["quantity"]+" is undefined in Dict. 236."
    print_error(msg,"",True)
    web_quantity=""
    return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3

  reaction_type=dict_retrieval("236","code",quantity_236,"reaction_type_code")
  web_quantity=dict_retrieval("213","code",reaction_type,"web_quantity_code")
    
  if coded_information["unit_combination"]=="(%)":
    index=0
  elif coded_information["unit_combination"]=="((%)=(%))":
    sf1=coded_information["code_unit"][0]["field"]["target"]
    if sf1=="1-H-1" or sf1=="1-H-2" or sf1=="1-H-3" or sf1=="2-HE-3" or sf1=="2-HE-4":
      index=1
    else:
      index=0
  else:
    msg=ansan_out+" REACTION combination "+coded_information["unit_combination"]+" is not supported."
    print_error(msg,"",True)
    return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3

  sf1=coded_information["code_unit"][index]["field"]["target"]
  sf2=coded_information["code_unit"][index]["field"]["projectile"]
  sf3=coded_information["code_unit"][index]["field"]["process"]
  sf4=coded_information["code_unit"][index]["field"]["product"]
  sf58=coded_information["code_unit"][index]["field"]["quantity"].split(",")
  sf9=coded_information["code_unit"][index]["field"]["data_type"]

  if re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(-(G|M\d?|L\d))?$").search(sf2):
    (sf2_za,sf2_iso_char,sf2_iso_num)=nucl_numeq(sf2)
    if re.compile(r"^\d\d\d\d\d$").search(sf2_za): # Z(proj)>99
      msg=ansan_out+" Projectile "+sf2+" is Z>99. Not converted."
      print_error(msg,"",True)
      return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3
    elif sf2_iso_char!=" ": # isomeric projectile cannot be accomodated
      msg=ansan_out+" Projectile "+sf2+" is an isomer. Not converted."
      print_error(msg,"",True)
      return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3

  if sf2!="0" and sf2!="G" and sf2!="N" and sf2!="P" and sf2!="D" and sf2!="T" and sf2!="HE3" and sf2!="A":
    if "-" not in sf2:
      msg=ansan_out+" Projectile "+sf2+" is not a supported projectile particle. Not converted."
      print_error(msg,"",True)
      return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3
    elif exclhi:
      msg=ansan_out+" Projectile "+sf2+" is a heavy ion. Not converted."
      print_error(msg,"",True)
      return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3

  if (sf9 is not None and sf9!="EXP" and sf9!="DERIV") or (sf9=="DERIV" and not incder):
    msg=ansan_out+" Data type is "+sf9+". Not converted."
    print_error(msg,"",True)
    return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3

  if not re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(\-M)?$").search(sf1):
    msg=ansan_out+" Target nuclide "+sf1+" is compouned. Not converted."
    print_error(msg,"",True)
    return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3

  if re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)\-[GML0-9]+").search(sf2):
    msg=ansan_out+" Projectile "+sf2+" is an isomer. Not converted."
    print_error(msg,"",True)
    return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3

  if not re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)").search(sf2):
    numeq=dict_retrieval("033","code",sf2,"internal_numerical_equivalent_1")
    if numeq=="" and sf2!="0":
      msg=ansan_out+" Projectile "+sf2+" without numerical equivalent. Not conerted."
      print_error(msg,"",True)
      return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3

# General quantity modifier
  genq=coded_information["code_unit"][0]["field"]["general_quantity_modifier"]
  if genq is not None:
    genqs=genq.split("/")
    specs_new=[]
    genqs_new=[]
    for genq in genqs:
      genq_flag=dict_retrieval("034","code",genq,"general_quantity_modifier_flag")
      if genq=="A":
        operation3["A"]=1
      elif genq=="DAM":
        operation3["DAM"]=1
      elif genq_flag=="GENQP":
        specs_new.append(genq)
      else:
        genqs_new.append(genq)

    if len(specs_new)==0:
      spec=""
    else:
      spec="/".join(specs_new)

    if len(genqs_new)==0:
      genq=None
    else:
      genq="/".join(genqs_new)

  if genq is not None and genq!="AV": # Only A, DAM or AV are GENQ for conversion
    msg=ansan_out+" Unsupported general quantity modifier "+genq
    print_error(msg,"",True)
    return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3

  skip=False

  if (sf3=="EL" or sf3=="INL" or sf3=="SCT") and sf4=="":
    msg=ansan_out+" sf3="+sf3+" and sf4 is empty. sf1=sf4="+sf1+" assumed"
    print_error(msg,"",True)
    sf4=sf1

  sf5=sf58[0]
  sf6=sf58[1]
  if len(sf58)>2:
    sf7=sf58[2]
  else:
    sf7=""
  if len(sf58)>3:
    sf8=sf58[3]
  else:
    sf8=""

# S-factor
  if sf6=="SIG" and sf8=="SFC":
    sf8=""
    operation3["SFC"]=1

# multiplied by root(Einc)
  if sf8=="RTE":
    sf8=""
    operation3["RTE"]=1

# multiplied by 4pi
  if sf6=="DA" and sf8=="4PI":
    sf8=""
    operation3["4PI"]=1

# divided by 4pi
  if sf8=="D4PI":
    sf8=""
    operation3["D4PI"]=1

# differential for outgoing momentum
  if sf6=="DP":
    sf6="DE"
    operation3["DP"]=1
  elif sf6=="DA/DP":
    sf6="DA/DE"
    operation3["DP"]=1

# Rutherford ratio
  if sf6=="DA" and sf8=="RTH":
    sf8=""
    operation3["RTH"]=1

# M-,SIG,M- -> ,SIG (M-,SIG is obsolete)
  if sf5=="M-" and sf6=="SIG":
    sf5=""

  return skip,reaction_code,web_quantity,sf1,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec,operation3


def nucl_numeq(code):
  pattern=re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(\-[GML0-9\+\/]+)?$")
  m=pattern.search(code)
  z=m.group(1)
  a=m.group(3)

  if int(z)<10:
    z="  "+z 
  elif int(z)<100:
    z=" "+z 

  if int(a)<10:
    a="00"+a 
  elif int(a)<100:
    a="0"+a 
  nucl_za=z+a

  pattern=re.compile(r"^\d+\-([A-Z][A-Z0]?|\*)\-\d+\-([GML0-9\+\/]+)$")
  m=pattern.search(code)
  if m:
    x=m.group(2)
    if c4out:
      if x=="G":
        iso_char="G"
        iso_num=0
      elif re.compile(r"^M\d$").search(x):
        iso_char=x[1:2]
        iso_num=x[1:2]
      elif re.compile(r"^L\d?$").search(x):
        iso_char="?"
        iso_num=6
      elif x=="M":
        iso_char="M"
        iso_num=7
      elif x.find("+")!=-1:
        iso_char="+"
        iso_num=8
      else:
        iso_char="X"
        iso_num=6
    else:
      if x=="G":
        iso_char="G"
        iso_num=0
      elif x=="M" or x=="M1":
        iso_char="M"
        iso_num=1
      elif x=="M2":
        iso_char="N"
        iso_num=2
      elif x=="G+M1":
        iso_char="P"
        iso_num=3
      elif x=="G+M2":
        iso_char="Q"
        iso_num=4
      elif x=="M1+M2":
        iso_char="R"
        iso_num=5
      elif re.compile(r"^L\d?$").search(x):
        iso_char="L"
        iso_num=7
      else:
        iso_char="?"
        iso_num=6

  else:
    iso_char=" "
    iso_num=9

  return nucl_za, iso_char, iso_num


def get_mfmt(ansan_out,sf2,sf3,sf4,sf5,sf6,sf7,sf8,spec):
  mf=""
  mt=""
  elemmass=False

  m=re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(\-[GML0-9\+\/]+)?$").search(sf4)
  if m:
    z=m.group(1)
    a=m.group(3)
    if int(z)>2 and re.compile(r"^\d+$").search(a):
      sf4="ELEM/MASS"

  if sf3=="INL":
    sf3a=sf2 # e.g., (N,INL) -> (N,N)
  else:
    sf3a=sf3

# cumulative=False
# if sf5 is not None:
#   branches=sf5.split("/")
#   branches_new=[]
#   for branch in branches:
#     if branch=="CUM" or branch=="(CUM)" or branch=="M+" or branch=="(M)":
#       cumulative=True
#     elif branch=="M-": # M- always appears after CUM
#       cumulative=False
#     else:
#       branches_new.append(branch)
#   if len(branches_new)==0 and cumulative:
#     sf5a="CUM"
#   else:
#     sf5a=sf5
# sf5a=""

  spec_flag=get_spectrum_flag(spec)
  if spec_flag=="/" or spec_flag=="X":
    pass
  else:
    for record in dict_json["336"]:
      if (record["sf2"]=="*" or record["sf2"]==sf2) and\
         (record["sf3"]=="*" or record["sf3"]==sf3 or (record["sf3"]==sf3a and record["flag"]==".") or (record["sf3"]=="+" and (sf3=="X" or sf3=="F"))) and\
         (record["sf4"]=="*" or record["sf4"]==sf4) and\
         (record["sf5"]==sf5 or (record["sf5"]=="+" and (sf5=="IND" or sf5=="")) or (record["sf5"]=="-" and (sf5=="CUM" or sf5=="(CUM)" or sf5=="M+" or sf5=="(M)"))) and\
         (record["sf6"]=="*" or record["sf6"]==sf6 or (record["sf6"]=="+" and (sf6=="SIG" or sf6=="FY")))  and\
         (record["sf7"]==sf7 or (record["sf7"]=="+" and (sf7=="G" or sf7==""))):
        mt=record["code"]
        if record["sf4"]=="ELEM/MASS":
          elemmass=True
        break

    if sf8=="":
      if sf6=="NU":
        mf=1
      elif sf6=="SIG":
        if sf7=="":
          mf=3
        elif sf7=="G":
          mf=13
      elif sf6=="DA":
        if sf7=="":
          mf=4
        elif sf7=="G":
          mf=14
      elif sf6=="DE":
        if sf7=="":
          mf=5
        elif sf7=="G":
          mf=15
      elif sf6=="DA/DE":
        if sf7=="":
          mf=6
      elif sf6=="FY":
        mf=8

  if mf=="" or mt=="":
    skip=True
  else:
    skip=False
    mf=int(mf)
    mt=int(mt)

  return skip,mf,mt,elemmass


def get_status(x4_json_status):
  status=" "
  author_s=""
  year_s=""
  expansion_s=""
  reference_code_s=""
  status_order={'APRVD' : 1
               ,'DEP'   : 2
               ,'COREL' : 3
               ,'RNORM' : 4
               ,'PRELM' : 5
               ,'OUTDT' : 6
               ,'SPSDD' : 7}

  for i, item in enumerate(x4_json_status):
    if item["coded_information"] is not None:
      for code in item["coded_information"]["status"]:
        if code in status_order:
          if status==" ":
            status=code
          elif status_order[status]<status_order[code]:
            status=code

      if author_s=="": # author is not updated if it was detected earlier
        if item["coded_information"]["author"] is not None:
          author_s=item["coded_information"]["author"]
          reference_code_s=item["coded_information"]["reference"]["code"]
          (year_s,expansion_s)=expand_reference(item["coded_information"]["reference"]["field"])

  return status,author_s,year_s,expansion_s,reference_code_s


def get_bibliography(author_s,author_a,year_s,year_r,expansion_s,expansion_r,reference_code_s,reference_code_r):
  if author_s!="": # author under STATUS preferred
    author=author_s
  else:
    author=author_a
  author=uptolow_author(author)
  author=author.replace("+"," et al.")
  
  if expansion_s!="":  # reference under STATUS preferred
    reference_code=reference_code_s
    reference_exp=expansion_s
    year=year_s
  else:
    reference_code=reference_code_r
    reference_exp=expansion_r
    year=year_r

  if reference_code in doi_list:
    doi=doi_list[reference_code]
  else:
    doi=None

  return author,reference_code,reference_exp,year,doi


def get_line_terminator(ansan_out,sf1,sf2,sf4,mf,mt,spec,status,author,year,pointer):
  if re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(-(G|M\d?|L\d))?$").search(sf2):
    (sf2_za,sf2_iso_char,sf2_iso_num)=nucl_numeq(sf2)
    sf2_za=sf2_za[1:6]
  else:
    sf2_za=part_numeq(sf2)

  (sf1_za,sf1_iso_char,sf1_iso_num)=nucl_numeq(sf1)

  mfout='{:>3}'.format(mf)
  mtout='{:>4}'.format(mt)

  if sf4=="":
    sf4_iso_char=" "
  elif mt==454 or mt==459: # nuclide production
    sf4_iso_char=" "
  else:
    (sf4_za,sf4_iso_char,sf4_iso_num)=nucl_numeq(sf4)

  an=ansan_out[0:5]
  san=ansan_out[6:9]
  san_out=re.sub("^0+","",san)
  san_out='{:>3}'.format(san_out)
  pointer_out='{:>1}'.format(pointer)

  if c4out:
    line_l=sf2_za+sf1_za+sf1_iso_char+mfout+mtout+sf4_iso_char+status[0] # Col.1-21 of output
  else:
    spec_flag=get_spectrum_flag(spec)
    line_l=sf2_za+sf1_za+sf1_iso_char+mfout+mtout+sf4_iso_char+spec_flag # Col.1-21 of output

  author=author.replace(" et al.","+")
  author='{:<21}'.format(author)
  line_r=author+"("+year[2:4]+")"+an+san_out+pointer_out # Col.98-131 of output

  return line_l,line_r,sf4_iso_char


def read_data(j,ansan_out,sf2,headings,units,values,spec):
  skip=False
  nodata=False
  value_out=dict()
  frame_inp=dict()
  operation2=dict()
  flag_percent=dict()
  field_E=""
  field_F=""
  family_running=""
  family_constant=dict()
  family_index=dict()

  for record in dict_json["324"]: # loop for combinations of headings

    index1=[]
    index2=[]
    if record["heading1"] in headings and record["heading2"]=="": # e.g., EN
      index1=[i for i, x in enumerate(headings) if x == record["heading1"]]
    elif record["heading1"] in headings and record["heading2"] in headings: # e.g., (EN-MIN,EN-MAX)
      index1=[i for i, x in enumerate(headings) if x == record["heading1"]]
      index2=[i for i, x in enumerate(headings) if x == record["heading2"]]

    if len(index1)==0:
      continue

    family=record["family"]
    if family=="A" or family=="E" or family=="G" or family=="L" or family=="I" or family=="J" or family=="M" or family=="T":
      family_index[family]=index1[0]
    frame_inp[family]=record["frame"]
    operation1=int(record["operation1"])
    operation2[family]=int(record["operation2"])
    flag_percent[family]=""

    if len(index2)==0:
      if len(index1)==1: # e.g., EN
        unit1=units[index1[0]]
        value1=values[index1[0]]
      elif family=="T": # Two or more ISOMER fields exist
        value1=9
      else:
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Multiple values found under heading "+record["heading1"]
        print_error(msg,"",force)
        skip=True
        return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running
    elif len(index2)==1:
      if len(index1)==1: # e.g., EN-MIN, EN-MAX
        unit1=units[index1[0]]
        unit2=units[index2[0]]
        value1=values[index1[0]]
        value2=values[index2[0]]
      else:
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Multiple values found under heading " +record["heading1"]
        print_error(msg,"",force)
        skip=True
        return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running
    else:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Multiple values found under heading "+record["heading2"]
      print_error(msg,"",force)
      skip=True
      return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running

     
    spec_flag=get_spectrum_flag(spec)

    if len(index2)==1:
      if family=="A" and spec_flag!=" ":
        if spec_flag=="B" or spec_flag=="S": # BRS or SPA
          value_mean=(value1+value2)/2.
          if abs(value1-value2)/value_mean>enewid:
            msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Too wide energy window with spectrum modifier "+spec
            print_error(msg,"",force)
            skip=True
            return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running
        else:
          msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Lower and upper energies with spectrum modifier "+spec
          print_error(msg,"",force)
          skip=True
          return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running

    if unit1=="MEV/A" or unit1=="GEV/A":
      (skip,value1)=convert_energy_per_mass(value1,unit1,sf2)
      if skip:
        return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running
      unit1="EV"
    if len(index2)==1:
      if unit2=="MEV/A" or unit2=="GEV/A":
        (skip,value2)=convert_energy_per_mass(value2,unit2,sf2)
        if skip:
          return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running
        unit2="EV"

    if unit1=="AMIN" or unit1=="ASEC":
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": AMIN and ASEC are not supported "
      print_error(msg,"",force)
      skip=True
      return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running
    if len(index2)==1:
      if unit2=="AMIN" or unit2=="ASEC":
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": AMIN and ASEC are not supported "
        print_error(msg,"",force)
        skip=True
        return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running

    factor1=dict_retrieval("025","keyword",unit1,"conversion_factor")
    if factor1 is None:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Conversion factor not found: "+unit1
      print_error(msg,"",True)
      skip=True
      return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running
    else:
      value1=value1*factor1

    if len(index2)==0:
      if family=="A" and spec_flag=="S":
        if value1<0.025 and value1>0.0254: # only E~0.0253 eV is processed for SPA
          msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": SACS characterized by an energy other than 0.0253 eV"
          print_error(msg,"",force)
          skip=True
          return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running

    if len(index2)==1:
      factor2=dict_retrieval("025","keyword",unit2,"conversion_factor")
      if factor2 is None:
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Conversion factor not found: "+unit2
        print_error(msg,"",True)
        skip=True
        return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running
      else:
        value2=value2*factor2

    if len(index2)==0:
      if operation1==2:
        value=value1/2
      else:
        value=value1
      if unit1=="PER-CENT":
        flag_percent[family]="%"
    else:
      if operation1==1:
        value=(value1+value2)/2
      elif operation1==3:
        value=(value1-value2)/2

    if family in value_out and family!=" ":
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Second usable data field for family "+family

      if len(index2)==0:
        msg+=" found under "+headings[index1[0]]+" and adopted"
      else:
        msg+=" found under "+headings[index1[0]]+","+headings[index2[0]]+" and adopted"
      print_error(msg,"",True)
          
    value_out[family]=value
    if family=="E" or family=="L":
      field_E=record["field"] # E2 or LVL
    elif family=="F" or family=="Q":
      field_F=record["field"] # E2 or LVL

    if len(index2)==1: # Calculation of uncertianty from *-min/*-max
      if operation1==1:
        if family=="A":
          family="B"
          operation2["B"]=operation2["A"]
        elif family=="E":
          family="F"
          operation2["F"]=operation2["E"]
          field_F=record["field"]
        elif family=="G":
          family="H"
          operation2["H"]=operation2["G"]
        elif family=="M":
          family="R"
          operation2["R"]=operation2["M"]
        elif family=="L":
          family="Q"
          operation2["Q"]=operation2["L"]
        flag_percent[family]=""
        value=(value1-value2)/2

        if family in value_out and family!=" ":
          msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Second usable data field for family "+family\
                       +" found under "+headings[index1[0]]+","+headings[index2[0]]+" and adopted"
          print_error(msg,"",True)

        value_out[family]=value


  if "*" not in value_out: # DATA is empty (e.g., in multiple reaction formalism)
    skip=True
    nodata=True
    return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running

  family_constant=dict(sorted(family_index.items(),key=itemgetter(1)))
  if len(family_constant)>0:
    last_key=list(family_constant.keys())[-1] # mostinner variable -> running family
    if last_key=="I" or last_key=="J" or last_key=="T": # I: ELEMENT etc., J: MASS etc., T: ISOMER etc.
      while last_key=="I" or last_key=="J" or last_key=="T":
        family_constant.popitem()
        if len(family_constant)>0:
          last_key=list(family_constant.keys())[-1]
        else:
          last_key=""
      family_running="I" # product nuclide distribution
    else:
      family_constant.popitem()
      family_running=last_key

  if field_F!="" and field_E!=field_F: # Both secondary energy and its uncertainty must be E2 or LVL
    if field_E=="E2":
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Outgoing energy given with level energy uncertainty"
    else:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Level energy given with outgoing energy uncertainty"
    print_error(msg,"",force)
    skip=True
    return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running

  if "M" in family_constant:
    family_constant["A"]=family_constant.pop("M")
  if "L" in family_constant:
    family_constant["E"]=family_constant.pop("L")

  return skip,nodata,value_out,frame_inp,operation2,flag_percent,field_E,family_constant,family_running


def convert_percent(j,ansan_out,flag_percent,value_out):
  family_uncertainty={" ": "*",
                      "B": "A",
                      "D": "C",
                      "F": "E",
                      "H": "G",
                      "R": "M"}
  for family_unc, family_val in family_uncertainty.items():
     if family_unc in value_out:
       if flag_percent[family_unc]=="%":
         if family_val in value_out:
           value_out[family_unc]=value_out[family_unc]*value_out[family_val]*0.01
         else:
           if family_unc=="B":
             msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Incident energy uncertainty without incident energy"
             print_error(msg,"",True)
           elif family_unc=="H":
             msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Angle uncertainty without angle"
             print_error(msg,"",True)
           elif family_unc=="F":
             msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Secondary energy uncertainty without secondary energy"
             print_error(msg,"",True)
           value_out.pop(family_unc)

  return value_out


def operation2_data(j,ansan_out,sf1,sf2,sf3,sf4,value_out,frame_inp,field_E,operation2):
  skip=False

  if "A" in operation2:
    if operation2["A"]==1: # Tcm -> Tinc
      m1=get_atomicweight(sf1)*ueV
      m2=get_atomicweight(sf2)*ueV
      tcm=value_out["A"]
      ecm=tcm+m1+m2
      tinc=(ecm**2-(m1+m2)**2)/(2*m1)
      value_out["A"]=tinc

      if "B" in value_out: # dTcm -> dTinc
        dtcm=value_out["B"]
        dtinc=(1+tcm/m1)*dtcm
        value_out["B"]=dtinc

  if "E" in value_out: # level energy, Q-value
    if operation2["E"]==6: # Q -> Tlab
      (skip,e_exc)=qval_to_eexc(j,ansan_out,value_out["E"],sf1,sf2,sf3,sf4)
      if skip:
        return skip,value_out,frame_inp
      else:
        value_out["E"]=e_exc
    elif operation2["E"]==10: # level number to level energy
      if value_out["E"]!=0:
        skip=True
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": non-zero level number LVL-NUMB: "+str(value_out["E"])
        print_error(msg,"","True")
        return skip,value_out,frame_inp

  if "G" in value_out:
    if operation2["G"]==7: # cos(theta) -> theta
      cosine=value_out["G"]
      if abs(cosine)>1:
        skip=True
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Illegal cosine value "+str(cosine)
        print_error(msg,"","True")
        return skip,value_out,frame_inp
      else:
        theta=math.degrees(math.acos(cosine))
        value_out["G"]=theta
    elif operation2["G"]==8 or operation2["G"]==9: # q(c.m.) -> theta(c.m.)
      if operation2["G"]==8:
        value_out["G"]=value_out["G"]*hbarc # 1/fm -> eV/c
      if sf3=="X":
        skip=True
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": qcm for inclusive reaction cannot be processed"
        print_error(msg,"","True")
        return skip,value_out,frame_inp
      elif ("E" in value_out and field_E=="E2"): # two-body cross section with outgoing energy as a variable
        skip=True
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": qcm with outgoing energy cannot be processed"
        print_error(msg,"","True")
        return skip,value_out,frame_inp
      else:
        m1=get_atomicweight(sf1)*ueV
        m2=get_atomicweight(sf2)*ueV
        m3=get_atomicweight(sf3)*ueV
        m4=get_atomicweight(sf4)*ueV
        tinc=value_out["A"]
        if "E" in value_out:
          m4=m4+value_out["E"]
        qcm=value_out["G"]
        (cosh,sinh,invmassq)=get_lorentzfactor(m1,m2,value_out["A"])
        pinccm=m1/math.sqrt(invmassq)*math.sqrt((tinc+m2)**2-m2**2)
        p3cm=tinc_to_pcm(tinc,m1,m2,m3,m4)
        cosinecm=(pinccm**2+p3cm**2-qcm**2)/(2*pinccm*p3cm)
        if abs(cosinecm)>1:
          skip=True
          msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Illegal cosine value "+str(cosinecm)
          print_error(msg,"","True")
          return skip,value_out,frame_inp
        else:
          thetacm=math.degrees(math.acos(cosinecm))
          value_out["G"]=thetacm
      
  if "H" in value_out:
    if operation2["H"]==7: # dcos(theta) -> dtheta, must be done after conversion for G
      dcosine=value_out["H"]
      dtheta=math.degrees(dcosine/abs(math.sin(math.radians(theta))))
      value_out["H"]=dtheta

  if "L" in value_out:
    if operation2["L"]==3: # p -> T
      p3=value_out["L"]
      m3=get_atomicweight(sf3)*ueV
      t3=math.sqrt(p3**2+m3**2)-m3
      value_out["E"]=t3
      frame_inp["E"]=frame_inp["L"]

  if "Q" in value_out:
    if operation2["Q"]==3: # dp -> dT
      dp3=value_out["Q"]
      m3=get_atomicweight(sf3)*ueV
      t3=value_out["E"]
      p3=math.sqrt((t3+m3)**2-m3**2)
      dt3=dp3*(p3/t3)
      value_out["F"]=dt3

  if "M" in value_out:
    if operation2["M"]==3: # pinc -> Tinc
      pinc=value_out["M"]
      m2=get_atomicweight(sf2)*ueV
      tinc=math.sqrt(pinc**2+m2**2)-m2
      value_out["A"]=tinc

  if "R" in value_out:
    if operation2["R"]==3: # dpinc -> dTinc
      pinc=value_out["M"]
      dpinc=value_out["R"]
      m2=get_atomicweight(sf2)*ueV
      dtinc=pinc/math.sqrt(m2**2+pinc**2)*dpinc
      value_out["B"]=dtinc

  return skip,value_out,frame_inp


def check_independentvariable(j,ansan_out,sf2,sf4,mf,value_out):
  skip=False

  if sf2!="0" and "A" not in value_out:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Incident energy is absent."
    print_error(msg,"",True)
    skip=True
  if (mf==4 or mf==6 or mf==14) and "G" not in value_out:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Outgoing angle is absent."
    print_error(msg,"",True)
    skip=True
  if (mf==5 or mf==6 or mf==15) and "E" not in value_out:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Outgoing energy is absent."
    print_error(msg,"",True)
    skip=True
  if sf4=="ELEM/MASS":
    if "I" not in value_out:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Atomic number is absent."
      print_error(msg,"",True)
      skip=True
    elif "J" not in value_out:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Mass number is absent."
      print_error(msg,"",True)
      skip=True

  return skip


def operation3_data(j,ansan_out,sf1,sf2,sf3,sf4,value_out,frame_inp,operation3):
  skip=False

  if "A" in operation3: # divide by the natural isotopic abundance
    abun=dict_retrieval("227","code",sf1,"isotopic_abundance")
    if abun is not None:
      value_out["*"]=value_out["*"]/abun
      if " " in value_out:
        value_out[" "]=value_out[" "]/abun
    else:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Natural isotopic abundance missing in Dict.227"
      print_error(msg,"",force)
      skip=True
      return skip,value_out,frame_inp

  if "RTE" in operation3: # sigma*sqrt(E) -> sigma
    einc=value_out["A"]
    value_out["*"]=value_out["*"]/math.sqrt(einc)
    if " " in value_out:
      value_out[" "]=value_out[" "]/math.sqrt(einc)

  if "SFC" in operation3: # S-factor -> sigma
    z1=float(get_charge(sf1))
    z2=float(get_charge(sf2))
    m1=get_atomicweight(sf1)*ueV
    m2=get_atomicweight(sf2)*ueV
    tcm=tinc_to_tcm(value_out["A"],m1,m2)
    if tcm==0:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Conversion of S(0) to cross section impossible"
      print_error(msg,"",True)
      skip=True
      return skip,value_out,frame_inp
    mu=m1*m2/(m1+m2)
    eta=alpha*z1*z2*math.sqrt(mu/2/tcm)
    value_out["*"]=value_out["*"]/tcm*math.exp(-2*math.pi*eta)
    if " " in value_out:
      value_out[" "]=value_out[" "]/tcm*math.exp(-2*math.pi*eta)

  if "4PI" in operation3: # divide by 4pi
    value_out["*"]=value_out["*"]/(4*pi)
    if " " in value_out:
      value_out[" "]=value_out[" "]/(4*pi)

  if "D4PI" in operation3: # multiply by 4pi
    value_out["*"]=value_out["*"]*4*pi
    if " " in value_out:
      value_out[" "]=value_out[" "]*4*pi

  if "DAM" in operation3: # multiply by the atomic mass of target
    aw1=get_atomicweight(sf1)
    value_out["*"]=value_out["*"]*aw1
    if " " in value_out:
      value_out[" "]=value_out[" "]*aw1

  if "DP" in operation3: # d/dp -> d/dE by multiplying p/E
    t3=value_out["E"]
    m3=get_atomicweight(sf2)*ueV
    p3=math.sqrt((t3+m3)**2-m3**2)
    value_out["*"]=value_out["*"]*(p3/t3)
    if " " in value_out:
      value_out[" "]=value_out[" "]*(p3/t3)

  if "RTH" in operation3: # Rutherford ratio -> sigma
    m1=get_atomicweight(sf1)*ueV
    m2=get_atomicweight(sf2)*ueV
    (cosh,sinh,invmassq)=get_lorentzfactor(m1,m2,value_out["A"])
    if "G" not in value_out:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Secondary angle not available for this data point"
      print_error(msg,"",True)
      skip=True
      return skip,value_out,frame_inp
    if frame_inp["G"]=="L":
      (skip,p3,p3cmsq)=anglab_to_plab(j,ansan_out,m1,m2,m2,m1,value_out["G"],cosh,sinh,invmassq)
      if skip:
        return skip,value_out,frame_inp
      ang3=value_out["G"]
      ang3cm=anglab_to_angcm(m2,ang3,p3,cosh,sinh)
      cos3cm=math.cos(math.radians(ang3cm))
    else:
      cos3cm=math.cos(math.radians(value_out["G"]))
    z1=float(get_charge(sf1))
    z2=float(get_charge(sf2))
    tcm=tinc_to_tcm(value_out["A"],m1,m2)
    sigruth_cm=((alpha*z1*z2)/(4*tcm*(1-cos3cm)/2))**2*hbarc**2/100.
    value_out["*"]=value_out["*"]*sigruth_cm
    if " " in value_out:
      value_out[" "]=value_out[" "]*sigruth_cm

    if frame_inp["G"]=="L": # sigma_cm -> sigma_lab if angle is given in lab. system (default)
      (skip,p3,p3cmsq)=anglab_to_plab(j,ansan_out,m1,m2,m2,m1,value_out["G"],cosh,sinh,invmassq)
      e3=math.sqrt(p3**2+m2**2)
      cos3=math.cos(math.radians(value_out["G"]))
      jacob=(math.sqrt(p3cmsq)/p3**2)*(p3*cosh-e3*cos3*sinh)
      value_out["*"]=value_out["*"]/jacob
      frame_inp["*"]="L"
      if " " in value_out:
        value_out[" "]=value_out[" "]/jacob
    else:
      frame_inp["*"]="C"

  return skip,value_out,frame_inp


def get_outputframe(mf,frame_inp):
  frame_out=dict()

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

  lorentz=False
  if mf==4:
    if frame_inp["G"]!=frame_out["G"] or frame_inp["*"]!=frame_out["*"]:
      lorentz=True
  elif mf==6:
    if frame_inp["G"]!=frame_out["G"] or frame_inp["E"]!=frame_out["E"] or frame_inp["*"]!=frame_out["*"]:
      lorentz=True

  return lorentz,frame_out


def get_lorentzfactor(m1,m2,t2):
  e2=t2+m2
  p2sq=e2**2-m2**2
  p2=math.sqrt(p2sq)
  invmassq=(m1+e2)**2-p2sq
  cosh=(m1+e2)/math.sqrt(invmassq)
  sinh=p2/math.sqrt(invmassq)

  return cosh,sinh,invmassq


def get_jacobian_angcmplab_to_pcm(m3,ang3cm,p3,cosh,sinh):
  sin3cm=math.sin(math.radians(ang3cm))
  cos3cm=math.cos(math.radians(ang3cm))
  e3=math.sqrt(m3**2+p3**2)

# partial p(cm)/partial theta(cm)
  jacob1=e3*sin3cm*sinh*(2+cos3cm**2*sinh**2) \
         /(1+sin3cm**2*sinh**2)**2 \
        -sin3cm*cos3cm*sinh**2*cosh*(m3**2-m3**2*sin3cm**2*sinh**2+2*p3**2) \
         /((1+sin3cm**2*sinh**2)**2*math.sqrt(p3**2-m3**2*sin3cm**2*sinh**2))

# partial p(cm)/partial p(lab)
  jacob2=p3/(1+sin3cm**2*sinh**2) \
         *(-cos3cm*sinh/e3+cosh/math.sqrt(p3**2-m3**2*sin3cm**2*sinh**2))

  return jacob1, jacob2


def get_jacobian_anglabpcm_to_plab(m3,ang3,p3cm,cosh,sinh):
  sin3=math.sin(math.radians(ang3))
  cos3=math.cos(math.radians(ang3))
  e3cm=math.sqrt(m3**2+p3cm**2)

# partial p(lab)/partial theta(lab)
  jacob1=-e3cm*sin3*sinh*(2+cos3**2*sinh**2) \
         /(1+sin3**2*sinh**2)**2 \
         -sin3*cos3*sinh**2*cosh*(m3**2-m3**2*sin3**2*sinh**2+2*p3cm**2) \
         /((1+sin3**2*sinh**2)**2*math.sqrt(p3cm**2-m3**2*sin3**2*sinh**2))

# partial p(lab)/partial p(cm)
  jacob2=p3cm/(1+sin3**2*sinh**2) \
         *(cos3*sinh/e3cm+cosh/math.sqrt(p3cm**2-m3**2*sin3**2*sinh**2))

  return jacob1, jacob2


def plabangcm_to_pcm(j,ansan_out,m3,p3,ang3cm,cosh,sinh):
  skip=False

  e3=math.sqrt(m3**2+p3**2)
  sin3cm=math.sin(math.radians(ang3cm))
  cos3cm=math.cos(math.radians(ang3cm))
  d=p3**2-m3**2*sin3cm**2*sinh**2
  if d<0:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Discriminant negative"
    print_error(msg,"",True)
    skip=True
    p3cm="NaN"
    return skip,p3cm

  p3cma=(-e3*cos3cm*sinh+cosh*math.sqrt(d))/(1+sin3cm**2*sinh**2)
  p3cmb=(-e3*cos3cm*sinh-cosh*math.sqrt(d))/(1+sin3cm**2*sinh**2)
  if p3cma>0 and p3cmb>0:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Two plab values exist for a given anglab"
    print_error(msg,"",True)
    skip=True
    p3cm="NaN"
  elif p3cma<0 and p3cmb<0:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": No positive plab value exists for a given anglab"
    print_error(msg,"",True)
    skip=True
    p3cm="NaN"
  else:
    p3cm=p3cma

  return skip,p3cm


def pcmanglab_to_plab(j,ansan_out,m3,p3cm,ang3,cosh,sinh):
  skip=False

  e3cm=math.sqrt(m3**2+p3cm**2)
  sin3=math.sin(math.radians(ang3))
  cos3=math.cos(math.radians(ang3))
  d=p3cm**2-m3**2*sin3**2*sinh**2

  if d<0:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Discriminant negative"
    print_error(msg,"",True)
    skip=True
    p3="NaN"
    return skip,p3

  p3a=(e3cm*cos3*sinh+cosh*math.sqrt(d))/(1+sin3**2*sinh**2)
  p3b=(e3cm*cos3*sinh-cosh*math.sqrt(d))/(1+sin3**2*sinh**2)
  if p3a>0 and p3b>0:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Two plab values exist for a given anglab"
    print_error(msg,"",True)
    skip=True
    p3="NaN"
  elif p3a<0 and p3b<0:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": No positive plab value exists for a given anglab"
    print_error(msg,"",True)
    skip=True
    p3="NaN"
  else:
    p3=p3a

  return skip,p3


def print_idx(l,tid,ansan_out,web_quantity,reaction_code,mf,mt,sf4_iso_char,j_tot,k_tot):
   mf="{:>4s}".format(str(mf))
   mt="{:>4s}".format(str(mt))
   sf4_iso_char="{:>4s}".format(str(sf4_iso_char))
   j_tot="{:>8s}".format(str(j_tot))
   k_tot="{:>8s}".format(str(k_tot))
   web_quantity="{:<5s}".format(web_quantity)
   l.write(ansan_out+" "+tid+"  "+mf+" "+mt+" "+sf4_iso_char+" "+j_tot+" "+k_tot+" "+web_quantity+" "+reaction_code+"\n")
   print(ansan_out,mf,mt,sf4_iso_char,j_tot,k_tot," ",web_quantity,reaction_code)

   return


def get_spectrum_flag(spec):
  spectrum_flags= {'BRS'   : "B"
                  ,'FIS'   : "F"
                  ,'MXW'   : "M"
                  ,'SDT'   : "D"
                  ,'SPA'   : "S"}

  if spec=="":
    spec_flag=" "
  elif "/" in spec:
    spec_flag="/"
  elif spec in spectrum_flags:
    spec_flag=spectrum_flags[spec]
  else:
    spec_flag="X"

  return spec_flag


def get_flag_cm(mf,mt,frame_inp,frame_out):
#       L: lab system, C: c.m. system
#
#       flag   sigma  theta    energy   
#---------------------------------------
# MF4     D      L      L               
#         E      C      C               
#         F      L      C               
#         G      C      L               
#---------------------------------------
# MF5     H      L               L      
#         I      C               C      
#         J      L               C      
#         K      C               L      
#---------------------------------------
# MF6     L      L      L        L      
#         M      C      C        C      
#         N      L      C        L      
#         O      L      L        C      
#         P      C      L        L      
#         Q      L      C        C      
#         R      C      C        L      
#         S      C      L        C      

  flag_cm_list={"   ": " ", \
                "LL ": "D", \
                "CC ": "E", \
                "LC ": "F", \
                "CL ": "G", \
                "L L": "H", \
                "C C": "I", \
                "L C": "J", \
                "C L": "K", \
                "LLL": "L", \
                "CCC": "M", \
                "LCL": "N", \
                "LLC": "O", \
                "CLL": "P", \
                "LCC": "Q", \
                "CCL": "R", \
                "CLC": "S"}

  flag=""
  header3="#F                                      "

  if mf==4 or mf==5 or mf==6 or mf==14 or mf==15: # reference frame for cross section
    if frame_out["*"]=="C":
      flag="C"
      header3+="   c.m.     c.m.  "
    else:
      flag="L"
      header3+="   lab.     lab.  "
  else:
    flag=" "
    header3+="                  "

  if mf==4 or mf==6 or mf==14: # reference frame for angle
    if frame_out["G"]=="C":
      flag+="C"
      header3+="   c.m.     c.m.  "
    else:
      flag+="L"
      header3+="   lab.     lab.  "
  else:
    header3+="                  "
    flag+=" "

  if mf==5 or mf==6 or mf==15: # reference frame for secondary energy
    if frame_out["E"]=="C":
      flag+="C"
      header3+="   c.m.     c.m.  "
    else:
      flag+="L"
      header3+="   lab.     lab.  "
  else:
    header3+="                  "
    flag+=" "

  header3+="                                     "

  if c4out:
    if "C" in flag:
      flag_cm="C"
    else:
      flag_cm=" "
  else:
    flag_cm=flag_cm_list[flag]

  return flag_cm,header3


def make_constant_text(value_out,family_constant,sf4_za,sf4_iso_char,frame_out,field_E):
  constants=[]
  if "A" in family_constant:
    einc='{:.3E}'.format(value_out["A"])
    constants.append("einc"+einc)
  if "G" in family_constant:
    if outcos:
      cos='{:+.2f}'.format(math.cos(math.radians(value_out["G"])))
      if frame_out["G"]=="C":
        constants.append("cosc"+cos)
      else:
        constants.append("cosl"+cos)
    else:
      ang='{:.0f}'.format(value_out["G"])
      if frame_out["G"]=="C":
        constants.append("angc"+ang)
      else:
        constants.append("angl"+ang)
  if "E" in family_constant:
    if field_E=="E2":
      eout='{:.3E}'.format(value_out["E"])
      if frame_out["E"]=="C":
        constants.append("eoutc"+eout)
      else:
        constants.append("eoutl"+eout)
    else:
      elvl='{:.3E}'.format(value_out["E"])
      constants.append("elvl"+elvl)
  if "I" in family_constant and "J" in family_constant:
    prod_z=int(float(sf4_za)/1000.)
    prod_a=int(float(sf4_za)-prod_z*1000.)
    prod=convert_z_to_s(str(prod_z))+str(prod_a)
    if sf4_iso_char!=" ":
      prod+=sf4_iso_char.lower()
    constants.append("prod"+prod)

  if constants is not None:
    constant_text="_".join(constants)
  else:
    constant_text=""
  return constant_text


def print_data(j,f,file_c6,ansan_out,subent_n2,trans_id,author,year,reference_code,reference_exp,doi,quantity,line_l,line_r,header_out,header_c4_out,mf,mt,spec,sf1,sf2,sf4,sf5,elemmass,value_out,frame_inp,frame_out,field_E,family_constant,family_running,header4_last,constant_last,x4_json,k_tot):
  (flag_cm,header3)=get_flag_cm(mf,mt,frame_inp,frame_out)

  printed=False
  line_out=line_l+flag_cm
  header4="#C                    "
  constant=""
  sf4_za=""
  sf4_iso_char=""

# Field 1
  if sf2=="0":
    line_out+="         "
    header4+="         "
  elif "A" in value_out:
    line_out+=print_value(value_out["A"])
    if "A" in family_constant:
      header4+=print_value(value_out["A"])
    else:
      header4+="         "
  else:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Incident energy value not available for this data point"
    print_error(msg,"",True)
    return f,header_out,header_c4_out,header4_last,constant_last,printed,k_tot

# Field 2
  if "B" in value_out:
    line_out+=print_value(value_out["B"])
    if "A" in family_constant:
      header4+=print_value(value_out["B"])
    else:
      header4+="         "
  else:
    line_out+="         "
    header4+="         "

# Field 3
  if "*" in value_out:
    line_out+=print_value(value_out["*"])
    header4+="         "
  else:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Quantity value not available for this data point"
    print_error(msg,"",True)
    return f,header_out,header_c4_out,header4_last,constant_last,printed,k_tot

# Field 4
  if " " in value_out:
    line_out+=print_value(value_out[" "])
  else:
    line_out+="         "
  header4+="         "

# Field 5
  if mf==4 or mf==6 or mf==14:
    if "G" in value_out:
      if outcos:
        line_out+=print_value(math.cos(math.radians(value_out["G"])))
        if "G" in family_constant:
          header4+=print_value(math.cos(math.radians(value_out["G"])))
        else:
          header4+="         "
      else:
        line_out+=print_value(value_out["G"])
        if "G" in family_constant:
          header4+=print_value(value_out["G"])
        else:
          header4+="         "
    else:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Secondary angle not available for this data point"
      print_error(msg,"",True)
      return f,header_out,header_c4_out,header4_last,constant_last,printed,k_tot

  elif not c4out and (mf==3 or mf==8): # product (Z,A)
    if elemmass: # products (Z,A) with Z>2 in SF4 or COMMON/DATA
      if sf4=="ELEM/MASS":
        z=str(int(value_out["I"]))
        a=str(int(value_out["J"]))
        if int(a)<10:
          a="00"+a 
        elif int(a)<100:
          a="0"+a 
        sf4_za=z+a
        if "T" in value_out:
          sf4_iso_data=str(int(value_out["T"]))
          if sf4_iso_data=="0":
            sf4_iso_char="G"
          elif sf4_iso_data=="1":
            sf4_iso_char="M"
          elif sf4_iso_data=="2":
            sf4_iso_char="N"
        else:
          sf4_iso_data=" "
        line_out+=print_product(sf4_za,sf4_iso_data)
        if "I" in family_constant and "J" in family_constant:
          header4+=print_product(sf4_za,sf4_iso_data)
        else:
          header4+="         "
      else:
        family_constant["I"]=-1 # dummy value
        family_constant["J"]=-1 # dummy value
        (sf4_za,sf4_iso_char,sf4_iso_num)=nucl_numeq(sf4)
        line_out+=print_product(sf4_za,sf4_iso_char)
        header4+=print_product(sf4_za,sf4_iso_char)

    else:
      line_out+="         "
      header4+="         "

  elif c4out and mf==8: # atomic number
    if sf4=="ELEM/MASS":
      line_out+=print_value(value_out["I"])
      if "I" in family_constant:
        header4+=print_value(value_out["I"])
      else:
        header4+="         "
    else:
      m=re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(\-[GML0-9\+\/]+)?$").search(sf4)
      z=m.group(1)
      line_out+=print_value(float(z))
      if "I" in family_constant:
        header4+=print_value(value_out["I"])
      else:
        header4+="         "

  else:
    line_out+="         "
    header4+="         "

# Field 6
  if c4out and mf==3: # product (Z,A)
    if elemmass: # products (Z,A) with Z>2 in SF4 or COMMON/DATA
      if sf4=="ELEM/MASS":
        z=str(int(value_out["I"]))
        a=str(int(value_out["J"]))
        if int(a)<10:
          a="00"+a 
        elif int(a)<100:
          a="0"+a 
        sf4_za=z+a
        if "T" in value_out:
          sf4_iso_data=str(int(value_out["T"]))
          if sf4_iso_data=="0":
            sf4_iso_char="G"
          elif sf4_iso_data=="1":
            sf4_iso_char="M"
          elif sf4_iso_data=="2":
            sf4_iso_char="N"
        else:
          sf4_iso_data=" "
        line_out+=print_product(sf4_za,sf4_iso_data)
        if "I" in family_constant and "J" in family_constant:
          header4+=print_product(sf4_za,sf4_iso_data)
        else:
          header4+="         "
      else:
        family_constant["I"]=-1 # dummy value
        family_constant["J"]=-1 # dummy value
        (sf4_za,sf4_iso_char,sf4_iso_num)=nucl_numeq(sf4)
        line_out+=print_product(sf4_za,sf4_iso_char)
        header4+=print_product(sf4_za,sf4_iso_char)

    else:
      line_out+="         "
      header4+="         "

  elif mf==4 or mf==6 or mf==14:

    if "H" in value_out:
      if outcos:
        line_out+=print_value(math.radians(value_out["H"])*abs(math.sin(math.radians(value_out["G"]))))
        if "G" in family_constant:
          header4+=print_value(math.radians(value_out["H"])*abs(math.sin(math.radians(value_out["G"]))))
        else:
          header4+="         "
      else:
        line_out+=print_value(value_out["H"])
        if "G" in family_constant:
          header4+=print_value(value_out["H"])
        else:
          header4+="         "

    else:
      line_out+="         "
      header4+="         "

  elif c4out and mf==8: # mass number
    if sf4=="ELEM/MASS":
      line_out+=print_value(value_out["J"])
      if "J" in family_constant:
        header4+=print_value(value_out["J"])
      else:
        header4+="         "
    else:
      m=re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(\-[GML0-9\+\/]+)?$").search(sf4)
      a=m.group(3)
      line_out+=print_value(float(a))
      header4+=print_value(float(a))
  else:
    line_out+="         "
    header4+="         "

# Field 7
  if mf==3 or mf==4 or mf==13 or mf==14:
    if sf5=="PAR":
      if "E" in value_out:
        line_out+=print_value(value_out["E"])
        if "E" in family_constant:
          header4+=print_value(value_out["E"])
        else:
          header4+="         "
      else:
        msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Secondary energy not available for this data point"
        print_error(msg,"",True)
        return f,header_out,header_c4_out,header4_last,constant_last,printed,k_tot
    else:
      line_out+="         "
      header4+="         "

  elif mf==5 or mf==6 or mf==15:
    if "E" in value_out:
      line_out+=print_value(value_out["E"])
      if "E" in family_constant:
        header4+=print_value(value_out["E"])
      else:
        header4+="         "
    else:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Secondary energy not available for this data point"
      print_error(msg,"",True)
      return f,header_out,header_c4_out,header4_last,constant_last,printed,k_tot

  elif c4out and mf==8: # Isomeric flag
    if sf4=="ELEM/MASS":
      if "T" in value_out:
        line_out+=print_value(value_out["T"])
        if "T" in family_constant:
          header4+=print_value(value_out["T"])
        else:
          header4+="         "
      else:
        line_out+=print_value(9)
        if "T" in family_constant:
          header4+=print_value(9)
        else:
          header4+="         "
    else:
      if re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)-(\w+)$").search(sf4):
        (sf4_za,sf4_iso_char,sf4_iso_num)=nucl_numeq(sf4)
        line_out+=print_value(float(sf4_iso_num))
        header4+=print_value(float(sf4_iso_num))
      else:
        line_out+=print_value(9)
        if "T" in family_constant:
          header4+=print_value(9)
        else:
          header4+="         "
  else:
    line_out+="         "
    header4+="         "

# Field 8
  if mf==3 or mf==4 or mf==14:
    if sf5=="PAR" and "F" in value_out:
      line_out+=print_value(value_out["F"])
      if "E" in family_constant:
        header4+=print_value(value_out["F"])
      else:
        header4+="         "
    else:
      line_out+="         "
      header4+="         "

  elif mf==5 or mf==6 or mf==15:
    if "F" in value_out:
      line_out+=print_value(value_out["F"])
      if "E" in family_constant:
        header4+=print_value(value_out["F"])
      else:
        header4+="         "
    else:
      line_out+="         "
      header4+="         "

  else:
    line_out+="         "
    header4+="         "

# Identification data field
  if mf==3 or mf==4:
    if sf5=="PAR":
      line_out+='{:>3}'.format(field_E)
      if "E" in family_constant:
        header4+='{:>3}'.format(field_E)
      else:
        header4+="   "
    else:
      line_out+="   "
      header4+="   "

  elif mf==5 or mf==6:
    line_out+='{:>3}'.format(field_E)
    if "E" in family_constant:
      header4+='{:>3}'.format(field_E)
    else:
      header4+="   "

  else:
    line_out+="   "
    header4+="   "

  line_out+=line_r

# Header lines
  if c4out and header_c4_out:
    print_header_c4_top(f,ansan_out,x4_json,reference_code,reference_exp,doi,year)
    header_c4_out=False

  if header4!=header4_last and (seplvl==2 or seplvl==3):
    header_out=True

  if header_out:
    if header4!=header4_last and header4_last!="" and (seplvl==2 or seplvl==3):
      if c4out:
        f.write("#/DATA      "+str(k_tot)+"\n")
        f.write("#/DATASET\n")
        k_tot=0
      else:
        f.write("\n")
        f.write("\n")
      if seplvl==3:
        f.close()
        (file_c6_pre,prod_const)=make_file_c6_pre(sf1,sf2,line_l,family_running,field_E,frame_out,spec)
        file_c6_new=file_c6+file_c6_pre
        constant=get_authoryear(author,year)
        if prod_const!="":
          constant="prod"+prod_const+"_"+constant
        if constant_last!="":
          constant=constant_last+"_"+constant
        file_c6_new+="-"+constant
        if c4out:
          file_c6_new+=".c4"
        else:
          file_c6_new+=".c6"
        shutil.move(file_c6,file_c6_new)
        f=open(file_c6,"w")
        if c4out:
          print_header_c4_top(f,ansan_out,x4_json,reference_code,reference_exp,doi,year)

    if c4out:
      print_header_c4(f,ansan_out,x4_json,line_l,sf4)
      if mf==8: # sf4_za and sf4_iso is not generated during field value preparation
        if elemmass: # products (Z,A) with Z>2 in SF4 or COMMON/DATA
          if sf4=="ELEM/MASS":
            z=str(int(value_out["I"]))
            a=str(int(value_out["J"]))
            if int(a)<10:
              a="00"+a 
            elif int(a)<100:
              a="0"+a 
            sf4_za=z+a
            if "T" in value_out:
              sf4_iso_char=str(int(value_out["T"]))
            else:
              sf4_iso_char=" "
          else:
            family_constant["I"]=-1 # dummy value
            family_constant["J"]=-1 # dummy value
            (sf4_za,sf4_iso_char,sf4_iso_num)=nucl_numeq(sf4)

    else:
      print_header_c6(f,ansan_out,x4_json,subent_n2,trans_id,author,reference_exp,doi,quantity,mf,mt,elemmass,sf2,sf5,field_E,header3,header4,spec)

    constant_last=make_constant_text(value_out,family_constant,sf4_za,sf4_iso_char,frame_out,field_E)
    header4_last=header4
    header_out=False

  f.write(line_out+"\n")
  printed=True

  return f,header_out,header_c4_out,header4_last,constant_last,printed,k_tot


def convert_z_to_s(z):
  z_to_s={\
    "0": "Nn",
    "1": "H",     "2": "He",    "3": "Li",    "4": "Be",    "5": "B",     "6": "C",     "7": "N",     "8": "O",     "9": "F",    "10": "Ne", \
   "11": "Na",   "12": "Mg",   "13": "Al",   "14": "Si",   "15": "P",    "16": "S",    "17": "Cl",   "18": "Ar",   "19": "K",    "20": "Ca", \
   "21": "Sc",   "22": "Ti",   "23": "V",    "24": "Cr",   "25": "Mn",   "26": "Fe",   "27": "Co",   "28": "Ni",   "29": "Cu",   "30": "Zn", \
   "31": "Ga",   "32": "Ge",   "33": "As",   "34": "Se",   "35": "Br",   "36": "Kr",   "37": "Rb",   "38": "Sr",   "39": "Y",    "40": "Zr", \
   "41": "Nb",   "42": "Mo",   "43": "Tc",   "44": "Ru",   "45": "Rh",   "46": "Pd",   "47": "Ag",   "48": "Cd",   "49": "In",   "50": "Sn", \
   "51": "Sb",   "52": "Te",   "53": "I",    "54": "Xe",   "55": "Cs",   "56": "Ba",   "57": "La",   "58": "Ce",   "59": "Pr",   "60": "Nd", \
   "61": "Pm",   "62": "Sm",   "63": "Eu",   "64": "Gd",   "65": "Tb",   "66": "Dy",   "67": "Ho",   "68": "Er",   "69": "Tm",   "70": "Yb", \
   "71": "Lu",   "72": "Hf",   "73": "Ta",   "74": "W",    "75": "Re",   "76": "Os",   "77": "Ir",   "78": "Pt",   "79": "Au",   "80": "Hg", \
   "81": "Tl",   "82": "Pb",   "83": "Bi",   "84": "Po",   "85": "At",   "86": "Rn",   "87": "Fr",   "88": "Ra",   "89": "Ac",   "90": "Th", \
   "91": "Pa",   "92": "U",    "93": "Np",   "94": "Pu",   "95": "Am",   "96": "Cm",   "97": "Bk",   "98": "Cf",   "99": "Es",  "100": "Fm", \
  "101": "Md",  "102": "No",  "103": "Lr",  "104": "Rf",  "105": "Db",  "106": "Sg",  "107": "Bh",  "108": "Hs",  "109": "Mt",  "110": "Ds", \
  "111": "Rg",  "112": "Cn",  "113": "Nh",  "114": "Fl",  "115": "Mc",  "116": "Lv",  "117": "Ts",  "118": "Og",  "119": "Uue", "120": "Ubn",\
  "121": "Ubu", "122": "Ubb", "123": "Ubt", "124": "Ubq", "125": "Ubp", "126": "Ubh", "127": "Ubs", "128": "Ubo", "129": "Ube", "130": "Utn"}

  s=z_to_s[z]
  return s


def convert_mt_to_reac(mt):
  mt_to_reac={\
   "1": "tot",    "2": "el",     "3": "non",   "4": "n",\
  "11": "2nd",   "16": "2n",    "17": "3n",   "18": "f",\
  "22": "na",    "23": "n3a",   "24": "2na",  "25": "3na",  "27": "abs",   "28": "np",   "29": "n2a",\
  "30": "2n2a",  "32": "nd",    "33": "nt",   "34": "nh",   "35": "nd2a",  "36": "nt2a", "37": "4n",\
  "41": "2np",   "42": "3np",   "44": "n2p",  "45": "npa",\
  "50": "n",     "51": "inl",\
 "102": "g",    "103": "p",    "104": "d",   "105": "t",    "106": "h",    "107": "a",    "108": "2a",   "109": "3a",\
 "111": "2p",   "112": "pa",   "113": "t2a", "114": "d2a",  "115": "pd",   "116": "pt",   "117": "da",\
 "152": "5n",   "153": "6n",   "154": "2nt", "155": "ta",   "156": "4np",  "157": "3nd",  "158": "nda",  "159": "2npa",\
 "160": "7n",   "161": "8n",   "162": "5np", "163": "6np",  "164": "7np",  "165": "4na",  "166": "5na",  "167": "6na",  "168": "7na",  "169": "4nd",\
 "170": "5nd",  "171": "6nd",  "172": "3nt", "173": "4nt",  "174": "5nt",  "175": "6nt",  "176": "2nh",  "177": "3nh",  "178": "4nh",  "179": "3n2p",\
 "180": "3n2a", "181": "3npa", "182": "dt",  "183": "npd",  "184": "npt",  "185": "ndt",  "186": "nph",  "187": "ndh",  "188": "nth",  "189": "nta",\
 "190": "2n2p", "191": "ph",   "192": "dh",  "193": "ha",   "194": "4n2p", "195": "4n2a", "196": "4npa", "197": "3p",   "198": "n3p",  "199": "3n2pa",\
 "200": "5n2p", "201": "xn",   "202": "xg",  "203": "xp",   "204": "xd",   "205": "xt",   "206": "xh",   "207": "xa",   "208": "xpip", "209": "xpi0",\
 "210": "xpin", "213": "xKp",  "216": "xKn", "217": "xpbar","218": "xnbar",\
 "452": "f",    "454": "x",    "455": "f",   "456": "f",    "459": "x",\
 "600": "p",    "601": "inl",  "650": "d",   "651": "inl",\
 "700": "t",    "701": "inl",  "750": "h",   "751": "inl",\
 "800": "a",    "801": "inl"}

  reac=mt_to_reac[mt]
  return reac


def convert_mt_to_zasum(mt):
  mt_to_zasum={\
   "4": [0,1],\
  "11": [1,4],   "16": [0,2],   "17": [0,3],\
  "22": [2,5],   "23": [6,13],  "24": [2,6],  "25": [2,7],  "28": [1,2],   "29": [4,9],\
  "30": [4,10],  "32": [1,3],   "33": [1,4],  "34": [2,4],  "35": [5,11],  "36": [5,12],  "37": [0,4],\
  "41": [1,3],   "42": [1,4],   "44": [2,3],  "45": [3,6],\
  "50": [0,1],   "51": [0,1],\
 "102": [0,0],  "103": [1,1],  "104": [1,2], "105": [1,3], "106": [2,3],  "107": [2,4],  "108": [4,8],  "109": [6,12],\
 "111": [2,2],  "112": [3,5],  "113": [5,11],"114": [5,10],"115": [2,3],  "116": [2,4],  "117": [3,6],\
 "152": [0,5],  "153": [0,6],  "154": [1,5], "155": [3,7], "156": [1,5],  "157": [1,5],  "158": [3,7],  "159": [3,7],\
 "160": [0,7],  "161": [0,8],  "162": [1,6], "163": [1,7], "164": [1,8],  "165": [2,8],  "166": [2,9],  "167": [2,10], "168": [2,11],"169": [1,6],\
 "170": [1,7],  "171": [1,8],  "172": [1,6], "173": [1,7], "174": [1,8],  "175": [1,9],  "176": [2,5],  "177": [2,6],  "178": [2,7], "179": [2,5],\
 "180": [4,11], "181": [3,8],  "182": [2,5], "183": [2,4], "184": [2,5],  "185": [2,6],  "186": [3,5],  "187": [3,6],  "188": [3,7], "189": [3,8],\
 "190": [2,4],  "191": [3,4],  "192": [3,5], "193": [4,7], "194": [2,6],  "195": [4,12], "196": [3,9],  "197": [3,3],  "198": [3,4], "199": [4,9],\
 "200": [2,7],
 "600": [1,1],  "601": [1,1],  "650": [1,2], "651": [1,2],\
 "700": [1,3],  "701": [1,3],  "750": [2,3], "751": [2,3],\
 "800": [2,4],  "801": [2,4]}

  if mt in mt_to_zasum:
    reac=mt_to_zasum[mt]
  else:
    reac=[]
  return reac


def make_file_c6_pre(sf1,sf2,line_l,family_running,field_E,frame_out,spec):
  m=re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(\-[GML][0-9]?)?$").search(sf1)
  targ_z=m.group(1)
  targ_a=m.group(3)
  targ=nucl_text(sf1,2)

  m=re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(\-[GML][0-9]?)?$").search(sf2)
  if m:
    proj=nucl_text(sf2,2)
    proj_z=m.group(1)
    proj_a=m.group(3)
  else:
    if sf2=="0":
      proj="0"
      proj_z=0
      proj_a=0
    elif sf2=="G":
      proj="g"
      proj_z=0
      proj_a=0
    elif sf2=="N":
      proj="n"
      proj_z=0
      proj_a=1
    elif sf2=="P":
      proj="p"
      proj_z=1
      proj_a=1
    elif sf2=="D":
      proj="d"
      proj_z=1
      proj_a=2
    elif sf2=="T":
      proj="t"
      proj_z=1
      proj_a=3
    elif sf2=="HE3":
      proj="h"
      proj_z=2
      proj_a=3
    elif sf2=="A":
      proj="a"
      proj_z=2
      proj_a=4
    else:
      proj="?"
      proj_z="?"
      proj_a="?"

  mf=line_l[12:15].strip()
  mt=line_l[15:19].strip()
  iso=line_l[19:20].strip()

  if mf=="1" and mt=="452":
    reac="f"
    quan="nut"
  elif mf=="1" and mt=="455":
    reac="f"
    quan="nud"
  elif mf=="1" and mt=="456":
    reac="f"
    quan="nup"
  elif mf=="3" and mt=="459":
    reac="x"
    quan="sigc"
  elif mf=="8" and mt=="454":
    reac="f"
    quan="fyi"
  elif mf=="8" and mt=="459":
    reac="f"
    quan="fyc"
  else:
    if mf=="3":
      quan="sig"
    elif mf=="4":
      quan="adx"
    elif mf=="5":
      quan="edx"
    elif mf=="6":
      quan="ddx"
    elif mf=="13":
      quan="sigg"
    elif mf=="14":
      quan="adxg"
    elif mf=="15":
      quan="edxg"
    if mf=="4" or mf=="5" or mf=="6" or mf=="14" or mf=="15":
      if frame_out["*"]=="C":
        quan+="c"
      else:
        quan+="l"
    if mt=="4" and proj=="n":
      reac="inl"
    elif mt=="102" and proj=="g":
      reac="inl"
    elif mt=="103" and proj=="p":
      reac="inl"
    elif mt=="104" and proj=="d":
      reac="inl"
    elif mt=="105" and proj=="t":
      reac="inl"
    elif mt=="106" and proj=="h":
      reac="inl"
    elif mt=="107" and proj=="a":
      reac="inl"
    else:
      reac=convert_mt_to_reac(mt)

  if spec=="":
    spec_text="mon"
  else:
    spec_text=spec.lower()

  if reac=="el" or reac=="inl":
    prod_const=targ
    prod_const+=iso.lower()
  elif len(targ_a)!=0:
    dzda=convert_mt_to_zasum(mt)
    if len(dzda)==2:
      if proj_z=="":
        proj_z="0"
      if proj_a=="":
        proj_a="0"
      if targ_z=="":
        targ_z="0"
      if targ_a=="":
        targ_a="0"
      prod_z=int(targ_z)+int(proj_z)-dzda[0]
      prod_a=int(targ_a)+int(proj_a)-dzda[1]
      prod_const=convert_z_to_s(str(prod_z))+str(prod_a)
      prod_const+=iso.lower()
    else:
      prod_const=""
  else:
    prod_const=""

  if family_running=="A" or family_running=="M":
    dist="excfun"
  elif family_running=="E" or family_running=="L":
    if field_E=="E2":
      if frame_out["E"]=="C":
        dist="enedisc"
      else:
        dist="enedisl"
    else:
      dist="lvldis"
  elif family_running=="G":
    if frame_out["G"]=="C":
      dist="angdisc"
    else:
      dist="angdisl"
  elif family_running=="I":
    dist="nucdis"
  elif proj=="0" and (mt=="452" or mt=="455" or mt=="456"):
    dist="sponnu"
  elif proj=="0" and (mt=="454" or mt=="459"):
    dist="nucdis"
  else:
    dist="othdis"

  file_c6_pre="-"+proj+"-"+targ+"-"+reac+"-"+quan+"-"+dist+"-"+spec_text

  return file_c6_pre,prod_const


def print_header_c4(f,ansan_out,x4_json,line_l,sf4):
  an=ansan_out[0:5]
  san=ansan_out[6:9]
  pointer=ansan_out[10:11]
  f.write("#\n")
  f.write("#DATASET    "+an+san+pointer+"\n")
  date=str(x4_json["SUBENT"]["N2"])
  f.write("#DATE       "+date+"\n")
  reaction=str(x4_json["REACTION"][0]["coded_information"]["code"])
  f.write("#REACTION   "+reaction+"\n")
  proj=re.sub(r"^\s+", "",line_l[0:5])
  f.write("#PROJ       "+proj+"\n")
  targ=re.sub(r"^\s+", "",line_l[5:11])
  targr='{:<7}'.format(targ)
  f.write("#TARG       "+targ+"\n")
  mf=re.sub(r"\s+", "",line_l[12:15])
  f.write("#MF         "+mf+"\n")
  mt=re.sub(r"\s+", "",line_l[15:19])
  f.write("#MT         "+mt+"\n")
  if re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(\-[GML0-9\+\/]+)?$").search(sf4):
    f.write("#PRODUCT    "+sf4+"\n")
  c4begin=line_l[0:21]
  f.write("#C4BEGIN    ["+c4begin+"]\n")
  f.write("#DATA       0\n")
  f.write("# Prj Targ M MF MT PXC  Energy  dEnergy  Data      dData   Cos/LO   dCos/LO   ELV/HL  dELV/HL I78 Refer (YY)              EntrySubP\n")
  f.write("#---><---->o<-><-->ooo<-------><-------><-------><-------><-------><-------><-------><-------><-><-----------------------><---><->o\n")

  return


def uptolow_author(author):
  if re.compile(r"[A-Z]+").search(author):
    author=re.sub(r"[A-Z]+", lambda m:m.group(0).capitalize(),author)
    m=re.compile(r"Mc([a-z])").search(author)
    if m:
      author=re.sub(r"Mc([a-z])","Mc"+m.group(1).upper(),author)
  return author


def print_header_c4_top(f,ansan_out,x4_json,reference_code,reference_exp,doi,year):
  an=ansan_out[0:5]
  f.write("#ENTRY      "+an+"\n")

  if "AUTHOR" in x4_json:
    author=x4_json["AUTHOR"][0]["coded_information"][0]
    author=uptolow_author(author)
    if len(author)>1:
      f.write("#AUTHOR1    "+author+"+\n")
    else:
      f.write("#AUTHOR1    "+author+"\n")

  if  "REFERENCE" in x4_json:
    f.write("#YEAR       "+year+"\n")

  if "INSTITUTE" in x4_json:
    institute=x4_json["INSTITUTE"][0]["coded_information"]
    f.write("#INSTITUTE  ("+institute[0]+")\n")

  if "TITLE" in x4_json:
    for i, item in enumerate(x4_json["TITLE"][0]["free_text"]):
      item=re.sub(r"^\s+","",item)
      if i==0:
        f.write("#TITLE      "+item+"\n")
      else:
        f.write("#+          "+item+"\n")

  if "AUTHOR" in x4_json:
    str=""
    out=True
    for i, author in enumerate(x4_json["AUTHOR"][0]["coded_information"]):
      author=uptolow_author(author)
      if i==len(x4_json["AUTHOR"][0]["coded_information"])-1: # last author
        str+=author
      else:
        str+=author+", "
      if len(str)>55 or i==len(x4_json["AUTHOR"][0]["coded_information"])-1:
        if out:
          f.write("#AUTHOR(S)  "+str+"\n")
          out=False
        else:
          str=re.sub(r"^\s+","",str)
          f.write("#+          "+str+"\n")
        str=""

  if  "REFERENCE" in x4_json:
    f.write("#REF-CODE   ("+reference_code+")\n")
    if doi is None:
      f.write("#REFERENCE  "+reference_exp+"\n")
    else:
      f.write("#REFERENCE  "+reference_exp+" (doi:"+doi+")\n")

  f.write("#DATASETS   "+"0"+"\n")


def print_header_c6(f,ansan_out,x4_json,subent_n2,trans_id,author,reference_exp,doi,quantity,mf,mt,elemmass,sf2,sf5,field_E,header3,header4,spec):
  f.write("# EXFOR #   : "+ansan_out+"\n")
  f.write("# EXFOR Ver.: "+subent_n2+"\n")
  f.write("# TRANS #   : "+trans_id+"\n")
  f.write("# Author    : "+author+"\n")
  f.write("# Reference : "+reference_exp+"\n")
  if doi is None:
    f.write("# DOI       : N/A\n")
  else:
    f.write("# DOI       : "+doi+"\n")
  f.write("# Quantity  : "+quantity+"\n")
  coded_information=x4_json["REACTION"][0]["coded_information"]
  if coded_information["unit_combination"]=="((%)=(%))":
    sf1=coded_information["code_unit"][0]["field"]["target"]
    if sf1=="1-H-1" or sf1=="1-H-2" or sf1=="1-H-3" or sf1=="2-HE-3" or sf1=="2-HE-4":
      index=1
    else:
      index=0
  else:
    index=0
  f.write("# REACTION  : "+str(x4_json["REACTION"][0]["coded_information"]["code_unit"][index]["unit"])+"\n")
  f.write("# MF/MT     : "+str(mf)+"/"+str(mt)+"\n")

  header1="#Proj Targ M MF MT ISC"
  header2="#                     "

  if sf2=="0":
    header1+="                  "
    header2+="                  "
  elif spec=="":
    header1+="   Einc    dEinc  "
    header2+="    eV       eV   "
  else:
    header1+="  <Einc>  d<Einc> "
    header2+="    eV       eV   "

  if mf==1:
    if mt==452:
      header1+="   nu-t    dnu-t                    "
    elif mt==455:
      header1+="   nu-d    dnu-d                    "
    elif mt==456:
      header1+="   nu-p    dnu-p                    "
    header2+="   /fiss   /fiss                    "

  elif mf==3 or mf==13:
    if elemmass:
      header1+="   sig     dsig    Product          "
      header2+="    b       b      1000*Z+A         "
    else:
      header1+="   sig     dsig                     "
      header2+="    b       b                       "
    if sf5=="PAR":
      if field_E=="E2":
        header1+="   Eout     dEout    "
        header2+="    eV       eV      "
      else:
        header1+="   Elvl     dElvl    "
        header2+="    eV       eV      "
    else:
      header1+="                     "
      header2+="                     "

  elif mf==4 or mf==14:
    header1+="   adx      dadx    theta    dtheta "
    header2+="   b/sr     b/sr     deg      deg   "


    if sf5=="PAR":
      if field_E=="E2":
        header1+="   Eout     dEout    "
        header2+="    eV       eV      "
      else:
        header1+="   Elvl     dElvl    "
        header2+="    eV       eV      "
    else:
      header1+="                     "
      header2+="                     "


  elif mf==5 or mf==15:
    if field_E=="E2":
      header1+="   edx      dedx                       Eout     dEout    "
      header2+="   b/eV     b/eV                        eV       eV      "
    else:
      header1+="   edx      dedx                       Elvl     dElvl     "
      header2+="   b/eV     b/eV                        eV       eV       "

  elif mf==6:
    header1+="   ddx      dddx    theta  "
    header2+="  b/sr/eV b/sr/eV    deg   "
    header1+="  dtheta "
    header2+="   deg   "
    if field_E=="E2":
      header1+="   Eout     dEout    "
      header2+="    eV       eV      "
    else:
      header1+="   Elvl     dElvl    "
      header2+="    eV       eV      "

  elif mf==8:
    if mt==454:
      header1+="    fyi     dfyi   Product                               "
      header2+="   /fis     /fis   1000*Z+A                              "
    elif mt==459:
      header1+="    fyc     dfyc   Product                               "
      header2+="   /fis     /fis   1000*Z+A                              "

  else:
    header1+="                                                         "
    header2+="                                                         "

  header1+="Author               (YY)EntrySubP"
  header2+="                                  "
  f.write("#\n")
  f.write(header1+"\n")
  f.write(header2+"\n")
  f.write(header3+"\n")
  if seplvl==2 or seplvl==3:
    f.write(header4+"\n")
  else:
    f.write("#C\n")
  f.write("#---><---->o<-><-->ooo<-------><-------><-------><-------><-------><-------><-------><-------><-><-----------------------><---><->o\n")

  return


def convert_energy_per_mass(value,unit,sf2):
  partnucl= {'A'   : '2-HE-4'
            ,'AN'  : '0-AN-1'
            ,'AP'  : '1-AP-1'
            ,'D'   : '1-H-2'
            ,'HE3' : '2-HE-3'
            ,'N'   : '0-NN-1'
            ,'P'   : '1-H-1'
            ,'T'   : '1-H-3'}

  skip=False

  if sf2 in partnucl:
    sf2=partnucl[sf2] 
  if re.compile(r"^\d+\-([A-Z][A-Z0]?|\*)\-(\d+)(-\w+)?$").search(sf2):
    m=re.compile(r"^\d+\-([A-Z][A-Z0]?|\*)\-(\d+)(-\w+)?$").search(sf2)
    a=m.group(2)
    if unit=="MEV/A":
      value=value*float(a)*1E+06
    else:
      value=value*float(a)*1E+09
  else:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Conversion from eV/A -> eV impossible"
    print_error(msg,"",force)
    skip=True
  return skip,value


def anglab_to_plab(j,ansan_out,m1,m2,m3,m4,ang3,cosh,sinh,invmassq):
  skip=False

  p3cmsq=((invmassq-m3**2-m4**2)**2-4*m3**2*m4**2)/(4*invmassq)
  e3cm=math.sqrt(m3**2+p3cmsq)

  sin3=math.sin(math.radians(ang3))
  cos3=math.cos(math.radians(ang3))
     
  d=p3cmsq-m3**2*sin3**2*sinh**2

  if d<0:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Discriminant negative"
    print_error(msg,"",True)
    skip=True
    p3="NaN"
  else:
    p3a=(e3cm*cos3*sinh+cosh*math.sqrt(d))/(1+sin3**2*sinh**2)
    p3b=(e3cm*cos3*sinh-cosh*math.sqrt(d))/(1+sin3**2*sinh**2)
    if p3a>0 and p3b>0:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Two plab values exist for a given anglab"
      print_error(msg,"",True)
      skip=True
      p3="NaN"
    elif p3a<0 and p3b<0:
      msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": No positive plab value exists for a given anglab"
      print_error(msg,"",True)
      skip=True
      p3cm="NaN"
    else:
      p3=p3a

  return skip,p3,p3cmsq


def anglab_to_angcm(m3,ang3,p3,cosh,sinh):
  cos3=math.cos(math.radians(ang3))
  sin3=math.sin(math.radians(ang3))

  e3=math.sqrt(p3**2+m3**2)

  tan3cm=p3*sin3/(p3*cos3*cosh-e3*sinh)
  ang3cm=math.degrees(math.atan(tan3cm))
  if ang3cm<0:
    ang3cm=ang3cm+180

  return ang3cm


def angcm_to_anglab(m3,ang3cm,p3cm,cosh,sinh):
  sin3cm=math.sin(math.radians(ang3cm))
  cos3cm=math.cos(math.radians(ang3cm))
  e3cm=math.sqrt(m3**2+p3cm**2)
  tan3=p3cm*sin3cm/(p3cm*cos3cm*cosh+e3cm*sinh)
  ang3=math.degrees(math.atan(tan3))
  if ang3<0:
    ang3=ang3+180

  return ang3


def tinc_to_tcm(tinc,m1,m2):
  tcm=tinc*m1/(m1+m2)

# relativistic formula
# tcm=(m1+m2)*(math.sqrt(1+(2*m1*tinc)/(m1+m2)**2)-1)

  return tcm


def tinc_to_pcm(tinc,m1,m2,m3,m4):
  invmassq=(m1+tinc+m2)**2-((tinc+m2)**2-m2**2)
  pcm=math.sqrt(((invmassq-m3**2-m4**2)**2-4*m3**2*m4**2)/(4*invmassq))

  return pcm


def qval_to_eexc(j,ansan_out,value,sf1,sf2,sf3,sf4):

  skip=False
  e_exc=""

  if sf3=="INL":
    sf3=sf2
    e_exc=-value

    return skip,e_exc
  
  aw1=get_atomicweight(sf1)
  aw2=get_atomicweight(sf2)

  sf3s=sf3.split("+")
  aw3=0
  for code in sf3s:
    aw=get_atomicweight(code)
    if aw==-1:
      aw3=-1
      break
    else:
      aw3+=aw

  aw4=get_atomicweight(sf4)

  if aw1==-1 or aw2==-1 or aw3==-1 or aw4==-1:
    msg=ansan_out+" point # "+'{:>5}'.format(str(j+1))+": Conversion of Q-value to level energy impossible"
    print_error(msg,"","True")
    skip=True
  else:
    q_gs=(aw1+aw2-aw3-aw4)*ueV # Qgs
    e_exc=q_gs-value

  return skip,e_exc
  

def get_charge(code):
  partnucl= {'A'   : '2-HE-4'
            ,'AN'  : '0-AN-1'
            ,'AP'  : '1-AP-1'
            ,'D'   : '1-H-2'
            ,'ETA' : '0-ET-0'
            ,'G'   : '0-G-0'
            ,'HE3' : '2-HE-3'
            ,'KN'  : '1-KN-0'
            ,'KP'  : '1-KP-0'
            ,'K0'  : '0-K0-0'
            ,'N'   : '0-NN-1'
            ,'P'   : '1-H-1'
            ,'PI0' : '0-P0-0'
            ,'PIN' : '1-PN-0'
            ,'PIP' : '1-PP-0'
            ,'T'   : '1-H-3'}

  charge=0
  if not re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(\-[GML0-9\+\/]+)?$").search(code):
    if code in partnucl:
      code=partnucl[code]
    else:
      charge=999

  m=re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-\d+(\-[GML0-9\+\/]+)?$").search(code)
  charge=m.group(1)

  return charge


def get_atomicweight(code):
  partnucl= {'A'   : '2-HE-4'
            ,'AN'  : '0-AN-1'
            ,'AP'  : '1-AP-1'
            ,'D'   : '1-H-2'
            ,'ETA' : '0-ET-0'
            ,'G'   : '0-G-0'
            ,'HE3' : '2-HE-3'
            ,'KN'  : '1-KN-0'
            ,'KP'  : '1-KP-0'
            ,'K0'  : '0-K0-0'
            ,'N'   : '0-NN-1'
            ,'P'   : '1-H-1'
            ,'PI0' : '0-P0-0'
            ,'PIN' : '1-PN-0'
            ,'PIP' : '1-PP-0'
            ,'T'   : '1-H-3'}

  aw=0
  if not re.compile(r"^(\d+)\-([A-Z][A-Z0]?|\*)\-(\d+)(-(G|M\d?|L\d))?$").search(code):
    if code in partnucl:
      code=partnucl[code]
    else:
      aw=-1

  if aw!=-1:
    aw=dict_retrieval("227","code",code,"atomic_weight")
    if aw is None:
      code=code+"-G"
      aw=dict_retrieval("227","code",code,"atomic_weight")
    if aw is None:
      aw=-1

  return aw


def print_value(value):
  if value==0:
    value='{:.6f}'.format(value)
    value=" "+value[0:8]
  elif abs(value)>=0.01 and abs(value)<1E+7:
    value='{:.6f}'.format(value)
    if float(value)<0:
      value=value[0:9]
    else:
      value=" "+value[0:8]
  elif abs(value)<=1E-9 or abs(value)>=1E+10:
    value='{:.3E}'.format(value)
    value=re.sub(r"E-","-",value)
    value=re.sub(r"E\+","+",value)
    value='{:>9}'.format(value)
  else:
    value='{:.4E}'.format(value)
    value=re.sub(r"E-0","-",value)
    value=re.sub(r"E\+0","+",value)
    value='{:>9}'.format(value)

  return value


def print_product(sf4_numeq,sf4_iso):
  isomeric_numeq_c4= {'G' : '0'
                     ,'?' : '6'
                     ,'L' : '6'
                     ,'M' : '7'
                     ,'+' : '8'
                     ,' ' : '9'}

  isomeric_numeq_c6= {'G' : '0'
                     ,'M' : '1'
                     ,'N' : '2'
                     ,'P' : '3'
                     ,'Q' : '4'
                     ,'R' : '5'
                     ,'?' : '6'
                     ,'L' : '7'
                     ,' ' : '9'}


  if re.compile(r"^\d+$").search(sf4_iso): # sf4_iso from ISOMER (e.g., 0)
    value=sf4_numeq+"."+sf4_iso
  else: # sf4_iso in char (e.g., G)
    if c4out and sf4_iso in isomeric_numeq_c4:
      value=sf4_numeq+"."+isomeric_numeq_c4[sf4_iso]
    elif not c4out and sf4_iso in isomeric_numeq_c6: 
      value=sf4_numeq+"."+isomeric_numeq_c6[sf4_iso]
  value='{:>9}'.format(value)

  return value


def expand_reaction(mf,mt,sf1,sf2,sf3,sf4,sf5):
  mtsf3={201: "n+x",\
         202: "g+x",\
         203: "p+x",\
         204: "d+x",\
         205: "t+x",\
         206: "h+x",\
         207: "a+x",\
         208: "pi++x",\
         209: "pi0+x",\
         210: "pi-+x",\
         213: "K++x",\
         216: "K-+x",\
         217: "p-bar+x"}

  pattern=re.compile(r"^\d+\-([A-Z][A-Z0]?|\*)\-(\d+)(\-[GML0-9\+\/]+)?$")

  sf1_text=nucl_text(sf1,1)
  m=pattern.search(sf2)
  if m:
    sf2_text=nucl_text(sf2,1)
  else:
    sf2_text=sf2.lower()
  if mt in mtsf3:
    sf3_text=mtsf3[mt]
    sf4_text=""
  else:
    sf3_text=sf3.lower()
    if sf4=="" or sf4=="ELEM/MASS" or sf4=="ELEM" or sf4=="MASS":
      sf4_text=""
    else:
      sf4_text=nucl_text(sf4,1)

  expansion=sf1_text+"("+sf2_text+","+sf3_text+")"+sf4_text
  expansion=expansion.replace("(0,f)", "(sf)") # spontaneous fission

  if sf5=="PAR":
    expansion+=" partial"
  if mf==1:
    if mt==452:
      expansion+=" total fission neutron multiplicity"
    elif mt==455:
      expansion+=" delayed fission neutron multiplicity"
    elif mt==456:
      expansion+=" prompt fission neutron multiplicity"
  elif mf==3:
    if mt==454:
      expansion+=" independent production cross section"
    elif mt==459:
      expansion+=" cumulative production cross section"
    else:
      expansion+=" cross section"
  elif mf==4:
    expansion+=" angular differential cross section"
  elif mf==5:
    expansion+=" energy differential cross section"
  elif mf==6:
    expansion+=" double differential cross section"
  elif mf==8:
    if mt==454:
      expansion+=" independent fission product yield"
    elif mt==459:
      expansion+=" cumulative fission product yield"
  elif mf==13:
    expansion+=" gamma production cross section"
  elif mf==14:
    expansion+=" gamma angular differential cross section"
  elif mf==15:
    expansion+=" gamma energy differential cross section"

  return expansion


def expand_reference(field):
  type=field["reference_type"]
  code=field["reference"]["code"]
  number=field["reference"]["number"]
  volume=field["reference"]["volume"]
  part=field["reference"]["part"]
  issue=field["reference"]["issue"]
  page=field["reference"]["page"]
  date=str(field["date"])
  if date[0:2]!="19" and date[0:2]!="20":
    date="19"+date
  year=date[0:4]

  expansion=""
  if type=="A" or type=="B" or type=="C":
    if type=="A":
      expansion="Abstract of "
    elif type=="C":
      expansion="Proceedings of "
    else:
      expansoin=""
    if type=="A" or type=="C":
      expansion_add=dict_retrieval("007","code",code,"expansion")
      if expansion_add is None:
        expansion+=code
      else:
        expansion+=expansion_add
    else:
      expansion_add=dict_retrieval("207","code",code,"expansion")
      if expansion_add is None:
        expansion+=code
      else:
        expansion+=expansion_add
         
    if volume is not None:
      expansion+=" "+volume
    if part is not None:
      expansion+=" "+" Part "+part
    if page is not None:
      expansion+=" page "+page
    if type=="B":
      expansion+=" ("+year+")"

  elif type=="J" or type=="K":
    if type=="K":
      expansion="Abstract of "
    else:
      expansion=""
    expansion_add=dict_retrieval("005","code",code,"short_expansion")
    if expansion_add is None:
      expansion+=code
    else:
      expansion+=expansion_add 
    if volume is not None:
      expansion+=" "+volume
    if issue is not None:
      expansion+=" No."+issue
    expansion+=" ("+year+")"
    if page is not None:
      expansion+=" "+page

  elif type=="P" or type=="R" or type=="S" or type=="X":
    if type=="P":
      expansion="Progress report "
    elif type=="R":
      expansion="Report "
    elif type=="S":
      expansion="Report (proceedings) "
    else:
      expansion="Preprint "
    if code[-1]!="-":
      expansion+=code+"-"+number
    else:
      expansion+=code+number
    if volume is not None:
      expansion+=" Vol."+volume
    if part is not None:
      expansion+=" "+" Part "+part
    if page is not None:
      expansion+=" page "+page
    expansion+=", "+year

  elif type=="T" or type=="W":
    if type=="T":
      expansion="Thesis "
    else:
      expansion="Private communication "
    if page is not None:
      expansion+=" page "+page
    expansion+=" ("+year+")"

  return year,expansion


def nucl_text(code,mod):
  m=re.compile(r"^\d+\-([A-Z][A-Z0]?|\*)\-(\d+)(\-[GML0-9\+\/]+)?$").search(code)
  s=m.group(1).capitalize()
  a=m.group(2)
  if a=="0":
    if mod==1:
      a="nat"
    else:
      a=""
  m=re.compile(r"^\d+\-([A-Z][A-Z0]?|\*)\-\d+\-([GML0-9\+\/]+)$").search(code)
  if m:
    x=m.group(2)
    if mod==1:
      text=a+x.lower()+s
    else:
      if x=="M1":
        x="M"
      elif x=="M2":
        x="N"
      text=s+a+x.lower()
  else:
    if mod==1:
      text=a+s
    else:
      text=s+a

  return text


def part_numeq(code):
  if code=="0": # spontaneous fission
    numeq="   -1"
  else:
    numeq=dict_retrieval("033","code",code,"internal_numerical_equivalent_1")
    if numeq is None:
      numeq="-9999"
    elif numeq=="0001": # neutron
      numeq="    1"
    elif int(numeq)<10:
      numeq="    "+numeq
    elif int(numeq)<100:
      numeq="   "+numeq
    elif int(numeq)<1000:
      numeq="  "+numeq
    elif int(numeq)<10000:
      numeq=" "+numeq

  return numeq


def dict_retrieval(dict_id,field_inp,value_inp,field_out):
  l=[x[field_out] for x in dict_json[dict_id] if x[field_inp]==value_inp]

  if len(l)==0 and dict_id=="227": # retrieve nuclide code with -G
    value_inp=value_inp+"-G"
    l=[x[field_out] for x in dict_json[dict_id] if x[field_inp]==value_inp]

  if len(l)==0:
    msg="code "+value_inp+" cannot be resolved by Dictionary "+dict_id
    line=""
    print_error(msg,line,force)
    value_out=None
  else:
    value_out=l[0]

  return value_out


def read_dict_324():
  dict_json["324"]=[]
  lines=get_file_lines("dict_arc_new.324")
  for line in lines:
    code=line[12:17]
    if re.compile(r"^\s+$").search(code):
      continue
    else:
      code=re.sub(r"\s+$","",code)
      family=line[43:44]
      operation1=re.sub(r"\s+$","",line[47:48])
      operation2=re.sub(r"\s+$","",line[50:52])
      frame=re.sub(r"\s+$","",line[53:55])
      field=re.sub(r"\s+$","",line[55:58])
      heading1=re.sub(r"\s+$","",line[59:69])
      heading2=re.sub(r"\s+$","",line[70:80])
      record={"code":       code,
              "family":     family,
              "operation1": operation1,
              "operation2": operation2,
              "frame":      frame,
              "field":      field,
              "heading1":   heading1,
              "heading2":   heading2}
      dict_json["324"].append(record)

  return


def read_dict_336():
  dict_json["336"]=[]
  lines=get_file_lines("dict_arc_new.336")
  for line in lines:
    code=line[12:42]
    if re.compile(r"^\s+$").search(code):
      continue
    else:
      code=re.sub(r"\s+$","",code)
      flag=line[48:49]
      sf2=re.sub(r"\s+$","",line[43:47])
      sf3=re.sub(r"\s+$","",line[50:60])
      sf4=re.sub(r"\s+$","",line[60:74])
      sf5=re.sub(r"\s+$","",line[75:85])
      sf6=re.sub(r"\s+$","",line[86:96])
      sf7=re.sub(r"\s+$","",line[97:107])
      record={"code": code, "flag":flag, "sf2":sf2, "sf3":sf3, "sf4":sf4, "sf5":sf5, "sf6":sf6, "sf7":sf7}
      dict_json["336"].append(record)

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


def read_x4json(file_x4):
  f=open(file_x4)
  try:
    x4_json=json.load(f)
  except json.JSONDecodeError:
    msg=file_x4+" is not in JSON format."
    print_error_fatal(msg,"")

  if x4_json["title"][0:18]!="J4 - EXFOR in JSON":
    msg=file_x4+" is not an EXFOR in JSON."
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

  f.close()
  return dict_json


def get_args(ver):
  parser=argparse.ArgumentParser(\
   usage="Convert J4 file to C6 file",\
   epilog="example: x4_j4toc6.py -i j4 -e 22742 -o exfor.c6")
  parser.add_argument("-v", "--version",\
   action="version", version=ver)
  parser.add_argument("-i", "--dir_j4",\
   help="directory of input J4 files")
  parser.add_argument("-d", "--file_dict",\
   help="input JSON dictionary (optional, default: dict.json)", default="dict.json")
  parser.add_argument("-e", "--entry",\
   help="EXFOR Entry number ('all' to process all files in the input directory)")
  parser.add_argument("-o", "--file_c6",\
   help="output C6 file/directory")
  parser.add_argument("-l", "--seplvl",\
   help="output separation level 1, 2 or 3 (optional, default: 3)", default="3")
  parser.add_argument("-n", "--file_idx",\
   help="output index file (optional)", default="x4_j4toc6.txt")
  parser.add_argument("-s", "--sysout",\
   help="output reference system identifier (optional, default: OOO)", default="OOO")
  parser.add_argument("-w", "--enewid",\
   help="energy width allowance in percent for SACS (optional, default: 10)", default="10")
  parser.add_argument("-f", "--force",\
   help="never prompt", action="store_true")
  parser.add_argument("-x", "--exclhi",\
   help="exclude heavy-ion (A>4) induced reactions", action="store_true")
  parser.add_argument("-y", "--incder",\
   help="include DERIVed data", action="store_true")
  parser.add_argument("-c4", "--c4out",\
   help="output in C4 format", action="store_true")

  args=parser.parse_args()
  return args


def get_input(args):
  time=datetime.datetime.now()
  date=time.strftime("%Y-%m-%d")
  print("J4TOC6 (Ver."+ver+") run on "+date)
  print("-----------------------------------------")

  force0=args.force
  exclhi0=args.exclhi
  incder0=args.incder
  c4out0=args.c4out

  dir_j4=args.dir_j4
  if dir_j4 is None:
    dir_j4=input("Directory of input J4 files [j4] --------> ")
    if dir_j4=="":
      dir_j4="j4"
  if not os.path.exists(dir_j4):
    print(" ** Directory "+dir_j4+" does not exist.")
  while not os.path.exists(dir_j4):
    dir_j4=input("Directory of input J4 files [j4] --------> ")
    if dir_j4=="":
      dir_j4="j4"
    if not os.path.exists(dir_j4):
      print(" ** Directory "+dir_j4+" does not exist.")

  file_dict=args.file_dict
  print("JSON Dictionary -------------------------> "+file_dict)
  if not os.path.exists(file_dict):
    print(" ** File "+file_dict+" does not exist.")
  while not os.path.exists(file_dict):
    file_dict=input("JSON DIctionary [dict.json] -------------> ")
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
    pattern=dir_j4+"/[a-z0-9][0-9][0-9][0-9][0-9].[0-9][0-9][0-9]*.json"
  else:
    pattern=dir_j4+"/"+entry_lower+".[0-9][0-9][0-9]*.json"
  all_files=glob.glob(pattern)
  files = [file for file in all_files if re.search(r"\d\d\d(\.[A-Z1-9])?", file)]
  if len(files)==0:
    if entry=="all":
      print(" ** J4 file does not exist.")
    else:
      print(" ** J4 file for EXFOR Entry "+entry+" does not exist.")
  while len(files)==0:
    entry=input("EXFOR Entry # [all] ---------------------> ")
    if entry=="":
      entry="all"
    entry_lower=entry.lower()
    if entry=="all":
      pattern=dir_j4+"/[a-z0-9][0-9][0-9][0-9][0-9].[0-9][0-9][0-9]*.json"
    else:
      pattern=dir_j4+"/"+entry_lower+".[0-9][0-9][0-9]*.json"
    all_files=glob.glob(pattern)
    files = [file for file in all_files if re.search(r"\d\d\d(\.[A-Z1-9])?", file)]
    if len(files)==0:
      if entry=="all":
        print(" ** J4 file does not exist.")
      else:
        print(" ** J4 file for EXFOR Entry "+entry+" does not exist.")
  entry=entry.lower()

  seplvl=args.seplvl
  print("output separation level -----------------> "+seplvl)
  if seplvl!="1" and seplvl!="2" and seplvl!="3":
    print(" ** Separation level must be 1, 2 or 3.")
  while seplvl!="1" and seplvl!="2" and seplvl!="3":
    seplvl=input("output separation level [3] ---------------> ")
    if seplvl=="":
      seplvl="3"
    if seplvl!="1" and seplvl!="2" and seplvl!="3":
      print(" ** Separation level must be 1, 2 or 3.")
  seplvl=int(seplvl)

  file_c6=args.file_c6
  if seplvl==1:
    if file_c6 is None:
      file_c6=input("Output C6 file [exfor.c6] ----------------------> ")
    if file_c6=="":
      file_c6="exfor.c6"
    if os.path.isfile(file_c6):
      msg="File '"+file_c6+"' exists and must be overwritten."
      print_error(msg,"",force0)
  else:
    if file_c6 is None:
      file_c6=input("Directory of output C6 files [c6] -------> ")
    if file_c6=="":
      file_c6="c6"
    if os.path.isdir(file_c6):
      msg="Directory '"+file_c6+"' exists and must be overwritten."
      print_error(msg,"",force0)
    else:
      msg="Directionry '"+file_c6+"' does not exist and must be created."
      print_error(msg,"",force0)
      os.mkdir(file_c6)

  file_idx=args.file_idx
  print("output index file -----------------------> "+file_idx)
  if os.path.isfile(file_idx):
    msg="File '"+file_idx+"' exists and must be appended."
    print_error(msg,"",force0)

  sysout=args.sysout
  sysout=sysout.upper()
  print("output reference system id --------------> "+sysout)
  if len(sysout)==2:
    sysout+="O"
  if not re.compile(r"^(O|L|C)(O|L|C)(O|L|C)$").search(sysout):
    print(" ** "+sysout+" is an invalid reference system identifier. Must be a combination of O, L and C.")
  while not re.compile(r"^(O|L|C)(O|L|C)(O|L|C)$").search(sysout):
    sysout=input("output reference system identifier [OOO] ---> ")
    if sysout=="":
      sysout="OOO"
    sysout=sysout.upper()
    if len(sysout)==2:
      sysout+="O"
    if not re.compile(r"^(O|L|C)(O|L|C)(O|L|C)$").search(sysout):
      print(" ** "+sysout+" is an invalid reference system identifier. Must be a combination of O, L and C.")

  enewid=args.enewid
  print("energy width allowance (%) for SACS -----> "+enewid)
  if not is_float(enewid):
    print(" ** "+enewid+" is not a number. Must be a real number or integer.")
    while not is_float(enewid):
      enewid=input("enegy width allowance (%) for SACS [10] -> ")
      if enewid=="":
        enewid=10
      if not is_float(enewid):
        print(" ** "+enewid+" is not a number. Must be a real number or integer.")
  enewid=float(enewid)

  return dir_j4,file_dict,entry,file_c6,seplvl,file_idx,sysout,enewid,force0,exclhi0,incder0,c4out0


def is_float(s):
  try:
    float(s)
    return True
  except ValueError:
    return False


def print_error(msg,line,force):
  print("** "+msg)
  if line!="":
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


def print_error_fatal(msg,line):
  print("**  "+msg)
  print(line)
  exit()


if __name__ == "__main__":
  j4toc6()
  exit()
