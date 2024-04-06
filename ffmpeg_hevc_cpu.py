#! /bin/python3
import os,sys,argparse
from pymediainfo import MediaInfo
uid=1000
gid=1000

convertAlreadyHEVC=False
verbosity=0
inputlist=[]
for item in sys.argv[1:]:
    if item.startswith("-"):
        if(item=="-f"):
            convertAlreadyHEVC=True
        if(item.startswith("-v")):
            verbosity=1
    else:
        inputlist.append(item)

if inputlist.__len__()==0:
    inputlist=["./"]
queue:list[list[str]]
queue=[]
def convert(inname,outname):
    command=f"taskset -a -c 12-15 nice -n 19 ffmpeg -hide_banner -filter_threads 4 -filter_complex_threads 4 -y -i \"{inname}\" -c:v libx265 -crf 28 -preset medium -c:a copy \"{outname}\""

#     command=f"""nice -n 15 ffmpeg -y -i \"{inname}\" -c:v libx265 -b:v 1600k -x265-params pass=1 -an -f null /dev/null && \
# nice -n 15 ffmpeg -y -i \"{inname}\" -c:v libx265 -b:v 1600k -x265-params pass=2 -c:a copy \"{outname}\""""

    print(command)
    result=os.system(command)
    print(result)
    os.chown(outname,uid,gid)
    return result


def addToQueue(infile,outfile):
    queue.append([infile,outfile])

def queueFiles(file):
    name=os.path.basename(file)
    if name!="converted" and os.path.isdir(file):
        for subpath in sorted(os.listdir(file)):
            queueFiles(os.path.join(file,subpath))
    elif file.endswith(".mkv") or file.endswith(".mp4"):
        if(convertAlreadyHEVC or not checkHEVC(file)):
            os.makedirs(os.path.join(os.path.dirname(file),"converted"),exist_ok=True)
            os.chown(os.path.join(os.path.dirname(file),"converted"),uid,gid)
            addToQueue(file,os.path.join(os.path.dirname(file),"converted",name))
        else:
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
    if size>1000000000:
        differString=f"{size/1000000000:+}GB"
    elif size>1000000:
        differString=f"{size/1000000:+}MB"
    elif size>1000:
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
        result=convert(item[0],item[1])
        size2=os.stat(item[1]).st_size
        if result==2:
            print(f"\033[0;37;41mCancelled: {i}/{queue.__len__()} '{item[0]}'=>'{item[1]}'\033[0m")
            return
        ratio=size2/size*100
        differString=getSizeStr(size2-size)
        converted.append([item[0],item[1],f"{size2-size}",differString,f"{ratio}%"])
        print(f"\033[0;37;44mConverted: {i}/{queue.__len__()} '{item[0]}'=>'{item[1]}' {differString} {ratio}%\033[0m")
for filename in inputlist:
    queueFiles(filename)
queue.sort()
convertInQueue()
for line in converted:
    print(line)
