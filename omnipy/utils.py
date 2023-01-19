import PySimpleGUI as sg
from PIL import Image, ImageTk
import io
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from influxdb_client import Point
import matplotlib.pyplot as plt
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime


def LEDIndicator(key=None, radius=30):
    return sg.Graph(canvas_size=(radius, radius),
             graph_bottom_left=(-radius, -radius),
             graph_top_right=(radius, radius),
             pad=(0, 0), key=key)

def get_img_data(f, maxsize=(800, 600), first=False):
    """Generate image data using PIL
    """
    img = Image.open(f)
    img.thumbnail(maxsize)
    if first:                     # tkinter is inactive the first time
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        del img
        return bio.getvalue()
    return ImageTk.PhotoImage(img)

class figure_tools:
    def __init__(self, window):
        self.window=window
    
    def draw_figure(self, canvas, figure, loc=(0, 0)):
        plt.close()
        figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        return figure_canvas_agg
    
    def delete_figure_agg(self, figure_agg):
        figure_agg.get_tk_widget().forget()
        plt.close('all')
    
    def SetLED(self, key, color):
        graph = self.window[key]
        graph.erase()
        graph.draw_circle((0, 0), 12, fill_color=color, line_color=color)
        #print('Colour Change')

        
    def LogDisp(self, key, txt):
        disp = self.window[key]
        print(txt)
        if key == '-LOG-':
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            err = txt
            try:
                disp.update(value=('['+current_time+']  '+str(err['txt'])))
            except:
                disp.update(value=('['+current_time+']  '+repr(err)))
        else:
            disp.update(value = txt)


class db_tools:
   
    def __init__(self, url, token, test_ID):
        org = "Omnidea Ltd."
        client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)
        self.write_api = client.write_api(write_options=SYNCHRONOUS)
        self.test = test_ID

    def db_write(self, point, field, data):
        # print(data)
        try:
            point = (
              Point(point)
              .field(field, float(data))
            )
        except:
            point = (
              Point(point)
              .field(field, float(data[0]))
            )
        # print('point created')
        self.write_api.write(bucket=self.test, org="Omnidea Ltd.", record=point)
        # print('write Complte')