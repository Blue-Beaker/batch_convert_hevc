#! /bin/python3
import os,sys,argparse
import shutil
from pymediainfo import MediaInfo
uid=1000
gid=1000

convertAlreadyHEVC=False
verbosity=0
inputlist=[]
dry_run=False
for item in sys.argv[1:]:
    if item.startswith("-"):
        if(item=="-f"):
            convertAlreadyHEVC=True
        if(item=="--dry-run"):
            dry_run=True
        if(item.startswith("-v")):
            verbosity=1
    else:
        inputlist.append(item)

if inputlist.__len__()==0:
    inputlist=["./"]
queue:list[list[str]]
queue=[]
def convert(inname,outname,crf=28,targetSize=0):
    
    command=f"taskset -a -c 12-15 nice -n 19 ffmpeg -hide_banner -filter_threads 4 -filter_complex_threads 4 -y -i \"{inname}\" -c:v libx265 -crf {crf} -preset medium -c:a copy \"{outname}\""

    print(command)
    if dry_run:
        return 0
    result=os.system(command)
    print(result)
    os.chown(outname,uid,gid)
    if targetSize>0 and crf<51:
        size2=os.stat(outname).st_size
        if size2/targetSize>0.75:
            return convert(inname,outname,crf=min(crf+5,51),targetSize=targetSize)
    return result
    return 0


def addToQueue(infile,outfile):
    queue.append([infile,outfile])

def readIgnoreList(folder):
    ignore_file=os.path.join(folder,".convert_ignore")
    if(os.path.exists(ignore_file)):
        with open(ignore_file, "r") as f:
            list1=[]
            for line in f.readlines():
                if(line not in list1):
                    list1.append(line.removesuffix("\n"))
            return list1
    return []

def addFileToIgnoreList(file):
    folder=os.path.dirname(file)
    ignore_file=os.path.join(folder,".convert_ignore")
    with open(ignore_file,"a") as f:
        f.write(os.path.basename(file)+"\n")
    
        

def queueFiles(file):
    name=os.path.basename(file)

    ignores=readIgnoreList(file)

    if os.path.basename(file) in ignores:
        print("ignored from .convert_ignore: "+file)
    elif name!="converted" and os.path.isdir(file):
        for subpath in sorted(os.listdir(file)):
            if(not subpath in ignores):
                queueFiles(os.path.join(file,subpath))
            else:
                print(f"ignored from {os.path.join(file,'.convert_ignore')}: "+os.path.join(file,subpath))

    elif file.endswith(".mkv") or file.endswith(".mp4"):
        if(convertAlreadyHEVC or not checkHEVC(file)):
            if not dry_run:
                os.makedirs(os.path.join(os.path.dirname(file),"converted"),exist_ok=True)
                os.chown(os.path.join(os.path.dirname(file),"converted"),uid,gid)
            addToQueue(file,os.path.join(os.path.dirname(file),"converted",name))
        else:
            addFileToIgnoreList(file)
            print(f"{file} is already in HEVC, skipping")
    else:
        if verbosity:
            print("ignored "+file)
def checkHEVC(file):
    tracks=MediaInfo.parse(file).video_tracks
    for track in tracks:
        data=track.to_data()
        if data.get("format")!="HEVC":
            return False
    return True
converted=[]
def getSizeStr(size:int):
    absSize=abs(size)
    if absSize>1000000000:
        differString=f"{size/1000000000:+.3f}GB"
    elif absSize>1000000:
        differString=f"{size/1000000:+.3f}MB"
    elif absSize>1000:
        differString=f"{size/1000:+}kB"
    else:
        differString=f"{size:+}B"
    return differString
def convertInQueue():
    for item in queue:
        print(item)
    print(f"\033[0;37;44mTotal files: {queue.__len__()}\033[0m")
    for i in range(queue.__len__()):
        item=queue[i]
        size=os.stat(item[0]).st_size
        print(f"\033[0;37;44m{item[0]} {getSizeStr(size).removeprefix('+')}\033[0m")
        result=convert(item[0],item[1],targetSize=size)

        size2=os.stat(item[1]).st_size
        if result==2:
            print(f"\033[0;37;41mCancelled: {i}/{queue.__len__()} '{item[0]}'=>'{item[1]}'\033[0m")
            return
        if result==0:
            addFileToIgnoreList(item)

        ratio=size2/size*100
        differString=getSizeStr(size2-size)
        converted.append([item[0],item[1],differString,f"{ratio:.1f}%"])
        print(f"\033[0;37;44mConverted: {i}/{queue.__len__()} '{item[0]}'=>'{item[1]}' {differString} {ratio:.1f}%\033[0m")
for filename in inputlist:
    queueFiles(filename)
queue.sort()
convertInQueue()
for line in converted:
    print(line)
