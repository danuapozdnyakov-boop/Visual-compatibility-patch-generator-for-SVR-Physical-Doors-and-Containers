"""Recover the moving panel in the known Dark Brotherhood Door replacement."""
from collections import defaultdict
from hashlib import sha256
from math import dist
import struct

from nif_io import children, clean_node, node_offsets, set_children


def name(nif, raw):
    index = struct.unpack_from('<i', raw)[0]
    return nif.strings[index] if 0 <= index < len(nif.strings) else ''


def geometry(raw):
    bounds = node_offsets(raw)['collision'] + 4
    descriptor, faces, count, size = struct.unpack_from('<QHHI', raw, bounds + 28)
    stride = (descriptor & 15) * 4
    start = bounds + 44
    end = start + count * stride
    if (stride < 12 or size != count * stride + faces * 6
            or raw[start + size:] != b'\0\0\0\0'):
        raise ValueError('Unexpected Black Door vertex format')
    vertices = [raw[i:i + stride] for i in range(start, end, stride)]
    points = [struct.unpack_from('<3f', vertex) for vertex in vertices]
    faces_raw = raw[end:end + faces * 6]
    triangles = list(struct.iter_unpack('<3H', faces_raw))
    keys = [tuple(round(v * 1000) for v in point) for point in points]
    signature = sha256(b''.join(struct.pack('<3i', *key) for key in keys) + faces_raw).hexdigest()
    return bounds, start, vertices, points, triangles, keys, signature


def keep_faces(raw, bounds, start, vertices, points, faces):
    used = sorted({i for face in faces for i in face})
    remap = {old: new for new, old in enumerate(used)}
    data = b''.join(vertices[i] for i in used)
    data += b''.join(struct.pack('<3H', *(remap[i] for i in face)) for face in faces)
    result = bytearray(raw[:start])
    struct.pack_into('<HHI', result, bounds + 36, len(faces), len(used), len(data))
    axes = list(zip(*(points[i] for i in used)))
    center = tuple((min(axis) + max(axis)) * 0.5 for axis in axes)
    struct.pack_into('<4f', result, bounds, *center, max(dist(center, points[i]) for i in used))
    return result + data + b'\0\0\0\0'


def prepare_black_door(nif):
    root_kind, root = nif.blocks[0]
    if root_kind != 'BSFadeNode' or name(nif, root) != 'CWTower01':
        return False
    kids = children(root)
    if len(kids) != 2 or any(i < 0 or nif.blocks[i][0] != 'BSTriShape' for i in kids):
        return False
    by_name = {name(nif, nif.blocks[i][1]): i for i in kids}
    if set(by_name) != {'CWTower01:0', 'CWTower01:1'}:
        return False
    relief = by_name['CWTower01:0']
    combined = by_name['CWTower01:1']
    raw = nif.blocks[combined][1]
    bounds, start, vertices, points, faces, keys, signature = geometry(raw)
    # Match the reported geometry only. Texture and shader changes do not affect this check.
    if (signature != 'b4976e7a2c4b5eba0f8ea7ec089402f0684ddcb45009aae781da1232c0e7a726'
            or geometry(nif.blocks[relief][1])[-1] != 'c84777d6efc9052839b0dc674a16f5f4c68e9f0da6acb6526f1703ce395f7067'):
        return False

    graph = defaultdict(set)
    for a, b, c in faces:
        for first, second in ((a, b), (b, c), (c, a)):
            graph[keys[first]].add(keys[second])
            graph[keys[second]].add(keys[first])
    candidates = []
    while graph:
        stack = [next(iter(graph))]
        group = set()
        while stack:
            key = stack.pop()
            if key in graph:
                group.add(key)
                stack.extend(graph.pop(key))
        if len(group) == 67:
            candidates.append(group)
    if len(candidates) != 1:
        raise ValueError('Cannot isolate the Black Door back panel')
    panel = [face for face in faces if keys[face[0]] in candidates[0]]
    frame = [face for face in faces if keys[face[0]] not in candidates[0]]
    if (len(panel), len(frame)) != (91, 97):
        raise ValueError('Unexpected Black Door panel/frame triangle counts')

    panel_raw = keep_faces(raw, bounds, start, vertices, points, panel)
    struct.pack_into('<i', panel_raw, 0, nif.string('SVR_BlackDoorBacking'))
    panel_index = nif.add('BSTriShape', panel_raw)
    nif.blocks[combined] = ('BSTriShape', keep_faces(raw, bounds, start, vertices, points, frame))
    node = clean_node(root, nif.string('BlackDoor'), -1, [relief, panel_index])
    transform = node_offsets(node)
    struct.pack_into('<3f9ff', node, transform['translation'],
                     0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1)
    set_children(root, [combined, nif.add('NiNode', node)])
    return True
