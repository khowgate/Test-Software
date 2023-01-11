from PIL import Image
from statistics import mean

filename = 'capt0008.jpg'
filepath = f"{filename}"

# Load the original image, and get its size and color mode.
orig_image = Image.open(filepath)
width, height = orig_image.size
mode = orig_image.mode

# Show information about the original image.
print(f"Original image: {filename}")
print(f"Size: {width} x {height} pixels")
print(f"Mode: {mode}")

# Load all pixels from the image.
orig_pixel_map = orig_image.load()


crop = 50
x_offset = 21
y_offset = 10
width_crop_centre = int(x_offset+(width/2) - crop/2)
height_crop_centre = int(y_offset+(height/2) - crop/2)
new_image = Image.new('RGB' ,(crop,crop))
new_pixel_map = new_image.load()

r = []
g = []
b = []

# Examine the 100 pixels in the top left corner of the image.
print("\nPixel data:")
# Modify each pixel in the new image.
for x in range(crop):
    for y in range(crop):
        # Grab the current pixel, and the component RGB values.
        orig_pixel = orig_pixel_map[x+width_crop_centre, y+height_crop_centre]
        orig_r = orig_pixel[0]
        orig_g = orig_pixel[1]
        orig_b = orig_pixel[2]

        # Copy this data over to the corresponding pixel in the new image.
        new_r = orig_r
        new_g = orig_g
        new_b = orig_b
        new_pixel = (new_r, new_g, new_b)
        new_pixel_map[x, y] = new_pixel
        r.append(new_pixel[0])
        g.append(new_pixel[1])
        b.append(new_pixel[2])

stats = [mean(r),
         mean(g),
         mean(b)
    ]
print(stats)
new_image.show()