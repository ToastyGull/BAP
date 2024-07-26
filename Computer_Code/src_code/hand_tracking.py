import mediapipe as mp
import numpy as np
import cv2
#hand tracking code
#updates------
#lateral angle calculation assuming forward orientation

#cameras
front_cam = cv2.VideoCapture(0)
back_cam = None #cv2.VideoCapture(1)

#files
#change directory to where the angle and dictionary text files are
transmission_file = r"C:\Users\adria\Downloads\bionic_arm_proj\data\angle_list.txt"
validation_file = r"C:\Users\adria\Downloads\bionic_arm_proj\data\dictionary.txt"

#hand initialisation
mp_draw = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands
front_hand = mp_hands.Hands(min_detection_confidence=0.9, min_tracking_confidence=0.9)
back_hand = mp_hands.Hands(min_detection_confidence=0.9, min_tracking_confidence=0.9)

finger_dictionary = {
    'Thumb' : [4, 3, 2, 1],
    'Index' : [8, 7, 6, 5], 
    'Middle': [12, 11, 10, 9], 
    'Ring'  : [16, 15, 14, 13],
    'Pinky' : [20, 19, 18, 17],
}

#-----------------------------------------------------------------------------------#
#                                   Write File
#
#-----------------------------------------------------------------------------------#
def clear_files():
    try:
        open(transmission_file, 'w').close()
        open(validation_file, 'w').close()
    except Exception as e:
        print(f'An error occured in clearing files: {e}')

def write_angles(angles):
    try:
        if not angles:
            clear_files()
            return
        
        #validate angles written to transmission are the same here
        with open(validation_file, 'w') as file:
            for finger, angle in angles.items():
                file.write(f"{finger}: A={angle['A']}, B={angle['B']}, C={angle['C']}, lat={angle['lat']}\n")

        #we are omitting the thumb for now and also angle A, need to experiment which angles to use
        angle_list = [value for finger, angle_dictionary in angles.items() if finger != 'Thumb'
                    for value in (angle_dictionary['A'], angle_dictionary['B'], angle_dictionary['lat'])]
        
        #write angles to file for bluetooth to read
        with open(transmission_file, 'w') as file:
            file.write(','.join(map(str, angle_list)))
    except Exception as e:
        print(f'An error occured in writing angles: {e}')
        return

#-----------------------------------------------------------------------------------#
#                                Validation functions
#
#-----------------------------------------------------------------------------------#
def is_cam_available(cam):
    try:
        return cam.isOpened()
    except Exception as e:
        print(f'An error occured in is_cam_available: {e}')
        return False
#----------------------------------#
def is_landmark_detected(landmark):
    try:
        return (landmark is not None and
                0 <= landmark.x <= 1 and 
                0 <= landmark.y <= 1 and 
                landmark.z != 0) 
    except Exception as e:
        print(f'An error occured in is_landmark_detected: {e}')
        return False

#-----------------------------------------------------------------------------------#
#                            Angle calculation functions
#
#-----------------------------------------------------------------------------------#
def mirror_x(landmark):
    try:
        return type(landmark)(x=1-landmark.x, y=landmark.y, z=landmark.z)
    except Exception as e:
        print(f'An error occured in mirroring: {e}')
        return None

def rotate_coordinates(landmark, angle_degrees=260):
    angle_radians = np.radians(angle_degrees)
    rotation_matrix = np.array([
        [1, 0, 0],
        [0, np.cos(angle_radians), -np.sin(angle_radians)],
        [0, np.sin(angle_radians), np.cos(angle_radians)]
    ])
    coordinates = np.array([landmark.x, landmark.y, landmark.z])
    rotated_coordinates = np.dot(rotation_matrix, coordinates)
    return type(landmark)(x=rotated_coordinates[0], y=rotated_coordinates[1], z=rotated_coordinates[2])  

def calculate_lateral_angle(pip, base, hand_type):
    try:
        if not all([pip, base]):
            return 90
        
        i = np.array([1, 0, 0])
        # j = np.array([0, 1, 0])
        # k = np.array([0, 0, 1])

        #only rotate it coords here, but that means you need to remember lateral angle is calculated in
        #a different dimension and orientation compared to the joint angles
        rotated_pip = rotate_coordinates(pip)
        rotated_base = rotate_coordinates(base)
        finger_vector = np.array([rotated_pip.x - rotated_base.x, 0, rotated_pip.z - rotated_base.z])
        magnitude = np.linalg.norm(finger_vector)

        if magnitude == 0:
            return 90
        
        unit_finger_vector = finger_vector / magnitude #  unit_a = (a / |a|)
        dot_product = np.dot(unit_finger_vector, i)
        angle = np.degrees(np.arccos(np.clip(dot_product, -1.0, 1.0)))
        capped_angle = max(60, min(120, angle)) #make min lateral bend 60 and max 120

        if hand_type == "Right":
            capped_angle = abs(180 - capped_angle) #make angle the same no matter what hand is detected

        return capped_angle

    except Exception as e:
        print(f'An error occured in calculating lateral angle: {e}')
        return 90

def calculate_angle(p1, p2, p3):
    try:
        if not all([p1, p2, p3]): #if one point is missing we can't calculate
            return 180
        
        v1 = np.array([p1.x - p2.x, p1.y - p2.y, p1.z - p2.z])
        v2 = np.array([p3.x - p2.x, p3.y - p2.y, p3.z - p2.z])
        magnitude_1 = np.linalg.norm(v1)
        magnitude_2 = np.linalg.norm(v2)

        if magnitude_1 == 0 or magnitude_2 == 0:
            return 180

        cosine_angle = np.dot(v1, v2) / (magnitude_1 * magnitude_2)
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0)) 
        degree = np.degrees(angle)
        return max(0, min(180, degree)) 
    
    except Exception as e:
        print(f'An error occured in calculate angle: {e}')
        return 180

def calculate_finger_angles(detected_landmarks, hand_type, is_back_camera=False):
    try:
        finger_angles = {}
        for finger, finger_landmarks in finger_dictionary.items():
            landmark = []
            for lm in finger_landmarks:
                if is_landmark_detected(detected_landmarks[lm]):
                    valid_lm = detected_landmarks[lm]
                    mirrored_lm = mirror_x(valid_lm) if is_back_camera else valid_lm
                    landmark.append(mirrored_lm)
                else:
                    landmark.append(None) #if its invalid, then populate it as none 

            if all(landmark): #we do not need to check if len(landmark) == 4 because every iteration of loop will be 4 elements
                tip, a, b, c = landmark 
                angle_a = calculate_angle(tip, a, b)
                angle_b = calculate_angle(a, b, c)
                angle_c = calculate_angle(b, c, detected_landmarks[0]) #[0] is wrist
                lateral_angle = calculate_lateral_angle(b, c, hand_type)
                finger_angles[finger] = {'A': int(angle_a), 'B' : int(angle_b), 'C' : int(angle_c), 'lat': int(lateral_angle)}
            else:
                finger_angles[finger] = {'A': 180, 'B': 180, 'C': 180, 'lat': 90}
        return finger_angles
    
    except Exception as e:
        print(f'An error occured in calculating finer angles: {e}')
        return {}

def average_angles(front, back):
    try:
        finger_order = [finger for finger, _ in finger_dictionary.items()]
        averaged_angles = {}
        for finger in finger_order:
            if finger in front and finger in back:
                averaged_angles[finger] = {
                    'A': (front[finger]['A'] + back[finger]['A']) // 2,
                    'B': (front[finger]['B'] + back[finger]['B']) // 2,
                    'C': (front[finger]['C'] + back[finger]['C']) // 2,
                    'lat': (front[finger]['lat'] + back[finger]['lat'] // 2)
                }
            #elif the finger is only captured in either front or back,
            #just use that orientation's angles
            elif finger in front:
                averaged_angles[finger] = front[finger]
            elif finger in back:
                averaged_angles[finger] = back[finger]
        return averaged_angles
    
    except Exception as e:
        print(f'An error occured in average_angles: {e}')
        return {}

#-----------------------------------------------------------------------------------#
#                                 Camera functions
#
#-----------------------------------------------------------------------------------#
def process_frame(frame, hand):
    try:   
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        captured_landmarks = hand.process(frame_rgb)
        return captured_landmarks.multi_hand_landmarks, captured_landmarks.multi_handedness
    except Exception as e:
        print(f'An error occured in process frame: {e}')
        return None, None

def cap_hand(cam, hand, orientation, is_back_camera=False):
    try:
        ret, frame = cam.read()
        angles = {}
        hand_type = None
        if ret:
            hand_obj_list, type = process_frame(frame, hand)
            if hand_obj_list:
                hand = hand_obj_list[0]
                hand_type = type[0].classification[0].label
                angles = calculate_finger_angles(hand.landmark, hand_type, is_back_camera) 
                mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
                #note that the hand type it detects is actually wrong, idk why that is... bad ai >.>
                cv2.putText(frame, f"Hand: {hand_type}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow(f'{orientation} Camera', frame)
        return angles
    
    except Exception as e:
        print(f'An error occured in cap_hand: {e}')
        return {}

def capture_loop():
    try:
        while True:
            angles = {}
            if front_cam:
                if is_cam_available(front_cam):
                    angles['front'] = cap_hand(front_cam, front_hand, 'Front')

            if back_cam: 
                if is_cam_available(back_cam):
                    angles['back'] = cap_hand(back_cam, back_hand, 'Back', is_back_camera=True) 

            if angles:
                if 'front' in angles.keys() and 'back' in angles.keys():
                    angles_to_write = average_angles(angles['front'], angles['back'])
                elif 'front':
                    angles_to_write = angles['front']
                elif 'back':
                    angles_to_write = angles['back']
                
                if angles_to_write:
                    write_angles(angles_to_write)
                
                else:
                    write_angles({})

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except Exception as e:
        print(f'An error occured in capture_loop: {e}')

#-----------------------------------------------------------------------------------#
#                                  Main Thread
#
#-----------------------------------------------------------------------------------#
def main():
    try:
        print('Starting...')
        capture_loop()
    except Exception as e:
        print(f'An error occured in main: {e}')
    finally:
        if front_cam:
            front_cam.release()
        if back_cam:
            back_cam.release()
        cv2.destroyAllWindows()
        clear_files()

if __name__ == '__main__':
    main()
    print('Program complete xx')
