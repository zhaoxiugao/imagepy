import numpy as np
from numba import jit
from scipy.ndimage import label, generate_binary_structure

def neighbors(shape):
    dim = len(shape)
    block = generate_binary_structure(dim, 1)
    block[tuple([1]*dim)] = 0
    idx = np.where(block>0)
    idx = np.array(idx, dtype=np.uint8).T
    idx = np.array(idx-[1]*dim)
    acc = np.cumprod((1,)+shape[::-1][:-1])
    return np.dot(idx, acc[::-1])

@jit
def dist(idx1, idx2, acc):
    dis = 0
    for i in range(len(acc)):
        c1 = idx1//acc[i]
        c2 = idx2//acc[i]
        dis += (c1-c2)**2
        idx1 -= c1*acc[i]
        idx2 -= c2*acc[i]
    return dis

@jit
def step(dis, pts, roots, s, level, nbs, acc):
    cur = 0
    while cur<s:
        p = pts[cur]
        rp = roots[cur]
        if dis[p] == 0xffff or dis[p]>level:
            cur += 1
            continue
        for dp in nbs:
            cp = p+dp
            if dis[cp]<level+2e-10:continue
            if dis[cp]==0xffff:continue
            tdist = dist(cp, rp, acc)
            if tdist<dis[cp]**2-1e-10:
                dis[cp] = tdist**0.5
                pts[s] = cp
                roots[s] = rp
                if s == len(pts):
                    s, cur = clear(pts, roots, s, cur)
                s+=1
        pts[cur] = -1
        cur+=1
    return cur

@jit
def clear(pts, roots, s, cur):
    ns = 0; nc=0;
    for c in range(s):
        if pts[c]!=-1:
            pts[ns] = pts[c]
            roots[ns] = roots[c]
            ns += 1
            if c<cur:nc += 1
    return ns, nc
        
@jit
def collect(dis, nbs, pts, root):
    cur = 0
    for p in range(len(dis)):
        if dis[p]>=0xffff-1: continue # edge or back
        for dp in nbs:
            if dis[p+dp]==0xffff-1:
                pts[cur] = p
                root[cur] = p
                cur += 1
                break
    return cur

def buffer(img, dtype):
    buf = np.ones(tuple(np.array(img.shape)+2), dtype=dtype)
    buf *= 0xffff
    buf[tuple([slice(1,-1)]*buf.ndim)] = (img>0)*(0xffff-1)
    return buf

@jit
def distance_transform_edt(img, output=np.float32):
    dis = buffer(img, output)
    nbs = neighbors(dis.shape)
    acc = np.cumprod((1,)+dis.shape[::-1][:-1])[::-1]

    line = dis.ravel()
    pts = np.zeros(line.size//2, dtype=np.int64)
    roots = np.zeros(line.size//2, dtype=np.int64)
    s = collect(line, nbs, pts, roots)
    for level in range(10000):
        s, c = clear(pts, roots, s, 0)
        s = step(line, pts, roots, s, level, nbs, acc)
        if s==0:break
    return dis[(slice(1,-1),)*img.ndim]
    
if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from skimage.io import imread, imsave
    from scipy.ndimage import distance_transform_edt as scipyedt
    from time import time

    img = np.ones((2048,2048))
    img[1024,1024] = 0

    start = time()
    for i in range(1):
        dis1 = scipyedt(img)
    print('scipy', time()-start)
    #start = time()
    dis = distance_transform_edt(img, np.uint16)
    #print('my', time()-start)
    start = time()
    for i in range(1):
        dis2 = distance_transform_edt(img, np.uint16)
    print('my', time()-start)

