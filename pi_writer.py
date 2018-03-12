from imutils.video.pivideostream import PiVideoStream
from picamera.array import PiRGBArray
from picamera import PiCamera
from imutils.video.webcamvideostream import WebcamVideoStream
from Xlib.display import Display
from Xlib import X
from threading import Thread
from queue import Queue
import argparse
import imutils
import time
import cv2
import os

q = Queue()
out_name = "result"
buffer_name = "temp"


def main(args):
    # created a *threaded *video stream, allow the camera sensor to warmup,
    # and start the FPS counter
    vs = PiVideoStream().start() if args["picamera"] else WebcamVideoStream().start()
    print("[INFO] warming up camera...")
    time.sleep(2.0)

    # initialize the FourCC, video writer, dimensions of the frame, and
    # zeros array
    writer = None
    temp = list()
    counter = 0
    timeframe = 0
    cv2.namedWindow("Frame", cv2.WINDOW_NORMAL)
    params = {
        "name": "",
        "fourcc": cv2.VideoWriter_fourcc(*args["codec"]),
        "fps": args["fps"],
        "w": None,
        "h": None
    }

    prefix = os.path.join(args["output"], out_name)
    # loop over some frames...this time using the threaded stream
    while True:
        # grab the frame from the threaded video stream and resize it
        # to have a maximum width of 400 pixels
        frame = vs.read()
        frame = imutils.resize(frame, width=400)

        params["name"] = prefix + "_" + str(timeframe) + "." + args["type"]
        if writer is None:
            # store the image dimensions, initialzie the video writer,
            # and construct the zeros array
            (params["h"], params["w"]) = frame.shape[:2]
            writer = cv2.VideoWriter(params["name"], params["fourcc"],
                                     params["fps"], (params["w"], params["h"]), True)

        if counter >= params["fps"] * args["length"]:
            temp.pop(0)
        else:
            counter += 1
        temp.append(frame)

        if not q.empty():
            flag = q.get()
            if flag == 0:
                writer.release()
                break
            click(temp, writer, params)
            timeframe += 1

        # check to see if the frame should be displayed to our screen
        if args["display"]:
            cv2.imshow("Frame", frame)

    print("[INFO] cleaning up...")
    cv2.destroyAllWindows()
    vs.stop()
    print("[INFO] done")


def watcher(dis):
    while True:
        start = time.time()
        event = dis.next_event()
        if event.type == X.ButtonPress and event.detail == 1:
            if time.time() - start > 5:
                q.put(1)
                print(q.empty())
        elif event.type == X.KeyPress and event.detail == 24:
            q.put(0)
            break


def click(temp, writer, params):
    if writer is not None:
        for img in temp:
            writer.write(img)
    writer.release()
    return cv2.VideoWriter(params["name"], params["fourcc"],
                                     params["fps"], (params["w"], params["h"]), True)


if __name__ == "__main__":
    # construct the argument parse and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", required=True,
                        help="path to output video directory")
    parser.add_argument("-p", "--picamera", type=bool,
                        help="whether or not the Raspberry Pi camera should be used")
    parser.add_argument("-f", "--fps", type=int, default=30,
                        help="FPS of output video")
    parser.add_argument("-c", "--codec", type=str, default="MJPG",
                        help="codec of output video")
    parser.add_argument("-t", "--type", type=str, default="avi",
                        help="video file type to save")
    parser.add_argument("-l", "--length", type=int, default=30,
                        help="length of seconds of summary")
    parser.add_argument("-d", "--display", type=bool,
                        help="Whether or not frames should be displayed")

    arg = vars(parser.parse_args())

    os.system("rm -rf %s" % arg["output"])
    os.system("rm -rf %s" % arg["buffer"])
    os.makedirs(arg["output"])
    os.makedirs(arg["buffer"])
    display = Display(':0')
    root = display.screen().root
    root.grab_pointer(True, X.ButtonPressMask | X.ButtonReleaseMask, X.GrabModeAsync,
                      X.GrabModeAsync, 0, 0, X.CurrentTime)
    root.grab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime)
    watcher_thread = Thread(target=watcher, args=(display, ))
    main_thread = Thread(target=main, args=(arg, ))
    watcher_thread.start()
    main_thread.start()

