"""Read bounded ELF identity notes without loading executable/debugger code."""
import pathlib, re, struct

MACHINES = {3:'x86', 62:'x86_64', 183:'aarch64', 40:'arm', 243:'riscv'}

def identity(file):
    with pathlib.Path(file).open('rb') as stream:
        head=stream.read(64)
        if len(head)<64 or head[:4]!=b'\x7fELF' or head[4] not in (1,2) or head[5] not in (1,2):
            raise ValueError('Invalid ELF header')
        endian='<' if head[5]==1 else '>'
        kind,machine=struct.unpack_from(endian+'HH',head,16)
        bits=head[4]*32
        offset=struct.unpack_from(endian+('Q' if bits==64 else 'I'),head,32 if bits==64 else 28)[0]
        entry,count=struct.unpack_from(endian+'HH',head,54 if bits==64 else 42)
        if count>256 or count and entry<(56 if bits==64 else 32): raise ValueError('ELF program headers exceed budget')
        result={'architecture':MACHINES.get(machine,'unknown'),'elfType':kind,'buildId':None,'kernelRelease':None,'configSha256':None}
        remaining=1024*1024
        for index in range(count):
            stream.seek(offset+index*entry);ph=stream.read(entry)
            if len(ph)!=entry: raise ValueError('Truncated ELF program header')
            if struct.unpack_from(endian+'I',ph)[0]!=4:continue
            start=struct.unpack_from(endian+('Q' if bits==64 else 'I'),ph,8 if bits==64 else 4)[0]
            size=struct.unpack_from(endian+('Q' if bits==64 else 'I'),ph,32 if bits==64 else 16)[0]
            if size>remaining:raise ValueError('ELF notes exceed budget')
            remaining-=size;stream.seek(start);notes=stream.read(size);pos=0
            if len(notes)!=size:raise ValueError('Truncated ELF notes')
            while pos+12<=len(notes):
                namesz,descsz,note_type=struct.unpack_from(endian+'III',notes,pos);pos+=12
                if pos+((namesz+3)//4*4)+((descsz+3)//4*4)>len(notes):raise ValueError('Invalid ELF note bounds')
                name=notes[pos:pos+namesz].rstrip(b'\0');pos+=(namesz+3)//4*4
                desc=notes[pos:pos+descsz];pos+=(descsz+3)//4*4
                if name==b'GNU' and note_type==3:result['buildId']=desc.hex()
                if name==b'VMCOREINFO':
                    values=dict(line.split('=',1) for line in desc.decode('ascii','replace').strip('\0').splitlines() if '=' in line)
                    result['kernelRelease']=values.get('OSRELEASE')
                    build=values.get('BUILD-ID','').lower()
                    if re.fullmatch('[a-f0-9]{8,128}',build):result['buildId']=build
                    config=values.get('CONFIG_SHA256','').lower()
                    if re.fullmatch('[a-f0-9]{64}',config):result['configSha256']=config
        return result

def events(file):
    """Group report boundaries; a later panic is a possible cascade, not a new cause."""
    start=re.compile(r'BUG: (?:KASAN|KFENCE|unable|soft lockup)|WARNING:.*\bat\b|Oops:|INFO: task .*blocked for more than|watchdog:.*lockup|rcu:.*(?:stall|detected stalls)|Out of memory|Kernel panic',re.I)
    groups=[];previous=None;source=None;truncated=False;last=0
    with pathlib.Path(file).open(encoding='utf-8',errors='replace') as stream:
        for number,text in enumerate(stream,1):
            last=number
            if text.startswith('# FILE:'):source=text.strip()[7:].strip();previous=None
            if not start.search(text):continue
            if 'kernel panic' in text.lower() and previous and number-previous['startLine']<=300:
                previous['possibleCascadeLines'].append(number);continue
            if len(groups)>=16:truncated=True;continue
            if groups:groups[-1]['endLine']=number-1
            previous={'id':'E'+str(len(groups)+1),'startLine':number,'endLine':None,'headline':text.strip()[:400],'source':source,'possibleCascadeLines':[]}
            groups.append(previous)
    if groups:groups[-1]['endLine']=last
    return {'events':groups,'eventsTruncated':truncated,'primaryEventId':groups[0]['id'] if groups else None}
