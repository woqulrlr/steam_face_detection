import cv2
import time
import json
import base64
import requests
import multiprocessing as mp


# Ali detect person server config
# headers
headers = {'Content-Type':'application/x-www-form-urlencoded'}
# url
url = 'http://10.128.111.148:3360/algorithm/image/detect'
# detection_threshold
DETECTION_THRESHOLD = 0.5

# Capture camera config
# detection GAP time
GAP = 10
# start time
start_time = time.time()
# frame counter, set in image_put()
frame_counter = 0

def detect_person(frame):
    # convert img to base64 format
    base64_str = cv2.imencode('.jpg',frame)[1].tostring()
    base64_str = base64.b64encode(base64_str).decode('utf-8')
    # request ali cv server to detect person
    data = json.dumps({"data":{"content":base64_str,"type":"person"}})
    response = requests.post(url=url, data=data, headers=headers)
    # process data format
    bounding_box_list = response.json()['data']
    result_list = [objTypeScore > DETECTION_THRESHOLD for objTypeScore in [i['objTypeScore'] for i in bounding_box_list]]
    # exist person 1, don't exist person 0
    result = '1' if True in result_list else '0'
    return result, bounding_box_list

def connect_camera(info, channel):
    if 'dahua' == info[3]:
        cap = cv2.VideoCapture("rtsp://%s:%s@%s/cam/realmonitor?channel=%d&subtype=0" % (info[1], info[2], info[0], channel))
    elif 'hiki' == info[3]:
        cap = cv2.VideoCapture("rtsp://%s:%s@%s//Streaming/Channels/%d" % (info[1], info[2], info[0], channel))  # HIKIVISION new version 2017
    return cap


def image_put(q, info, channel=1):
    frame_counter = 0
    cap = connect_camera(info, channel)
    if cap.isOpened():
        print('CameraIsOpened')
    else:
        # re-connect
        cap = connect_camera(info, channel)
        print('connect camera succes')

    while True:
        # count the frame
        frame_counter = frame_counter + 1
        try:
            # detect frame
            if frame_counter%(GAP*25)==0:
                print('image put:', info, q.qsize(), cap.read()[1].shape)
                q.put(cap.read()[1])
                q.get() if q.qsize() > 1 else time.sleep(0.01)
            # discard frame
            else:
                cap.grab()
        except:
            # re-connect
            cap = connect_camera(info, channel)
        
        


def image_get(queues, camera_info_l):
    while True:
        result_list = []
        for queue, camera_info in zip(queues, camera_info_l):
            frame = queue.get()
            result, bounding_box_list = detect_person(frame)
            # extract crop images
            try:
                crop_image = [box['cropImage'] for box in bounding_box_list]
            except:
                crop_image = []
            # handle output data format
            result = {
                'result':result,
                'crop_image':crop_image,
                'room_name':camera_info[-1],
            }
            result_list.append(result)
            # TODO, send the result_list via post 
            '''write code here'''
            print(result_list)


def run_multi_camera():
    camera_info_l = [
        ["172.16.143.10","admin", "admin@123", 'dahua', 'test-room']
    ]

    mp.set_start_method(method='spawn')  # init
    queues = [mp.Queue(maxsize=4) for _ in camera_info_l]

    # create and put process in the list
    processes = [mp.Process(target=image_get, args=(queues, camera_info_l))]

    # create and put process in the list
    for queue, camera_info in zip(queues, camera_info_l):
        processes.append(mp.Process(target=image_put, args=(queue, camera_info)))

    for process in processes:
        process.daemon = True
        process.start()
    for process in processes:
        process.join()

if __name__ == '__main__':
    run_multi_camera()




