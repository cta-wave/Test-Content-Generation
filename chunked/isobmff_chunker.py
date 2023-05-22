#!/usr/bin/env python3
import sys
import struct

def read_bytes(fobj, bytes):
    data = fobj.read(bytes)
    if len(data) != bytes:
        raise RuntimeError('Not enough data: requested %d, read %d' % (bytes, len(data)))
    return data

def read_ulong(fobj):
    return struct.unpack('>L', read_bytes(fobj, 4))[0]

def read_ulonglong(fobj):
    return struct.unpack('>Q', read_bytes(fobj, 8))[0]

def read_fourcc(fobj):
    return read_bytes(fobj, 4)

def read_atom(fobj):
    pos = fobj.tell()
    size = read_ulong(fobj)
    type = read_fourcc(fobj)

    if size == 1:
        size = read_ulonglong(fobj)
    elif size == 0:
        fobj.seek(0, 2)
        size = fobj.tell() - pos
        fobj.seek(pos + 8)

    return size, type

def isobmff_read_topboxes(f):
    size = 0
    f.seek(0)
    pos = 0
    f.seek(0, 2)
    end = f.tell()
    f.seek(0)

    result = []
    while 1:
        if pos + size < end:
            pos += size
            f.seek(pos)
            a = read_atom(f)
            result.append(a)
            size = a[0]
        else:
            break

    return result

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} num_frag_per_chunk input_file")
        sys.exit(1)

    num_frag_per_chunk = int(sys.argv[1])
    input_file = sys.argv[2]

    # open and parse
    fi = open(input_file + ".m4s", 'rb')
    boxes = isobmff_read_topboxes(fi)
    fi.seek(0)
    
    # iterate on boxes
    i_moof = -1
    i_chunk = -1
    global fo
    fo = None
    for b in boxes:
        bytes = fi.read(b[0]);
        if b[1] == b'styp':
            continue

        if b[1] == b'moof':
            i_moof += 1

        if i_moof % num_frag_per_chunk == 0 and i_moof / num_frag_per_chunk != i_chunk:
            # new chunk
            if fo is not None:
                fo.close()
            i_chunk += 1
            fo = open(input_file + "_" + str(i_chunk+1) + ".m4s", 'wb')
            styp = open("styp", 'rb')
            fo.write(styp.read(28))
            styp.close();
        
        fo.write(bytes)

    # close
    fo.close()
    fi.close()
    sys.exit(0)
