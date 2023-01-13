from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from influxdb_client import InfluxDBClient, Point, WritePrecision
import matplotlib.pyplot as plt
import influxdb_client, os, time
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime

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