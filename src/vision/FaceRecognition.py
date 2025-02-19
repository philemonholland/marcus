import cv2
import threading
import numpy as np

def detect_profiles_combined(gray, face_cascade, profile_cascade):


    face = face_cascade.detectMultiScale(gray, scaleFactor=1.07, minNeighbors=15, minSize=(30, 30))

    # Detect profiles in the original image
    profiles = profile_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=20, minSize=(30, 30))

    # Detect profiles in the flipped image
    flipped_gray = cv2.flip(gray, 1)
    flipped_profiles = profile_cascade.detectMultiScale(flipped_gray, scaleFactor=1.08, minNeighbors=20, minSize=(30, 30))

    # Adjust coordinates of flipped profiles to match the original image
    flipped_width = gray.shape[1]
    flipped_profiles_adjusted = [(flipped_width - x - w, y, w, h) for (x, y, w, h) in flipped_profiles]

    # Combine detections and remove duplicates
    combined_profiles = list(face) + list(profiles) + flipped_profiles_adjusted
    unique_profiles = remove_duplicates(combined_profiles)

    return unique_profiles

def remove_duplicates(profiles, threshold=100):
    """
    Removes duplicate detections based on proximity.
    Args:
        profiles: List of profile rectangles (x, y, w, h).
        threshold: Maximum distance between rectangles to consider them duplicates.
    Returns:
        List of unique profiles.
    """
    if not profiles:
        return []
    profiles_array = np.array(profiles)
    unique = []
    for profile in profiles_array:
        if all(np.linalg.norm(profile[:2] - np.array(u[:2])) > threshold for u in unique):
            unique.append(profile)
    return unique


def draw_rectangles(frame, detections, color, height=None):
    for (x, y, w, h) in detections:
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        if height is not None:
            center_x = x + w // 2
            center_y = y + h // 2
            position_text = f"X: {center_x}, Y: {height-center_y}"
            cv2.putText(frame, position_text, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

def draw_flipped_rectangles(frame, detections, color):
    for (x, y, w, h) in detections:
        x = frame.shape[1] - (x + w)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

def main():
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml')
    profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
    stream = cv2.VideoCapture(0)

    if not stream.isOpened():
        print("No stream :(")
        exit()

    while True:
        ret, frame = stream.read()
        if not ret:
            print("No more stream :(")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # faces = (detect_faces(gray, face_cascade))
        profiles = detect_profiles_combined(gray, face_cascade, profile_cascade)
        # flipped_gray = cv2.flip(gray, 1)
        # flipped_profiles = detect_flipped_profiles(flipped_gray, profile_cascade)
        height = frame.shape[0]

        # draw_rectangles(frame, faces, (255, 0, 0), height)
        draw_rectangles(frame, profiles, (0, 255, 0),height)
        # draw_flipped_rectangles(frame, flipped_profiles, (0, 255, 255))

        cv2.imshow('Face and Profile Detection', frame)

        if cv2.waitKey(1) != -1:
            break

    stream.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()