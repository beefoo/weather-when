import numpy as np
import os
from pprint import pprint
import pyopencl as cl
import random

os.environ['PYOPENCL_COMPILER_OUTPUT'] = '1'

def getPixelData(fData, dw, dh, tw, th, particles, pointsPerParticle, velocityMultiplier, magRange, lineWidthRange, alphaRange, brightnessFactor):
    h = len(particles)
    w = pointsPerParticle
    dim = 4 # four points: x, y, alpha, width

    result = np.zeros(tw * th, dtype=np.float32)
    pData = np.array(particles)
    pData = pData.astype(np.float32)
    pData = pData.reshape(-1)

    # the kernel function
    src = """

    static float lerp(float a, float b, float mu) {
        return (b - a) * mu + a;
    }

    static float det(float a0, float a1, float b0, float b1) {
        return a0 * b1 - a1 * b0;
    }

    static float2 lineIntersection(float x0, float y0, float x1, float y1, float x2, float y2, float x3, float y3) {
        float xd0 = x0 - x1;
        float xd1 = x2 - x3;
        float yd0 = y0 - y1;
        float yd1 = y2 - y3;

        float div = det(xd0, xd1, yd0, yd1);

        float2 intersection;
        intersection.x = -1.0;
        intersection.y = -1.0;

        if (div != 0.0) {
            float d1 = det(x0, y0, x1, y1);
            float d2 = det(x2, y2, x3, y3);
            intersection.x = det(d1, d2, xd0, xd1) / div;
            intersection.y = det(d1, d2, yd0, yd1) / div;
        }

        return intersection;
    }


    static float norm(float value, float a, float b) {
        float n = (value - a) / (b - a);
        if (n > 1.0) {
            n = 1.0;
        }
        if (n < 0.0) {
            n = 0.0;
        }
        return n;
    }

    static float wrap(float value, float a, float b) {
        if (value < a) {
            value = b - (a - value);
        } else if (value > b) {
            value = a + (value - b);
        }
        return value;
    }

    void drawLine(__global float *p, int x0, int y0, int x1, int y1, int w, int h, float alpha, int thickness);
    void drawSingleLine(__global float *p, int x0, int y0, int x1, int y1, int w, int h, float alpha);
    void plot(__global float *p, int w, int h, float alpha, float fx, float fy, float brightness);

    void drawLine(__global float *p, int x0, int y0, int x1, int y1, int w, int h, float alpha, int thickness) {
        int dx = abs(x1-x0);
        int dy = abs(y1-y0);

        if (dx==0 && dy==0) {
            return;
        }

        // draw the first line
        drawSingleLine(p, x0, y0, x1, y1, w, h, alpha);

        thickness--;
        if (thickness < 1) return;

        int stepX = 0;
        int stepY = 0;
        if (dx > dy) stepY = 1;
        else stepX = 1;

        // loop through thickness
        int offset = 1;
        for (int i=0; i<thickness; i++) {
            int xd = stepX * offset;
            int yd = stepY * offset;

            drawSingleLine(p, x0+xd, y0+yd, x1+xd, y1+yd, w, h, alpha);

            // alternate above and below
            offset *= -1;
            if (offset > 0) {
                offset++;
            }
        }


    }

    // integer part of x
    static float ipart(float x) {
        return floor(x);
    }
    static float xround(float x) {
        return ipart(x + 0.5);
    }
    // fractional part of x
    static float fpart(float x) {
        return x - floor(x);
    }
    static float rfpart(float x) {
        return 1.0 - fpart(x);
    }

    void plot(__global float *p, int w, int h, float alpha, float fx, float fy, float brightness) {
        int x = (int) round(fx);
        int y = (int) round(fy);
        x = clamp(x, 0, w-1);
        y = clamp(y, 0, h-1);
        // hack to make things darker
        if (brightness > 0.0) {
            float factor = %f; // lower number = darker
            brightness = pow((float) brightness, factor);
        }
        p[y*w+x] = alpha * brightness;
    }

    // anti-aliased line
    // https://en.wikipedia.org/wiki/Xiaolin_Wu's_line_algorithm
    void drawSingleLine(__global float *p, int _x0, int _y0, int _x1, int _y1, int w, int h, float alpha) {
        // clamp
        _x0 = clamp(_x0, 0, w-1);
        _x1 = clamp(_x1, 0, w-1);
        _y0 = clamp(_y0, 0, h-1);
        _y1 = clamp(_y1, 0, h-1);

        float x0 = (float) _x0;
        float x1 = (float) _x1;
        float y0 = (float) _y0;
        float y1 = (float) _y1;

        float dx = (float) abs(_x1-_x0);
        float dy = (float) abs(_y1-_y0);
        bool steep = (dy > dx);
        float temp = 0;

        if (dx==0.0 && dy==0.0) {
            return;
        }

        if (steep) {
            // swap x0, y0
            temp = x0;
            x0 = y0;
            y0 = temp;
            // swap x1, y1
            temp = x1;
            x1 = y1;
            y1 = temp;
        }

        if (x0 > x1) {
            // swap x0, x1
            temp = x0;
            x0 = x1;
            x1 = temp;
            // swap y0, y1
            temp = y0;
            y0 = y1;
            y1 = temp;
        }

        dx = x1 - x0;
        dy = y1 - y0;
        float gradient = 1.0;
        if (dx >= 0) {
            gradient = dy / dx;
        }

        // handle first endpoint
        float xend = xround(x0);
        float yend = y0 + gradient * (xend - x0);
        float xgap = rfpart(x0 + 0.5);
        float xpxl1 = xend;
        float ypxl1 = ipart(yend);
        if (steep) {
            plot(p, w, h, alpha, ypxl1, xpxl1, rfpart(yend) * xgap);
            plot(p, w, h, alpha, ypxl1+1.0, xpxl1, fpart(yend) * xgap);
        } else {
            plot(p, w, h, alpha, xpxl1, ypxl1, rfpart(yend) * xgap);
            plot(p, w, h, alpha, xpxl1, ypxl1+1.0, fpart(yend) * xgap);
        }
        float intery = yend + gradient; // first y-intersection for the main loop

        // handle second endpoint
        xend = xround(x1);
        yend = y1 + gradient * (xend - x1);
        xgap = fpart(x1 + 0.5);
        float xpxl2 = xend;
        float ypxl2 = ipart(yend);
        if (steep) {
            plot(p, w, h, alpha, ypxl2, xpxl2, rfpart(yend) * xgap);
            plot(p, w, h, alpha, ypxl2+1.0, xpxl2, fpart(yend) * xgap);
        } else {
            plot(p, w, h, alpha, xpxl2, ypxl2, rfpart(yend) * xgap);
            plot(p, w, h, alpha, xpxl2, ypxl2+1.0, fpart(yend) * xgap);
        }

        // main loop
        int xfrom = (int) xpxl1 + 1;
        int xto = (int) xpxl2 - 1;
        if (steep) {
            for(int x=xfrom; x<=xto; x++) {
                plot(p, w, h, alpha, ipart(intery), x, rfpart(intery));
                plot(p, w, h, alpha, ipart(intery)+1.0, x,  fpart(intery));
                intery = intery + gradient;
            }
        } else {
            for(int x=xfrom; x<=xto; x++) {
                plot(p, w, h, alpha, x, ipart(intery), rfpart(intery));
                plot(p, w, h, alpha, x, ipart(intery)+1.0, fpart(intery));
                intery = intery + gradient;
            }
        }
    }

    __kernel void getParticles(__global float *data, __global float *pData, __global float *result){
        int points = %d;
        int dw = %d;
        int dh = %d;
        float tw = %f;
        float th = %f;
        float offset = 1.0;
        float magMin = %f;
        float magMax = %f;
        float alphaMin = %f;
        float alphaMax = %f;
        float velocityMult = %f;
        float lineWidthMin = %f;
        float lineWidthMax = %f;

        // get current position
        int i = get_global_id(0);
        float dx = pData[i*2];
        float dy = pData[i*2+1];
        float doffset = 0;

        // set starting position
        float x = dx * (tw-1);
        float y = dy * (th-1);

        for(int j=0; j<points; j++) {
            // get UV value
            int lon = (int) round(dx * (dw-1));
            int lat = (int) round(dy * (dh-1));
            int dindex = lat * dw * 2 + lon * 2;
            float u = data[dindex];
            float v = data[dindex+1];

            // check for invalid values
            if (u >= 999.0 || u <= -999.0) {
                u = 0.0;
            }
            if (v >= 999.0 || v <= -999.0) {
                v = 0.0;
            }

            // calc magnitude
            float mag = sqrt(u * u + v * v);
            mag = norm(mag, magMin, magMax);

            // determine alpha transparency based on magnitude and offset
            float jp = (float) j / (float) (points-1);
            float progressMultiplier = (jp + offset + doffset) - floor(jp + offset + doffset);

            float alpha = lerp(alphaMin, alphaMax, mag * progressMultiplier);
            float thickness = lerp(lineWidthMin, lineWidthMax, mag * progressMultiplier);
            if (thickness < 1.0) thickness = 1.0;

            float x1 = x + u * velocityMult;
            float y1 = y + (-v) * velocityMult;

            // clamp y
            if (y1 < 0.0) {
                y1 = 0.0;
            }
            if (y1 > (th-1.0)) {
                y1 = th-1.0;
            }

            // check for no movement
            if (x==x1 && y==y1) {
                break;

            // check for invisible line
            } else if (alpha < 1.0) {
                // continue

            // wrap from left to right
            } else if (x1 < 0) {
                float2 intersection = lineIntersection(x, y, x1, y1, (float) 0.0, (float) 0.0, (float) 0.0, th);
                if (intersection.y > 0.0) {
                    drawLine(result, (int) round(x), (int) round(y), 0, (int) intersection.y, (int) tw, (int) th, round(alpha), (int) thickness);
                    drawLine(result, (int) round((float) (tw-1.0) + x1), (int) round(y), (int) (tw-1.0), (int) intersection.y, (int) tw, (int) th, round(alpha), (int) thickness);
                }

            // wrap from right to left
            } else if (x1 > tw-1.0) {
                float2 intersection = lineIntersection(x, y, x1, y1, (float) (tw-1.0), (float) 0.0, (float) (tw-1.0), th);
                if (intersection.y > 0.0) {
                    drawLine(result, (int) round(x), (int) round(y), (int) (tw-1.0), (int) intersection.y, (int) tw, (int) th, round(alpha), (int) thickness);
                    drawLine(result, (int) round((float) x1 - (float)(tw-1.0)), (int) round(y), 0, (int) intersection.y, (int) tw, (int) th, round(alpha), (int) thickness);
                }

            // draw it normally
            } else {
                drawLine(result, (int) round(x), (int) round(y), (int) round(x1), (int) round(y1), (int) tw, (int) th, round(alpha), (int) thickness);
            }

            // wrap x
            x1 = wrap(x1, 0.0, tw-1);
            dx = x1 / tw;
            dy = y1 / th;

            x = x1;
            y = y1;
        }
    }
    """ % (brightnessFactor, w, dw, dh, tw, th, magRange[0], magRange[1], alphaRange[0], alphaRange[1], velocityMultiplier, lineWidthRange[0], lineWidthRange[1])

    # Get platforms, both CPU and GPU
    plat = cl.get_platforms()
    GPUs = plat[0].get_devices(device_type=cl.device_type.GPU)
    CPU = plat[0].get_devices()

    # prefer GPUs
    if GPUs and len(GPUs) > 0:
        # print "Using GPU"
        ctx = cl.Context(devices=GPUs)
    else:
        print "Warning: using CPU"
        ctx = cl.Context(CPU)

    # Create queue for each kernel execution
    queue = cl.CommandQueue(ctx)
    mf = cl.mem_flags

    # Kernel function instantiation
    prg = cl.Program(ctx, src).build()

    inData =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=fData)
    inPData =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=pData)
    outResult = cl.Buffer(ctx, mf.WRITE_ONLY, result.nbytes)

    prg.getParticles(queue, (h, ), None, inData, inPData, outResult)

    # Copy result
    cl.enqueue_copy(queue, result, outResult)

    result = result.reshape((th, tw))
    result = result.astype(np.uint8)

    return result

def offsetData(data, w, h, offset=0):
    dim = 2
    result = np.empty(h * w * dim, dtype=np.float32)

    # the kernel function
    src = """
    __kernel void offsetData(__global float *dataIn, __global float *result){
        int w = %d;
        int dim = %d;
        int offsetX = %d;

        // get current position
        int posx = get_global_id(1);
        int posy = get_global_id(0);

        // convert position from 0,360 to -180,180
        int posxOffset = posx;
        if (offsetX > 0 || offsetX < 0) {
            if (posx < offsetX) {
                posxOffset = posxOffset + offsetX;
            } else {
                posxOffset = posxOffset - offsetX;
            }
        }

        // get indices
        int i = posy * w * dim + posxOffset * dim;
        int j = posy * w * dim + posx * dim;

        // set result
        result[j] = dataIn[i];
        result[j+1] = dataIn[i+1];
    }
    """ % (w, dim, offset)

    # Get platforms, both CPU and GPU
    plat = cl.get_platforms()
    GPUs = plat[0].get_devices(device_type=cl.device_type.GPU)
    CPU = plat[0].get_devices()

    # prefer GPUs
    if GPUs and len(GPUs) > 0:
        ctx = cl.Context(devices=GPUs)
    else:
        print "Warning: using CPU"
        ctx = cl.Context(CPU)

    # Create queue for each kernel execution
    queue = cl.CommandQueue(ctx)
    mf = cl.mem_flags

    # Kernel function instantiation
    prg = cl.Program(ctx, src).build()

    dataIn =  cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=data)
    outResult = cl.Buffer(ctx, mf.WRITE_ONLY, result.nbytes)

    prg.offsetData(queue, [h, w], None , dataIn, outResult)

    # Copy result
    cl.enqueue_copy(queue, result, outResult)

    return result

def pseudoRandom(seed):
    random.seed(seed)
    return random.random()

def roundInt(v):
    return int(round(v))
