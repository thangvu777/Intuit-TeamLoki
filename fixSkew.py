import pytesseract
from pytesseract import Output
import time
import cv2
import os
import numpy as np
import math
import PIL

def process (directory : str, outD:str) -> None:
    for filename in sorted(os.listdir(directory)):
        start_time = time.time()
        if filename.endswith('.jpg'):
            file = os.path.join(directory, filename)
            print('Fixing Skew of %s: ' %(file))
            fix_skew(file)
        else:
            continue
        end_time = time.time()
        total = end_time - start_time
        print('========================================================')
        print('%s took %.2f seconds to finish.' % (filename, total))
        print('========================================================')

# Fix text skew of an image
def fix_skew(img: str):
    fix_skew_helper(img)

''' 
    Fix skew helper:
    1. Find the biggest contour outline of a given image
    2. Get the dimensions of the image using shape
    3. Find the approximate Cartesian coordinates of the image  
    4. Calculate the angle between 3 points (2 points from the image, 1 from (0,0))
    5. Check for straight image, if image is crooked, rotation will occur
    6. Rotate and crop the image using the center of the original image
'''
def fix_skew_helper(img: str):
    # save path string
    path = img

    # load image
    img = cv2.imread(img)

    # convert to gray
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # threshold image
    thresh = cv2.threshold(gray, 4, 255, 0)[1]

    # apply morphology open to smooth the outline
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # find all contours
    cntrs = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cntrs = cntrs[0] if len(cntrs) == 2 else cntrs[1]

    # STEP 1: find biggest contour to outline the W2 form
    area_thresh = 0
    for c in cntrs:
        area = cv2.contourArea(c)
        if area > area_thresh:
            area = area_thresh
            big_contour = c

    '''
    # Uncomment if you want to see the contour lines
    # (RED) draw the contour on a copy of the input image
    results = img.copy()
    cv2.drawContours(results, [big_contour], 0, (0, 0, 255), 2)
    out = str('Contouring     ' + path)
    cv2.imshow(out, results)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    '''

    # STEP 2: get dimensions of image
    dimensions = img.shape
    height = img.shape[0]
    width = img.shape[1]
    print ("w: %d h: %d" %(width, height))
    # STEP 3: Find approximate coordinates of outlining box
        # .05 approx level gives us the 4 coordinates of the W-2 Rectangular shape
    approx = cv2.approxPolyDP(big_contour, .05 * cv2.arcLength(big_contour, True), True)
    # Used to flatten the array containing the co-ordinates of the vertices.
    n = approx.ravel()
    i = 0
    points = []
    for j in n:
        if (i % 2 == 0):
            x = n[i]
            y = n[i + 1]
        i = i + 1
        points.append([x,y])
        #print(x,y)

    # STEP 4: Calculate degree of rotation
    # FUNCTION DEFINITION: Calculate an angle given 3 Cartesian coordinates
    def getAngle(a, b, c):
        ang = math.degrees(math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(a[1] - b[1], a[0] - b[0]))
        return ang + 360 if ang < 0 else ang

    '''
    This is for images that don't necessarily need to be rotated since they already stand correctly
         .00166 is equal to 1/600
         ex. Original Dimensions (w x h): 2005 x 2340
         1/600 * (2005) = 3.33; 1/600 * (2340) = 3.88
         If one of the vertices of the image lies at approximately 2004 x 2339
         the image is most likely straight because the absolute difference is 1 pixel apart 
    '''
    if (abs(width - points[4][0]) <= .00166 * width and abs(height - points[4][1] <= .00166 * height)):
        angle = 0
    else: # Rotation needs to occur
        # This is for images rotated counter-clockwise originally with respect to the center
        # X1 > Y2: ex. P1 = (1221,0); P2 = (0,172) -> True
        if (points[0][0] >= points[2][1]):
            angle = (getAngle([0, 0], points[0], points[2]))
        # This is for images rotated clockwise originally with respect to the center
        # X1 < Y1: ex. P1 = (405,0); P2 = (0,2303) -> True
        elif (points[0][0] < points[2][1]):
            angle = (getAngle([0, 0], points[0], points[2])) + 90
    #print('angle = %.3f' % angle)

    # STEP 5: Rotate and Crop
    # FUNCTION DEFINITION: Rotate a given image around the center with angle theta in degrees,
    # then the image is cropped according to width and height.
    def rotate(image, center: int, theta: float, width: int, height: int):
        # Uncomment to use theta instead
        # theta *= 180/np.pi

        shape = (image.shape[1], image.shape[0])  # cv2.warpAffine expects shape in (length, height)

        matrix = cv2.getRotationMatrix2D(center=center, angle=theta, scale=1)
        image = cv2.warpAffine(src=image, M=matrix, dsize=shape)

        x = int(center[0] - width / 2)
        y = int(center[1] - height / 2)

        image = image[y:y + height, x:x + width]
        return image

    rotated_image = rotate(img, center=(width/2, height/2), theta=angle, width= width, height=height)

    '''
     # Uncomment if you want to see the rotated image
    out = str('Rotated     ' + path)
    cv2.imshow(out, rotated_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    '''
    # Return the final rotated image
    return rotated_image

if __name__ == '__main__':
    dir = 'data/fake-w2-us-tax-form-dataset/w2_samples_multi_noisy'
    outD = 'data/skewed/rotatefix'
    if not os.path.exists(outD):
        os.mkdir(outD)
    #img = fix_skew('data/skewed/W2_Multi_Sample_Data_input_ADP1_noisy_15677.jpg')
    process('data/fake-w2-us-tax-form-dataset/w2_samples_multi_noisy','out')
